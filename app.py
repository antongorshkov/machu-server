import os
import json
import logging
import requests
import threading
import time
from logtail import LogtailHandler
from flask import Flask, render_template, request, send_from_directory, jsonify
from dotenv import load_dotenv
from morning_message import main
from form_submit import form_submit, add_to_group
from message_receive import message_receive

# Load environment variables from .env file
if os.getenv('FLASK_ENV') != 'production':
    load_dotenv()

app = Flask(__name__, static_folder='static')

# In-memory cache dictionary for directory data
directory_cache = {
    "data": None,
    "last_updated": 0,
    "updating": False
}

# Cache expiry time (5 minutes)
CACHE_EXPIRY = 5 * 60  # seconds
app.config['RAPID_API_KEY'] = os.getenv('RAPID_API_KEY')
app.config['ABSTRACT_API_KEY'] = os.getenv('ABSTRACT_API_KEY')
app.config['MORNING_MESSAGE_PHONE_NUM'] = os.getenv('MORNING_MESSAGE_PHONE_NUM')
app.config['LOGTAIL_TOKEN'] = os.getenv('LOGTAIL_TOKEN')
app.config['MACHUKITA_TEST_GID'] = os.getenv('MACHUKITA_TEST_GID')
app.config['MV_ADMINS_GID'] = os.getenv('MV_ADMINS_GID')
app.config['AMBIENT_APPLICATION_KEY'] = os.getenv('AMBIENT_APPLICATION_KEY')
app.config['AMBIENT_API_KEY'] = os.getenv('AMBIENT_API_KEY')
app.config['MV_NEIGHBORS_GROUP_ID'] = os.getenv('MV_NEIGHBORS_GROUP_ID')
app.config['MACHUKITA_TEST_GROUP_ID'] = os.getenv('MACHUKITA_TEST_GROUP_ID')
app.config['OPENAI_API_KEY'] = os.getenv('OPENAI_API_KEY')
app.config['OPENAI_ASSISTANT_ID'] = os.getenv('OPENAI_ASSISTANT_ID')
app.config['OPENAI_ASSISTANT_ID_PUNCT'] = os.getenv('OPENAI_ASSISTANT_ID_PUNCT')
app.config['MY_WA_NUMBER'] = os.getenv('MY_WA_NUMBER')
app.config['MACHU_NUMBER'] = os.getenv('MACHU_NUMBER')

# Airtable configuration
app.config['AIRTABLE_API_KEY'] = os.getenv('AIRTABLE_API_KEY')  # New modern API key name
app.config['AIRTABLE_TOKEN'] = os.getenv('AIRTABLE_TOKEN')      # Legacy token name
app.config['AIRTABLE_BASE_ID'] = os.getenv('AIRTABLE_BASE_ID')
app.config['AIRTABLE_TABLE_NAME'] = os.getenv('AIRTABLE_TABLE_NAME', 'main-directory')

handler = LogtailHandler(source_token=app.config['LOGTAIL_TOKEN'])
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.handlers = []
logger.addHandler(handler)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s:%(levelname)s:%(message)s"
)

@app.route("/add_to_group", methods=['GET'])
def add2group():
    phone_number = request.args.get('phoneNumber')
    return add_to_group(phone_number)

@app.route("/")
def hello_world():
    return render_template("index.html")

def fetch_directory_data_from_airtable():
    """Fetch data from Airtable and update the cache"""
    # Set updating flag to prevent multiple simultaneous updates
    directory_cache["updating"] = True
    
    try:
        airtable_token = app.config.get('AIRTABLE_API_KEY') or app.config.get('AIRTABLE_TOKEN')
        airtable_base_id = app.config.get('AIRTABLE_BASE_ID', 'appU0yK4n5WOdzSDU')
        airtable_table_name = app.config.get('AIRTABLE_TABLE_NAME', 'main-directory')
        
        airtable_url = f"https://api.airtable.com/v0/{airtable_base_id}/{airtable_table_name}"
        headers = {"Authorization": f"Bearer {airtable_token}"}
        
        logger.info("Refreshing directory data from Airtable")
        response = requests.get(airtable_url, headers=headers)
        
        if response.status_code == 200:
            # Update cache
            directory_cache["data"] = response.json()
            directory_cache["last_updated"] = time.time()
            logger.info("Directory cache refreshed successfully")
        else:
            logger.error(f"Failed to refresh directory data. Status code: {response.status_code}")
    except Exception as e:
        logger.error(f"Error refreshing directory data: {str(e)}")
    finally:
        # Clear updating flag
        directory_cache["updating"] = False

@app.route("/get_directory_data")
def get_directory_data():
    """Get directory data, with auto-refresh on stale cache"""
    current_time = time.time()
    
    # Check if cache needs refreshing (expired or empty)
    cache_age = current_time - directory_cache["last_updated"]
    if (directory_cache["data"] is None or cache_age > CACHE_EXPIRY) and not directory_cache["updating"]:
        # Start a background thread to refresh cache
        # This prevents blocking the current request
        refresh_thread = threading.Thread(target=fetch_directory_data_from_airtable)
        refresh_thread.daemon = True
        refresh_thread.start()
        
        # If we have existing data, use it while refresh happens in background
        if directory_cache["data"] is not None:
            return jsonify(directory_cache["data"])
        
        # Otherwise wait for the refresh to complete (first load)
        refresh_thread.join()
    
    return jsonify(directory_cache["data"] or {"records": []})

@app.route("/directory")
def directory():
    # Get Airtable credentials
    airtable_token = app.config.get('AIRTABLE_API_KEY') or app.config.get('AIRTABLE_TOKEN')
    airtable_base_id = app.config.get('AIRTABLE_BASE_ID', 'appU0yK4n5WOdzSDU')
    airtable_table_name = app.config.get('AIRTABLE_TABLE_NAME', 'main-directory')
    
    # Log the credentials being used (without exposing the full token)
    token_preview = airtable_token[:10] + '...' if airtable_token else 'None'
    logger.info(f"Directory page using Airtable token starting with: {token_preview}")
    logger.info(f"Directory page using base ID: {airtable_base_id}")
    logger.info(f"Directory page using table name: {airtable_table_name}")
    
    return render_template("directory.html", 
                           airtable_token=airtable_token,
                           airtable_base_id=airtable_base_id,
                           airtable_table_name=airtable_table_name,
                           use_cache=True)

@app.route("/add_directory_entry", methods=['POST'])
def add_directory_entry():
    try:
        # Invalidate cache to force refresh on next request
        directory_cache["last_updated"] = 0
        
        # Get the JSON data from the request
        data = request.get_json()
        if not data:
            logger.error("No JSON data received in request")
            return jsonify({"success": False, "error": "No data received"}), 400
            
        logger.info(f"Received form data: {data}")
        
        # Ensure data has the correct structure for Airtable
        if 'fields' not in data:
            logger.warning("Missing 'fields' key in the request data - restructuring")
            data = {'fields': data}
        
        # Get Airtable credentials exactly as used in the directory page
        airtable_token = app.config.get('AIRTABLE_API_KEY') or app.config.get('AIRTABLE_TOKEN')
        airtable_base_id = app.config.get('AIRTABLE_BASE_ID', 'appU0yK4n5WOdzSDU')  # Use from config
        airtable_table_name = app.config.get('AIRTABLE_TABLE_NAME', 'main-directory')  # Use from config
        
        # Log the credentials being used (without exposing the full token)
        token_preview = airtable_token[:10] + '...' if airtable_token else 'None'
        logger.info(f"Using Airtable token starting with: {token_preview}")
        logger.info(f"Using base ID: {airtable_base_id}")
        logger.info(f"Using table name: {airtable_table_name}")
        
        # Use the same URL format that works for reading data
        airtable_url = f"https://api.airtable.com/v0/{airtable_base_id}/{airtable_table_name}"
        logger.info(f"Airtable URL: {airtable_url}")
        
        # Use the same headers format as the frontend
        headers = { 
            "Authorization": f"Bearer {airtable_token}",  # Use token as is
            "Content-Type": "application/json"
        }
        
        # Log the full request details (except token) to help debug
        logger.info(f"Full request URL: {airtable_url}")
        logger.info("Request headers (excluding auth): " + 
                   json.dumps({k:v for k,v in headers.items() if k.lower() != 'authorization'}))
        
        # Keep the field names exactly as they are sent from the frontend
        # For Category, it should be an array since it's a Multiple Select field in Airtable
        fields = {
            "Title": data['fields'].get('Title', '').strip(),
            "Category": data['fields'].get('Category', []), # Accept the array directly for Multiple Select
            "Subtitle": data['fields'].get('Subtitle', '').strip() or None,
            "Phone Number": data['fields'].get('Phone Number', '').strip() or None
        }
        
        # Remove any None values to match how we read data
        fields = {k: v for k, v in fields.items() if v is not None}
        
        # Validate required fields
        if not fields.get('Title') or not fields.get('Category'):
            error_msg = "Title and Category are required fields"
            logger.error(error_msg)
            return jsonify({"success": False, "error": error_msg}), 400
            
        # Validate that Category array is not empty
        # Since Category is now an array for Multiple Select field
        if not fields.get('Category') or len(fields.get('Category', [])) == 0:
            error_msg = "At least one Category is required"
            logger.error(error_msg)
            return jsonify({"success": False, "error": error_msg}), 400
            
        # Log the Category array for debugging
        logger.info(f"Category values being sent: {fields.get('Category')}")
        
        # Try multiple options for the create URL
        # Option 1: Standard format
        airtable_create_url = f"https://api.airtable.com/v0/{airtable_base_id}/{airtable_table_name}"
        logger.info(f"Option 1 URL for creating records: {airtable_create_url}")
        
        # Create data with the exact structure expected by Airtable
        airtable_data = {
            "fields": fields
        }
        
        logger.info(f"Trying direct create with URL: {airtable_create_url}")
        logger.info(f"Sending to Airtable: {airtable_data}")
        
        try:
            # First try the direct URL with single record format
            response = requests.post(airtable_create_url, headers=headers, json=airtable_data, timeout=10)
            
            # Log the response from Airtable
            logger.info(f"Airtable response status: {response.status_code}")
            
            # If that fails, try the /records endpoint with the records array format
            if response.status_code == 404:
                logger.info("First attempt failed with 404, trying /records endpoint")
                records_url = f"{airtable_create_url}/records"
                records_data = {
                    "records": [
                        {
                            "fields": fields
                        }
                    ]
                }
                logger.info(f"Trying records endpoint: {records_url}")
                logger.info(f"Using records data format: {records_data}")
                response = requests.post(records_url, headers=headers, json=records_data, timeout=10)
                logger.info(f"Second attempt response status: {response.status_code}")
            
            if response.status_code >= 400:
                error_text = response.text
                logger.error(f"Airtable error response: {error_text}")
                return jsonify({"success": False, "error": f"Airtable API error: {error_text}"}), response.status_code
                
            response.raise_for_status()
            return jsonify({"success": True, "data": response.json()}), 200
            
        except requests.exceptions.Timeout:
            error_msg = "Request to Airtable timed out"
            logger.error(error_msg)
            return jsonify({"success": False, "error": error_msg}), 504
            
        except requests.exceptions.RequestException as req_err:
            error_msg = f"Request to Airtable failed: {str(req_err)}"
            logger.error(error_msg)
            return jsonify({"success": False, "error": error_msg}), 502
            
    except Exception as e:
        error_msg = f"Error adding directory entry: {str(e)}"
        logger.error(error_msg)
        return jsonify({"success": False, "error": error_msg}), 500

@app.route("/update_directory_entry", methods=['POST'])
def update_directory_entry():
    # Invalidate cache to force refresh on next request
    directory_cache["last_updated"] = 0
    
    # Log the incoming data
    data = request.get_json()
    logger.info(f"Received update data: {data}")
    
    # Check if record_id is provided
    if not data.get('record_id'):
        error_msg = "Record ID is required for updates"
        logger.error(error_msg)
        return jsonify({"success": False, "error": error_msg}), 400
    
    # Extract record ID and fields
    record_id = data.get('record_id')
    
    # Get Airtable credentials from app.config (which loads from environment variables)
    airtable_token = app.config.get('AIRTABLE_API_KEY') or app.config.get('AIRTABLE_TOKEN')
    airtable_base_id = app.config.get('AIRTABLE_BASE_ID')
    airtable_table_name = app.config.get('AIRTABLE_TABLE_NAME')
    
    # Check if we have all required credentials
    if not all([airtable_token, airtable_base_id, airtable_table_name]):
        missing = []
        if not airtable_token: missing.append("AIRTABLE_API_KEY")
        if not airtable_base_id: missing.append("AIRTABLE_BASE_ID")
        if not airtable_table_name: missing.append("AIRTABLE_TABLE_NAME")
        
        error_msg = f"Missing required environment variables: {', '.join(missing)}"
        logger.error(error_msg)
        return jsonify({"success": False, "error": error_msg}), 500
        
    logger.info(f"Using Airtable token starting with: {airtable_token[:10]}...")
    logger.info(f"Using base ID: {airtable_base_id}")
    logger.info(f"Using table name: {airtable_table_name}")
    
    # Use the direct URL for the specific record
    airtable_url = f"https://api.airtable.com/v0/{airtable_base_id}/{airtable_table_name}/{record_id}"
    logger.info(f"Airtable URL for update: {airtable_url}")
    
    # Use the same headers format as the frontend
    headers = { 
        "Authorization": f"Bearer {airtable_token}", 
        "Content-Type": "application/json"
    }
    
    # Keep the field names exactly as they are sent from the frontend
    # For Category, it should be an array since it's a Multiple Select field in Airtable
    fields = {
        "Title": data['fields'].get('Title', '').strip(),
        "Category": data['fields'].get('Category', []), # Accept the array for Multiple Select
        "Subtitle": data['fields'].get('Subtitle', '').strip() or None,
        "Phone Number": data['fields'].get('Phone Number', '').strip() or None
    }
    
    # Remove any None values to match how we read data
    fields = {k: v for k, v in fields.items() if v is not None}
    
    # Validate required fields
    if not fields.get('Title') or not fields.get('Category'):
        error_msg = "Title and Category are required fields"
        logger.error(error_msg)
        return jsonify({"success": False, "error": error_msg}), 400
    
    # Validate that Category array is not empty
    if len(fields.get('Category', [])) == 0:
        error_msg = "At least one Category is required"
        logger.error(error_msg)
        return jsonify({"success": False, "error": error_msg}), 400
    
    # Log the Category array for debugging
    logger.info(f"Category values being sent: {fields.get('Category')}")
    
    # Create the update payload
    airtable_data = {
        "fields": fields
    }
    
    logger.info(f"Sending update to Airtable: {airtable_data}")
    
    try:
        # Use PATCH method to update the record
        response = requests.patch(airtable_url, headers=headers, json=airtable_data, timeout=10)
        
        # Log the response from Airtable
        logger.info(f"Airtable update response status: {response.status_code}")
        
        if response.status_code >= 400:
            error_text = response.text
            logger.error(f"Airtable update error response: {error_text}")
            return jsonify({"success": False, "error": f"Airtable API error: {error_text}"}), response.status_code
        
        # Return success response with updated record
        response_data = response.json()
        logger.info(f"Successfully updated record: {record_id}")
        return jsonify({
            "success": True, 
            "message": "Record updated successfully",
            "record": response_data
        })
    
    except requests.exceptions.RequestException as e:
        error_msg = f"Error updating record: {str(e)}"
        logger.error(error_msg)
        return jsonify({"success": False, "error": error_msg}), 500

@app.route("/delete_directory_entry", methods=['POST'])
def delete_directory_entry():
    """Delete an existing entry from the Airtable directory"""
    # Invalidate cache to force refresh on next request
    directory_cache["last_updated"] = 0
    
    # Log the incoming data
    data = request.get_json()
    logger.info(f"Received delete request: {data}")
    
    # Check if record_id is provided
    if not data.get('record_id'):
        error_msg = "Record ID is required for deletion"
        logger.error(error_msg)
        return jsonify({"success": False, "error": error_msg}), 400
    
    # Extract record ID
    record_id = data.get('record_id')
    
    # Get Airtable credentials from app.config
    airtable_token = app.config.get('AIRTABLE_API_KEY') or app.config.get('AIRTABLE_TOKEN')
    airtable_base_id = app.config.get('AIRTABLE_BASE_ID')
    airtable_table_name = app.config.get('AIRTABLE_TABLE_NAME')
    
    # Check if we have all required credentials
    if not all([airtable_token, airtable_base_id, airtable_table_name]):
        missing = []
        if not airtable_token: missing.append("AIRTABLE_API_KEY")
        if not airtable_base_id: missing.append("AIRTABLE_BASE_ID")
        if not airtable_table_name: missing.append("AIRTABLE_TABLE_NAME")
        
        error_msg = f"Missing required environment variables: {', '.join(missing)}"
        logger.error(error_msg)
        return jsonify({"success": False, "error": error_msg}), 500
    
    # Use the direct URL for the specific record
    airtable_url = f"https://api.airtable.com/v0/{airtable_base_id}/{airtable_table_name}/{record_id}"
    logger.info(f"Airtable URL for delete: {airtable_url}")
    
    # Set headers for the Airtable API
    headers = { 
        "Authorization": f"Bearer {airtable_token}", 
        "Content-Type": "application/json"
    }
    
    try:
        # Send DELETE request to Airtable
        response = requests.delete(airtable_url, headers=headers, timeout=10)
        
        # Check for errors
        if response.status_code >= 400:
            error_text = response.text
            logger.error(f"Airtable error response: {error_text}")
            return jsonify({"success": False, "error": f"Airtable API error: {error_text}"}), response.status_code
        
        # Return success response
        return jsonify({"success": True, "message": "Record deleted successfully"}), 200
        
    except requests.exceptions.Timeout:
        error_msg = "Request to Airtable timed out"
        logger.error(error_msg)
        return jsonify({"success": False, "error": error_msg}), 504
        
    except requests.exceptions.RequestException as req_err:
        error_msg = f"Request to Airtable failed: {str(req_err)}"
        logger.error(error_msg)
        return jsonify({"success": False, "error": error_msg}), 502
        
    except Exception as e:
        error_msg = f"Unexpected error deleting record: {str(e)}"
        logger.error(error_msg)
        return jsonify({"success": False, "error": error_msg}), 500

@app.route('/tally_form_submit', methods=['POST'])
def post_route():
    # Get JSON data from the request
    data = request.get_json()
    return form_submit(data)

@app.route('/message_receive', methods=['POST'])
def message_receive_route():
    data = request.get_json()
    logger.info(data)
    return message_receive(data)

@app.route("/morning_message")
def morning_message():
    return main({})

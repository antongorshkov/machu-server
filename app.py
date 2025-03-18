import os
import json
import logging
import requests
import threading
import time
import base64
import cloudinary
import cloudinary.uploader
import cloudinary.api
from logtail import LogtailHandler
from flask import Flask, render_template, request, send_from_directory, jsonify
from dotenv import load_dotenv
from morning_message import main
from form_submit import form_submit, add_to_group
from message_receive import message_receive
from flask_cors import CORS

# Load environment variables from .env file
if os.getenv('FLASK_ENV') != 'production':
    load_dotenv()

app = Flask(__name__, static_folder='static')
CORS(app, resources={r"/*": {"origins": ["https://lovable-directory-app-5ixj8.ondigitalocean.app", "http://192.168.68.58:8080"]}})

# Configure Cloudinary
cloud_name = os.environ.get('CLOUDINARY_CLOUD_NAME')
api_key = os.environ.get('CLOUDINARY_API_KEY')
api_secret = os.environ.get('CLOUDINARY_API_SECRET')

if cloud_name and api_key and api_secret:
    cloudinary.config(
        cloud_name=cloud_name,
        api_key=api_key,
        api_secret=api_secret
    )
    logger = logging.getLogger(__name__)
    logger.info("Cloudinary configured successfully")
else:
    logger = logging.getLogger(__name__)
    logger.warning("Cloudinary not configured - missing environment variables")

# In-memory cache dictionary for directory data
directory_cache = {
    "data": None,
    "last_updated": 0,
    "updating": False,
    "force_refresh": False  # New flag to indicate forced refresh
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

# Add a monkey patch to handle the proxies parameter incompatibility
try:
    from openai._base_client import SyncHttpxClientWrapper
    original_init = SyncHttpxClientWrapper.__init__
    
    def patched_init(self, *args, **kwargs):
        # Remove 'proxies' from kwargs if it exists
        if 'proxies' in kwargs:
            logger.info("Removing 'proxies' parameter from OpenAI client initialization")
            del kwargs['proxies']
        return original_init(self, *args, **kwargs)
    
    SyncHttpxClientWrapper.__init__ = patched_init
    logger.info("Successfully patched OpenAI client to handle 'proxies' parameter")
except (ImportError, AttributeError) as e:
    logger.warning(f"Could not patch OpenAI client: {str(e)}")
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
    
    # Check if cache needs refreshing (expired, empty, or force refresh requested)
    cache_age = current_time - directory_cache["last_updated"]
    if (directory_cache["data"] is None or cache_age > CACHE_EXPIRY or directory_cache["force_refresh"]) and not directory_cache["updating"]:
        # Reset force refresh flag if it was set
        directory_cache["force_refresh"] = False
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

@app.route("/refresh_directory_cache")
def refresh_directory_cache():
    """Force a refresh of the directory data cache"""
    # Set the force refresh flag and invalidate timestamp
    directory_cache["force_refresh"] = True
    directory_cache["last_updated"] = 0
    
    # Start a background thread to refresh cache immediately
    refresh_thread = threading.Thread(target=fetch_directory_data_from_airtable)
    refresh_thread.daemon = True
    refresh_thread.start()
    
    # Return a success response
    return jsonify({"success": True, "message": "Cache refresh initiated"})

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
        
        # Handle multipart form data or JSON
        logo_action = 'keep'
        logo_file = None
        
        if request.content_type and 'multipart/form-data' in request.content_type:
            # For multipart form data with file uploads
            json_data = json.loads(request.form.get('data', '{}'))
            logo_action = request.form.get('logo_action', 'keep')
            logo_file = request.files.get('logo_file')
            logger.info(f"Received add request with logo action: {logo_action}")
        else:
            # For regular JSON data
            json_data = request.get_json()
            if not json_data:
                logger.error("No JSON data received in request")
                return jsonify({"success": False, "error": "No data received"}), 400
        
        logger.info(f"Received form data: {json_data}")
        
        # Ensure data has the correct structure for Airtable
        if 'fields' not in json_data:
            logger.warning("Missing 'fields' key in the request data - restructuring")
            json_data = {'fields': json_data}
        
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
            "Title": json_data['fields'].get('Title', '').strip(),
            "Category": json_data['fields'].get('Category', []), # Accept the array directly for Multiple Select
            "Subtitle": json_data['fields'].get('Subtitle', '').strip() or None,
            "Phone Number": json_data['fields'].get('Phone Number', '').strip() or None
        }
        
        # Store logo file data for later upload (second step)
        logo_file_data = None
        logo_file_name = None
        logo_file_type = None
        
        # For new entries, we'll use two-step upload process
        if logo_action == 'upload' and logo_file:
            try:
                # Read the file data for use after the record is created
                logo_file_data = logo_file.read()
                logo_file_name = logo_file.filename
                logo_file_type = logo_file.content_type
                
                logger.info(f"Prepared logo file for upload after record creation: {logo_file_name}, type: {logo_file_type}, size: {len(logo_file_data)} bytes")
                
                # We'll exclude the Logo field from the initial record creation
                # We'll add it in a second step after getting the Airtable record ID
                if 'Logo' in fields:
                    del fields['Logo']
            except Exception as e:
                logger.error(f"Error preparing logo file: {str(e)}")
                # Continue without the logo if there's an error
        
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
            
            # Get the created record data
            created_data = response.json()
            
            # Extract record ID from response
            # The structure depends on which endpoint we used
            record_id = None
            if 'id' in created_data:
                # Direct creation response
                record_id = created_data['id']
            elif 'records' in created_data and len(created_data['records']) > 0:
                # Records endpoint response
                record_id = created_data['records'][0]['id']
            
            # STEP 2: Handle file upload if we have a file to upload and a record ID
            if logo_file_data and logo_file_name and logo_file_type and record_id:
                try:
                    logger.info(f"Starting Cloudinary upload for new record: {record_id}")
                    
                    # 1. Upload the image to Cloudinary
                    # Create a unique folder for each record
                    upload_folder = f"directory_logos/{record_id}"
                    
                    # Upload the image to Cloudinary
                    upload_result = cloudinary.uploader.upload(
                        logo_file_data,
                        folder=upload_folder,
                        public_id=logo_file_name.split('.')[0],  # Use filename without extension
                        resource_type="auto"  # Auto-detect resource type
                    )
                    
                    logger.info(f"Cloudinary upload result: {upload_result}")
                    
                    # Get the secure URL from the upload result
                    if 'secure_url' in upload_result:
                        cloudinary_url = upload_result['secure_url']
                        logger.info(f"Cloudinary URL: {cloudinary_url}")
                        
                        # 2. Update the Airtable record with the Cloudinary URL
                        attachment_data = {
                            "fields": {
                                "Logo": [
                                    {
                                        "url": cloudinary_url,
                                        "filename": logo_file_name
                                    }
                                ]
                            }
                        }
                        
                        # Update the record with our Cloudinary URL
                        attachment_url = f'https://api.airtable.com/v0/{airtable_base_id}/{airtable_table_name}/{record_id}'
                        attachment_response = requests.patch(
                            attachment_url,
                            headers={
                                'Authorization': f'Bearer {airtable_token}',
                                'Content-Type': 'application/json'
                            },
                            json=attachment_data
                        )
                        
                        if attachment_response.status_code >= 400:
                            logger.error(f"Error updating record with Cloudinary URL: {attachment_response.status_code} - {attachment_response.text}")
                        else:
                            # Get the updated record data
                            attachment_result = attachment_response.json()
                            logger.info(f"Successfully updated record with Cloudinary URL")
                            
                            # Update the response data with file information
                            created_data = attachment_result
                    else:
                        logger.error(f"No secure_url in Cloudinary upload response: {upload_result}")
                except Exception as e:
                    logger.error(f"Error in Cloudinary upload process for new record: {str(e)}")
            
            return jsonify({"success": True, "data": created_data}), 200
            
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
    
    # Handle multipart form data
    try:
        # Get form data
        if request.content_type and 'multipart/form-data' in request.content_type:
            # For multipart form data with file uploads
            json_data = json.loads(request.form.get('data', '{}'))
            logo_action = request.form.get('logo_action', 'keep')
            logo_file = request.files.get('logo_file')
            logger.info(f"Received update with logo action: {logo_action}")
        else:
            # For regular JSON data
            json_data = request.get_json()
            logo_action = 'keep'
            logo_file = None
            
        logger.info(f"Received update data: {json_data}")
        
        # Check if record_id is provided
        if not json_data.get('record_id'):
            error_msg = "Record ID is required for updates"
            logger.error(error_msg)
            return jsonify({"success": False, "error": error_msg}), 400
        
        # Extract record ID
        record_id = json_data.get('record_id')
    except Exception as e:
        error_msg = f"Error processing form data: {str(e)}"
        logger.error(error_msg)
        return jsonify({"success": False, "error": error_msg}), 400
    
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
        "Title": json_data['fields'].get('Title', '').strip(),
        "Category": json_data['fields'].get('Category', []), # Accept the array for Multiple Select
        "Subtitle": json_data['fields'].get('Subtitle', '').strip() or None,
        "Phone Number": json_data['fields'].get('Phone Number', '').strip() or None,
        "Website URL": json_data['fields'].get('Website URL', '').strip() or None
    }
    
    # Handle logo upload
    logo_url = None
    logo_file_data = None
    logo_file_name = None
    logo_file_type = None
    
    # If user wants to remove the logo
    if logo_action == 'remove':
        # Set Logo to an empty array to remove existing logo
        fields["Logo"] = []
        # Also ensure any Cloudinary URL is cleared
        fields["LogoCloudinaryUrl"] = None
        logger.info("Removing existing logo and Cloudinary URL")
    
    # For uploading, we'll use the two-step approach required by Airtable:
    # 1. First update the record normally (without attachment)
    # 2. Then use the returned attachment URL to upload the file in a separate request
    elif logo_action == 'upload' and logo_file:
        try:
            # Read and store the file data for later use (after initial update)
            logo_file_data = logo_file.read()
            logo_file_name = logo_file.filename
            logo_file_type = logo_file.content_type
            
            logger.info(f"Preparing logo file for upload: {logo_file_name}, type: {logo_file_type}, size: {len(logo_file_data)} bytes")
            
            # We'll temporarily exclude the Logo field from this update
            # We'll add it in the second step after getting the upload URL
            if 'Logo' in fields:
                del fields['Logo']
                
        except Exception as e:
            logger.error(f"Error preparing logo file: {str(e)}")
            # Continue without the logo if there's an error in preparation
    
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
        
        # STEP 2: Handle file upload if we have prepared logo file data
        if logo_file_data and logo_file_name and logo_file_type:
            try:
                logger.info(f"Starting Cloudinary upload for update record: {record_id}")
                
                # 1. Upload the image to Cloudinary
                # Create a unique folder for each record
                upload_folder = f"directory_logos/{record_id}"
                
                # Upload the image to Cloudinary
                upload_result = cloudinary.uploader.upload(
                    logo_file_data,
                    folder=upload_folder,
                    public_id=logo_file_name.split('.')[0],  # Use filename without extension
                    resource_type="auto",  # Auto-detect resource type
                    overwrite=True  # Overwrite any existing file with the same public_id
                )
                
                logger.info(f"Cloudinary upload result: {upload_result}")
                
                # Get the secure URL from the upload result
                if 'secure_url' in upload_result:
                    cloudinary_url = upload_result['secure_url']
                    logger.info(f"Cloudinary URL: {cloudinary_url}")
                    
                    # 2. Update the Airtable record with the Cloudinary URL
                    attachment_data = {
                        "fields": {
                            "Logo": [
                                {
                                    "url": cloudinary_url,
                                    "filename": logo_file_name
                                }
                            ],
                            # Store the Cloudinary URL in a custom field for easier access
                            "LogoCloudinaryUrl": cloudinary_url
                        }
                    }
                    
                    # Update the record with our Cloudinary URL
                    attachment_url = f'https://api.airtable.com/v0/{airtable_base_id}/{airtable_table_name}/{record_id}'
                    attachment_response = requests.patch(
                        attachment_url,
                        headers={
                            'Authorization': f'Bearer {airtable_token}',
                            'Content-Type': 'application/json'
                        },
                        json=attachment_data
                    )
                    
                    if attachment_response.status_code >= 400:
                        logger.error(f"Error updating record with Cloudinary URL: {attachment_response.status_code} - {attachment_response.text}")
                    else:
                        # Get the updated record data
                        attachment_result = attachment_response.json()
                        logger.info(f"Successfully updated record with Cloudinary URL")
                        
                        # Update the response data with file information
                        response_data = attachment_result
                else:
                    logger.error(f"No secure_url in Cloudinary upload response: {upload_result}")
            except Exception as e:
                logger.error(f"Error in Cloudinary upload process: {str(e)}")
        
        # Extract the logo URL from the final response data
        logo_url = None
        if response_data.get('fields', {}).get('Logo'):
            logo_attachments = response_data['fields'].get('Logo', [])
            if logo_attachments and isinstance(logo_attachments, list) and len(logo_attachments) > 0:
                logo_url = logo_attachments[0].get('url')
                logger.info(f"Logo URL from response: {logo_url}")
        
        return jsonify({
            "success": True, 
            "message": "Record updated successfully",
            "record": response_data,
            "id": record_id,
            "logoUrl": logo_url
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

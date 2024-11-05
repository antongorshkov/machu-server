import requests
import os
from flask import current_app

def is_currently_living_or_moving_soon(response_data):
    # Define the key for the question and the ID of the "Yes" answer
    question_key = "question_MXrKKl"
    yes_option_id = "2eb07d19-f5bd-4344-9893-72d15d431a39"
    
    # Iterate through each field to find the question with the specified key
    for field in response_data["fields"]:
        # Check if the key matches
        if field["key"] == question_key:
            # Return True if the "Yes" option ID is in the value array
            return yes_option_id in field.get("value", [])
    return False

def add_to_group(phone):
    url = "https://mywhinlite.p.rapidapi.com/groups/addmembers"

    clean_number = phone.lstrip('+').strip()
    GroupID = current_app.config['MACHUKITA_TEST_GROUP_ID'] if os.getenv('FLASK_ENV') != 'production' else current_app.config['MV_NEIGHBORS_GROUP_ID']
    payload = {
      "gid": GroupID,
      "participants": [clean_number]
    }
    headers = {
      "x-rapidapi-key": current_app.config['RAPID_API_KEY'],
      "x-rapidapi-host": "mywhinlite.p.rapidapi.com",
      "Content-Type": "application/json"
    }
    print(payload)
    response = requests.post(url, json=payload, headers=headers)
    print(response)

    return {"body": "OK"}
   
def form_submit(args):
    params = args.get("data")
    Name = params["fields"][1]["value"]
    Phone = params["fields"][2]["value"]
    if is_currently_living_or_moving_soon(params):
      Message = Name + " agreed to everything and lives here(I tried adding the number), please check that it worked. Phone Number: " + Phone  
      add_to_group(Phone)
    else:
      Message = Name + " does not live here please reject if applied. Phone Number: " + Phone

    #Send a Message to WhatsApp Group
    url = "https://mywhinlite.p.rapidapi.com/sendmsg"
    
    GroupID = current_app.config['MV_ADMINS_GID'] #MV Admins
    #GroupID = current_app.config['MACHUKITA_TEST_GID']

    payload = {
    	"phone_number_or_group_id": GroupID,
    	"is_group": False,
    	"message": Message
    }
    headers = {
    	"x-rapidapi-key": current_app.config['RAPID_API_KEY'],
    	"x-rapidapi-host": "mywhinlite.p.rapidapi.com",
    	"Content-Type": "application/json"
    }
    
    response = requests.post(url, json=payload, headers=headers)
    
    print(response)

    return {"body": "OK"}
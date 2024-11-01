import requests

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

def form_submit(args):
    params = args.get("data")
    Name = params["fields"][1]["value"]
    Phone = params["fields"][2]["value"]
    if is_currently_living_or_moving_soon(params):
      Message = Name + " agreed to everything and lives here, please approve. Phone Number: " + Phone  
    else:
      Message = Name + " does not live here please reject if applied. Phone Number: " + Phone

    #Machukita Test Group: "120363348507910736@g.us"
    #MV Admin Group: "120363318028761250@g.us"
    #Send a Message to WhatsApp Group
    url = "https://mywhinlite.p.rapidapi.com/sendmsg"
    
    GroupID = "120363318028761250@g.us" #MV Admins
    #GroupID = "120363348507910736@g.us" #Machukita Test Group

    payload = {
    	"phone_number_or_group_id": GroupID,
    	"is_group": False,
    	"message": Message
    }
    headers = {
    	"x-rapidapi-key": "d574bdedafmsh0e3d7125d9ded3bp12c38djsnd19751f3439d",
    	"x-rapidapi-host": "mywhinlite.p.rapidapi.com",
    	"Content-Type": "application/json"
    }
    
    response = requests.post(url, json=payload, headers=headers)
    
    print(response)

    return {"body": "OK"}
import sys
import requests
import json
import logging
from datetime import datetime, timedelta
from flask import current_app

logger = logging.getLogger(__name__)

def formatted_today_date(today):
    # Get the current date
    current_date = today
    
    # Format the date as "Today is Day, Month DD, YYYY"
    formatted_date = current_date.strftime("Good Morning MV! Today is %A, %B %d, %Y")
    
    return formatted_date

def get_random_quote():
  response = requests.get('https://zenquotes.io/api/random')
  data = response.json()[0]
  quote = data['q'] + ' - ' + data['a']
  return quote

# Function to dynamically retrieve moon phase data for a given year
def fetch_moon_phases(year):
    url = f"https://craigchamberlain.github.io/moon-data/api/moon-phase-data/{year}/"
    response = requests.get(url)
    
    if response.status_code == 200:
        return response.json()  # Return the parsed JSON data
    else:
        raise Exception(f"Failed to retrieve moon phase data. Status code: {response.status_code}")

def find_next_full_moon():
    today = datetime.now()
    current_year = datetime.now().year  # Get the current year dynamically
    moon_phases = fetch_moon_phases(current_year)

    # Loop through the data and find the next full moon (Phase == 2)
    for entry in moon_phases:
        date_obj = datetime.fromisoformat(entry["Date"])
        if date_obj > today and entry["Phase"] == 2:
            return date_obj.date()  # Return the date of the next full moon
    
    return None

# Function to check if today is a full moon (Phase == 2)
def IsTodayFullMoon(today):
    current_year = today.year
    moon_phases = fetch_moon_phases(current_year)
    
    # Loop through the data to find if today's date is a full moon (Phase == 2)
    for entry in moon_phases:
        date_obj = datetime.fromisoformat(entry["Date"])
        if date_obj.date() == today and entry["Phase"] == 2:
            return True
    return False

def SendMessage(Message):
    url = "https://mywhinlite.p.rapidapi.com/sendmsg"
    
    payload = {
    	"phone_number_or_group_id": current_app.config['MORNING_MESSAGE_PHONE_NUM'],
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

    return True

def todayHoliday(today):
    # Get the current date
    current_date = today
    year = current_date.year
    month = current_date.month
    day = current_date.day

    url = "https://holidays.abstractapi.com/v1/"
    querystring = {
        "api_key": current_app.config['ABSTRACT_API_KEY'], 
        "country": "CR", 
        "year": year, 
        "month": month, 
        "day": day
    }

    response = requests.get(url, params=querystring)

    if response.status_code == 200:
        holidays = response.json()
        if holidays:
            holiday_name = holidays[0].get("name", "No holiday name found")
            return holiday_name
        else:
            return None
    else:
        print(f"Error: {response.status_code}, {response.text}")

def year_progress_no_decimals_string(today):
    # Get the current date and the total number of days in the current year
    current_date = today
    year = current_date.year
    start_of_year = datetime(year, 1, 1).date()  # Convert to date object
    end_of_year = datetime(year, 12, 31).date()  # Convert to date object
    
    # Calculate the number of days in the year
    total_days_in_year = (end_of_year - start_of_year).days + 1
    
    # Calculate how many days have passed in the current year
    days_passed = (current_date - start_of_year).days + 1
    
    # Calculate how many days are left in the year
    days_left = total_days_in_year - days_passed
    
    # Calculate the percentage of the year that has passed
    percentage_passed = (days_passed / total_days_in_year) * 100
    
    # Assign the results to variables as strings
    days_left_str = f"Days left in the year: {days_left}"
    percentage_passed_str = f"Percentage of the year passed: {int(percentage_passed)}%"
    
    return days_left_str, percentage_passed_str

def FullMoonMsg(today):
    try:
        if IsTodayFullMoon(today):
            return "Today is a full moon!"
        else:
            return ""
    except Exception as e:
        print(str(e))

def main(args):
    today = datetime.now().date()

    logger.info("Starting MorningMessage: {}".format(today))
    #yesterday = today - timedelta(days=4)
    #today = datetime(year=2025, month=8, day=9).date()

    # Call the updated function and assign the strings to variables
    formatted_date = formatted_today_date(today)
    days_left_str, percentage_passed_str = year_progress_no_decimals_string(today)
    full_moon_str = FullMoonMsg(today)
    today_holiday_str = todayHoliday(today)
    get_random_quote_str = get_random_quote()

    # Create morning message with conditionally including the full moon message
    morning_message = formatted_date + "\n" + days_left_str + "\n" + percentage_passed_str
    if full_moon_str:
        morning_message += "\n" + full_moon_str
    if get_random_quote_str:
        morning_message += "\n" + get_random_quote_str
    if today_holiday_str:
        morning_message += "\n" + "Today is: " + today_holiday_str

    logger.info('Sending Morning Message: ' +morning_message )
    SendMessage(morning_message)

    return {
        "statusCode": 200,
        "body": json.dumps("ok")  # Explicitly make the body JSON serializable
    }
import json
import logging
from openai import OpenAI
import shelve
import time
from flask import current_app
import requests
import re
from audio_download_decode import download_and_decrypt
from transcribe import transcribe_audio
import os

client = None

def init_openai_client():
    global client
    if client is None:
        OPENAI_API_KEY = current_app.config['OPENAI_API_KEY']
        
        try:
            # Basic initialization with the monkey patch in app.py handling the proxies issue
            client = OpenAI(api_key=OPENAI_API_KEY)
            logging.info("OpenAI client initialized successfully")
        except Exception as e:
            # Log detailed error information
            logging.error(f"Failed to initialize OpenAI client: {str(e)}")
            # If initialization fails, log the error and re-raise
            raise

def create_assistant(file):
    """
    You currently cannot set the temperature for Assistant via the API.
    """
    assistant = client.beta.assistants.create(
        name="WhatsApp AirBnb Assistant",
        instructions="You're a helpful WhatsApp assistant that can assist guests that are staying in our Paris AirBnb. Use your knowledge base to best respond to customer queries. If you don't know the answer, say simply that you cannot help with question and advice to contact the host directly. Be friendly and funny.",
        tools=[{"type": "retrieval"}],
        model="gpt-4-1106-preview",
        file_ids=[file.id],
    )
    return assistant

# Use context manager to ensure the shelf file is closed properly
def check_if_thread_exists(wa_id):
    with shelve.open("threads_db") as threads_shelf:
        return threads_shelf.get(wa_id, None)

def store_thread(wa_id, thread_id):
    with shelve.open("threads_db", writeback=True) as threads_shelf:
        threads_shelf[wa_id] = thread_id

def run_assistant(thread, name,assistant_id=None):
    # Retrieve the Assistant
    assistant = client.beta.assistants.retrieve(assistant_id)

    # Run the assistant
    run = client.beta.threads.runs.create(
        thread_id=thread.id,
        assistant_id=assistant.id,
        # instructions=f"You are having a conversation with {name}",
    )

    # Wait for completion
    # https://platform.openai.com/docs/assistants/how-it-works/runs-and-run-steps#:~:text=under%20failed_at.-,Polling%20for%20updates,-In%20order%20to
    while run.status != "completed":
        # Be nice to the API
        time.sleep(0.5)
        run = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)

    # Retrieve the Messages
    messages = client.beta.threads.messages.list(thread_id=thread.id)
    new_message = messages.data[0].content[0].text.value
    logging.info(f"Generated message: {new_message}")
    current_app.logger.info(f"Generated message: {new_message}")
    return new_message


def generate_response(message_body, wa_id, name, assistant_id=None):
    # Check if there is already a thread_id for the wa_id
    thread_id = check_if_thread_exists(wa_id)

    # If a thread doesn't exist, create one and store it
    if thread_id is None:
        logging.info(f"Creating new thread for {name} with wa_id {wa_id}")
        thread = client.beta.threads.create()
        store_thread(wa_id, thread.id)
        thread_id = thread.id

    # Otherwise, retrieve the existing thread
    else:
        logging.info(f"Retrieving existing thread for {name} with wa_id {wa_id}")
        thread = client.beta.threads.retrieve(thread_id)

    # Add message to thread
    message = client.beta.threads.messages.create(
        thread_id=thread_id,
        role="user",
        content=message_body,
    )

    # Run the assistant and get the new message
    new_message = run_assistant(thread, name, assistant_id)

    return new_message

def send_response(Message, wa_id, is_group):
    clean_message = clean_string(Message)   
    url = "https://mywhinlite.p.rapidapi.com/sendmsg"
    
    payload = {
    	"phone_number_or_group_id": wa_id,
    	"is_group": is_group,
    	"message": clean_message
    }
    headers = {
    	"x-rapidapi-key": current_app.config['RAPID_API_KEY'],
    	"x-rapidapi-host": "mywhinlite.p.rapidapi.com",
    	"Content-Type": "application/json"
    }
    
    current_app.logger.info("About to respond to " + wa_id)
    current_app.logger.info(payload)
    response = requests.post(url, json=payload, headers=headers)
    
    # Log the full response
    try:
        response_json = response.json()
        current_app.logger.info(f"Response JSON: {response_json}")
    except ValueError:
        current_app.logger.info(f"Response Text: {response.text}")

    return True

def clean_string(text):
    # Replace the specific substring with an empty string
    substring = "【6:0†source】"
    cleaned_text = text.replace(substring, '')
    
    # Remove non-printable characters
    cleaned_text = re.sub(r'[^\x20-\x7E]', '', cleaned_text)
    
    return cleaned_text

def punctuate(text):
    thread_id = "punct_thread" #don't need threading here, just re-use the same one always
    # Retrieve the Assistant
    OPENAI_ASSISTANT_ID = current_app.config['OPENAI_ASSISTANT_ID_PUNCT']
    punctuated_text = generate_response(text, thread_id, "Punctuation", OPENAI_ASSISTANT_ID)
    return punctuated_text
    
def handle_audio_message(audio_data):
    payload_audio = {
        'url': audio_data['URL'],
        'mediaKey': audio_data['mediaKey'],
        'messageType': 'audioMessage',
        'whatsappTypeMessageToDecode': 'WhatsApp Audio Keys',
        'mimetype': audio_data['mimetype']
    }
    audio_file = download_and_decrypt(payload_audio)
    transcript = transcribe_audio(audio_file)
    punctuated_transcript = punctuate(transcript)
    #punctuated_transcript = transcript

    # Delete the encrypted file after decryption
    if os.path.exists(audio_file):
        os.remove(audio_file)    
    return punctuated_transcript

def message_receive(data):
    init_openai_client()
    # Extract the text attribute from the extendedTextMessage or conversation
    try:
        name = data['Info']['PushName']
        sender = data['Info']['Sender'] 
        is_from_me = current_app.config['MY_WA_NUMBER'] in sender
        is_group = data['Info']['IsGroup']
        chat = data['Info']['Chat']
        current_app.logger.info(f"Received message from {name} in chat {chat}")
        is_reaction = False
        is_audio = False
        text = None

        if 'extendedTextMessage' in data['Message']:
            text = data['Message']['extendedTextMessage']['text']
        elif 'conversation' in data['Message']:
            text = data['Message']['conversation']
        elif 'reactionMessage' in data['Message']:
            text = data['Message']['reactionMessage']['text']
            is_reaction = True
        elif 'audioMessage' in data['Message']:
            is_audio = True
            if not is_group:
                transcript = handle_audio_message(data['Message']['audioMessage'])
                current_app.logger.info(f"And now I'm about to respond with a transcription.")
                send_response(transcript,chat,is_group) # Send the response to the user
        else:
            text = None
        
        current_app.logger.info(f"Extracted text: {text}")
        
        if text is None or is_reaction or is_audio:
            return {
                "statusCode": 200,
                "body": json.dumps({"text": "No text found or is reaction or is audio"})
            }
        
        is_machu_mention = current_app.config['MACHU_NUMBER'] in text

        if is_group and is_from_me and is_machu_mention:
            current_app.logger.info(f"And now I'm about to respond !!!")
            request_text = text.replace(current_app.config['MACHU_NUMBER'], '').strip()
            request_text = text.replace("@", '').strip()
            response = generate_response(request_text,sender,name,current_app.config['OPENAI_ASSISTANT_ID'])
            send_response(response,chat,is_group) # Send the response to the user

    except KeyError as e:
        current_app.logger.info(f"Key error: {e}")
        text = None

    return {
        "statusCode": 200,
        "body": json.dumps({"text": text})  # Return the extracted text in the response
    }
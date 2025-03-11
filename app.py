import os
import logging
from logtail import LogtailHandler
from flask import Flask, render_template, request
from dotenv import load_dotenv
from morning_message import main
from form_submit import form_submit, add_to_group
from message_receive import message_receive

# Load environment variables from .env file
if os.getenv('FLASK_ENV') != 'production':
    load_dotenv()

app = Flask(__name__)
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

@app.route("/directory")
def directory():
    return render_template("directory.html")

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

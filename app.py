from flask import Flask, request, jsonify
from flask import render_template
from morning_message import main
from form_submit import form_submit
from dotenv import load_dotenv
import os
import logging
from logtail import LogtailHandler

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

handler = LogtailHandler(source_token=app.config['LOGTAIL_TOKEN'])
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.handlers = []
logger.addHandler(handler)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s:%(levelname)s:%(message)s"
    )


@app.route("/")
def hello_world():
    return render_template("index.html")


@app.route('/tally_form_submit', methods=['POST'])
def post_route():
    # Get JSON data from the request
    data = request.get_json()
    return form_submit(data)

@app.route("/morning_message")
def morning_message():
    return main({})

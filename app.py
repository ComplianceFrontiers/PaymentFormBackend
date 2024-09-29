from flask import Flask, jsonify, request
from flask_cors import CORS
from datetime import datetime
from pymongo import MongoClient
from dotenv import load_dotenv
import os,time
from bson.objectid import ObjectId
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
 

MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 1

app = Flask(__name__)
CORS(app)
load_dotenv()

# Get the MongoDB URI from the environment variable
mongo_uri = os.getenv('MONGO_URI')
# MongoDB setup
client = MongoClient(mongo_uri)
db = client.chessclub
users_collection = db.registered_users
Tornument_collection = db.TornumentTimings
@app.route('/')
def home():
    return "Hello, Flask on Vercel!"

def time_now():
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


SENDER_EMAIL = os.getenv('SENDER_EMAIL', 'connect@chesschamps.us')
SENDER_PASSWORD = os.getenv('SENDER_PASSWORD', 'iyln tkpp vlpo sjep')

@app.route('/send-email', methods=['POST'])
def send_email():
    try:
        data = request.get_json()
        recipient_email = data['email']
        subject = data.get('subject', 'Registration Confirmation')
        body = data.get('body', 'Thank you for registering for the Kids Chess Tournament!')

        # Set up the MIME
        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = recipient_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        # Connect to Gmail's SMTP server
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        text = msg.as_string()
        server.sendmail(SENDER_EMAIL, recipient_email, text)
        server.quit()

        return jsonify({"message": "Email sent successfully!"}), 200
    except Exception as e:
        print(f'Error: {e}')
        return jsonify({"message": "Failed to send email."}), 500



@app.route('/signup', methods=['POST'])
def signup():
    data = request.json

    # Validate incoming data
    required_fields = ['playerFirstName', 'playerLastName', 'parentFirstName', 'parentLastName', 'phoneNumber', 'email', 'section']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'Missing required field: {field}'}), 400

    # Prepare the data for MongoDB
    user_data = {
        'playerFirstName': data['playerFirstName'],
        'playerLastName': data['playerLastName'],
        'parentFirstName': data['parentFirstName'],
        'parentLastName': data['parentLastName'],
        'phoneNumber': data['phoneNumber'],
        'email': data['email'],
        'section': data['section'],
        'signupDate': datetime.utcnow()
    }

    # Insert data into MongoDB with retry mechanism
    for attempt in range(MAX_RETRIES):
        try:
            users_collection.insert_one(user_data)
            return jsonify({'message': 'Registration successful'}), 201
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY_SECONDS)
            else:
                return jsonify({'error': 'Error occurred during registration', 'details': str(e)}), 500
@app.route('/signin', methods=['POST'])
def signin():
    user_data = request.get_json()
    if not user_data or 'email' not in user_data:
        return jsonify({'error': 'Email is required.'}), 400
    
    email = user_data.get('email')
    
    # Check if user exists
    existing_user = users_collection.find_one({'email': email})
    if existing_user:
        return jsonify({'success': True, 'message': 'Sign in successful.'}), 200
    else:
        return jsonify({'error': 'Email not registered. Please sign up.'}), 404

@app.route('/Club_users', methods=['GET'])
def get_users():
    try:
        # Fetch all records from the collection
        users = users_collection.find({}, {'_id': 0})  # Exclude the _id field
        # Convert MongoDB documents to a list of dictionaries
        users_list = list(users)
        return jsonify(users_list)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route('/tournament-timings', methods=['GET'])
def get_tournament_timings():
    try:
        # Fetch the latest document from the TornumentTimings collection
        timing_document = Tornument_collection.find_one({}, sort=[('_id', -1)])
        if timing_document:
            # Convert ObjectId to string for JSON serialization
            timing_document['_id'] = str(timing_document['_id'])
            return jsonify(timing_document['TornumentTimings']), 200
        else:
            return jsonify({"error": "No tournament timings found"}), 404
    except Exception as e:
        print(f"An error occurred: {e}")
        return jsonify({"error": "An error occurred while fetching tournament timings"}), 500


@app.route('/update_tournament', methods=['PUT'])
def update_tournament():
    data = request.json
    
    tournament_id = "66a8c52fad0e6b211e580cda"
    new_timing = data['TornumentTimings']

    # Attempt to update the tournament timing in the collection with retries
    for attempt in range(MAX_RETRIES):
        try:
            result = Tornument_collection.update_one(
                {'_id': ObjectId(tournament_id)},
                {'$set': {'TornumentTimings': new_timing, 'updated_at': time_now()}}
            )
            if result.matched_count == 0:
                return jsonify({'error': 'No record found with the provided ID'}), 404
            return jsonify({'message': 'Tournament timing updated successfully!'}), 200
        except Exception as e:
            print(f"Attempt {attempt + 1} failed: {e}")
            time.sleep(RETRY_DELAY_SECONDS)

    return jsonify({'error': 'Failed to update tournament timing after multiple attempts'}), 500



if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)
from flask import Flask, jsonify, request
from flask_cors import CORS
from datetime import datetime
from pymongo import MongoClient
from dotenv import load_dotenv
import os,time

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

@app.route('/')
def home():
    return "Hello, Flask on Vercel!"

def time_now():
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

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
    
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)
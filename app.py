import os
import json
from flask import Flask, request, jsonify
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from datetime import datetime
import pytz 

app = Flask(__name__)
app.secret_key = os.environ.get("API_SECRET_KEY", "supersecretkey123")
serializer = URLSafeTimedSerializer(app.secret_key)

# BFL login
VALID_USERNAME = os.environ.get("BFL_USERNAME", "bfluser")
VALID_PASSWORD = os.environ.get("BFL_PASSWORD", "bflpass")

# Connect to Google Sheet
cred_json = os.environ.get("GOOGLE_SHEET_CREDENTIALS")
cred_dict = json.loads(cred_json)
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(cred_dict, scope)
client = gspread.authorize(creds)
sheet = client.open("SI-SR-Validation").sheet1

@app.route('/')
def home():
    return "🎉 Pillow EMI Serial Checker is live!"

@app.route('/generateToken', methods=['POST'])
def generate_token():
    data = request.get_json()
    if not data or "username" not in data or "password" not in data:
        return jsonify({"error": "Missing username or password"}), 400

    if data["username"] == VALID_USERNAME and data["password"] == VALID_PASSWORD:
        token = serializer.dumps({"user": data["username"]})
        return jsonify({"token": token, "expiresInSeconds": 600})
    else:
        return jsonify({"error": "Invalid credentials"}), 401

def verify_token(token):
    try:
        serializer.loads(token, max_age=600)
        return True
    except (BadSignature, SignatureExpired):
        return False

@app.route('/ValidateSrNo', methods=['POST'])
def validate_serial():
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return jsonify(responseStatus="-403", responseMessage="Missing or invalid token")

    token = auth_header.split(" ")[1]
    if not verify_token(token):
        return jsonify(responseStatus="-403", responseMessage="Token expired or invalid")

    try:
        data = request.get_json()
        if "serialNumber" not in data:
            return jsonify(responseStatus="-99", responseMessage="Missing serial number")

        serial = data["serialNumber"]
        rows = sheet.get_all_records()

        for row in rows:
            if row["serialNumber"] == serial:
                row_index = rows.index(row) + 2  # +2 because 1st row is header
                if row["isValidated"].lower() == "yes":
                    return jsonify(responseStatus="-3", responseMessage="Serial Number Already Validated")
		ist = pytz.timezone('Asia/Kolkata')
		current_time = datetime.now(ist).strftime('%Y-%m-%d %H:%M:%S')
                sheet.update_cell(row_index, 2, "Yes")           # isValidated (column 2)
                sheet.update_cell(row_index, 3, current_time)    # validatedAt (column 3)

                return jsonify(responseStatus="0", responseMessage="Valid Serial Number")

        return jsonify(responseStatus="-1", responseMessage="Invalid Serial Number")

    except Exception as e:
        return jsonify(responseStatus="-500", responseMessage=f"Internal Error: {str(e)}")

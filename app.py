import os
import json
import time
from flask import Flask, request, jsonify
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer, BadSignature, SignatureExpired

app = Flask(__name__)
app.secret_key = os.environ.get("API_SECRET_KEY", "supersecretkey123")  # Keep it safe!

# Setup token serializer (token lasts for 600 seconds = 10 minutes)
serializer = Serializer(app.secret_key, expires_in=600)

# BFL login credentials (set in env variables or hardcoded for now)
VALID_USERNAME = os.environ.get("BFL_USERNAME", "bfluser")
VALID_PASSWORD = os.environ.get("BFL_PASSWORD", "bflpass")

# Load Google Sheet
cred_json = os.environ.get("GOOGLE_SHEET_CREDENTIALS")
cred_dict = json.loads(cred_json)
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(cred_dict, scope)
client = gspread.authorize(creds)
sheet = client.open("Pillow Serial Numbers").sheet1

@app.route('/')
def home():
    return "🎉 Pillow EMI API is live with token authentication!"

@app.route('/generateToken', methods=['POST'])
def generate_token():
    auth = request.get_json()
    if not auth or "username" not in auth or "password" not in auth:
        return jsonify({"error": "Missing username or password"}), 400

    username = auth["username"]
    password = auth["password"]

    if username == VALID_USERNAME and password == VALID_PASSWORD:
        token = serializer.dumps({"user": username}).decode("utf-8")
        return jsonify({"token": token, "expiresInSeconds": 600})
    else:
        return jsonify({"error": "Invalid credentials"}), 401

def verify_token(token):
    try:
        data = serializer.loads(token)
        return True
    except SignatureExpired:
        return False
    except BadSignature:
        return False

@app.route('/ValidateSrNo', methods=['POST'])
def validate_serial():
    # Step 1: Check for token
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return jsonify(responseStatus="-403", responseMessage="Missing or invalid token")

    token = auth_header.split(" ")[1]
    if not verify_token(token):
        return jsonify(responseStatus="-403", responseMessage="Token expired or invalid")

    # Step 2: Business logic
    try:
        data = request.get_json()
        required_fields = ["materialCode", "serialNumber", "dealerCode", "accessKey"]
        if not all(field in data for field in required_fields):
            return jsonify(responseStatus="-99", responseMessage="Missing required fields")

        serial = data["serialNumber"]
        material = data["materialCode"]
        dealer = data["dealerCode"]

        rows = sheet.get_all_records()
        for row in rows:
            if row["serialNumber"] == serial:
                if row["materialCode"] != material:
                    return jsonify(responseStatus="-2", responseMessage="Mismatch in model and serial number")
                if row["dealerCode"] != dealer:
                    return jsonify(responseStatus="-6", responseMessage="Serial number is not billed to this Dealer")
                if row["isValidated"].lower() == "yes":
                    return jsonify(responseStatus="-3", responseMessage="Serial Number Already Validated")
                return jsonify(responseStatus="0", responseMessage="Valid Serial Number")

        return jsonify(responseStatus="-1", responseMessage="Invalid Serial Number")
    except Exception as e:
        return jsonify(responseStatus="-500", responseMessage=f"Internal Error: {str(e)}")
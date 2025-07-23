import os
import json
from flask import Flask, request, jsonify
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

# === Flask Setup ===
app = Flask(__name__)
app.secret_key = os.environ.get("API_SECRET_KEY", "supersecretkey123")  # Keep secret in env

# === Token Serializer ===
serializer = URLSafeTimedSerializer(app.secret_key)

# === BFL Credentials ===
VALID_USERNAME = os.environ.get("BFL_USERNAME", "bfluser")
VALID_PASSWORD = os.environ.get("BFL_PASSWORD", "bflpass")

# === Connect to Google Sheets ===
cred_json = os.environ.get("GOOGLE_SHEET_CREDENTIALS")
cred_dict = json.loads(cred_json)
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(cred_dict, scope)
client = gspread.authorize(creds)
sheet = client.open("Pillow Serial Numbers").sheet1

# === Home Test ===
@app.route('/')
def home():
    return "🎉 Pillow EMI API is live with token authentication!"

# === Generate Token API ===
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

# === Token Verification ===
def verify_token(token):
    try:
        serializer.loads(token, max_age=600)  # 10 minutes expiry
        return True
    except (BadSignature, SignatureExpired):
        return False

# === Validate Serial Number API ===
@app.route('/ValidateSrNo', methods=['POST'])
def validate_serial():
    # 1. Check for Token
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return jsonify(responseStatus="-403", responseMessage="Missing or invalid token")

    token = auth_header.split(" ")[1]
    if not verify_token(token):
        return jsonify(responseStatus="-403", responseMessage="Token expired or invalid")

    # 2. Main Logic
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
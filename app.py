import os
import json
from flask import Flask, request, jsonify
import gspread
from oauth2client.service_account import ServiceAccountCredentials

app = Flask(__name__)

# Step 1: Load and parse credentials from Render environment variable
cred_json = os.environ.get("GOOGLE_SHEET_CREDENTIALS")

if not cred_json:
    raise ValueError("Missing GOOGLE_SHEET_CREDENTIALS environment variable")

try:
    # Step 2: Convert the JSON string into a dictionary
    cred_dict = json.loads(cred_json)
except Exception as e:
    raise ValueError(f"Could not parse GOOGLE_SHEET_CREDENTIALS: {str(e)}")

# Step 3: Define the scope and connect to Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(cred_dict, scope)
client = gspread.authorize(creds)
sheet = client.open("Pillow Serial Numbers").sheet1  # Make sure this name matches your actual sheet

# Step 4: Create a POST endpoint to validate serial numbers
@app.route('/ValidateSrNo', methods=['POST'])
def validate_serial():
    try:
        data = request.get_json()

        # Check if all required fields are present
        required_fields = ["materialCode", "serialNumber", "dealerCode", "accessKey"]
        if not all(field in data for field in required_fields):
            return jsonify(responseStatus="-99", responseMessage="Missing required fields")

        serial = data["serialNumber"]
        material = data["materialCode"]
        dealer = data["dealerCode"]

        # Read all records from Google Sheet
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

# Step 5: Default homepage to test if API is running
@app.route('/')
def home():
    return "🎉 Pillow EMI API is live!"

# Step 6: Run locally only if this file is executed directly
if __name__ == '__main__':
    app.run(debug=True)

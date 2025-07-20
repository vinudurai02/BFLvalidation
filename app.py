import os
import json
from flask import Flask, request, jsonify
import gspread
from oauth2client.service_account import ServiceAccountCredentials

app = Flask(__name__)

# Use credentials from environment variable (for Render)
cred_json = os.environ.get("GOOGLE_SHEET_CREDENTIALS")

if cred_json:
    cred_dict = json.loads(cred_json)
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(cred_dict, scope)
    client = gspread.authorize(creds)
    sheet = client.open("Pillow Serial Numbers").sheet1
else:
    raise ValueError("Missing Google Sheets credentials")

@app.route('/ValidateSrNo', methods=['POST'])
def validate_serial():
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

if __name__ == '__main__':
    app.run()

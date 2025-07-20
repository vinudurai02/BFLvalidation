import os
import json
from flask import Flask, request, jsonify
import gspread
from oauth2client.service_account import ServiceAccountCredentials

app = Flask(__name__)

# Get raw JSON string from environment
cred_json = os.environ.get("GOOGLE_SHEET_CREDENTIALS")

# Parse string into dictionary (this is critical!)
try:
    cred_dict = json.loads(cred_json)
except Exception as e:
    raise ValueError(f"Error parsing GOOGLE_SHEET_CREDENTIALS: {str(e)}")

# Authorize Google Sheets API
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(cred_dict, scope)
client = gspread.authorize(creds)
sheet = client.open("Validation-test").sheet1

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

        for index, row in enumerate(rows):
            if row["serialNumber"] == serial:
                if row["materialCode"] != material:
                    return jsonify(responseStatus="-2", responseMessage="Mismatch in model and serial number")
                if row["dealerCode"] != dealer:
                    return jsonify(responseStatus="-6", responseMessage="Serial number is not billed to this Dealer")
                if row["isValidated"].lower() == "yes":
                    return jsonify(responseStatus="-3", responseMessage="Serial Number Already Validated")

                # ✅ Mark this serial number as validated in the sheet
                cell_row = index + 2  # +2 because Google Sheets is 1-indexed and row 1 is headers
                sheet.update_cell(cell_row, 4, "Yes")  # Column 4 is "isValidated"

                return jsonify(responseStatus="0", responseMessage="Valid Serial Number")

        return jsonify(responseStatus="-1", responseMessage="Invalid Serial Number")
    except Exception as e:
        return jsonify(responseStatus="-500", responseMessage=f"Internal Error: {str(e)}")

@app.route('/')
def home():
    return "🎉EMI API is live!"

if __name__ == '__main__':
    app.run(debug=True)

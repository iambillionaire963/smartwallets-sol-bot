import os
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials

scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']

json_str = os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON')
if not json_str:
    raise Exception("Environment variable GOOGLE_SERVICE_ACCOUNT_JSON not set")

creds_dict = json.loads(json_str)
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)

gc = gspread.authorize(creds)

# Open your sheet by name here
SPREADSHEET_NAME = "SmartWalletsLog"
sh = gc.open(SPREADSHEET_NAME)
worksheet = sh.sheet1  # Use the first worksheet

def log_user(data):
    """
    Append a row to the Google Sheet.
    data: list of values, e.g. ["timestamp", "user_id", "action"]
    """
    worksheet.append_row(data)

import os
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

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

def log_user(user_id, first_name=None, username=None):
    """
    Append a row to the Google Sheet.
    Each row contains: timestamp (UTC), user_id, first_name, username
    """
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    row = [timestamp, user_id, first_name, username]
    worksheet.append_row(row)

from datetime import datetime

def log_user(user_id, first_name=None, username=None):
    try:
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        row = [timestamp, user_id, first_name, username]
        worksheet.append_row(row)
    except Exception as e:
        print(f"[Google Sheets] Error logging user: {e}")

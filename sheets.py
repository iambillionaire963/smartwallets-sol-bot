import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# Define the scope and authorize client
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("service_account.json", scope)
client = gspread.authorize(creds)

# Open the spreadsheet using the URL
sheet = client.open_by_url("https://docs.google.com/spreadsheets/d/1-6k994osXh2vGO7DThlgRdsGtcchwTePoKqY_fGFxjc/edit#gid=0").sheet1

def log_user(user_id, first_name, username, is_member=False):
    joined_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    username = username or ""
    is_member = "Yes" if is_member else "No"

    data = [str(user_id), first_name, username, is_member, joined_at]
    sheet.append_row(data)

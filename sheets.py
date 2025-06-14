import os
import json
from oauth2client.service_account import ServiceAccountCredentials

scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']

json_str = os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON')
if not json_str:
    raise Exception("Environment variable GOOGLE_SERVICE_ACCOUNT_JSON not set")

creds_dict = json.loads(json_str)
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)

import json

bot_token = "8721782525:AAHVZqkMea-zlo5k3rBxpW6G9pZKbjoa5Kk"

data = json.loads(open('service_account.json').read())
clean = json.dumps(data)

with open('.env', 'w') as f:
    f.write('BOT_TOKEN=' + bot_token + '\n')
    f.write('GOOGLE_SERVICE_ACCOUNT_JSON=' + clean + '\n')

print('Listo')
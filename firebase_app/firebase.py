import os
import json
import requests
from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2 import service_account
from firebase_admin import messaging




def generate_firebase_auth_key():
    scopes = ['https://www.googleapis.com/auth/firebase.messaging']
    
    credentials_path = os.getenv('FIREBASE_CREDENTIAL_PATH')

    credentials = service_account.Credentials.from_service_account_file(
        credentials_path, scopes=scopes
    )

    credentials.refresh(Request())
    access_token = credentials.token

    return access_token
   

def send_push_notification(auth_token, fcm_token):
    url = "https://fcm.googleapis.com/v1/projects/notification-1622c/messages:send"
    
    payload = json.dumps({
        "message": {
            "token": fcm_token,
            "notification": {
                "title": "Your file is uploaded and backup is created ",
                "body": "You can restore your file if deleted "
            },
            "data": {
                "key1": "value1",
                "key2": "value2"
            }
        }
    })
    
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {auth_token}'
    }

    print("Payload:", payload)
    print("Headers:", headers)
    response = requests.post(url, headers=headers, data=payload)
    print("FCM Response status:", response.status_code)
    print("FCM Response body:", response.text)

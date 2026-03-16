import os
import requests
from dotenv import load_dotenv
from SOCaaSClient import SOCaaSClient

load_dotenv()

AUTH_URL = os.getenv('AUTH_URL')
USERNAME = os.getenv('USERNAME')
PASSWORD = os.getenv('PASSWORD')
CLIENT_ID = os.getenv('CLIENT_ID')
BASE_URL = os.getenv('BASE_URL')

def main():
    client = SOCaaSClient(
        username=USERNAME,
        password=PASSWORD,
        client_id=CLIENT_ID,
        authentication_url=AUTH_URL,
        base_url=BASE_URL
    )

    try:
        response = client.request("GET", "/socaasAPI/v1/alert")
        print(response)
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()

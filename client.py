import components.config as config

import requests
import json


if __name__ == "__main__":

    # API_URL = "http://127.0.0.1:8000"

    try:
        results = requests.get(f"{config.API_URL}/coe/", json={'coe_name': 'PV'}).json()
        print('\n', print(json.dumps(results, indent=4)), '\n')

        resume = requests.get(f"{config.API_URL}/code/", json={'code': 'ROD'}).json()
        print('\n', "LLM Summary: \n", resume['answer'], '\n')

    except Exception as e:
        print(f"An error occurred: {e}")

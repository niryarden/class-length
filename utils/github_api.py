import json
import os
import requests


def make_requests_to_github_api(api_url, params={}):
    GITHUB_TOKEN = os.environ['GITHUB_TOKEN']
    headers = {'Authorization': 'token %s' % GITHUB_TOKEN}
    response = requests.get(api_url, headers=headers, params=params)
    output_json = json.loads(response.text)
    return output_json

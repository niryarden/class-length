import json
import os
import logging
import time
import datetime

import requests


GITHUB_TOKEN = os.environ['GITHUB_TOKEN']
logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")


def handle_search_rate_limit(response):
    # if the request triggered the abuse detection mechanism of Github API and response is broken.. wait the 'Retry-After' time and rerun the request.
    if "message" in json.loads(response.text) and response.status_code == 403:
        reset_time_stamp = int(response.headers["X-RateLimit-Reset"])
        retry_after = reset_time_stamp - time.time() + 2
        logging.info(f"Reached Github search API rate limit. waiting {retry_after} seconds")
        time.sleep(int(retry_after))
        new_response = requests.get(response.request.url, headers=response.request.headers)
        return new_response
    return response


def handle_repo_rate_limit(response):
    logging.info("repos api reached its rate limit, waiting for reset...")
    rate_limit_url = "https://api.github.com/rate_limit"
    headers = {'Authorization': f'token {GITHUB_TOKEN}'}

    waiting_for_reset = True
    while waiting_for_reset:
        res_rate_limit = requests.get(rate_limit_url, headers=headers)
        rate_limit_data = json.loads(res_rate_limit.text)
        if rate_limit_data["rate"]["remaining"] > 0:
            waiting_for_reset = False
            continue
        time_to_wait = datetime.datetime.fromtimestamp(rate_limit_data["rate"]["reset"]) - datetime.datetime.now()
        seconds_to_wait = int(time_to_wait.total_seconds()) + 5
        logging.info(f"time to reset: {seconds_to_wait} seconds")
        time.sleep(seconds_to_wait)
    new_response = requests.get(response.request.url, headers=response.request.headers)
    return new_response
# The following script is separated from the rest of the scanner, and is being run manually only.
# The script automatically generates a list of repositories, which is later used for the Rookout Logs Report.
# The script takes the 5,000 most popular (most starred) repositories in Github, which are written in one of the supported languages, and runs few "sanity" checks on them.
# A repository who entered the final list has passed the following tests:
#   It is an active repo, which means it had a commit in the last 50 days.
#   It has an English description which does not contain the words: "learn", "tutorial", "book", "guide", "Examples", "Introduction", "Course".
#   It has more than 15 files written in the main programming language it is tagged under.

import os
import json
import datetime
import time
import string
import logging

import requests
import langid

GITHUB_TOKEN = os.environ['GITHUB_TOKEN']
logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")

# WISHED_LIST_SIZE = 5000
# PER_PAGE = 100
WISHED_LIST_SIZE = 100
PER_PAGE = 10

LANG = "JAVA"
DAYS_LIMIT = 100
MIN_CODE_FILES = 100
MIN_CONTRIBUTORS = 3



def handle_search_rate_limit(response):
    # if the request triggered the abuse detection mechanism of Github API and response is broken.. wait the 'Retry-After' time and rerun the request.
    if "message" in json.loads(response.text) and response.status_code == 403:
        reset_time_stamp = response.headers["X-RateLimit-Reset"]
        retry_after = int(reset_time_stamp) - time.time()
        logging.info(f"Reached Github search API rate limit. waiting {retry_after} seconds")
        time.sleep(int(retry_after))
        new_response = requests.get(response.request.url, headers=response.request.headers)
        return new_response
    return response


def handle_repo_rate_limit():
    logging.info("repos api reached its rate limit, waiting for reset...")
    rate_limit_url = "https://api.github.com/rate_limit"
    headers = {'Authorization': f'token {GITHUB_TOKEN}'}
    response = requests.get(rate_limit_url, headers=headers)
    rete_limit_data = json.loads(response.text)
    reset_time_stamp = rete_limit_data["rate"]["reset"]
    waiting_status = True
    while waiting_status:
        if time.time() > reset_time_stamp:
            waiting_status = False
        else:
            time_to_wait = datetime.datetime.fromtimestamp(reset_time_stamp) - datetime.datetime.now()
            logging.info(f"time to reset: {int(time_to_wait.total_seconds())} seconds")
            time.sleep(30)


def check_if_bad_description(repo):
    repo_description = repo["description"]
    repo_name = repo["full_name"]
    if repo_description is None:
        logging.info(f"repo ({repo_name}) was filtered due to empty description")
        return True

    description_language = langid.classify(repo_description)[0]
    if description_language != 'en':
        logging.info(
            f"repo ({repo_name}) was filtered due to description language - {description_language}")
        return True

    # clean description
    punctuation = string.punctuation + "0123456789"
    for char in punctuation:
        repo_description = repo_description.replace(char, '')

    key_words = ["learn", "learning", "tutorial", "tutorials", "book", "books", "guide", "guides", "Example",
                 "Examples", "Introduction", "Introductions", "Course", "Courses"]
    for key_word in key_words:
        if key_word.upper() in repo_description.upper():
            logging.info(
                f"repo ({repo_name}) was filtered due to use of prohibited key_word in the description - '{key_word}'")
            return True
    return False


def check_if_too_few_code_files(repo):
    repo_name = repo["full_name"]
    api_url = f"https://api.github.com/search/code?q=language:{LANG}+repo:{repo_name}"
    headers = {'Authorization': f'token {GITHUB_TOKEN}'}
    response = requests.get(api_url, headers=headers)
    response = handle_search_rate_limit(response)

    search_results = json.loads(response.text)
    if "total_count" not in search_results or search_results["total_count"] < MIN_CODE_FILES:
        try:
            logging.info(
                f"repo ({repo_name}) was filtered due to amount of code files - {search_results['total_count']} files only")
        except:
            logging.error("no total_count")
            logging.error(search_results)
        return True

    return False


def check_if_not_active(repo):  # check if there were any commits in last 50 days
    repo_name = repo["full_name"]
    commit_api_url = f"https://api.github.com/repos/{repo_name}/commits"
    headers = {
        'Authorization': 'token %s' % GITHUB_TOKEN
    }
    response = requests.get(commit_api_url, headers=headers)
    if int(response.headers["X-RateLimit-Remaining"]) == 1:
        handle_repo_rate_limit()
    commit_date = datetime.date.fromisoformat(json.loads(response.text)[0]["commit"]["committer"]["date"][:10])
    delta = datetime.date.today() - commit_date
    if delta.days > DAYS_LIMIT:
        logging.info(f"repo ({repo_name}) was filtered because not active - {delta.days} days")
        return True
    return False


def check_if_fork(repo):
    if repo["fork"]:
        logging.info(f"repo ({repo['full_name']}) was filtered because it is a fork")
        return True
    return False

def check_if_too_few_contributors(repo):
    status = True
    counter = 0
    sum_contributors = 0
    while status:
        counter = counter + 1
        contributors_url = repo["contributors_url"]
        params = {
            'anon': '1',
            'page': str(counter)
        }
        headers = {'Authorization': f'token {GITHUB_TOKEN}'}
        response = requests.get(contributors_url, headers=headers, params=params)
        if int(response.headers["X-RateLimit-Remaining"]) == 1:
            handle_repo_rate_limit()
        data = json.loads(response.text)
        sum_contributors = sum_contributors + len(data)
        if len(data) == 0:
            status = False
        if sum_contributors > MIN_CONTRIBUTORS:
            return False

    if sum_contributors < MIN_CONTRIBUTORS:
        logging.info(f"repo ({repo['full_name']}) was filtered because it has less than {MIN_CONTRIBUTORS} contributors")
        return True
    return False


def sanity_check(repo):
    if check_if_fork(repo):  # no further requests
        return False

    if check_if_bad_description(repo):  # no further requests
        return False

    if check_if_not_active(repo):  # single repos request
        return False

    if check_if_too_few_contributors(repo):  # single repos request
        return False

    if check_if_too_few_code_files(repo):  # single search request
        return True

    return True


def set_search_request(lang, page, query):
    api_url = f"https://api.github.com/search/repositories"
    headers = {'Authorization': f'token {GITHUB_TOKEN}'}
    params = {
        'q': f'{query} language:{lang}',
        'sort': 'stars',
        'order': 'desc',
        'page': str(page),
        'per_page': f'{PER_PAGE}'
    }
    response = requests.get(api_url, params=params, headers=headers)
    response = handle_search_rate_limit(response)
    search_results = json.loads(response.text)
    return search_results


def collect_repos():
    output = []
    query = ""
    page_reduce_amount = 0
    for i in range(1, int(WISHED_LIST_SIZE  / PER_PAGE) + 1, 1):
        page = i - page_reduce_amount
        search_results = set_search_request(LANG, page, query)

        for index, repo in enumerate(search_results['items']):
            check = sanity_check(repo)
            # try:
            #     check = sanity_check(repo)
            # except KeyboardInterrupt:
            #     quit()
            # except Exception as e:
            #     logging.error(f"!!!!!! skipped {index + 1} {repo['full_name']}")
            #     logging.error(e)
            #     continue
            if check:
                output.append(repo['html_url'])
                logging.info(
                    f"repo ({repo['full_name']}) was approved --- page {page + page_reduce_amount}. {len(output)}/{WISHED_LIST_SIZE} done.")

            if page == 10 and index == PER_PAGE - 1:
                last_repo_stars = repo["stargazers_count"]
                query = f"stars:<{last_repo_stars}"
                page_reduce_amount = i


    logging.info(">>>")
    logging.info(f"{len(output)} repositories approved")
    logging.info("<<<")

    output = list(set(output))  # remove duplicates
    with open(os.path.join("inputs", "repositories_list.txt"), 'w') as output_file:
        for repo in output:
            output_file.write(repo + "\n")


if __name__ == "__main__":
    collect_repos()

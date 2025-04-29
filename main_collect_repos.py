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


def handle_search_rate_limit(response):
    # if the request triggered the abuse detection mechanism of Github API and response is broken.. wait the 'Retry-After' time and rerun the request.
    if "message" in json.loads(response.text):
        retry_after = response.headers["Retry-After"]
        logging.info(f"triggered Github API's abuse detection mechanism. waiting {retry_after} seconds")
        time.sleep(int(retry_after))
        new_response = requests.get(response.request.url, headers=response.request.headers)
        return new_response

    # if the request brought me close to rate limit but the response isn't broken - wait and return it as is
    if "X-RateLimit-Remaining" in response.headers:
        if int(response.headers["X-RateLimit-Remaining"]) in [1, 0]:
            logging.info("waiting 20 seconds in order to avoid search api rate limit")
            time.sleep(20)
        return response
    else:  # for unknown reason, sometimes the "X-RateLimit-Remaining" header isn't supplied in github's response and it is needed to check seperatelly using the api.
        rate_limit_url = "https://api.github.com/rate_limit"
        headers = {'Authorization': f'token {GITHUB_TOKEN}'}
        r = requests.get(rate_limit_url, headers=headers)
        rete_limit_data = json.loads(r.text)
        if rete_limit_data["resources"]["search"]["remaining"] in [1, 0]:
            logging.info("waiting 20 seconds in order to avoid search api rate limit")
            time.sleep(20)
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


def check_if_not_a_code_repo(repo_description, lang, repo_name, index):
    if repo_description is None:
        logging.info(f"repo number {index} ({repo_name}) was denied due to empty description")
        return True

    description_language = langid.classify(repo_description)[0]
    if description_language != 'en':
        logging.info(
            f"repo number {index} ({repo_name}) was denied due to description language - {description_language}")
        return True

    # clean discription
    punctuation = string.punctuation + "0123456789"
    for char in punctuation:
        repo_description = repo_description.replace(char, '')

    key_words = ["learn", "learning", "tutorial", "tutorials", "book", "books", "guide", "guides", "Example",
                 "Examples", "Introduction", "Introductions", "Course", "Courses"]
    for key_word in key_words:
        if key_word.upper() in repo_description.upper():
            logging.info(
                f"repo number {index} ({repo_name}) was denied due to use of prohibited key_word in the description - '{key_word}'")
            return True

    minimun_amount_of_code_files = 15
    api_url = f"https://api.github.com/search/code?q=language:{lang}+repo:{repo_name}"
    headers = {'Authorization': f'token {GITHUB_TOKEN}'}
    response = requests.get(api_url, headers=headers)
    response = handle_search_rate_limit(response)

    search_results = json.loads(response.text)
    if "total_count" not in search_results or search_results["total_count"] < minimun_amount_of_code_files:
        try:
            logging.info(
                f"repo number {index} ({repo_name}) was denied due to amount of code files - {search_results['total_count']} files only")
        except:
            logging.error("no total_count")
            logging.error(search_results)
        return True

    return False


def check_if_not_active(repo_name, index):  # check if there were any commits in last 50 days
    days_limit = 50
    commit_api_url = f"https://api.github.com/repos/{repo_name}/commits"
    headers = {
        'Authorization': 'token %s' % GITHUB_TOKEN
    }
    response = requests.get(commit_api_url, headers=headers)
    if int(response.headers["X-RateLimit-Remaining"]) == 1:
        handle_repo_rate_limit()
    commit_date = datetime.date.fromisoformat(json.loads(response.text)[0]["commit"]["committer"]["date"][:10])
    delta = datetime.date.today() - commit_date
    if delta.days > days_limit:
        logging.info(f"repo number {index} ({repo_name}) was denied because not active - {delta.days} days")
        return True
    return False


def sanity_check(repo, lang, index):
    if check_if_not_active(repo["full_name"], index):
        return False

    if check_if_not_a_code_repo(repo["description"], lang, repo["full_name"], index):
        return False

    return True


def set_search_request(lang, page, query):
    api_url = f"https://api.github.com/search/repositories"
    headers = {'Authorization': f'token {GITHUB_TOKEN}'}
    params = {
        'q': f'{query} language:{lang}',
        'sort': 'stars',
        'order': 'desc',
        'page': str(page),
        'per_page': '100'
    }
    response = requests.get(api_url, params=params, headers=headers)
    response = handle_search_rate_limit(response)
    search_results = json.loads(response.text)
    return search_results


def collect_repos():
    output = []
    langs = ["Java"]

    # modify the wished size of list to fit the github api. calc how many response pages needed per language.
    wished_list_size = 5000
    addition = wished_list_size % (len(langs) * 100)
    wished_list_size += addition
    pages_per_lang = int(wished_list_size / len(langs) / 100)

    langs_division = {}
    output_len_reducer = 0

    for lang in langs:
        query = ""
        page_reduce_amount = 0
        for i in range(1, pages_per_lang + 1, 1):
            page = i - page_reduce_amount
            search_results = set_search_request(lang, page, query)

            for index, repo in enumerate(search_results['items']):
                try:
                    check = sanity_check(repo, lang, index + 1)
                except KeyboardInterrupt:
                    quit()
                except Exception as e:
                    logging.error(f"!!!!!! skipped {index + 1} {repo['full_name']}")
                    logging.error(e)
                    continue
                if check:
                    output.append(repo['html_url'])
                    logging.info(
                        f"repo number {index + 1} ({repo['full_name']}) was approved --- {lang} page {page + page_reduce_amount}")

                if page == 10 and index == 99:
                    last_repo_stars = repo["stargazers_count"]
                    query = f"stars:<{last_repo_stars}"
                    page_reduce_amount = i

        langs_division[lang] = len(output) - output_len_reducer
        output_len_reducer = len(output)

    logging.info(">>>")
    for lang in langs_division.keys():
        logging.info(f"{lang} -- {langs_division[lang]} repositories approved")
    logging.info("<<<")

    output = list(set(output))  # remove duplicates
    with open(os.path.join("inputs", "repositories_list.txt"), 'w') as output_file:
        for repo in output:
            output_file.write(repo + "\n")


if __name__ == "__main__":
    collect_repos()

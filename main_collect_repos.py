import os
import json
import datetime
import string
import logging

import requests
import langid

from libs.github_api import handle_repo_rate_limit, handle_search_rate_limit

GITHUB_TOKEN = os.environ['GITHUB_TOKEN']
logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")

WISHED_LIST_SIZE = 4000
PER_PAGE = 100

LANG = "JAVA"
DAYS_LIMIT = 365
MIN_CODE_FILES = 50
MIN_CONTRIBUTORS = 3

BOOK_KEYWORDS = ["learn", "learning", "tutorial", "tutorials", "book", "books", "guide", "guides", "Example",
                 "Examples", "Introduction", "Introductions", "Course", "Courses", "Getting Started"]



BAD_DESCRIPTION = "bad_description"
TOO_FEW_CODE_FILES = "too_few_code_files"
NOT_ACTIVE = "not_active"
TOO_FEW_CONTRIBUTORS = "too_few_contributors"
FORK = "fork"
rejection_reason_histogram = {
    BAD_DESCRIPTION: 0,
    TOO_FEW_CODE_FILES: 0,
    NOT_ACTIVE: 0,
    TOO_FEW_CONTRIBUTORS: 0,
    FORK: 0
}


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


    for key_word in BOOK_KEYWORDS:
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


def check_should_collect_repo(repo):
    if check_if_fork(repo):  # no further requests
        rejection_reason_histogram[FORK] += 1
        return False

    if check_if_bad_description(repo):  # no further requests
        rejection_reason_histogram[BAD_DESCRIPTION] += 1
        return False

    if check_if_not_active(repo):  # single repos request
        rejection_reason_histogram[NOT_ACTIVE] += 1
        return False

    if check_if_too_few_contributors(repo):  # single repos request
        rejection_reason_histogram[TOO_FEW_CONTRIBUTORS] += 1
        return False

    if check_if_too_few_code_files(repo):  # single search request
        rejection_reason_histogram[TOO_FEW_CODE_FILES] += 1
        return False

    return True


def set_search_request(query, page):
    api_url = f"https://api.github.com/search/repositories"
    headers = {'Authorization': f'token {GITHUB_TOKEN}'}
    params = {
        'q': f'{query} language:{LANG}',
        'sort': 'stars',
        'page': str(page),
        'order': 'desc',
        'per_page': f'{PER_PAGE}'
    }
    response = requests.get(api_url, params=params, headers=headers)
    response = handle_search_rate_limit(response)
    search_results = json.loads(response.text)
    return search_results


def save_output(output_lst):
    logging.info(">>>")
    logging.info(f"{len(output_lst)} repositories approved")
    logging.info("<<<")

    with open(os.path.join("inputs", "repositories_list.txt"), 'w') as output_file:
        for repo in output_lst:
            output_file.write(repo + "\n")

    with open(os.path.join("outputs", "rejection_reasons.json"), 'w') as output_file:
        json.dump(rejection_reason_histogram, output_file, indent=4)


def collect_repos():
    output_lst = []
    last_repo_stars = 100000
    page = 0
    while len(output_lst) < WISHED_LIST_SIZE and last_repo_stars > 0:
        try:
            search_results = set_search_request(f"stars:<{last_repo_stars}", page)
            repos = search_results['items']
        except Exception as e:
            logging.error("Broken", exc_info=True)
            save_output(output_lst)
            quit()
        for index, repo in enumerate(repos):
            try:
                should_collect_repo = check_should_collect_repo(repo)
            except KeyboardInterrupt:
                quit()
            except Exception as e:
                logging.error(f"!!!!!! skipped {index + 1} {repo['full_name']}", exc_info=True)
                continue
            if should_collect_repo:
                output_lst.append(repo['html_url'])
                logging.info(
                    f"repo ({repo['full_name']}) was approved - {len(output_lst)}/{WISHED_LIST_SIZE} done.")
        try:
            if repos[-1]["stargazers_count"] == last_repo_stars:
                page += 1
            else:
                last_repo_stars = repos[-1]["stargazers_count"]
                page = 0
        except Exception as e:
            logging.error("Broken", exc_info=True)
            save_output(output_lst)
            quit()

    save_output(output_lst)


if __name__ == "__main__":
    collect_repos()

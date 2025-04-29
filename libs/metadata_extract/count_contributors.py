import os
from utils.github_api import make_requests_to_github_api


def count_contributors(repo_url):
    user = repo_url.split("/")[-2]
    project = repo_url.split("/")[-1]
    status = True
    counter = 0
    sum_contributors = 0
    while status:
        counter = counter + 1
        api_url = f"https://api.github.com/repos/{user}/{project}/contributors"
        params = {
            'anon': '1',
            'page': str(counter)
        }
        data = make_requests_to_github_api(api_url, params)
        sum_contributors = sum_contributors + len(data)
        if len(data) == 0:
            status = False
    return sum_contributors

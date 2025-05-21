import os
import json

import requests

from libs.github_api import handle_repo_rate_limit


GITHUB_TOKEN = os.environ['GITHUB_TOKEN']
HEADERS = {"Authorization": f"token {GITHUB_TOKEN}"}


def extract_repo_info(url):
    parts = url.strip().split('/')
    if len(parts) >= 5:
        return parts[3], parts[4]
    return None, None


def get_all_contributors(owner, repo):
    status = True
    counter = 0
    contributors = []
    url = f"https://api.github.com/repos/{owner}/{repo}/contributors"
    while status:
        counter = counter + 1
        params = {
            'anon': '1',
            'page': str(counter)
        }
        headers = {'Authorization': f'token {GITHUB_TOKEN}'}
        response = requests.get(url, headers=headers, params=params)
        if int(response.headers["X-RateLimit-Remaining"]) == 1:
            handle_repo_rate_limit()
        data = json.loads(response.text)
        contributors.extend(data)
        if len(data) == 0:
            status = False
    return contributors


def get_repo_metadata(owner, repo):
    url = f"https://api.github.com/repos/{owner}/{repo}"
    response = requests.get(url, headers=HEADERS)
    if response.status_code != 200:
        print(f"Error fetching metadata for {owner}/{repo}: {response.status_code}")
        return {}

    data = response.json()

    metadata = {
        "main_lang": data.get("language"),
        "license_type": data.get("license", {}).get("spdx_id") if data.get("license") else "NO_LICENSE",
        "owner_type": data.get("owner", {}).get("type"),  # "User" or "Organization"
        "count_forks": data.get("forks_count", 0),
        "count_stars": data.get("stargazers_count", 0),
        "count_watches": data.get("subscribers_count", 0)
    }

    return metadata


def get_contribution_friendly_metrics(repo_path):
    files_to_check = [
        'CONTRIBUTING.md',
        'CODE_OF_CONDUCT.md',
        os.path.join('.github', 'CONTRIBUTING.md'),
        os.path.join('.github', 'CODE_OF_CONDUCT.md')
    ]

    contributing_guidance_file = any(os.path.isfile(os.path.join(repo_path, file)) for file in files_to_check)

    readme_keywords = [
        'contribute', 'contributing', 'how to contribute', 'developer setup'
    ]
    readme_path = os.path.join(repo_path, 'README.md')
    readme_mentions_contributing = False
    if os.path.isfile(readme_path):
        with open(readme_path, 'r', encoding='utf-8', errors='ignore') as f:
            text = f.read().lower()
            readme_mentions_contributing = any(keyword in text for keyword in readme_keywords)

    return {
        "contributing_guidance_file": contributing_guidance_file,
        "readme_mentions_contributing": readme_mentions_contributing
    }


def get_repo_contributors_distribution(url, current_clone_location):
    owner, repo = extract_repo_info(url)
    if not (owner and repo):
        return []

    contributors = get_all_contributors(owner, repo)
    if not contributors:
        return []

    distribution = sorted([c.get('contributions', 0) for c in contributors], reverse=True)
    total_contributions = sum(distribution)

    metadata = get_repo_metadata(owner, repo)
    contribution_friendly_metrics = get_contribution_friendly_metrics(current_clone_location)

    record = {
        "repo": f"{owner}/{repo}",
        **metadata,
        **contribution_friendly_metrics,
        "total_contributors": len(contributors),
        "total_contributions": total_contributions,
        "contributors_distribution": distribution
    }
    return record

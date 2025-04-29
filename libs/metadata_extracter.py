import os
from libs.metadata_extract.used_langs import used_langs
from libs.metadata_extract.is_open_source import is_open_source
from libs.metadata_extract.count_contributors import count_contributors
from utils.github_api import make_requests_to_github_api


def extract_metadata(repo_url, current_clone_location):
    user = repo_url.split("/")[-2]
    project = repo_url.split("/")[-1]
    api_url = f"https://api.github.com/repos/{user}/{project}"
    repo_data = make_requests_to_github_api(api_url)

    metadata = {
        "repo_url": repo_url,
        "project_name": project,
        "company/user": user,
        "used_langs": used_langs(current_clone_location),
        "main_lang": repo_data["language"],
        "license_type": is_open_source(repo_data),
        "is_private_or_organization": repo_data["owner"]["type"],
        "count_forks": repo_data["forks_count"],
        "count_watches": repo_data["subscribers_count"],
        "count_stars": repo_data["stargazers_count"],
        "count_contributors": count_contributors(repo_url)
    }

    return metadata

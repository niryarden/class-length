import os
import sys
import shutil
import random
import stat
import string
import logging

from git import Repo

try: # macOS
    BASE_CLONE_LOCATION = os.path.join(os.path.dirname(sys.modules['__main__'].__file__), "current_clone")
except: # Windows
    BASE_CLONE_LOCATION = os.path.join(os.getcwd(), "current_clone")

try:
    GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]
except:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
    logging.error("GITHUB_TOKEN must be supplied as environment variable")
    quit()


def generate_random_key():
    letters = string.ascii_lowercase
    return ''.join(random.choice(letters) for i in range(12))


def clone_repository(repo_url):
    current_clone_location = os.path.join(BASE_CLONE_LOCATION, generate_random_key())
    creator = repo_url.split("/")[-2]
    project_name = repo_url.split("/")[-1]
    tokenized_repo_url = f"https://{GITHUB_TOKEN}:x-oauth-basic@github.com/{creator}/{project_name}"
    os.makedirs(current_clone_location, exist_ok=True)
    Repo.clone_from(tokenized_repo_url, current_clone_location)
    return current_clone_location

# handles deleting readonly files with shutil
def remove_readonly(func, path, excinfo):
    os.chmod(path, stat.S_IWRITE)
    func(path)


def delete_currently_cloned_repository(current_clone_location):
    if (os.path.exists(current_clone_location)):
        shutil.rmtree(current_clone_location, onerror=remove_readonly)

import os


def is_open_source(repo_data):
    repo_license = repo_data["license"]
    if isinstance(repo_license, dict):
        repo_license = repo_license["key"]
    with open(os.path.join("data", "open_source_license.txt"), 'r') as xfile:
        for line in xfile:
            if line.rstrip() == repo_license:
                return "open source"
    return "closed source"

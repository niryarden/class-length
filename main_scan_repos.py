import os
import multiprocessing as mp
import shutil
import logging

import pandas as pd

from libs.cloner import BASE_CLONE_LOCATION, clone_repository, delete_currently_cloned_repository
from libs.class_length import get_class_length_metrics
from libs.contributors import get_repo_contributors_distribution

logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")


def start_with_clean_sheet():
    if os.path.exists(BASE_CLONE_LOCATION):
        shutil.rmtree(BASE_CLONE_LOCATION)


def get_repos_list():
    repos_url = []
    with open(os.path.join("inputs", "repositories_list.txt"), 'r') as repos_txt:
        for line in repos_txt:
            repos_url.append(line.rstrip())
    logging.info(f"Received {len(repos_url)} repositories")
    return repos_url


def handle_repo(args):
    repo_url, counter, lock = args
    with lock:
        counter.value += 1
        index = counter.value
    logging.info(f"running repo number {index}")

    try:
        current_clone_location = clone_repository(repo_url)
    except Exception as e:
        logging.error(f"skiping repository number {index} due to clone fail: {repo_url}")
        logging.error(e, exc_info=True)
        return None

    try:
        class_length_metrics = get_class_length_metrics(current_clone_location)
        if class_length_metrics is None:
            delete_currently_cloned_repository(current_clone_location)
            logging.info(f"skipped repo number {index}")
            return None

        contributors_metrics = get_repo_contributors_distribution(repo_url, current_clone_location)
        delete_currently_cloned_repository(current_clone_location)
        logging.info(f"finished repo number {index}")
        return {**contributors_metrics, **class_length_metrics}
    except Exception as e:
        delete_currently_cloned_repository(current_clone_location)
        logging.error(f"skiping repository number {index} due to an error: {repo_url}")
        logging.error(e, exc_info=True)
        return None


def save_output(all_metrics):
    df = pd.DataFrame(all_metrics)
    pathToFile = os.path.join("outputs", "output.parquet")
    df.to_parquet(pathToFile, index=False)  # or engine="fastparquet"


def delete_leftovers():
    delete_currently_cloned_repository(BASE_CLONE_LOCATION)


def main_scan_repos():
    GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]
    if GITHUB_TOKEN:
        start_with_clean_sheet()
        repos_url = get_repos_list()
        
        with mp.Manager() as manager:
            counter = manager.Value('i', 0)
            lock = manager.Lock()

            with mp.Pool(mp.cpu_count()) as pool:
                metrics_metadata_results = pool.map_async(handle_repo,
                      [(repo_url, counter, lock) for repo_url in repos_url]).get()
                pool.close()
                pool.join()

        save_output([item for item in metrics_metadata_results if item is not None])
        delete_leftovers()
    else:
        logging.error("GITHUB_TOKEN must be supplied as environment variable")
        quit()

if __name__ == "__main__":
    main_scan_repos()

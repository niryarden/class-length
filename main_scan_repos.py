import os
import multiprocessing as mp

import shutil
import logging

import pandas as pd

from libs.cloner import BASE_CLONE_LOCATION, clone_repository, delete_currently_cloned_repository
from libs.scanner import scan_repo
from libs.metadata_extracter import extract_metadata
from libs.build_log_string_histogram import build_log_string_histogram

logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")


def start_with_clean_sheet():
    with open(os.path.join("data", "logs_strings.txt"), 'w') as logs_data_histogram_file:
        logs_data_histogram_file.write("")  # create empty file for later appending

    all_logs_record = os.path.join("outputs", "all_logs_record")  # delete the contents of outputs/all_logs_record  directory.
    if (os.path.exists(all_logs_record)):
        shutil.rmtree(all_logs_record)
    os.mkdir(os.path.join("outputs", "all_logs_record"))


def extract_repos_list():
    repos_url = []
    with open(os.path.join("inputs", "repositories.txt"), 'r') as repos_txt:
        for line in repos_txt:
            repos_url.append(line.rstrip())
    logging.info(f"Received {len(repos_url)} repositories")
    return repos_url


def handle_repo(repo):
    # optional: define your ROOKOUT_TOKEN as an environment variable and use Rookout
    ROOKOUT_TOKEN = os.environ.get("ROOKOUT_TOKEN")
    if ROOKOUT_TOKEN:
        import rook
        rook.start()

    index, repo_url = repo
    logging.info(f"running repo number {index + 1}")
    try:
        current_clone_location = clone_repository(repo_url)
        metadata = extract_metadata(repo_url, current_clone_location)
        repo_log_metrics = scan_repo(current_clone_location, repo_url)
        delete_currently_cloned_repository(current_clone_location)
        logging.info(f"finished repo number {index + 1} with {repo_log_metrics['logs_total_amount']} logs detected")
        return repo_log_metrics, metadata
    except Exception as e:
        logging.error(f"skiping repository number {index + 1} due to an error: {repo_url}")
        return -1, -1


def generate_outputs(metrics_metadata_results):
    df = pd.DataFrame(columns=[
        "Repository_URL", "Project_Name", "Creator",
        "Organization_or_User", "Contributors", "License_Type",
        "Main_Language", "Used_Languages",
        "Total_Amount_of_Logs", "No_Logger_Logs",
        "Debug_Verbosity_Level_Usage",
        "Info_Verbosity_Level_Usage",
        "Warning_Verbosity_Level_Usage",
        "Error_Verbosity_Level_Usage",
        "Critical_Verbosity_LevelsUsage",
        "Amount_of_Files_Which_Contains_Logs",
        "Amount_of_Files_in_Supported_Languages",
        "Files_with_Logs_Divided_by_Total_Files",
        "Amount_of_Lines_in_Supported_Languages",
        "Total_Logs_Divided_by_Total_Lines",
        "Forks", "Stars", "Watchers"
    ])
    for index, repo in enumerate(metrics_metadata_results):
        repo_log_metrics, metadata = repo
        if repo_log_metrics == -1:
            continue
        else:
            df.loc[index] = [
                metadata["repo_url"], metadata["project_name"], metadata["company/user"],
                metadata["is_private_or_organization"], metadata["count_contributors"], metadata["license_type"],
                metadata["main_lang"], metadata["used_langs"],
                repo_log_metrics["logs_total_amount"], repo_log_metrics["no_logger_logs_amount"],
                repo_log_metrics["debug_verbosity_level_usage"],
                repo_log_metrics["info_verbosity_level_usage"],
                repo_log_metrics["warning_verbosity_level_usage"],
                repo_log_metrics["error_verbosity_level_usage"],
                repo_log_metrics["critical_verbosity_level_usage"],
                repo_log_metrics["amount_of_files_which_contains_logs"],
                repo_log_metrics["amount_of_files_in_supported_langs"],
                repo_log_metrics["files_with_logs_devided_by_total_files"],
                repo_log_metrics["amount_of_lines_in_supported_langs"],
                repo_log_metrics["total_logs_devided_by_total_lines"],
                metadata["count_forks"], metadata["count_stars"], metadata["count_watches"]
            ]
    pathToFile = os.path.join("outputs", "output.csv")
    logging.debug(pathToFile)
    df.to_csv(pathToFile, index=False)
    build_log_string_histogram()


def delete_leftovers():
    delete_currently_cloned_repository(BASE_CLONE_LOCATION)
    os.remove(os.path.join("data", "logs_strings.txt"))


def main_scan_repos():
    GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]
    if GITHUB_TOKEN:
        start_with_clean_sheet()

        # multiprocess
        repos_url = extract_repos_list()
        pool = mp.Pool(mp.cpu_count())
        metrics_metadata_results = pool.map_async(handle_repo, [(index, repo_url) for index, repo_url in enumerate(repos_url)]).get()
        pool.close()

        generate_outputs(metrics_metadata_results)
        delete_leftovers()
    else:
        logging.error("GITHUB_TOKEN must be supplied as environment variable")
        quit()

if __name__ == "__main__":
    main_scan_repos()

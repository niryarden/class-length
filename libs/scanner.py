import os
import json
from libs.scan.scan_repo_by_lang import scan_repo_by_lang
from libs.scan.extract_log_metrics import extract_log_metrics
from libs.scan.merge_metrics import merge_metrics
from libs.scan.get_repo_size import amount_of_files_in_supported_langs, amount_of_lines_in_supported_langs


def scan_repo(current_clone_location, repo_url):
    repo_full_name = repo_url.split("/")[-2] + "--" + repo_url.split("/")[-1]

    with open(os.path.join("outputs", "all_logs_record", f"{repo_full_name}.txt"), 'w') as file_content:
        file_content.write("")  # create an empty file which will later record all logs using append.

    scanned_metrics = {  # empty dictionary structure to fill
        'logs_total_amount': 0,
        'no_logger_logs_amount': 0,
        'debug_verbosity_level_usage': 0,
        'info_verbosity_level_usage': 0,
        'warning_verbosity_level_usage': 0,
        'error_verbosity_level_usage': 0,
        'critical_verbosity_level_usage': 0,
        "amount_of_files_which_contains_logs": 0
    }

    with open(os.path.join("data", "regex_logs.json"), 'r') as logs_file:
        logs_book = json.loads(logs_file.read())

    for lang in list(logs_book.keys()):
        matching_files = scan_repo_by_lang(lang, current_clone_location)
        if len(matching_files) > 0:
            lang_logs_list = logs_book[lang]
            new_metrics = extract_log_metrics(lang_logs_list, matching_files, repo_full_name)
            scanned_metrics = merge_metrics(scanned_metrics, new_metrics)

    amount_of_lines = amount_of_lines_in_supported_langs(current_clone_location)
    amount_of_files = amount_of_files_in_supported_langs(current_clone_location)
    additional_metrics = {
        "total_logs_devided_by_total_lines": scanned_metrics["logs_total_amount"] / amount_of_lines,
        "files_with_logs_devided_by_total_files": scanned_metrics["amount_of_files_which_contains_logs"] / amount_of_files,
        "amount_of_lines_in_supported_langs": amount_of_lines,
        "amount_of_files_in_supported_langs": amount_of_files
    }
    scanned_metrics.update(additional_metrics)

    return scanned_metrics

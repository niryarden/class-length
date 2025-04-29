import os
import json
from libs.scan.scan_repo_by_lang import scan_repo_by_lang


def amount_of_lines_in_supported_langs(current_clone_location):
    total_amount = 0
    with open(os.path.join("data", "regex_logs.json"), 'r') as logs_file:
        logs_book = json.loads(logs_file.read())
    for lang in list(logs_book.keys()):
        matching_files = scan_repo_by_lang(lang, current_clone_location)
        if len(matching_files) > 0:
            for code_file in matching_files:
                total_amount += sum(1 for line in open(code_file, 'rb') if len(line.strip()) > 2)
    return total_amount


def amount_of_files_in_supported_langs(current_clone_location):
    total_amount = 0
    with open(os.path.join("data", "regex_logs.json"), 'r') as logs_file:
        logs_book = json.loads(logs_file.read())
    for lang in list(logs_book.keys()):
        matching_files = scan_repo_by_lang(lang, current_clone_location)
        total_amount += len(matching_files)
    return total_amount

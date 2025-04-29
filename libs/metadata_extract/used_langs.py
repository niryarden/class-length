import os
import json


def get_programming_language_by_file_type(file_type):
    with open(os.path.join("data", "file_extension_to_lang.json"), 'r') as file_data:
        programming_file_types = json.loads(file_data.read())
    if file_type in programming_file_types:
        return programming_file_types[file_type]
    else:
        return -1


def scan_repo_for_file_type(current_clone_location):
    total_amount_of_code_files = 0
    langs_histogram = {}
    if os.path.exists(current_clone_location):
        for r, d, f in os.walk(current_clone_location):
            for file_name in f:
                file_type = file_name.split(".")[-1]
                programming_lang = get_programming_language_by_file_type(file_type)
                if programming_lang == -1:
                    continue
                else:
                    total_amount_of_code_files = total_amount_of_code_files + 1
                    if programming_lang in langs_histogram:
                        langs_histogram[programming_lang] = langs_histogram[programming_lang] + 1
                    else:
                        langs_histogram[programming_lang] = 1

    return langs_histogram, total_amount_of_code_files


def used_langs(current_clone_location):
    langs_histogram, total_amount_of_code_files = scan_repo_for_file_type(current_clone_location)
    other_langs_percentage = 0
    final_percentages = {}

    for key in langs_histogram:
        percentage = langs_histogram[key] / total_amount_of_code_files
        if percentage > 0.01:
            final_percentages[key] = percentage
        else:
            other_langs_percentage = other_langs_percentage + percentage

    final_percentages["other_langs"] = other_langs_percentage
    return final_percentages

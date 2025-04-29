import os
import re
import json


def is_exclude(line):
    with open(os.path.join("data", "regex_excludes.json"), 'r') as file_content:
        excludes = json.loads(file_content.read())
    for exclude in excludes:
        if re.search(exclude, line):
            return True
    return False


def extreact_and_store_logged_strings(log, line):
    logged_data = re.findall(log, line.strip())
    try:
        logged_data = logged_data[-1][-1]
    except:
        return
    regexs = ["\"(.*)\"", "'(.*)'"]
    logged_strings = []
    for regex in regexs:
        logged_strings = logged_strings + re.findall(regex, logged_data)
    with open(os.path.join("data", "logs_strings.txt"), 'a') as my_file:
        for log_string in logged_strings:
            my_file.write(log_string + "\n")


def check_line(line, lang_logs_list, repo_full_name):
    for log in lang_logs_list:
        if re.search(log, line.strip()):
            if not is_exclude(line.strip()):
                with open(os.path.join("outputs", "all_logs_record", f"{repo_full_name}.txt"), 'a') as logs_record:
                    logs_record.write(line.strip() + "\n")
                extreact_and_store_logged_strings(log, line)
                return True
    return False

import json
import re
import os


def check_a_log_line(verbosity_division, log_line):
    for level in verbosity_division.keys():
        for option in verbosity_division[level]:
            if re.search(option, log_line):
                return level
    return "No_Level"


def verbosity_levels_usage(list_of_log_lines):
    with open(os.path.join("data", "verbosity_division.json"), 'r') as file_content:
        verbosity_division = json.loads(file_content.read())

    usage = {"No_Level": 0}
    for level in verbosity_division.keys():
        usage[level] = 0

    for log_line in list_of_log_lines:
        level = check_a_log_line(verbosity_division, log_line)
        usage[level] += 1

    no_logger_logs_amount = usage["No_Level"]
    usage["Info"] += usage["No_Level"]
    usage.pop('No_Level', None)

    return usage, no_logger_logs_amount

from libs.scan.check_line import check_line
from libs.scan.verbosity_levels_usage import verbosity_levels_usage


def extract_log_metrics(lang_logs_list, matching_files, repo_full_name):
    found_log_lines = []
    files_with_logs_count = 0
    for code_file in matching_files:
        are_there_logs_in_file = False
        with open(code_file, 'rb') as file_lines:
            for line in file_lines:
                if check_line(line.decode("ISO-8859-1"), lang_logs_list, repo_full_name):
                    found_log_lines.append(line.decode("ISO-8859-1").strip())
                    are_there_logs_in_file = True
        if are_there_logs_in_file:
            files_with_logs_count += 1

    verbosity_levels, no_logger_logs_amount = verbosity_levels_usage(found_log_lines)

    metrics = {
        "logs_total_amount": len(found_log_lines),
        "no_logger_logs_amount": no_logger_logs_amount,
        "debug_verbosity_level_usage": verbosity_levels["Debug"],
        "info_verbosity_level_usage": verbosity_levels["Info"],
        "warning_verbosity_level_usage": verbosity_levels["Warning"],
        "error_verbosity_level_usage": verbosity_levels["Error"],
        "critical_verbosity_level_usage": verbosity_levels["Critical"],
        "amount_of_files_which_contains_logs": files_with_logs_count
    }
    return metrics

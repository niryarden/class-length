def merge_metrics(existing_metrics, new_metrics):
    merged = {
        'logs_total_amount': 0,
        'no_logger_logs_amount': 0,
        'debug_verbosity_level_usage': 0,
        'info_verbosity_level_usage': 0,
        'warning_verbosity_level_usage': 0,
        'error_verbosity_level_usage': 0,
        'critical_verbosity_level_usage': 0,
        "amount_of_files_which_contains_logs": 0
    }

    for key in merged.keys():
        merged[key] = existing_metrics[key] + new_metrics[key]

    return merged

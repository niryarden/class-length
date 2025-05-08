import os
import re


def scan_repo_by_lang(current_clone_location):
    scanned_files = []
    for r, d, f in os.walk(current_clone_location):
        for file_name in f:
            if file_name.split(".")[-1] == "java":
                scanned_files.append(os.path.join(r, file_name))
    return scanned_files


def extract_classes_length(code_file):
    with open(code_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    class_pattern = re.compile(r'^\s*(public|protected|private)?\s*(abstract|final)?\s*class\s+(\w+)\b')
    class_lengths = []
    in_class = False
    brace_count = 0
    start_line = 0

    for i, line in enumerate(lines):
        if not in_class:
            match = class_pattern.match(line)
            if match:
                start_line = i
                brace_count = line.count('{') - line.count('}')
                if brace_count > 0:
                    in_class = True
                else:
                    class_lengths.append(i - start_line + 1)
        else:
            brace_count += line.count('{')
            brace_count -= line.count('}')
            if brace_count == 0:
                class_lengths.append(i - start_line + 1)
                in_class = False

    return class_lengths


def get_class_lengths_metrics(current_clone_location):
    matching_files = scan_repo_by_lang(current_clone_location)
    if len(matching_files) < 100:
        return None
    lengths = []
    for code_file in matching_files:
        lengths.extend(extract_classes_length(code_file))

    metrics = {"class_length_mean": sum(lengths) / len(lengths), "class_length_max": max(lengths),
               "class_length_min": min(lengths), "class_length_median": sorted(lengths)[len(lengths) // 2],
               "java_files_number": len(matching_files), "classes_number": len(lengths),
               "top_10_mean": sum(sorted(lengths)[-10:]) / 10 if len(lengths) > 10 else -1,
               "top_20_mean": sum(sorted(lengths)[-20:]) / 20 if len(lengths) > 20 else -1,
               "top_50_mean": sum(sorted(lengths)[-50:]) / 50 if len(lengths) > 50 else -1,
               "top_100_mean": sum(sorted(lengths)[-100:]) / 100 if len(lengths) > 100 else -1}

    return metrics

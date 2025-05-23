import os
import re
from bdb import effective


def scan_repo_by_lang(current_clone_location):
    scanned_files = []
    for r, d, f in os.walk(current_clone_location):
        for file_name in f:
            if file_name.split(".")[-1] == "java":
                scanned_files.append(os.path.join(r, file_name))
    return scanned_files


def extract_classes_length(code_file):
    with open(code_file, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()

    class_pattern = re.compile(r'^\s*(public|protected|private)?\s*(abstract|final)?\s*class\s+(\w+)\b')
    effective_class_lengths = []
    full_class_lengths = []
    in_class = False
    in_block_comment = False
    brace_count = 0
    full_line_count = 0
    effective_line_count = 0

    for line in lines:
        stripped = line.strip()
        if not in_class:
            match = class_pattern.match(line)
            if match:
                in_class = True
                brace_count = line.count('{') - line.count('}')
                effective_line_count, full_line_count = 1, 1
        else:
            full_line_count += 1
            if in_block_comment:
                if '*/' in stripped:
                    in_block_comment = False
                continue

            if '/*' in stripped:
                if '*/' not in stripped:
                    in_block_comment = True
                continue

            if stripped == "" or stripped.startswith("//"):
                continue

            brace_count += line.count('{') - line.count('}')
            effective_line_count += 1
            if brace_count == 0:
                effective_class_lengths.append(effective_line_count)
                full_class_lengths.append(full_line_count)
                in_class = False

    return full_class_lengths, effective_class_lengths


def get_class_length_metrics(current_clone_location):
    matching_files = scan_repo_by_lang(current_clone_location)
    if len(matching_files) < 50:
        return None
    class_full_lengths, class_effective_lengths = [], []
    for code_file in matching_files:
        full_file_class_lengths, effective_file_class_lengths = extract_classes_length(code_file)
        class_full_lengths.extend(full_file_class_lengths)
        class_effective_lengths.extend(effective_file_class_lengths)

    return {
        "class_full_lengths": sorted(class_full_lengths, reverse=True),
        "class_effective_lengths": sorted(class_effective_lengths, reverse=True),
    }

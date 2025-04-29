import os
import json


def scan_repo_by_lang(lang, current_clone_location):
    with open(os.path.join("data", "lang_to_file_extensions.json"), 'r') as extensions_file:
        lang_extensions = json.loads(extensions_file.read())[lang]
    scanned_files = []
    for r, d, f in os.walk(current_clone_location):
        for file_name in f:
            if file_name.split(".")[-1] in lang_extensions:
                scanned_files.append(os.path.join(r, file_name))
    return scanned_files

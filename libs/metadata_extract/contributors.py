import requests
import pandas as pd
import time

GITHUB_TOKEN = ""
HEADERS = {"Authorization": f"token {GITHUB_TOKEN}"}

def extract_repo_info(url):
    parts = url.strip().split('/')
    if len(parts) >= 5:
        return parts[3], parts[4]
    return None, None

def get_all_contributors(owner, repo):
    contributors = []
    page = 1
    while True:
        url = f"https://api.github.com/repos/{owner}/{repo}/contributors"
        params = {"per_page": 100, "page": page}
        response = requests.get(url, headers=HEADERS, params=params)
        if response.status_code != 200:
            print(f"Error fetching {owner}/{repo}: {response.status_code}")
            break
        data = response.json()
        if not data:
            break
        contributors.extend(data)
        page += 1
        time.sleep(0.5)
    return contributors

def analyze_repo_contributors(url):
    owner, repo = extract_repo_info(url)
    if not (owner and repo):
        return []

    contributors = get_all_contributors(owner, repo)
    if not contributors:
        return []

    total_contributions = sum(c.get('contributions', 0) for c in contributors)
    sorted_contributors = sorted(contributors, key=lambda x: x.get('contributions', 0), reverse=True)

    # אחוזים מהחמישה התורמים הגדולים
    top_percentages = {}
    for i in range(1, 6):
        top_total = sum(c.get('contributions', 0) for c in sorted_contributors[:i])
        top_percentages[f"top_{i}_contributors_percent"] = round((top_total / total_contributions) * 100, 2) if total_contributions else 0.0

    # כמה תרמו בדיוק 1–5 פעמים
    contrib_counts = {i: 0 for i in range(1, 6)}
    for c in contributors:
        count = c.get('contributions', 0)
        if count in contrib_counts:
            contrib_counts[count] += 1

    metadata = get_repo_metadata(owner, repo)

    record = {
        **metadata,
        "repo": f"{owner}/{repo}",
        "total_contributors": len(contributors),
        "total_contributions": total_contributions,
        **top_percentages,
        "one_time_contributors": contrib_counts[1],
        "two_time_contributors": contrib_counts[2],
        "three_time_contributors": contrib_counts[3],
        "four_time_contributors": contrib_counts[4],
        "five_time_contributors": contrib_counts[5]
    }
    return [record]

def get_repo_metadata(owner, repo):
    url = f"https://api.github.com/repos/{owner}/{repo}"
    response = requests.get(url, headers=HEADERS)
    if response.status_code != 200:
        print(f"Error fetching metadata for {owner}/{repo}: {response.status_code}")
        return {}

    data = response.json()

    metadata = {
        "main_lang": data.get("language"),
        "license_type": data.get("license", {}).get("spdx_id") if data.get("license") else None,
        "owner_type": data.get("owner", {}).get("type"),  # "User" or "Organization"
        "count_forks": data.get("forks_count", 0),
        "count_stars": data.get("stargazers_count", 0),
        "count_watches": data.get("subscribers_count", 0)
    }

    return metadata

def main():
    with open("projects.txt", "r") as f:
        urls = [line.strip() for line in f if line.strip()]

    all_results = []
    for url in urls:
        print(f"Processing {url} ...")
        all_results.extend(analyze_repo_contributors(url))

    df = pd.DataFrame(all_results)
    df.to_excel("github_contributors_and_metadata_analysis.xlsx", index=False)
    print("✅ Excel file saved as 'github_contributors_analysis.xlsx'")

if __name__ == "__main__":
    main()

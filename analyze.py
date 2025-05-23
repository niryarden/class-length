import pandas as pd


def analyze():
    df = pd.read_parquet("outputs/output.parquet")
    print(df)

if __name__ == "__main__":
    analyze()

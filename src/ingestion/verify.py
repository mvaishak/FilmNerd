import pandas as pd
from pathlib import Path

DATA_DIR = Path("data/raw")

def verify_data():
    ratings = DATA_DIR / "ratings.csv"

    if not ratings.exists():
        raise FileNotFoundError(f"{ratings} does not exist")

    df = pd.read_csv(ratings)
    
    print("=== Letterboxd Export Verification ===\n")
    print(f"Total rated films:    {len(df)}")
    print(f"Columns:              {list(df.columns)}")
    print(f"\nRating distribution:")
    print(df["Rating"].value_counts().sort_index())
    print(f"\nDate range: {df['Date'].min()} → {df['Date'].max()}")
    print(f"\nSample rows:")
    print(df.head(3).to_string())
    
    # Check for the columns we depend on
    required = {"Name", "Year", "Rating"}
    missing = required - set(df.columns)
    if missing:
        print(f"\n Missing expected columns: {missing}")
    else:
        print(f"\n All required columns present")
        
    unrated = df["Rating"].isna().sum()
    if unrated > 0:
        print(f"  {unrated} entries have no rating — these will be skipped in the taste model")

if __name__ == "__main__":
    verify_data()
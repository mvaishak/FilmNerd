import pandas as pd
from pathlib import Path
from .models import FilmRecord
from typing import Optional


def parse_letterboxd_export(ratings_path: Path, reviews_path: Optional[Path] = None) -> list[FilmRecord]:
    
    
    df = pd.read_csv(ratings_path)
    
    # Load reviews if available — merge on Name + Year
    reviews = {}
    if reviews_path and reviews_path.exists():
        rdf = pd.read_csv(reviews_path)
        for _, row in rdf.iterrows():
            key = (str(row.get("Name", "")), str(row.get("Year", "")))
            reviews[key] = str(row.get("Review", ""))

    records = []
    for _, row in df.iterrows():
        rating_raw = row.get("Rating")
        rating = float(rating_raw) if pd.notna(rating_raw) else None

        key = (str(row.get("Name", "")), str(row.get("Year", "")))
        
        record = FilmRecord(
            title=str(row["Name"]),
            year=int(row["Year"]) if pd.notna(row.get("Year")) else None,
            rating=rating,
            watch_date=str(row["Date"]) if pd.notna(row.get("Date")) else None,
            letterboxd_uri=str(row.get("Letterboxd URI", "")) or None,
            review=reviews.get(key),
        )
        records.append(record)

    rated = [r for r in records if r.rating is not None]
    print(f"Parsed {len(records)} total entries, {len(rated)} with ratings")
    return records
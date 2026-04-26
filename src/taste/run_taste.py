# src/taste/run_taste.py
from ..annotation.store import load_annotations
from ..enrichment.store import load_enriched
from .model import train_taste_model, print_taste_report

def main():
    annotations = load_annotations()
    records     = load_enriched()

    print(f"Loaded {len(annotations)} annotations")
    print(f"Loaded {len(records)} enriched records")

    profile = train_taste_model(annotations, records)
    print_taste_report(profile)

if __name__ == "__main__":
    main()
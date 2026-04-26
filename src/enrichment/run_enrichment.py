# src/enrichment/run_enrichment.py
import asyncio
from pathlib import Path
from ..ingestion.parser import parse_letterboxd_export
from .tmdb import enrich_all, retry_failed
from .store import save_enriched, load_enriched

async def main():
    # Parse Letterboxd export
    records = parse_letterboxd_export(
        ratings_path=Path("data/raw/ratings.csv"),
        reviews_path=Path("data/raw/reviews.csv"),
    )

    # Enrich with TMDB
    enriched = await enrich_all(records)
    # Retry any failures once more, since TMDB can be flaky
    enriched = await retry_failed(enriched)
    
    # Report
    success = sum(1 for r in enriched if r.enriched)
    failed  = sum(1 for r in enriched if r.enrichment_error)
    print(f"\nEnrichment complete: {success} succeeded, {failed} failed")

    # Show a sample of failures so we can diagnose
    failures = [r for r in enriched if r.enrichment_error][:10]
    for f in failures:
        print(f"  ✗ {f.title} ({f.year}): {f.enrichment_error}")

    save_enriched(enriched)

if __name__ == "__main__":
    asyncio.run(main())
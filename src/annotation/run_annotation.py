# src/annotation/run_annotation.py
import json
import time
from pathlib import Path
from tqdm import tqdm
from ..enrichment.store import load_enriched
from .annotator import annotate_film, _cache_path
from .store import save_annotations

def run_annotation_pipeline(limit: int | None = None, rated_only: bool = True):
    records = load_enriched()

    # Filter to enriched, non-TV, rated films
    eligible = [
        r for r in records
        if r.enriched
        and not getattr(r, 'is_tv', False)
        and (not rated_only or r.rating is not None)
    ]

    if limit:
        eligible = eligible[:limit]

    # Skip already-annotated films — safe resume if run is interrupted
    remaining = [r for r in eligible if not _cache_path(r.tmdb_id).exists()]
    already   = len(eligible) - len(remaining)

    print(f"Eligible films:      {len(eligible)}")
    print(f"Already annotated:   {already}  (skipping)")
    print(f"To annotate:         {len(remaining)}")

    if not remaining:
        print("Nothing to do — all eligible films already annotated.")
        return []

    annotations = []
    failed      = []

    for record in tqdm(remaining, desc="Annotating"):
        ann = annotate_film(record)
        if ann:
            annotations.append(ann)
        else:
            failed.append(record.title)

    print(f"\nAnnotation complete: {len(annotations)} succeeded, {len(failed)} failed")
    if failed:
        # Write failed titles so we can retry them specifically
        Path("data/processed/annotation_failures.txt").write_text("\n".join(failed))
        print(f"Failures written to data/processed/annotation_failures.txt")
        print(f"First failures: {failed[:10]}")

    # Save only the new annotations from this run
    # (cache files are the source of truth — this is just a convenience export)
    if annotations:
        save_annotations(annotations)

    return annotations

if __name__ == "__main__":
    run_annotation_pipeline()
import pandas as pd
import numpy as np
from sklearn.feature_selection import VarianceThreshold
from ..annotation.schema import CraftAnnotation
from ..ingestion.models import FilmRecord

# Ordered categorical dimensions —which I will encode as integers
ORDINAL_FIELDS = {
    "dialogue_density":   ["near_silent", "sparse", "moderate", "dense"],
    "genre_subversion":   ["none", "light", "moderate", "heavy"],
    "world_building_depth": ["minimal", "light", "rich", "immersive"],
    "annotation_confidence": ["LOW", "MEDIUM", "HIGH"],
}


# Nominal categorical dimensions — one-hot encode
NOMINAL_FIELDS = [
    "narrative_time",
    "pacing_signature",
    "point_of_view",
    "ending_valence",
    "tone_primary",
    "reality_register",
    "moral_complexity",
    "character_legibility",
    "cinematographic_language",
    "colour_palette",
    "aspect_ratio",
    "score_style",
    "editor_signature",
    "thematic_primary",
    "director_lineage",
    "body_experience",
    "production_register",
]

def build_feature_matrix(annotations: list[CraftAnnotation], 
                         records: list[FilmRecord],
                         target: str = "divergence_from_mean",  # "raw_rating" or "divergence_from_mean"
                         ) -> tuple[pd.DataFrame, pd.Series]:
    """
    Build a feature matrix from the given annotations and film records.
    """
    rating_map = {
        r.tmdb_id: r.rating
        for r in records
        if r.tmdb_id and r.rating is not None
    }
    
    letterboxd_map = {
        r.tmdb_id: r.tmdb_rating
        for r in records
        if r.tmdb_id and r.tmdb_rating is not None
    }
    
    rows = []
    for ann in annotations:
        rating = rating_map.get(ann.tmdb_id)
        if rating is None:
            continue  

        row = {"tmdb_id":ann.tmdb_id, "title": ann.title, "user_rating": rating}

        tmdb_avg = letterboxd_map.get(ann.tmdb_id)
        if tmdb_avg:
            row["critical_divergence"] = rating - (tmdb_avg / 2)
        else:
            row["critical_divergence"] = np.nan  

        
        #Ordinal encoding
        for field, order in ORDINAL_FIELDS.items():
            value = getattr(ann, field)
            if isinstance(value, int):
                row[field] = value
            elif value in order:
                val_str = value.value if hasattr(value, 'value') else str(value)
                try:
                    row[field] = order.index(val_str)
                except ValueError:
                    row[field] = np.nan
            else:
                row[field] = np.nan
        
        #Nominal 
        for field in NOMINAL_FIELDS:
            value = getattr(ann, field)
            if value is not None:
                val_str = value.value if hasattr(value, 'value') else str(value)
                row[field] = val_str
            else:
                row[field] = np.nan

        # Secondary themes — binary flag if present
        sec_themes = ann.thematic_secondary or []
        sec_vals   = [v.value if hasattr(v, 'value') else str(v) for v in sec_themes]
        row["has_secondary_theme"] = int(len(sec_vals) > 0)

        rows.append(row)
    
    df = pd.DataFrame(rows)
    print(f"Constructed feature matrix with {len(df)} rows and {len(df.columns)} columns.")

    # One-hot encode nominal fields
    df_encoded = pd.get_dummies(df, columns=NOMINAL_FIELDS, dummy_na=False)

    # Separate target variable
    y = df_encoded.pop("user_rating")

    # Drop non-feature columns
    X = df_encoded.drop(columns=["tmdb_id", "title", "critical_divergence"], errors='ignore')
    X = X.fillna(X.median(numeric_only=True).fillna(0))

    selector = VarianceThreshold(threshold=0.01)
    X_reduced = pd.DataFrame(
        selector.fit_transform(X),
        columns=X.columns[selector.get_support()]
    )
    print(f"Features after variance threshold: {X_reduced.shape[1]} (was {X.shape[1]})")
    
    correlations = X_reduced.corrwith(y).abs()
    useful = correlations[correlations > 0.05].index
    X_reduced = X_reduced[useful]

    print(f"Features after correlation filter:  {X_reduced.shape[1]}")

    if target == "divergence_from_mean":
        mean_rating = y.mean()
        y = y - mean_rating  # now predicting +/- from your mean
        print(f"Modelling divergence from mean ({mean_rating:.2f})")
        print(f"New target range: [{y.min():.1f}, {y.max():.1f}]")

    return X_reduced, y, df
# Save as debug_taste.py in project root
import pandas as pd
import numpy as np
from src.annotation.store import load_annotations
from src.enrichment.store import load_enriched
from src.taste.encoder import build_feature_matrix

annotations = load_annotations()
records     = load_enriched()

X, y, df = build_feature_matrix(annotations, records)

print("=== RATING DISTRIBUTION ===")
print(y.value_counts().sort_index())
print(f"\nMean: {y.mean():.2f}, Std: {y.std():.2f}")
print(f"Films rated 4.0+: {(y >= 4.0).sum()} ({(y >= 4.0).mean()*100:.1f}%)")
print(f"Films rated 2.5-: {(y <= 2.5).sum()} ({(y <= 2.5).mean()*100:.1f}%)")

print("\n=== FEATURE MATRIX ===")
print(f"Shape: {X.shape}")
print(f"Features with zero variance: {(X.std() == 0).sum()}")
print(f"NaN count: {X.isna().sum().sum()}")

print("\n=== CLASS BALANCE CHECK ===")
# Check if ratings cluster heavily around one value
top_rating = y.value_counts().index[0]
top_count  = y.value_counts().iloc[0]
print(f"Most common rating: {top_rating} ({top_count} films, {top_count/len(y)*100:.1f}%)")

print("\n=== SINGLE FEATURE CORRELATIONS ===")
# Which individual features correlate most with your rating
correlations = []
for col in X.columns:
    if X[col].std() > 0:
        corr = X[col].corr(y)
        if abs(corr) > 0.1:
            correlations.append((col, corr))
correlations.sort(key=lambda x: abs(x[1]), reverse=True)
print("Top 15 features by correlation with your rating:")
for feat, corr in correlations[:15]:
    bar = '█' * int(abs(corr) * 40)
    direction = '↑' if corr > 0 else '↓'
    print(f"  {direction} {feat:<45} {corr:+.3f} {bar}")
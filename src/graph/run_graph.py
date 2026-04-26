# src/graph/run_graph.py
from ..enrichment.store import load_enriched
from .builder import build_graph, get_graph_stats
from .store import save_graph

def main():
    records = load_enriched()
    G = build_graph(records)

    print("\nGraph stats:")
    for k, v in get_graph_stats(G).items():
        print(f"  {k}: {v}")

    save_graph(G)

if __name__ == "__main__":
    main()
# src/graph/store.py
import json
import networkx as nx
from pathlib import Path
from networkx.readwrite import json_graph

GRAPH_PATH = Path("data/processed/knowledge_graph.json")

def save_graph(G: nx.DiGraph):
    GRAPH_PATH.parent.mkdir(parents=True, exist_ok=True)
    data = json_graph.node_link_data(G)
    GRAPH_PATH.write_text(json.dumps(data, indent=2, default=str))
    print(f"Graph saved → {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")

def load_graph() -> nx.DiGraph:
    if not GRAPH_PATH.exists():
        raise FileNotFoundError("No graph found. Run build_graph first.")
    data = json.loads(GRAPH_PATH.read_text())
    return json_graph.node_link_graph(data, directed=True)
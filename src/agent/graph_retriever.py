"""
Knowledge graph traversal for recommendation candidates.

Strategy:
  1. Find the user's top-rated directors (avg_user_rating >= threshold)
  2. Follow INFLUENCED_BY edges backwards to find who those directors were influenced by
  3. Follow COLLABORATED_WITH edges to find cinematographers/editors who worked
     with those top directors
  4. Collect all films by those related people that the user hasn't seen
  5. Return candidates ranked by how closely the crew node's avg_user_rating
     predicts the user will like them
"""
import networkx as nx

from ..graph.models import EdgeType, NodeType
from ..graph.store import load_graph


def _seen_ids(records) -> set[int]:
    return {r.tmdb_id for r in records if r.tmdb_id and r.rating is not None}


def get_graph_candidates(
    records,
    seen_ids: set[int] | None = None,
    top_n_directors: int = 10,
    hop_depth: int = 2,
    max_candidates: int = 30,
) -> list[dict]:
    """
    Traverse the knowledge graph to surface film candidates the user hasn't seen.

    Returns list of dicts with keys:
        tmdb_id, title, year, via_person, via_role, hop_type, graph_score
    """
    if seen_ids is None:
        seen_ids = _seen_ids(records)

    G = load_graph()

    # ── Step 1: Find top directors by avg user rating ─────────────
    director_nodes = [
        (node_id, data)
        for node_id, data in G.nodes(data=True)
        if data.get("node_type") == NodeType.DIRECTOR.value
        and data.get("avg_user_rating", 0) > 0
        and not data.get("seed_only", False)
    ]
    director_nodes.sort(key=lambda x: x[1].get("avg_user_rating", 0), reverse=True)
    top_directors = director_nodes[:top_n_directors]

    candidates: dict[int, dict] = {}  # tmdb_id → candidate

    def _add_film_candidate(film_node_id: str, via_person: str, via_role: str,
                             hop_type: str, graph_score: float):
        data = G.nodes.get(film_node_id, {})
        if data.get("node_type") != NodeType.FILM.value:
            return
        tmdb_id = data.get("tmdb_id")
        if not tmdb_id or tmdb_id in seen_ids:
            return
        if tmdb_id not in candidates or candidates[tmdb_id]["graph_score"] < graph_score:
            candidates[tmdb_id] = {
                "tmdb_id":    tmdb_id,
                "title":      data.get("title", "Unknown"),
                "year":       data.get("year"),
                "via_person": via_person,
                "via_role":   via_role,
                "hop_type":   hop_type,
                "graph_score": round(graph_score, 3),
                "source":     "graph",
            }

    # ── Step 2: Direct films by top directors (not yet seen) ──────
    for dir_id, dir_data in top_directors:
        dir_name  = dir_data.get("name", dir_id)
        dir_score = dir_data.get("avg_user_rating", 0)
        for _, film_id, edge_data in G.out_edges(dir_id, data=True):
            if edge_data.get("edge_type") == EdgeType.DIRECTED.value:
                _add_film_candidate(film_id, dir_name, "director",
                                    "direct_filmography", dir_score)

    # ── Step 3: Multi-hop via INFLUENCED_BY ───────────────────────
    for dir_id, dir_data in top_directors:
        dir_name  = dir_data.get("name", dir_id)
        dir_score = dir_data.get("avg_user_rating", 0)
        # Who did this director influence? (outgoing INFLUENCED_BY)
        for _, target_id, edge_data in G.out_edges(dir_id, data=True):
            if edge_data.get("edge_type") != EdgeType.INFLUENCED_BY.value:
                continue
            target_data  = G.nodes.get(target_id, {})
            target_name  = target_data.get("name", target_id)
            # Films by the influenced director
            for _, film_id, film_edge in G.out_edges(target_id, data=True):
                if film_edge.get("edge_type") == EdgeType.DIRECTED.value:
                    _add_film_candidate(
                        film_id, target_name, "director",
                        f"influenced_by_{dir_name}",
                        dir_score * 0.85,  # slight discount for indirect hop
                    )

        # Who influenced this director? (incoming INFLUENCED_BY)
        for source_id, _, edge_data in G.in_edges(dir_id, data=True):
            if edge_data.get("edge_type") != EdgeType.INFLUENCED_BY.value:
                continue
            source_data = G.nodes.get(source_id, {})
            source_name = source_data.get("name", source_id)
            for _, film_id, film_edge in G.out_edges(source_id, data=True):
                if film_edge.get("edge_type") == EdgeType.DIRECTED.value:
                    _add_film_candidate(
                        film_id, source_name, "director",
                        f"influences_{dir_name}",
                        dir_score * 0.9,
                    )

    # ── Step 4: Collaborators of top directors ────────────────────
    collab_edge_types = {
        EdgeType.COLLABORATED_WITH.value,
        EdgeType.SHOT.value,
        EdgeType.EDITED.value,
    }
    for dir_id, dir_data in top_directors[:5]:  # only top-5 to avoid noise
        dir_score = dir_data.get("avg_user_rating", 0)
        for _, collab_id, edge_data in G.out_edges(dir_id, data=True):
            if edge_data.get("edge_type") not in collab_edge_types:
                continue
            collab_data = G.nodes.get(collab_id, {})
            collab_name = collab_data.get("name", collab_id)
            collab_role = collab_data.get("node_type", "collaborator")
            for _, film_id, film_edge in G.out_edges(collab_id, data=True):
                _add_film_candidate(
                    film_id, collab_name, collab_role,
                    "collaborator",
                    dir_score * 0.75,
                )

    result = sorted(candidates.values(), key=lambda x: x["graph_score"], reverse=True)
    return result[:max_candidates]

# src/graph/builder.py
import json
import networkx as nx
from pathlib import Path
from collections import defaultdict
from ..ingestion.models import FilmRecord
from .models import NodeType, EdgeType

GRAPH_PATH = Path("data/processed/knowledge_graph.json")


def build_graph(records: list[FilmRecord]) -> nx.DiGraph:
    G = nx.DiGraph()

    eligible = [
        r for r in records
        if r.enriched
        and not getattr(r, 'is_tv', False)
        and r.tmdb_id
    ]

    print(f"Building graph from {len(eligible)} films...")

    # ── Pass 1: Film nodes ────────────────────────────────────
    for r in eligible:
        G.add_node(
            f"film_{r.tmdb_id}",
            node_type=NodeType.FILM.value,
            tmdb_id=r.tmdb_id,
            title=r.title,
            year=r.year,
            user_rating=r.rating,
            genres=r.genres,
        )

    # ── Pass 2: Person nodes + crew edges ─────────────────────
    crew_fields = [
        ("director",        NodeType.DIRECTOR,        EdgeType.DIRECTED),
        ("cinematographer", NodeType.CINEMATOGRAPHER,  EdgeType.SHOT),
        ("editor",          NodeType.EDITOR,           EdgeType.EDITED),
        ("writer",          NodeType.WRITER,           EdgeType.WROTE),
        ("composer",        NodeType.COMPOSER,         EdgeType.COMPOSED),
    ]

    person_films = defaultdict(list)

    for r in eligible:
        for attr, node_type, edge_type in crew_fields:
            crew = getattr(r, attr, None)
            if not crew:
                continue

            person_key = f"{node_type.value}_{crew.tmdb_id}"

            if not G.has_node(person_key):
                G.add_node(
                    person_key,
                    node_type=node_type.value,
                    tmdb_id=crew.tmdb_id,
                    name=crew.name,
                    role=node_type.value,
                    film_count=0,
                    avg_user_rating=0.0,
                )

            G.add_edge(
                person_key,
                f"film_{r.tmdb_id}",
                edge_type=edge_type.value,
                film_title=r.title,
            )

            person_films[person_key].append(r)

    # ── Pass 3: Person node stats ─────────────────────────────
    for person_key, films in person_films.items():
        rated = [f for f in films if f.rating is not None]
        G.nodes[person_key]['film_count']      = len(films)
        G.nodes[person_key]['avg_user_rating'] = (
            round(sum(f.rating for f in rated) / len(rated), 2) if rated else 0.0
        )

    # ── Pass 4: COLLABORATED_WITH edges ───────────────────────
    film_to_crew = defaultdict(list)
    for u, v, data in G.edges(data=True):
        if data.get('edge_type') in (
            EdgeType.DIRECTED.value, EdgeType.SHOT.value,
            EdgeType.EDITED.value,   EdgeType.WROTE.value,
            EdgeType.COMPOSED.value
        ):
            film_to_crew[v].append(u)

    collab_count = 0
    for film_id, crew_list in film_to_crew.items():
        film_title = G.nodes[film_id].get('title', '')
        for i, person_a in enumerate(crew_list):
            for person_b in crew_list[i+1:]:
                if G.has_edge(person_a, person_b):
                    G[person_a][person_b]['weight'] += 1
                    G[person_a][person_b]['films'].append(film_title)
                else:
                    G.add_edge(
                        person_a, person_b,
                        edge_type=EdgeType.COLLABORATED_WITH.value,
                        weight=1,
                        films=[film_title],
                    )
                    collab_count += 1

    print(f"Added {collab_count} collaboration edges")

    # ── Pass 5: INFLUENCED_BY edges from seed list ────────────
    seeds_path = Path("data/raw/influence_seeds.json")
    if not seeds_path.exists():
        print("⚠️  No influence_seeds.json found — skipping influence edges")
        print("   Create data/raw/influence_seeds.json to add director lineage edges")
        return G

    seeds = json.loads(seeds_path.read_text())

    # Name → node key lookup for directors only
    name_to_key = {
        data['name'].lower(): node_key
        for node_key, data in G.nodes(data=True)
        if data.get('node_type') == NodeType.DIRECTOR.value
    }

    influence_count = 0
    for seed in seeds:
        source_name = seed['source'].lower()
        target_name = seed['target'].lower()

        source_key = name_to_key.get(source_name)
        target_key = name_to_key.get(target_name)

        # Add seed-only director nodes if not in watch history
        if not source_key:
            source_key = f"director_seed_{seed['source'].replace(' ', '_')}"
            if not G.has_node(source_key):
                G.add_node(
                    source_key,
                    node_type=NodeType.DIRECTOR.value,
                    name=seed['source'],
                    role=NodeType.DIRECTOR.value,
                    film_count=0,
                    avg_user_rating=0.0,
                    seed_only=True,
                )
            name_to_key[source_name] = source_key

        if not target_key:
            target_key = f"director_seed_{seed['target'].replace(' ', '_')}"
            if not G.has_node(target_key):
                G.add_node(
                    target_key,
                    node_type=NodeType.DIRECTOR.value,
                    name=seed['target'],
                    role=NodeType.DIRECTOR.value,
                    film_count=0,
                    avg_user_rating=0.0,
                    seed_only=True,
                )
            name_to_key[target_name] = target_key

        if not G.has_edge(source_key, target_key):
            G.add_edge(
                source_key,
                target_key,
                edge_type=EdgeType.INFLUENCED_BY.value,
                note=seed.get('note', ''),
            )
            influence_count += 1

    print(f"Added {influence_count} influence edges from seed list")
    return G


def get_graph_stats(G: nx.DiGraph) -> dict:
    node_types = defaultdict(int)
    edge_types = defaultdict(int)

    for _, data in G.nodes(data=True):
        node_types[data.get('node_type', 'unknown')] += 1

    for _, _, data in G.edges(data=True):
        edge_types[data.get('edge_type', 'unknown')] += 1

    return {
        'total_nodes': G.number_of_nodes(),
        'total_edges': G.number_of_edges(),
        'node_types':  dict(node_types),
        'edge_types':  dict(edge_types),
        'density':     round(nx.density(G), 6),
    }
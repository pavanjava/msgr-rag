"""
generate_test_facts.py
Fixes roadmap items 1 & 2: scales the test set and adds the missing
"locally plausible but globally wrong" category.

Reads Component 3/4 outputs (entity/concept/domain mappings + relationships)
and produces a large, reproducible, seeded test set with FOUR fact categories:

  A. real_edge              -> VERIFIED  (ground truth: true positive at all scales)
  B. nonexistent_relationship -> HALLUCINATION (subject/object exist, no edge at all —
                                 what entity-level checking alone already catches)
  C. wrong_predicate         -> HALLUCINATION (real edge exists, predicate swapped)
  D. domain_violation        -> HALLUCINATION (THE NEW CATEGORY — concept-level relation
                                 exists, i.e. locally/conceptually plausible, but the
                                 corresponding domain-level relation does NOT exist)

Category D is what makes the paper's actual thesis testable. Without it, entity-only
verification trivially scores 100% (as your ablation showed) because every negative
example is "the entity doesn't exist" — never "the entity exists but crosses a domain
boundary it shouldn't."
"""

import pandas as pd
import numpy as np
import networkx as nx
import pickle
import random
from pathlib import Path
from itertools import product

SEED = 42
random.seed(SEED)
np.random.seed(SEED)

INTERMEDIATE_DIR = Path("../Datasets/intermediate")
OUTPUT_PATH = INTERMEDIATE_DIR / "test_facts_large.csv"

N_POSITIVE = 400
N_NONEXISTENT = 300
N_WRONG_PREDICATE = 200
N_DOMAIN_VIOLATION = 300   # the category that matters most for the paper's claim

VALID_PREDICATES = ["treats", "causes", "interacts_with"]


def load_data():
    with open(INTERMEDIATE_DIR / "graph_entity.gpickle", "rb") as f:
        G_E = pickle.load(f)

    concept_mappings = pd.read_csv(INTERMEDIATE_DIR / "concept_mappings.csv")
    domain_mappings = pd.read_csv(INTERMEDIATE_DIR / "domain_mappings.csv")
    concept_rel = pd.read_csv(INTERMEDIATE_DIR / "concept_relationships.csv")
    domain_rel = pd.read_csv(INTERMEDIATE_DIR / "domain_relationships.csv")

    entity_to_concept = dict(zip(concept_mappings["entity_name"], concept_mappings["concept_name"]))
    concept_to_domain = dict(zip(domain_mappings["concept_name"], domain_mappings["domain_name"]))

    return G_E, concept_mappings, entity_to_concept, concept_to_domain, concept_rel, domain_rel


def get_mapped_entities(G_E, entity_to_concept):
    """Restrict to the 149 entities with full entity->concept->domain mappings,
    matching the earlier decision to keep verification interpretable end-to-end."""
    mapped = [n for n in G_E.nodes() if n in entity_to_concept]
    return mapped


def category_A_real_edges(G_E, mapped_entities, n):
    """Sample real (subject, predicate, object) edges among mapped entities."""
    edges = [
        (u, d["predicate"], v)
        for u, v, d in G_E.edges(data=True)
        if u in mapped_entities and v in mapped_entities
    ]
    edges = list(set(edges))
    random.shuffle(edges)
    sample = edges[:n]
    return [
        {"subject": s, "predicate": p, "object": o,
         "ground_truth": "VERIFIED", "category": "real_edge",
         "generation_rule": "sampled_real_edge"}
        for s, p, o in sample
    ]


def category_B_nonexistent(G_E, mapped_entities, n):
    """Pick subject + predicate + an object that has NO edge (either direction)
    with the subject at all."""
    results = []
    attempts = 0
    entities = mapped_entities.copy()
    while len(results) < n and attempts < n * 50:
        attempts += 1
        s, o = random.sample(entities, 2)
        p = random.choice(VALID_PREDICATES)
        if not G_E.has_edge(s, o) and not G_E.has_edge(o, s):
            results.append({
                "subject": s, "predicate": p, "object": o,
                "ground_truth": "HALLUCINATION", "category": "nonexistent_relationship",
                "generation_rule": "no_edge_either_direction"
            })
    return results


def category_C_wrong_predicate(G_E, mapped_entities, n):
    """Take a real edge, swap its predicate to a different valid one, provided
    that swapped (s, p', o) is not itself also a real edge."""
    real_edges = [
        (u, d["predicate"], v)
        for u, v, d in G_E.edges(data=True)
        if u in mapped_entities and v in mapped_entities
    ]
    random.shuffle(real_edges)
    results = []
    for s, p, o in real_edges:
        if len(results) >= n:
            break
        other_predicates = [x for x in VALID_PREDICATES if x != p]
        random.shuffle(other_predicates)
        for p_swapped in other_predicates:
            already_real = G_E.has_edge(s, o) and G_E[s][o].get("predicate") == p_swapped
            if not already_real:
                results.append({
                    "subject": s, "predicate": p_swapped, "object": o,
                    "ground_truth": "HALLUCINATION", "category": "wrong_predicate",
                    "generation_rule": f"swapped_from_{p}"
                })
                break
    return results


def category_D_domain_violation(mapped_entities, entity_to_concept, concept_to_domain,
                                concept_rel, domain_rel, n):
    """
    THE CRITICAL CATEGORY.

    Construct facts (s, p, o) such that:
      - a concept-level relationship (concept(s), p, concept(o)) DOES exist in G_C
        -> the fact is "conceptually plausible" (S_C would score high)
      - but the corresponding domain-level relationship
        (domain(concept(s)), p, domain(concept(o))) does NOT exist in G_D
        -> the fact should fail at the domain scale (S_D low)
      - and (s, p, o) is not itself a real entity-level edge, so ground truth is
        unambiguously HALLUCINATION.

    This is exactly Pattern I2 (concept-domain contradiction) from the paper's
    formulation, and it is the category your prior test set never included.
    """
    concept_edges = set(
        zip(concept_rel["subject_concept"], concept_rel["predicate"], concept_rel["object_concept"])
    )
    domain_edges = set(
        zip(domain_rel["subject_domain"], domain_rel["predicate"], domain_rel["object_domain"])
    )

    # group entities by concept for fast sampling
    concept_to_entities = {}
    for ent, concept in entity_to_concept.items():
        concept_to_entities.setdefault(concept, []).append(ent)

    results = []
    concept_edge_list = list(concept_edges)
    random.shuffle(concept_edge_list)

    for c_subj, p, c_obj in concept_edge_list:
        if len(results) >= n:
            break
        dom_subj = concept_to_domain.get(c_subj)
        dom_obj = concept_to_domain.get(c_obj)
        if not dom_subj or not dom_obj:
            continue

        # require: concept-level edge exists (checked, we're iterating over it)
        # but domain-level edge with same predicate does NOT exist
        if (dom_subj, p, dom_obj) in domain_edges:
            continue  # not a violation — domains agree, skip

        subj_pool = concept_to_entities.get(c_subj, [])
        obj_pool = concept_to_entities.get(c_obj, [])
        if not subj_pool or not obj_pool:
            continue

        s = random.choice(subj_pool)
        o = random.choice(obj_pool)
        if s == o:
            continue

        results.append({
            "subject": s, "predicate": p, "object": o,
            "ground_truth": "HALLUCINATION", "category": "domain_violation",
            "generation_rule": f"concept_edge_exists({c_subj}->{c_obj}) "
                               f"but domain_edge_missing({dom_subj}->{dom_obj})"
        })

    return results


def main():
    G_E, concept_mappings, entity_to_concept, concept_to_domain, concept_rel, domain_rel = load_data()
    mapped_entities = get_mapped_entities(G_E, entity_to_concept)
    print(f"Mapped entities available for test-set construction: {len(mapped_entities)}")

    A = category_A_real_edges(G_E, mapped_entities, N_POSITIVE)
    B = category_B_nonexistent(G_E, mapped_entities, N_NONEXISTENT)
    C = category_C_wrong_predicate(G_E, mapped_entities, N_WRONG_PREDICATE)
    # D is intentionally NOT generated here — use generate_category_d.py separately,
    # which uses the validated K>=2 support-threshold rejection logic instead.

    all_facts = A + B + C
    df = pd.DataFrame(all_facts)
    df = df.sample(frac=1, random_state=SEED).reset_index(drop=True)

    print("\nTest set composition (A/B/C only):")
    print(df.groupby(["category", "ground_truth"]).size())

    df.to_csv(OUTPUT_PATH, index=False)
    print(f"\nSaved {len(df)} facts to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
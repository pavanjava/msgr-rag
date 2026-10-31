"""Independent test of the multi-scale contribution (R2-W1, R3 major #1) without any label derived from K=2.

Hold out a random fraction of REAL entity edges from G_E (simulated KG incompleteness), rebuild G_C and G_D
from the masked G_E with the same K=2 rule, then ask: among facts the entity scale cannot support (S_E<1),
do the concept/domain scores separate the held-out TRUE facts from the FALSE facts?
Entity-only scoring is constant on that pool (AUC 0.5) by construction.
Run: python3 -I edge_masking.py  (from this directory; needs scorer.py alongside)"""
import collections, pathlib, sys
import numpy as np, pandas as pd, networkx as nx
from sklearn.metrics import roc_auc_score
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import scorer as S

OUT = pathlib.Path(__file__).resolve().parent / "out"; OUT.mkdir(exist_ok=True)
GE0, GC0, GD0, ov = S.load()
v = pd.read_csv(S.D / "verification_results.csv")
hand = [(a, b, d["predicate"]) for a, b, d in GD0.edges(data=True) if d["source"] == "domain_specific_medical_practice"]
concept_of = {n: d.get("concept") for n, d in GE0.nodes(data=True) if d.get("concept")}
dom_of_concept = {c: d["domain"] for c, d in GC0.nodes(data=True)}
K = 2


def rebuild(GE, masked):
    """Rebuild concept and domain graphs from entity edges minus `masked` (set of (s,o) pairs, both directions)."""
    cp = collections.defaultdict(set)
    for s, o, d in GE.edges(data=True):
        if (s, o) in masked: continue
        cs, co = concept_of.get(s), concept_of.get(o)
        if cs and co: cp[(cs, co)].add(d["predicate"])
    GC = nx.DiGraph(); GC.add_nodes_from(GC0.nodes(data=True))
    for (a, b), ps in cp.items():
        GC.add_edge(a, b, predicate=sorted(ps)[0], preds=ps)
    sup = collections.defaultdict(set)
    for (a, b), ps in cp.items():
        for p in ps: sup[(dom_of_concept[a], p, dom_of_concept[b])].add((a, b))
    GD = nx.MultiDiGraph(); GD.add_nodes_from(GD0.nodes(data=True))
    for (da, p, db), pairs in sup.items():
        if len(pairs) >= K: GD.add_edge(da, db, predicate=p, source="k2")
    for a, b, p in hand: GD.add_edge(a, b, predicate=p, source="hand")
    return GC, GD


def preds_c(G, a, b):  # rebuilt concept graph keeps the full predicate set per pair
    d = G.get_edge_data(a, b); return d["preds"] if d else set()


S.edge_preds_orig = S.edge_preds
def edge_preds(G, a, b):
    if G.is_multigraph() or not G.is_directed() or "preds" not in (G.get_edge_data(a, b) or {"preds": 0}):
        return S.edge_preds_orig(G, a, b)
    return preds_c(G, a, b)
S.edge_preds = edge_preds

facts = v[["subject", "predicate", "object", "ground_truth", "category"]].reset_index(drop=True)
real = facts.index[facts.category == "real_edge"].to_numpy()
false = facts.index[facts.ground_truth == "HALLUCINATION"].to_numpy()


def run(rate, seed):
    rng = np.random.default_rng(seed)
    held = rng.choice(real, int(round(rate * len(real))), replace=False)
    masked = set()
    for i in held:
        s, p, o = facts.loc[i, ["subject", "predicate", "object"]]
        masked.add((s, o))
        if p == "interacts_with": masked.add((o, s))
    GE = GE0.copy(); GE.remove_edges_from(masked)
    GC, GD = rebuild(GE, set())  # GE already masked
    idx = np.concatenate([held, false]); y_true = np.r_[np.ones(len(held)), np.zeros(len(false))]  # 1 = held-out TRUE
    sc = np.array([S.score(GE, GC, GD, ov, *facts.loc[i, ["subject", "predicate", "object"]]) for i in idx])
    der = np.array([S.derived(*r) for r in sc])
    return held, idx, y_true, sc, der


def baseline_unmasked():
    GC, GD = rebuild(GE0, set())
    print("rebuilt (unmasked) concept edges", GC.number_of_edges(), "(frozen 339; DiGraph keeps 1 predicate/pair)",
          "| domain edges", GD.number_of_edges(), "(frozen 119 = 90 K2 + 29 hand)",
          "| K2:", sum(1 for *_, d in GD.edges(data=True) if d["source"] == "k2"))


baseline_unmasked()
rows = []
for rate in (0.1, 0.2, 0.3):
    for seed in range(5):
        held, idx, yt, sc, der = run(rate, seed)
        se = sc[:, 0]
        pool = se < 1  # entity scale cannot support the fact
        r = dict(rate=rate, seed=seed, n_true=len(held), n_false=int((yt == 0).sum()), pool=int(pool.sum()),
                 entity_flag_rate_true=float((se[yt == 1] < 1).mean()))
        for name, score in {"S_E": sc[:, 0], "S_C": sc[:, 1], "S_D": sc[:, 2], "SC+SD": sc[:, 1] + sc[:, 2], "C(f)": der[:, 0], "Conf(f)": der[:, 1]}.items():
            r["AUC_" + name] = roc_auc_score(yt[pool], score[pool])
        # simple domain-aware rescue: accept if S_C==1 and S_D==1 (concept AND domain corroborate)
        acc = (sc[:, 1] == 1) & (sc[:, 2] == 1)
        r["rescue_TPR"] = float(acc[(yt == 1)].mean()); r["rescue_FPR"] = float(acc[(yt == 0)].mean())
        full = (der[:, 0] < .5) | (der[:, 1] < .55) | der[:, 2].astype(bool)
        r["full_rule_flags_true"] = float(full[yt == 1].mean())
        rows.append(r)
res = pd.DataFrame(rows)
res.to_csv(OUT / "edge_masking_runs.csv", index=False)
s = res.groupby("rate").mean(numeric_only=True).drop(columns="seed").round(3)
sd = res.groupby("rate").std(numeric_only=True)[["AUC_S_C", "AUC_S_D", "AUC_Conf(f)", "rescue_TPR", "rescue_FPR"]].round(3)
print(s.T.to_string()); print("\nsd across seeds\n", sd.T.to_string())
s.to_csv(OUT / "edge_masking_summary.csv")

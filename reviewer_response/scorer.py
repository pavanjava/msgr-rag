"""Deterministic S_E/S_C/S_D (paper Table 3) re-implemented on the frozen graph pickles, so the
graphs can be perturbed for the edge-masking test. Validated against verification_results.csv."""
import pathlib, pickle
import numpy as np, pandas as pd

D = pathlib.Path(__file__).resolve().parent.parent / "Datasets" / "intermediate"
FLOOR = dict(E=(1.0, 0.3, 0.1), C=(1.0, 0.4, 0.2), D=(1.0, 0.5, 0.3))  # exact, mismatch, none
W = (0.30, 0.25, 0.20, 0.25)


def load():
    g = {n: pickle.load(open(D / f"graph_{n}.gpickle", "rb")) for n in ("entity", "concept", "domain")}
    ov = dict(pd.read_csv(D / "atc_entity_domain_overrides.csv").values)
    return g["entity"], g["concept"], g["domain"], ov


def _s(preds_fwd, preds_rev, p, fl, sym):
    if p in preds_fwd or (sym and p in preds_rev): return fl[0]
    if preds_fwd or (sym and preds_rev): return fl[1]
    return fl[2]


def edge_preds(G, a, b):
    if G.is_multigraph():
        return {d["predicate"] for d in (G.get_edge_data(a, b) or {}).values()}
    d = G.get_edge_data(a, b)
    return {d["predicate"]} if d else set()


def score(GE, GC, GD, ov, s, p, o):
    sym = p == "interacts_with"
    SE = _s(edge_preds(GE, s, o), edge_preds(GE, o, s), p, FLOOR["E"], sym) if s in GE and o in GE else 0.0
    cs, co = (GE.nodes[s].get("concept") if s in GE else None), (GE.nodes[o].get("concept") if o in GE else None)
    SC = _s(edge_preds(GC, cs, co), edge_preds(GC, co, cs), p, FLOOR["C"], False) if cs and co else 0.0
    dom = lambda x, c: ov.get(x) or (GC.nodes[c].get("domain") if c in GC else None)
    ds, do = dom(s, cs), dom(o, co)
    SD = _s(edge_preds(GD, ds, do), edge_preds(GD, do, ds), p, FLOOR["D"], False) if ds and do else 0.0
    return SE, SC, SD


def derived(SE, SC, SD):
    c = ((1 - abs(SE - SC)) * (1 - abs(SC - SD)) * (1 - abs(SE - SD))) ** (1 / 3)
    conf = W[0] * SE + W[1] * SC + W[2] * SD + W[3] * c
    pat = (SE > .7 and SD < .3) or (SC > .7 and SD < .3) or max(abs(SE - SC), abs(SC - SD), abs(SE - SD)) > .5
    return c, conf, bool(pat)


if __name__ == "__main__":
    GE, GC, GD, ov = load()
    v = pd.read_csv(D / "verification_results.csv")
    got = np.array([score(GE, GC, GD, ov, *r) for r in v[["subject", "predicate", "object"]].itertuples(index=False)])
    for i, c in enumerate(("S_E", "S_C", "S_D")):
        ok = np.isclose(got[:, i], v[c]); print(c, "match", ok.mean().round(4), "mismatches", int((~ok).sum()))

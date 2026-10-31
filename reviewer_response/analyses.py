"""Additive reviewer-response analyses. Reads frozen CSVs only; writes to ./out/.
Run: python3 -I analyses.py   (from this directory)"""
import itertools, json, pathlib
import numpy as np, pandas as pd

D = pathlib.Path(__file__).resolve().parent.parent / "Datasets" / "intermediate"
OUT = pathlib.Path(__file__).resolve().parent / "out"; OUT.mkdir(exist_ok=True)
TH_C, TH_F = 0.50, 0.55

v = pd.read_csv(D / "verification_results.csv")
v["pat"] = v.patterns_detected.fillna("None").ne("None") & v.patterns_detected.fillna("None").ne("[]")
y = (v.ground_truth == "HALLUCINATION").to_numpy()
cat = v.category.to_numpy()
CATS = ["nonexistent_relationship", "wrong_predicate", "domain_violation", "real_edge"]


def met(p, mask=None):
    p = np.asarray(p, bool); yy = y
    if mask is not None: p, yy = p[mask], y[mask]
    tp = int((p & yy).sum()); fp = int((p & ~yy).sum()); fn = int((~p & yy).sum()); tn = int((~p & ~yy).sum())
    pr = tp / (tp + fp) if tp + fp else float("nan"); rc = tp / (tp + fn) if tp + fn else float("nan")
    f1 = 2 * pr * rc / (pr + rc) if pr == pr and rc == rc and pr + rc else float("nan")
    return dict(TP=tp, FP=fp, FN=fn, TN=tn, acc=(tp + tn) / len(yy), prec=pr, rec=rc, f1=f1)


def full_rule(tc, tf, c=v.C_f, cf=v.Conf_f, pat=v.pat):
    return ((c < tc) | (cf < tf) | pat).to_numpy()


# ---- A. frozen headline must not drift -------------------------------------------------
full = full_rule(TH_C, TH_F)
m = met(full)
assert (m["TP"], m["FP"], m["FN"], m["TN"]) == (574, 85, 0, 315), m
print("csv 'decision' column agrees with 0.50/0.55 rule:", bool((full == (v.decision == "HALLUCINATION").to_numpy()).all()))
print("A. frozen confusion matrix reproduced:", {k: m[k] for k in ("TP", "FP", "FN", "TN")})

# ---- B. ablation -----------------------------------------------------------------------
from sklearn.metrics import roc_auc_score
rules = {
    "Entity-only (S_E<1)": (v.S_E < 1).to_numpy(),
    "Concept-only (S_C<1)": (v.S_C < 1).to_numpy(),
    "Domain-only (S_D<1)": (v.S_D < 1).to_numpy(),
    f"Conf-only (theta={TH_F})": (v.Conf_f < TH_F).to_numpy(),
    f"C-only (theta={TH_C})": (v.C_f < TH_C).to_numpy(),
    "Full rule (C | Pattern | Conf)": full,
    "Full minus consistency gate": full_rule(-1, TH_F),
    "Full minus pattern gate": full_rule(TH_C, TH_F, pat=pd.Series(False, index=v.index)),
    "Full minus confidence gate": full_rule(TH_C, -1),
    "Consistency gate only": full_rule(TH_C, -1, pat=pd.Series(False, index=v.index)),
    "Pattern gate only (I3)": v.pat.to_numpy(),
}
# conf-only at a midpoint of the non-overlapping gap, reported as oracle (chosen after seeing labels)
lo, hi = v.Conf_f[y].max(), v.Conf_f[~y].min()
rules[f"Conf-only (oracle gap midpoint {(lo+hi)/2:.3f})"] = (v.Conf_f < (lo + hi) / 2).to_numpy()
rows = []
for name, p in rules.items():
    r = met(p); r["rule"] = name
    for c in CATS:
        r["acc_" + c] = met(p, cat == c)["acc"]
    rows.append(r)
abl = pd.DataFrame(rows).set_index("rule")
abl.round(4).to_csv(OUT / "ablation.csv")
print("\nB. ablation\n", abl[["TP", "FP", "FN", "TN", "acc", "prec", "rec", "f1"]].round(4).to_string())
print(abl[[c for c in abl if c.startswith("acc_")]].round(3).to_string())
auc = {k: roc_auc_score(y, s) for k, s in {"S_E": -v.S_E, "S_C": -v.S_C, "S_D": -v.S_D, "C(f)": -v.C_f, "Conf(f)": -v.Conf_f}.items()}
print("AUCs:", {k: round(a, 4) for k, a in auc.items()}, " conf gap:", (round(lo, 3), round(hi, 3)))
# gate attribution of the 85 FP
fp = full & ~y
print("FP by first gate: consistency", int((fp & (v.C_f < TH_C)).sum()), "| pattern-only", int((fp & ~(v.C_f < TH_C) & v.pat).sum()),
      "| conf-only", int((fp & ~(v.C_f < TH_C) & ~v.pat).sum()))
print("S_E distribution per category:\n", v.groupby("category").S_E.agg(["min", "max"]).to_string())

# ---- C. nested threshold selection -----------------------------------------------------
GC = np.round(np.arange(0.5, 0.9001, 0.05), 2); GF = np.round(np.arange(0.3, 0.7001, 0.05), 2)
rng = np.random.default_rng(0)
strata = [np.where(cat == c)[0] for c in CATS]


def best(idx):
    b = None
    for tc, tf in itertools.product(GC, GF):
        f = met(full_rule(tc, tf), mask=np.isin(np.arange(len(y)), idx))["f1"]
        if b is None or f > b[0]: b = (f, tc, tf)
    return b


def best_conf(idx):
    mk = np.isin(np.arange(len(y)), idx)
    return max(GF, key=lambda t: np.nan_to_num(met((v.Conf_f < t).to_numpy(), mk)["f1"], nan=-1))


res, chosen = [], []
for rep in range(20):
    tr, te = [], []
    for s in strata:
        s = rng.permutation(s); h = len(s) // 2; tr += list(s[:h]); te += list(s[h:])
    _, tc, tf = best(np.array(tr)); chosen.append((tc, tf))
    mk = np.isin(np.arange(len(y)), te)
    r = met(full_rule(tc, tf), mk); r.update(kind="full")
    for c in CATS: r["acc_" + c] = met(full_rule(tc, tf), mk & (cat == c))["acc"]
    res.append(r)
    t2 = best_conf(np.array(tr)); r2 = met((v.Conf_f < t2).to_numpy(), mk); r2.update(kind="conf_only")
    for c in CATS: r2["acc_" + c] = met((v.Conf_f < t2).to_numpy(), mk & (cat == c))["acc"]
    res.append(r2)
nest = pd.DataFrame(res)
summ = nest.groupby("kind")[["acc", "prec", "rec", "f1"] + ["acc_" + c for c in CATS]].agg(["mean", "std"]).round(4)
summ.to_csv(OUT / "nested_split.csv")
print("\nC. nested 50/50 split x20 (thresholds chosen on train half, scored on test half)\n", summ.T.to_string())
print("chosen (theta_c, theta_f) frequency:", pd.Series(chosen).value_counts().head(5).to_dict())

# ---- D. aligned denominators for pipeline vs plain RAG ---------------------------------
e = pd.read_csv(D / "component6_e2e_results.csv")
s = pd.read_csv(D / "simple_rag_v2_results.csv")
k = ["subject", "predicate", "object"]
e = e.rename(columns={"original_subject": "subject", "original_predicate": "predicate", "original_object": "object"})
j = e.merge(s[k + ["simple_rag_decision"]], on=k, how="left", validate="1:1")
assert len(j) == 974 and j.simple_rag_decision.notna().all()
j["truth"] = j.ground_truth
res_mask = j.pipeline_decision.isin(["VERIFIED", "HALLUCINATION"])
j["pipe_ok"] = j.pipeline_decision == j.truth
j["rag_ok"] = j.simple_rag_decision == j.truth
catmap = {"nonexistent_relationship": "Absent", "wrong_predicate": "Predicate-swapped", "domain_violation": "Domain-inconsistent", "real_edge": "Real"}
rows = []
for name, mk in {"resolved (n=%d)" % res_mask.sum(): res_mask, "all 974": pd.Series(True, index=j.index)}.items():
    sub = j[mk]
    rows.append(dict(subset=name, system="MSGR pipeline (UNKNOWN=error)", acc=sub.pipe_ok.mean()))
    rows.append(dict(subset=name, system="Plain RAG", acc=sub.rag_ok.mean()))
    for c, lab in catmap.items():
        ss = sub[sub.category == c]
        rows.append(dict(subset=name, system=f"  {lab} MSGR (n={len(ss)})", acc=ss.pipe_ok.mean()))
        rows.append(dict(subset=name, system=f"  {lab} Plain RAG", acc=ss.rag_ok.mean()))
al = pd.DataFrame(rows); al.round(4).to_csv(OUT / "aligned_pipeline_vs_plain_rag.csv", index=False)
print("\nD. aligned denominators\n", al.round(3).to_string(index=False))
sub = j[res_mask]
for nm, col in (("MSGR", "pipeline_decision"), ("PlainRAG", "simple_rag_decision")):
    p = (sub[col] == "HALLUCINATION").to_numpy(); yy = (sub.truth == "HALLUCINATION").to_numpy()
    tp = (p & yy).sum(); fp_ = (p & ~yy).sum(); fn = (~p & yy).sum()
    pr, rc = tp / (tp + fp_), tp / (tp + fn)
    print(nm, "on resolved: prec %.3f rec %.3f f1 %.3f" % (pr, rc, 2 * pr * rc / (pr + rc)))
b = ((sub.pipe_ok) & ~(sub.rag_ok)).sum(); c_ = (~(sub.pipe_ok) & (sub.rag_ok)).sum()
from scipy.stats import chi2
chi = (abs(b - c_) - 1) ** 2 / (b + c_); print("McNemar on resolved: b=%d c=%d chi2=%.2f p=%.2g" % (b, c_, chi, chi2.sf(chi, 1)))

# ---- E. count reconciliation -------------------------------------------------------------
dr = pd.read_csv(D / "domain_relationships.csv"); rj = pd.read_csv(D / "rejected_domain_claims.csv")
ec = pd.read_csv(D / "entity_catalog.csv")
print("\nE. domain edges admitted", len(dr), "| withheld", len(rj), "| candidates", len(dr) + len(rj),
      "| sources", dr.source.unique().tolist(), "| entity types", ec.entity_type.value_counts().to_dict())

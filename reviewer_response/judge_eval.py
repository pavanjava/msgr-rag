"""Score the closed-book gemma3 judge against MSGR core and TF-IDF on identical 974 facts. Run after llm_judge.py."""
import pathlib, numpy as np, pandas as pd
from scipy.stats import chi2

H = pathlib.Path(__file__).resolve().parent; D = H.parent / "Datasets" / "intermediate"
j = pd.read_csv(H / "out" / "llm_judge_gemma3.csv"); v = pd.read_csv(D / "verification_results.csv")
assert len(j) == 974 and (j.subject.values == v.subject.values).all()
y = (v.ground_truth == "HALLUCINATION").to_numpy()
msgr = ((v.C_f < .5) | (v.Conf_f < .55) | (v.patterns_detected.fillna("None") != "None")).to_numpy()
judge = (j.judge_decision == "HALLUCINATION").to_numpy()
tf = pd.read_csv(D / "semantic_rag_predictions.csv")  # pre-refinement 981 facts; align by triple
k = ["subject", "predicate", "object"]
al = v[k + ["category"]].merge(tf[k + ["decision"]], on=k, how="left")
tfp = (al.decision == "HALLUCINATION").to_numpy(); has = al.decision.notna().to_numpy()


def m(p, yy):
    tp = (p & yy).sum(); fp = (p & ~yy).sum(); fn = (~p & yy).sum(); tn = (~p & ~yy).sum()
    pr = tp / max(tp + fp, 1); rc = tp / max(tp + fn, 1)
    return dict(n=len(yy), acc=(tp + tn) / len(yy), prec=pr, rec=rc, f1=2 * pr * rc / max(pr + rc, 1e-9), FP=int(fp), FN=int(fn))


rows = {"MSGR core (full rule)": m(msgr, y), "Closed-book gemma3 judge": m(judge, y), "TF-IDF (aligned subset)": m(tfp[has], y[has])}
print(pd.DataFrame(rows).T.round(4).to_string())
cats = v.category.to_numpy()
out = {}
for nm, p, mk in (("MSGR", msgr, np.ones(974, bool)), ("Judge", judge, np.ones(974, bool)), ("TF-IDF", tfp, has)):
    out[nm] = {c: float(((p == y)[(cats == c) & mk]).mean()) for c in np.unique(cats)}
print(pd.DataFrame(out).round(3).to_string())
b = ((msgr == y) & (judge != y)).sum(); c = ((msgr != y) & (judge == y)).sum()
x = (abs(b - c) - 1) ** 2 / (b + c); print("McNemar MSGR vs judge: b=%d c=%d chi2=%.2f p=%.2g" % (b, c, x, chi2.sf(x, 1)))
pd.DataFrame(rows).T.round(4).to_csv(H / "out" / "baseline_comparison.csv")

# Reviewer-response findings (step 1, offline analyses)

Reproduce: `cd reviewer_response && python3 -I analyses.py`. Outputs in `out/`. No frozen file was modified.
Frozen headline reproduced exactly: TP 574 / FP 85 / FN 0 / TN 315 (acc 0.9127, F1 0.9311).

## 1. BLOCKER: Table 16 / Fig. 7 plain-RAG numbers come from the sensitivity-analysis file, not the primary run
- Paper Table 16 plain RAG (67.8 overall; 84.4 / 71.6 / 80.5 / 30.6) equals `Datasets/intermediate/plain_rag_sensitivity.csv` column `simple_rag_decision`, all 974 facts.
- That file (`data_status = SENSITIVITY_ANALYSIS`, `sensitivity_rule = "approximately 15% relative reduction in category accuracy"`) differs from the primary run in 117 decisions (`sensitivity_modified = YES`) with identical answer text. How those decisions were produced is not documented in the repo.
- The primary plain-RAG run is `simple_rag_v2_results.csv` (= column `simple_rag_decision_original`). On those:

| | Plain RAG (measured) | MSGR pipeline |
|---|---|---|
| Resolved subset (n=733) overall | 78.9% | 75.7% |
| All 974 (UNKNOWN = error) | 79.8% | 57.0% |
| Domain-inconsistent, resolved (n=50) | 94.0% | 100.0% |
| Predicate-swapped, resolved (n=154) | 25.3% | 39.0% |
| Absent, resolved (n=170) | 100.0% | 98.2% |
| Real, resolved (n=359) | 89.7% | 77.4% |

- McNemar on the resolved subset: b=59, c=82, chi2=3.43, p=0.064 (plain RAG not worse). The claims "outperforms plain RAG on every category" and "+19.5 points" do not survive measured data.

## 2. Ablation (identical facts, thresholds 0.50 / 0.55)
- Entity-only (S_E<1): 100.0% acc. All 75 domain-inconsistent facts have S_E=0.1 by construction.
- Conf-only at 0.55: 99.69% (0 FP, 3 FN, all predicate-swapped). Oracle gap midpoint 0.687: 100%.
- Full rule: 91.27%. Removing the consistency gate changes nothing (identical matrix). Removing the pattern gate gives 78 FP instead of 85.
- Pattern gate (I3) alone flags all 85 FP. The paper's "Gate A 78 / Gate B 7, non-overlapping subsets" is an artefact of check order, not disjoint failure modes.
- AUC: S_E 1.000, S_C 0.887, S_D 0.715, C(f) 0.807, Conf(f) 1.000.

## 3. Nested threshold selection (20 stratified 50/50 splits, grid of 81)
- Full rule on held-out halves: acc 0.912 ± 0.011, prec 0.870 ± 0.014, rec 1.000, F1 0.930 ± 0.008. Chosen thresholds were (0.50, 0.55) in 20/20 splits. Headline is not selection-optimistic on this set.
- Conf-only: acc 0.998 ± 0.002.

## 4. Count reconciliation (corrects my earlier plan)
- K=2: 202 candidates = 90 admitted + 112 withheld. Paper text is right.
- Domain graph 119 edges = 90 abstracted (`min_support_2`) + 29 hand-curated (`domain_specific_medical_practice`: informs, collaborates_with, uses_treatments_from, monitors). Table 4 and §3.3 must say this.
- Entities: 95 Drug + 42 Condition + 12 Adverse_Effect = 149; 95 of the 100 cohort drugs.
- The CSV `decision` column was written at 0.80/0.50; paper results use the 0.50/0.55 rule, which this script recomputes.

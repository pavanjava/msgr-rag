# MSGR-RAG revision: modification report (Reviewer 2 and Reviewer 3)

All numbers below are reproducible: `cd reviewer_response && python3 -I analyses.py | edge_masking.py | judge_eval.py`.
No frozen file or verifier code was changed. The headline matrix (TP 574 / FP 85 / FN 0 / TN 315; acc 91.27%, F1 93.11%) is re-asserted at the top of `analyses.py`.

## 0. Must-fix before resubmission (found while checking provenance)

**0.1 Table 16 / Fig. 7 / "+19.5 points" / abstract claim "outperforms plain RAG on every category" are not supported.**
The plain-RAG column in the paper (67.8; 84.4 / 71.6 / 80.5 / 30.6) comes from the sensitivity-analysis file `plain_rag_sensitivity.csv`, not from the primary plain-RAG run `simple_rag_v2_results.csv`. The two differ in 117 decisions (same answer text, different VERIFIED/HALLUCINATION label; the file notes "~15% relative reduction in category accuracy"). How those 117 decisions were produced is not documented in the repo. The paper must say which run Table 16 reports and how the sensitivity variant was generated. Primary-run numbers, for reference or as the main table with the sensitivity variant reported separately:

| Resolved subset, same 733 questions | Plain RAG (measured) | MSGR pipeline |
|---|---|---|
| Overall accuracy | 78.9% | 75.7% |
| Absent relationship (n=170) | 100.0% | 98.2% |
| Real relationship (n=359) | 89.7% | 77.4% |
| Domain-inconsistent (n=50) | 94.0% | 100.0% |
| Predicate-swapped (n=154) | 25.3% | 39.0% |

All 974 questions (UNKNOWN counted as error): plain RAG 79.8%, MSGR 57.0%. McNemar on the resolved subset: b=59, c=82, chi2=3.43, p=0.064.
Suggested wording: "On the 733 questions the pipeline resolves, plain RAG and MSGR-RAG are statistically indistinguishable overall (78.9% vs 75.7%, p=0.064). MSGR-RAG is higher on domain-inconsistent (+6.0 points) and predicate-swapped (+13.7 points) questions and lower on real relationships (-12.3 points), reflecting its conservative decision rule." Remove every sentence that says MSGR-RAG beats plain RAG on every category. Also delete the declaration/Data-availability line implying the sensitivity file is a measurement, or state it was excluded.

**0.2 Gate attribution (§5.6) is order-dependent.** Pattern I3 alone flags all 85 false positives; removing the consistency gate changes no decision. Replace "78 consistency + 7 pattern, non-overlapping subsets" with: "All 85 false positives are flagged by the scale-divergence pattern I3 (max pairwise |S_i - S_j| > 0.5); 78 of them also fall below theta_consistency." Remove the claim that the two gates catch non-overlapping subsets.

**0.3 Domain-inconsistent labels vs S_D.** 15 of the 75 domain-inconsistent facts have S_D = 1.0 under the ATC-grounded phi_ED; 36 have S_D = 0.3 and 24 have 0.5. The category is defined on the transitive phi_ED + K=2, not on the final score.

## 1. Reviewer 2

| Comment | Result | What to change in the paper |
|---|---|---|
| W1 / Q1 / S1 (labels = K=2 rule) | Confirmed. Entity-only (S_E<1) scores 100.0% on all 974 facts; every domain-inconsistent fact has S_E = 0.1 by construction. | Say so in §4.3, §5.4, §8 and the abstract: the 100% on this category checks the set's construction and the rule's internal consistency; it is not independent evidence of detecting unseen scale inconsistencies. Add the edge-masking result (§3 below). |
| W2 / Q3 / S3 (threshold selection) | Thresholds came from the sweep on the 981-fact pre-refinement set (paper §5.1). Re-selecting on a random stratified 50% and scoring the other 50%, 20 times: acc 91.2% ± 1.1, prec 87.0% ± 1.4, rec 100%, F1 93.0% ± 0.8; chosen thresholds were (0.50, 0.55) in 20/20 splits. | State where thresholds were chosen; add the nested-split row to Table 9/10. Keep 91.3% as the full-set figure. |
| W3 / Q2 / S2 (confidence-only ablation) | Conf-only at 0.55: acc 99.69% (0 FP, 3 FN), F1 99.74%. At the gap midpoint 0.687: 100%. Nested split: 99.8% ± 0.2. Full rule: 91.27%. Consistency gate removed: identical. Pattern gate removed: 78 FP (acc 91.99%). AUC: S_E 1.000, S_C 0.887, S_D 0.715, C(f) 0.807, Conf(f) 1.000. | Add the ablation table (`out/ablation.csv`). State that on this set the full rule is a conservative design that costs 85 FP, and that a confidence-only rule is better on every metric. Do not claim the gates improve accuracy. |
| W4 / S5 (title, abstract) | Pipeline: 91.3% (clean triples), 75.7% (resolved 75.3%), 57.0% (all 974). | Drop "Hallucination-Resilient" (agreed). Report all three numbers in the abstract. |
| W5 / Q4 / S4 (counts) | 202 = 90 admitted + 112 withheld (text correct). Domain graph 119 = 90 K=2-abstracted + 29 hand-curated edges (informs, collaborates_with, uses_treatments_from, monitors). Entities: 95 Drug + 42 Condition + 12 Adverse_Effect = 149; 5 of the 100 cohort drugs yield no extractable relationship. 103,552 relationships collapse to 103,551 DiGraph edges (one duplicate ordered pair). 187 to 118 is a 36.9% reduction. | Add to §3.3/Table 4: "119 = 90 + 29 expert-added". Replace "nearly halves" with "reduces by 36.9%". Fix the Eq. (14)/(21) reference, define the satisfiability symbol and divergence. |
| W6 / S5 (refs [14], [20], [35]) | Verified by text search of both PDFs. [14] (arXiv 2311.07914): no occurrence of "multi-scale", "level of abstraction", "single level" or "granularity". [20] (arXiv 2408.08921): "granularity" means retrieval unit (nodes, triplets, paths, subgraphs); its Future Prospects (§10) list dynamic graphs, multimodality, scalability, graph foundation models, context compression, benchmarks, applications; no multi-scale verification. [35] is BM25. | Remove the attributed sentences or rewrite as "to our knowledge, the surveyed KG-grounded methods [5, 14, 20, 25] do not perform cross-granularity consistency checks", framed as the authors' own observation. Remove "hybrid sparse-dense" next to [35]; say BM25. Remove the single-level claim from the abstract and §1.1 unless cited. |
| W7 / S5 (baseline) | See §4 (judge baseline). | Add the LLM-judge row; keep TF-IDF but state it was run on the 981-fact pre-refinement set. List NLI, RAGAS, ARES and RAGTruth detectors under future work. |

## 2. Reviewer 3

| Comment | Response |
|---|---|
| Negatives rely on rules close to the detector | Same as R2-W1. Add the sentence from W1 and restrict claims to "this evaluation setting". |
| Component contribution; confidence-only; AUC vs. 85 FP | Ablation (R2-W3). Rewrite §5.7: Conf(f) separates the classes perfectly on this set (AUC 1.000, gap 0.652 to 0.722); the gates are retained as a deliberately conservative layer for safety-critical use, costing 85 FP; the gates are not shown to add accuracy here. |
| NL degradation; 5-sentence regex test; denominators; practical readiness | Table 16 replaced with aligned denominators (0.1). Mark §6.7 as an anecdotal n=5 check. Replace "robust" in §6.5 and §8. The predicate-swap drop is a question-generation artefact and limits the pipeline end to end. |
| Abstract too long | Cut to about 150 words: problem; approach; core 91.3% (clean triples), 75.7% resolved, 57.0% all questions; ablation finding; limitations (single DrugBank cohort, deterministic scorer, set construction). |
| Deterministic vs learned verifier; generalisation | One scope paragraph in §1.3; label Eq. (5) "not evaluated"; §8 states one cohort, one LLM. |

## 3. Independent test: edge masking (`edge_masking.py`, `out/edge_masking_summary.csv`)
Setup: hold out 10/20/30% of the 400 real entity edges (5 seeds each), rebuild G_C and G_D from the masked G_E with the same K=2 rule plus the 29 hand-curated edges, and ask whether the concept and domain scores separate the held-out TRUE facts from the 574 false facts among facts the entity scale cannot support. No label depends on K. Rebuilt unmasked graphs give 339 concept edges (matches) and 118 domain edges (frozen 119); the scorer matches frozen S_E 100%, S_C 99.9%, S_D 97.5%.

| Held-out rate | AUC S_E | AUC S_C | AUC S_D | AUC S_C+S_D | AUC Conf(f) | AUC C(f) | Held-out true flagged by full rule |
|---|---|---|---|---|---|---|---|
| 10% | 0.328 | 0.828 | 0.674 | 0.856 | 0.752 | 0.116 | 100% |
| 20% | 0.330 | 0.835 | 0.704 | 0.876 | 0.772 | 0.101 | 100% |
| 30% | 0.331 | 0.841 | 0.698 | 0.880 | 0.770 | 0.098 | 100% |

Reading: concept and domain scores carry real signal beyond the entity scale (AUC about 0.88 for S_C+S_D versus about 0.33 for S_E), which is the independent evidence for a multi-scale contribution. The shipped decision rule does not use it: cross-scale consistency C(f) is anti-correlated with truth here (AUC about 0.10) and the full rule flags 100% of held-out true facts. An exploratory rescue rule (accept if S_C = 1 and S_D = 1) recovers 62-63% of held-out true facts at a 5.2% false-accept rate. Present this as an exploratory result and as motivation for future work; do not add it to the headline method.

## 4. Stronger baseline (closed-book LLM judge)
Closed-book LLM-as-judge: gemma3 (local Ollama, temperature 0) is asked whether each rendered triple ("X is used to treat Y.") is a true established fact, on the same 974 clean triples (`llm_judge.py`, `judge_eval.py`, `out/llm_judge_gemma3.csv`, `out/baseline_comparison.csv`).

| System | n | Acc | Prec | Rec | F1 |
|---|---|---|---|---|---|
| MSGR core (full rule) | 974 | 91.3% | 87.1% | 100.0% | 93.1% |
| Closed-book gemma3 judge | 974 | 61.7% | 65.6% | 73.5% | 69.4% |
| TF-IDF (aligned subset) | 914 | 68.6% | 100.0% | 44.2% | 61.3% |

Per-category accuracy (MSGR / judge / TF-IDF): absent 100 / 68.6 / 73.6; predicate-swapped 100 / 83.0 / 0.0; domain-inconsistent 100 / 68.0 / 46.7; real 78.8 / 44.8 / 100.
McNemar MSGR vs judge: b=332, c=44, chi2=219.07, p=1.4e-49.

Caveats to state in the paper: the judge is closed-book (parametric knowledge only, no KG evidence) and a single 4B-class model, so it shows the task is not solved by a general LLM, not that MSGR beats a retrieval-grounded judge. The judge's low real-edge accuracy partly reflects that DrugBank-derived interacts_with/causes facts are obscure. NLI-based, RAGAS, ARES and RAGTruth detectors remain future work.

## 5. Consistency checklist for the LaTeX
Changes to a number or claim also appear in: abstract; §1.3 contributions; §2.2 (refs); §3.3 and Table 4 (119 = 90 + 29); §4.3; §5.4; §5.6; §5.7; §6.3 to §6.6; Table 16 and Fig. 7; §8. Add the ablation, nested-split and edge-masking tables to §5.

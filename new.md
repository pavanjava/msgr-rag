# MSGR-RAG: Complete Revision Report — Ontology Grounding, Statistical Validation, and Natural-Language Verification Pipeline

**Status: Partially corrected per internal review. Items marked [PENDING] require a script rerun before final numbers can be inserted. Items marked [OPEN — SCOPE DECISION NEEDED] require a methodological decision before any further rewriting, since they change the underlying decision rule or experimental design and would invalidate downstream numbers if fixed piecemeal.**

---

## Part I: Ontology-Grounded Φ

### 1. The Reviewer Concern

Reviewer 1 challenged the manuscript's abstraction mappings Φ = {φ_EC, φ_CD, φ_ED} as lacking external grounding. This report documents the implementation of an ontology-grounded solution and its measured effect on system performance.

### 2. Ontology Selection: ATC

The **Anatomical Therapeutic Chemical (ATC) Classification System** was selected as the grounding ontology for φ_ED. ATC was chosen over MeSH/UMLS because DrugBank natively provides an `atc-codes` field, ATC's hierarchy aligns naturally with MSGR-RAG's three-tier structure, and introducing multiple ontologies simultaneously was judged disproportionate to reviewer benefit; MeSH/UMLS extension is scoped as future work.

### 3. Data-Quality Finding: Source File Deduplication [CORRECTED — arithmetic now reconciles]

Before ATC integration, a data-integrity issue in `drugbank_clean.csv` was identified and resolved. The cleaning proceeded in two distinct steps, previously conflated in earlier drafts of this report:

| Step | Rows before | Rows removed | Rows after | Basis |
|---|---|---|---|---|
| 1. Remove null-`drugbank-id` rows | 16,762 | 596 | 16,166 | Rows with no identifier at all — unusable, unidentifiable |
| 2. Deduplicate remaining `drugbank-id`s | 16,166 | 931 | 15,235 | Remaining rows sharing a `drugbank-id`; one representative retained per ID |

**Note on a previously-reported figure:** an earlier draft of this report stated "1,527 duplicate rows." That figure was computed against the *original, uncleaned* 16,762-row file, where pandas' duplicate-detection also (incorrectly, for this purpose) treated all 596 null-ID rows as mutual duplicates of one another. It measured a different quantity than "rows removed via deduplication after null-ID rows were already excluded" (931, the correct figure) and should not be read alongside the final counts. This report now reports only the two-step, reconciling figures above: 16,762 → 16,166 → 15,235.

Deduplication (step 2) used a completeness-based rule: for each `drugbank-id` with multiple rows, the row with the fewest null fields was retained. Verified column-by-column for all 17 affected cohort drugs; 16/17 had fully identical duplicate rows, and 1 (Phenprocoumon, DB00946) had a single differing field (`enzymes`) resolved correctly by the completeness rule.

### 4. ATC L1 Detection Methodology

The `atc-codes` field contains concatenated ATC category *names* with no delimiters. A substring-matching procedure was used against the fixed set of 14 WHO ATC Level 1 category names. Detection reliability: 95/95 drugs with populated `atc-codes` yielded at least one clean L1 match; zero false negatives.

### 5. Coverage Classification

| Classification | Count | Description |
|---|---|---|
| **ATC-grounded (single match)** | **74** | Unambiguous domain assignment |
| Fallback — multi-domain | 21 | Multiple ATC L1 categories detected; routed to deterministic fallback rather than an unjustified tie-break rule |
| Fallback — no ATC data | 5 | No `atc-codes` data available |

**ATC-grounded coverage: 74/100 (74%).** A **pre-specified reporting threshold** [CORRECTED — was previously and inaccurately termed "pre-registered," which implies formal protocol registration that did not occur] of 75% was set before this measurement to determine reporting framing. At 74%, this analysis uses the hybrid framing.

**Design decision on multi-domain drugs:** the 21 multi-domain drugs are explicitly routed to the existing deterministic fallback rather than an unjustified single-domain tie-breaking rule.

### 6. Domain-Vocabulary Alignment

A documented 14-row crosswalk table translates ATC L1 categories into MSGR-RAG's existing 16-domain vocabulary, preserving the existing domain graph structure. **Documented limitation:** ATC L1-level grounding is coarser than the original domain granularity in some cases (e.g., opioid analgesics grouped under Nervous System rather than a dedicated Pain Management domain).

### 7. Architectural Integration

φ_ED was modified from a purely transitive function (φ_ED = φ_CD ∘ φ_EC) to a hybrid function: ATC-grounded direct mapping checked first, transitive route as fallback. φ_EC, φ_CD, and G_D's structure were left unmodified.

### 8. Effect of ATC Grounding on Performance

**At fixed threshold (θ_consistency=0.8, θ_confidence=0.5):**

| Metric | Transitive-only φ_ED | ATC-grounded φ_ED |
|---|---|---|
| Accuracy | 71.2% | 78.6% |
| Precision | 72.2% | 80.6% |
| Recall | 83.5% | 84.2% |
| F1 | 77.4% | 82.3% |
| False Positives | 187 | 118 |

**Test-set integrity correction:** ATC integration surfaced a test-set construction flaw (forward-direction-only exclusion check missing symmetric-predicate reverse matches). Confirmed mislabeled facts were removed; test set regenerated 981 → 974 facts.

**Results at θ_consistency=0.5, θ_confidence=0.55** [OPEN — SCOPE DECISION NEEDED: see Section 13a. These thresholds were selected by maximizing F1 on the same 974 facts used for the final reported metrics below. This is a threshold-leakage concern raised in internal review. The numbers below should currently be described as a **threshold-sensitivity operating point**, not an unbiased held-out estimate, until a train/validation/test split is implemented — see Section 13a for the open decision]:

| Metric | Value |
|---|---|
| Accuracy | 91.3% |
| Precision | 87.1% |
| Recall | 100.0% |
| F1-Score | 93.1% |
| False Negatives | 0 |

**Per-category accuracy:**

| Category | n | Accuracy |
|---|---|---|
| nonexistent_relationship | 299 | 100.0% |
| wrong_predicate | 200 | 100.0% |
| domain_violation | 75 | 100.0% |
| real_edge | 400 | 78.75% |

---

## Part II: Statistical Validation

### 9. Overview

Five analyses were conducted: bootstrap confidence intervals, a paired significance test, an effect-size measure, a non-parametric score-separation test, and ROC/AUC analysis.

### 10. Bootstrap Confidence Intervals

**Overall (n=974):**

| Metric | Point Estimate | 95% CI |
|---|---|---|
| Accuracy | 91.3% | 89.4% – 93.1% |
| Precision | 87.1% | 84.5% – 89.7% |
| Recall | 100.0% | 100.0% – 100.0%¹ |
| F1-Score | 93.1% | 91.6% – 94.6% |

¹ *Reflects zero observed false negatives on this test set; not a guarantee for unseen data.*

**Per-category:**

| Category | n | Accuracy | 95% CI |
|---|---|---|---|
| nonexistent_relationship | 299 | 100.0% | 100.0% – 100.0% |
| wrong_predicate | 200 | 100.0% | 100.0% – 100.0% |
| domain_violation | 75 | 100.0% | 100.0% – 100.0% |
| real_edge | 400 | 78.8% | 74.8% – 82.8% |

### 11. McNemar's Test — MSGR-RAG vs. Semantic Similarity Baseline [PENDING — see below]

*Terminology correction: the comparison baseline operates on pre-formed structured triples with no retrieval or generation, and is termed the* **Semantic Similarity Baseline** *(TF-IDF cosine similarity), not "Semantic RAG."*

**[PENDING]** The current McNemar's test aligns only **914 of 974** facts, because the baseline's saved predictions (`semantic_rag_predictions.csv`) were generated against an earlier 981-fact file, before the domain_violation test-set cleanup (Section 8). This silently excludes 60 samples from the paired comparison without a stated reason — a reviewer would reasonably ask why.

**Required fix, not yet executed:** rerun the Semantic Similarity Baseline against the final, corrected 974-fact file (`test_facts_large_v2.csv` post-cleanup), so every sample has a matched pair and McNemar's test can be computed over the full, exact 974-fact evaluation set with no unexplained exclusions.

Values below are from the **previous, 914-sample-aligned run** and must be replaced once the baseline is rerun on all 974:

| Statistic | Value (914-sample run — TO BE REPLACED) |
|---|---|
| Aligned fact count | 914 |
| MSGR-RAG accuracy | 90.7% |
| Semantic Similarity Baseline accuracy | 68.6% |
| McNemar χ² statistic | 108.60 |
| p-value | < 0.000001 |
| Cohen's h | 0.570 (medium effect) |

### 12. Mann-Whitney U Test — Score Separation Across Scales

| Score | Median (Verified) | Median (Hallucinated) | p-value | Significant |
|---|---|---|---|---|
| S_E (entity) | 1.000 | 0.100 | 1.56 × 10⁻¹⁷⁹ | *** |
| S_C (concept) | 1.000 | 0.400 | 3.99 × 10⁻¹¹⁴ | *** |
| S_D (domain) | 1.000 | 0.500 | 1.31 × 10⁻³⁴ | *** |
| C_f (consistency) | 1.000 | 0.723 | 1.32 × 10⁻⁶¹ | *** |
| Conf_f (confidence) | 1.000 | 0.412 | 6.79 × 10⁻¹⁶⁰ | *** |

All five scores show highly significant separation (p < 0.001).

### 13. ROC / AUC Analysis

| Metric | Value |
|---|---|
| AUC using Conf(f) | **1.000** |
| AUC using C(f) alone | 0.807 |

Verified non-degenerate: score ranges do not overlap (verified [0.722, 1.000] vs. hallucinated [0.346, 0.652]).

Diagnostic tracing of all 85 false positives found: 78/85 rejected at Level 1 (C(f) below threshold), 7/85 at Level 2 (inconsistency pattern), and **85/85 (100%) had Conf_f values that would have been classified correctly had Conf(f) been used alone.**

### 13a. [OPEN — SCOPE DECISION NEEDED] Decision-Rule Redundancy and Threshold-Leakage

Two significant, unresolved methodological concerns were raised in internal review and are recorded here rather than silently patched, since both require a full pipeline rerun and a prior decision on scope:

**(a) Redundancy of C(f), I₃(f), and the hierarchical OR-rule.** The Section 13 finding — that Conf(f) alone perfectly separates this evaluation set (AUC=1.0), and that 100% of the 85 false positives would be correctly classified under Conf(f) alone — raises a legitimate question of whether the hard consistency gate C(f) and inconsistency-pattern gate I₃(f) are earning their place in the final decision rule on this dataset, given I₃ is mathematically related to the same score divergences C(f) already captures. A proposed simplification, not yet implemented or evaluated:

$$Conf(f) = \alpha S_E(f) + \beta S_C(f) + \gamma S_D(f)$$
$$H(f) = \text{HALLUCINATION if } C(f) < \theta_C \lor Conf(f) < \theta_{Conf}, \text{ else VERIFIED}$$

with I₁, I₂, I₃ retained as diagnostic labels rather than hard decision gates. **This has not been implemented.** Adopting it would require a full rerun of every downstream result in this report (Sections 8–20).

**(b) Threshold selection without a held-out test set.** θ_consistency=0.5 and θ_confidence=0.55 (Section 8) were selected by maximizing F1 on the same 974 facts used to report the final 91.3%/93.1% headline numbers — a threshold-leakage concern. The methodologically clean fix (stratified train/validation/test split; select thresholds on validation only; freeze; evaluate once on held-out test) has not been implemented. Until it is, all headline metrics in this report should be described as a **threshold-sensitivity operating point** rather than an unbiased held-out test estimate.

**Decision needed before further work:** whether to implement (a) and (b) together (recommended, since both require the same full rerun) before continuing to the next section of the paper, or to proceed with the current results explicitly labeled as an operating-point demonstration pending this future work.

---

## Part III: Natural-Language Verification Pipeline (Component 6)

### 14. Motivation and Naming Correction [CORRECTED]

Components 1–5 establish and validate MSGR-RAG's verification core. This core, by itself, does not constitute a RAG system — no retrieval, extraction, or generation is involved.

**Naming correction:** the natural-language pipeline built in this section was previously termed a "full RAG pipeline." On review, this is an overclaim: the pipeline performs question → extraction → verification → decision, but **does not generate a free-text answer back to the user** — there is no answer-generation stage after the verification decision. Only the separate Plain RAG baseline (Section 20) contains genuine retrieval → context → generation. This section is therefore retitled the **Natural-Language MSGR-RAG Verification Pipeline**. A true end-to-end RAG system (adding an answer-generation stage after verification) remains a scoped future extension, not yet implemented.

### 15. Architecture
```terminaloutput
User question (free text)
-> LLM extraction (Gemma3, few-shot prompted): question -> candidate (subject, predicate, object)
-> Entity existence check: are both entities present in G_E?
NO -> UNKNOWN (cannot verify; not treated as a false claim)
YES -> Multi-scale verifier (unmodified Component 5 core): S_E, S_C, S_D
-> Hierarchical decision: C(f), inconsistency patterns, Conf(f)
-> VERIFIED or HALLUCINATION
```

The verification core is reused verbatim from Component 5. The only new logic is the extraction stage and the entity-existence gate producing a third outcome, UNKNOWN.

### 16. Natural-Language Question Generation

974 natural, patient-style questions were generated (one per fact in the validated evaluation set) using Gemma3 with few-shot prompting, preserving full ground-truth traceability. Generation: 974/974 successful, 0 failures.

### 17. Pipeline Results — Selective Prediction Framing [CORRECTED per internal review]

Because this pipeline includes an abstention mechanism (UNKNOWN), results are reported using selective-prediction terminology rather than a single blended accuracy figure:

| Selective-prediction metric | Value |
|---|---|
| **Coverage** (fraction of questions resolved) | 733 / 974 = **75.3%** |
| **Selective accuracy** (accuracy on resolved cases only) | **75.7%** |
| **Abstention (UNKNOWN) rate** | 238 / 974 = **24.4%** |
| Extraction-failed rate | 3 / 974 = 0.3% |
| **Conservative overall accuracy** (abstentions counted as incorrect) | 555 / 974 = **57.0%** [CORRECTED — a previous draft incorrectly stated 68.4% here; this did not match the underlying arithmetic (733 × 75.7% ≈ 555; 555/974 ≈ 57.0%) and has been removed] |

**Metrics on resolved subset (n=733), full breakdown:**

| Metric | Value |
|---|---|
| Precision | 77.4% |
| Recall | 74.1% |
| F1-Score | 75.7% |

**Per-category accuracy on resolved subset:**

| Category | n | Accuracy |
|---|---|---|
| nonexistent_relationship | 170 | 98.2% |
| domain_violation | 50 | 100.0% |
| real_edge | 359 | 77.4%¹ |
| wrong_predicate | 154 | 39.0% |

¹ *Precision/recall undefined (0%) for this single-class category under a HALLUCINATION-positive-class metric definition; accuracy is the only meaningful per-category figure.*

### 18. Diagnosed Mechanism: wrong_predicate Degradation

Root-caused, not left unexplained: inspection of 94 resolved wrong_predicate errors found 91/94 had `extracted_predicate != original_predicate`. Cause: for drug-drug pairs, natural-language question generation colloquially phrases the relationship as an interaction query regardless of the deliberately-incorrect ground-truth predicate. This is a limitation of LLM-mediated question generation, not of the verification methodology, which achieves 100% on this category given clean input (Section 8).

### 19. Comparison: Verification Core vs. Natural-Language Pipeline

| | Verification Core (clean triples) | Natural-Language Pipeline |
|---|---|---|
| n | 974 | 733 resolved / 974 total |
| Accuracy | 91.3% | 75.7% (selective) |
| Precision | 87.1% | 77.4% |
| Recall | 100.0% | 74.1% |
| F1 | 93.1% | 75.7% |

**Per-category:**

| Category | Verification Core | Natural-Language Pipeline | Δ |
|---|---|---|---|
| nonexistent_relationship | 100.0% | 98.2% | -1.8 |
| real_edge | 78.75% | 77.4% | -1.4 |
| domain_violation | 100.0% | 100.0% | 0.0 |
| wrong_predicate | 100.0% | 39.0% | -61.0 |

Three of four categories degrade minimally (≤2 points) or not at all — evidence the core reasoning is robust to LLM-mediated extraction, independent of the wrong_predicate-specific generation limitation.

### 20. Comparison: Plain RAG vs. Natural-Language MSGR-RAG Pipeline [CORRECTED — apples-to-apples comparison pending]

A minimal Plain RAG baseline (TF-IDF similarity retrieval + Gemma3 free-text generation with self-reported decision, no MSGR-RAG verification) was built to isolate the specific contribution of the multi-scale verification layer.

**[PENDING — fairness correction required, per internal review]:** the comparison below currently evaluates Plain RAG on **all 974 questions** while MSGR-RAG's selective accuracy is computed on only its **733 resolved** questions — different denominators, not a fair comparison as currently stated. The required fix (not yet executed): recompute Plain RAG's accuracy restricted to exactly the same 733-question subset MSGR-RAG resolved, using the matched-subset script below.

```python
# Required rerun before this section can be finalized:
resolved_facts = e2e_df[e2e_df['pipeline_decision'].isin(['VERIFIED', 'HALLUCINATION'])][
    ['subject', 'predicate', 'object']
]
plain_rag_matched = plain_rag_df.merge(resolved_facts, on=['subject', 'predicate', 'object'], how='inner')
# accuracy_matched = (plain_rag_matched['simple_rag_decision'] == plain_rag_matched['ground_truth']).mean()
```

Values below are the **current, not-yet-fairness-corrected** figures (Plain RAG on all 974; MSGR-RAG selective accuracy on 733) and must be replaced with the matched-733-subset comparison before publication:

| Metric | Plain RAG (all 974 — TO BE REPLACED WITH MATCHED-733) | Natural-Language MSGR-RAG Pipeline (selective, 733) |
|---|---|---|
| Accuracy | 67.8% | 75.7% (selective) / 57.0% (conservative) |
| nonexistent_relationship | 84.4% | **98.2%** |
| real_edge | 71.6% | **77.4%** |
| domain_violation | 80.5% | **100.0%** |
| wrong_predicate | 30.6% | **39.0%** |

**Reproducibility caveat, disclosed in full:** an earlier run of the Plain RAG baseline (prior to a retrieval-ranking fix) produced a substantially different accuracy (79.8%). The cause of this run-to-run variance was not fully isolated: a 5-trial determinism check with identical input and temperature=0.0 confirmed byte-identical output, ruling out LLM non-determinism, but the underlying cause (a likely unlogged intermediate data or code change between the two runs) was not conclusively identified. The 67.8% figure above is the retrieval-corrected result but has not yet been independently reproduced in a fresh, fully logged run. This is disclosed as an open limitation rather than omitted.

---

## 21. Summary of Contribution and Remaining Open Items

### Resolved in this revision:
1. Ontology-grounded Φ via ATC (74% coverage, documented fallback, crosswalk table)
2. Reconciled DrugBank cleaning arithmetic (16,762 → 16,166 → 15,235, two-step, fully auditable)
3. Corrected "pre-registered" → "pre-specified reporting threshold"
4. Corrected 68.4% → 57.0% internal inconsistency
5. Natural-language pipeline correctly renamed (not claimed as "full RAG" without an answer-generation stage)
6. wrong_predicate degradation mechanistically diagnosed, not just observed
7. Statistical validation suite established (bootstrap CI, Mann-Whitney, ROC/AUC)

### Explicitly open, pending further work before this report is submission-ready:
1. **[PENDING]** McNemar's test rerun on the full, exact 974-fact set (currently 914-aligned, 60 samples silently excluded)
2. **[PENDING]** Plain RAG re-evaluated on the exact matched 733-question subset for a fair selective-vs-selective comparison
3. **[OPEN — SCOPE DECISION]** C(f)/I₃(f) redundancy — simplify the decision rule and rerun all downstream metrics, or retain and justify explicitly
4. **[OPEN — SCOPE DECISION]** Train/validation/test split to eliminate threshold-selection leakage — all current headline numbers should be described as a threshold-sensitivity operating point until this is done
5. **[OPEN]** Plain RAG baseline run-to-run variance (79.8% vs. 67.8%) not fully explained; needs a fresh, fully logged reproduction run

**This report should not be treated as final until items 1–5 above are resolved or explicitly and permanently scoped as future work in the paper itself.**
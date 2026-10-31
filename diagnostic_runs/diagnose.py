import pandas as pd
from pathlib import Path

INTERMEDIATE_DIR = Path("../Datasets/intermediate")

selected_drugs = pd.read_csv(INTERMEDIATE_DIR / "selected_drugs_100.csv")
drugbank_deduped = pd.read_csv("../Datasets/drugbank_clean_deduped.csv", low_memory=False)

merged = selected_drugs.merge(
    drugbank_deduped[['drugbank-id', 'atc-codes']],
    on='drugbank-id',
    how='left'
)

print(f"Merged cohort size: {len(merged)}  (should be exactly 100 now)")
assert len(merged) == 100, f"Expected 100 rows, got {len(merged)} — dedup did not fully resolve the fan-out"

ATC_L1_CATEGORIES = {
    "A": "ALIMENTARY TRACT AND METABOLISM",
    "B": "BLOOD AND BLOOD FORMING ORGANS",
    "C": "CARDIOVASCULAR SYSTEM",
    "D": "DERMATOLOGICALS",
    "G": "GENITO URINARY SYSTEM AND SEX HORMONES",
    "H": "SYSTEMIC HORMONAL PREPARATIONS, EXCL. SEX HORMONES AND INSULINS",
    "J": "ANTIINFECTIVES FOR SYSTEMIC USE",
    "L": "ANTINEOPLASTIC AND IMMUNOMODULATING AGENTS",
    "M": "MUSCULO-SKELETAL SYSTEM",
    "N": "NERVOUS SYSTEM",
    "P": "ANTIPARASITIC PRODUCTS, INSECTICIDES AND REPELLENTS",
    "R": "RESPIRATORY SYSTEM",
    "S": "SENSORY ORGANS",
    "V": "VARIOUS",
}

def detect_atc_l1(blob):
    if pd.isna(blob):
        return []
    blob_upper = str(blob).upper()
    return [(code, name) for code, name in ATC_L1_CATEGORIES.items() if name in blob_upper]

merged['atc_l1_detected'] = merged['atc-codes'].apply(detect_atc_l1)
merged['atc_l1_count'] = merged['atc_l1_detected'].apply(len)

def classify(row):
    if row['atc_l1_count'] == 1:
        return 'atc_grounded_single'
    elif row['atc_l1_count'] > 1:
        return 'fallback_multi_domain'
    else:
        return 'fallback_no_atc'

merged['mapping_source'] = merged.apply(classify, axis=1)

print(f"\n{merged['mapping_source'].value_counts()}")
print(f"\nATC-grounded coverage: {(merged['mapping_source']=='atc_grounded_single').sum()}/100")

merged['atc_l1_domain'] = merged['atc_l1_detected'].apply(
    lambda lst: lst[0][1] if len(lst) == 1 else None
)

output_cols = ['drugbank-id', 'name', 'mapping_source', 'atc_l1_domain', 'atc_l1_count']
merged[output_cols].to_csv(INTERMEDIATE_DIR / "atc_domain_classification.csv", index=False)
print(f"\nSaved: {INTERMEDIATE_DIR / 'atc_domain_classification.csv'}")
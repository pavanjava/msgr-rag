import spacy
import re
from typing import List, Tuple

class MedicalFactExtractor:
    def __init__(self):
        # Load medical NLP model (install: pip install scispacy, pip install https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.5.1/en_core_sci_sm-0.5.1.tar.gz)
        self.nlp = spacy.load("en_core_sci_sm")

    def extract_facts(self, text: str) -> List[Tuple[str, str, str]]:
        """Extract medical facts as (subject, predicate, object) triples"""
        doc = self.nlp(text)
        facts = []

        # Simple pattern matching for medical relationships
        patterns = [
            (r"(\w+) (?:is|are) increased in (\w+)", "increased_in"),
            (r"(\w+) (?:is|are) associated with (\w+)", "associated_with"),
            (r"(\w+) treats? (\w+)", "treats"),
            (r"(\w+) causes? (\w+)", "causes"),
            (r"(\w+) prevents? (\w+)", "prevents"),
            (r"(\w+) (?:is|are) contraindicated in (\w+)", "contraindicated_in")
        ]

        for pattern, relation in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                subject = match.group(1).strip()
                object_entity = match.group(2).strip()
                facts.append((subject, relation, object_entity))

        return facts

# Test with your PubMedQA example
extractor = MedicalFactExtractor()
sample_text = "ILC2s are increased in patients with CRSwNP and were associated with nasal polyps."
facts = extractor.extract_facts(sample_text)
print("Extracted facts:", facts)
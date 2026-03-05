import numpy as np
from typing import Dict, Tuple, List
import logging

class CrossScaleConsistencyCalculator:
    def __init__(self, entity_verifier, concept_verifier, domain_verifier, graph_verifier):
        self.entity_verifier = entity_verifier
        self.concept_verifier = concept_verifier
        self.domain_verifier = domain_verifier
        self.graph_verifier = graph_verifier

        # Thresholds from our mathematical framework
        self.tau_high = 0.7
        self.tau_low = 0.3
        self.delta_threshold = 0.5
        self.theta_consistency = 0.8
        self.theta_confidence = 0.5

    def abstract_fact(self, fact_triple: Tuple[str, str, str], target_scale: str) -> Tuple[str, str, str]:
        """Abstract fact to target scale using φ functions"""
        subject, predicate, obj = fact_triple

        if target_scale == "concept":
            # φ_EC: Entity to Concept
            subject_abstract = self.graph_verifier.get_abstraction(subject, "entity", "concept")
            obj_abstract = self.graph_verifier.get_abstraction(obj, "entity", "concept")
        elif target_scale == "domain":
            # φ_ED: Entity to Domain (transitive)
            subject_abstract = self.graph_verifier.get_abstraction(subject, "entity", "domain")
            obj_abstract = self.graph_verifier.get_abstraction(obj, "entity", "domain")
        else:
            return fact_triple

        if subject_abstract and obj_abstract:
            return (subject_abstract, predicate, obj_abstract)
        else:
            return None

    def get_verification_scores(self, fact_triple: Tuple[str, str, str]) -> Dict[str, float]:
        """Get S_E(f), S_C(f), S_D(f) verification scores"""
        scores = {}

        # Entity-level verification: S_E(f)
        entity_neural = self.entity_verifier.verify_fact(fact_triple)
        entity_graph = self.graph_verifier.verify_fact_in_graph(fact_triple, "entity")
        scores['S_E'] = (entity_neural + entity_graph) / 2.0  # Combine neural and graph scores

        # Concept-level verification: S_C(φ_EC(f))
        concept_fact = self.abstract_fact(fact_triple, "concept")
        if concept_fact:
            concept_neural = self.concept_verifier.verify_fact(concept_fact)
            concept_graph = self.graph_verifier.verify_fact_in_graph(concept_fact, "concept")
            scores['S_C'] = (concept_neural + concept_graph) / 2.0
            scores['concept_fact'] = concept_fact
        else:
            scores['S_C'] = 0.0
            scores['concept_fact'] = None

        # Domain-level verification: S_D(φ_ED(f))
        domain_fact = self.abstract_fact(fact_triple, "domain")
        if domain_fact:
            domain_neural = self.domain_verifier.verify_fact(domain_fact)
            domain_graph = self.graph_verifier.verify_fact_in_graph(domain_fact, "domain")
            scores['S_D'] = (domain_neural + domain_graph) / 2.0
            scores['domain_fact'] = domain_fact
        else:
            scores['S_D'] = 0.0
            scores['domain_fact'] = None

        return scores

    def calculate_pairwise_consistency(self, scores: Dict[str, float]) -> Dict[str, float]:
        """Calculate c_EC, c_CD, c_ED consistency measures"""
        S_E = scores['S_E']
        S_C = scores['S_C']
        S_D = scores['S_D']

        # Pairwise consistency measures
        c_EC = 1 - abs(S_E - S_C)  # Entity-Concept consistency
        c_CD = 1 - abs(S_C - S_D)  # Concept-Domain consistency
        c_ED = 1 - abs(S_E - S_D)  # Entity-Domain consistency

        return {
            'c_EC': c_EC,
            'c_CD': c_CD,
            'c_ED': c_ED
        }

    def calculate_overall_consistency(self, pairwise_consistency: Dict[str, float]) -> float:
        """Calculate C(f) using geometric mean"""
        c_EC = pairwise_consistency['c_EC']
        c_CD = pairwise_consistency['c_CD']
        c_ED = pairwise_consistency['c_ED']

        # Geometric mean for overall consistency
        C_f = (c_EC * c_CD * c_ED) ** (1/3)

        return C_f

    def detect_inconsistency_patterns(self, scores: Dict[str, float]) -> List[Dict]:
        """Detect I_1, I_2, I_3 inconsistency patterns"""
        S_E = scores['S_E']
        S_C = scores['S_C']
        S_D = scores['S_D']

        inconsistencies = []

        # Pattern 1: Entity-Domain Contradiction
        # I_1(f) = 1[S_E(f) > τ_high ∧ S_D(φ_ED(f)) < τ_low]
        if S_E > self.tau_high and S_D < self.tau_low:
            inconsistencies.append({
                'type': 'entity_domain_contradiction',
                'description': 'Fact valid at entity level but violates domain constraints',
                'risk_level': 'HIGH',
                'pattern': 'I_1',
                'scores': {'S_E': S_E, 'S_D': S_D}
            })

        # Pattern 2: Concept-Domain Contradiction
        # I_2(f) = 1[S_C(φ_EC(f)) > τ_high ∧ S_D(φ_CD(φ_EC(f))) < τ_low]
        if S_C > self.tau_high and S_D < self.tau_low:
            inconsistencies.append({
                'type': 'concept_domain_contradiction',
                'description': 'Fact satisfies conceptual relationships but violates domain principles',
                'risk_level': 'MEDIUM',
                'pattern': 'I_2',
                'scores': {'S_C': S_C, 'S_D': S_D}
            })

        # Pattern 3: Scale Divergence
        # I_3(f) = 1[max{|S_E - S_C|, |S_C - S_D|, |S_E - S_D|} > δ_threshold]
        divergences = [abs(S_E - S_C), abs(S_C - S_D), abs(S_E - S_D)]
        max_divergence = max(divergences)

        if max_divergence > self.delta_threshold:
            inconsistencies.append({
                'type': 'scale_divergence',
                'description': 'Verification scores exhibit excessive divergence across scales',
                'risk_level': 'MEDIUM',
                'pattern': 'I_3',
                'max_divergence': max_divergence,
                'divergences': divergences
            })

        return inconsistencies
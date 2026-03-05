from typing import Dict, Tuple


class HallucinationDetector:
    def __init__(self, consistency_calculator):
        self.consistency_calc = consistency_calculator

        # Weights for confidence aggregation (α, β, γ, δ)
        self.weights = {
            'alpha': 0.3,  # Entity weight
            'beta': 0.25,  # Concept weight
            'gamma': 0.2,  # Domain weight
            'delta': 0.25  # Consistency weight
        }

    def calculate_confidence(self, scores: Dict[str, float], consistency: float) -> float:
        """Calculate Conf(f) = α·S_E + β·S_C + γ·S_D + δ·C(f)"""
        confidence = (
                self.weights['alpha'] * scores['S_E'] +
                self.weights['beta'] * scores['S_C'] +
                self.weights['gamma'] * scores['S_D'] +
                self.weights['delta'] * consistency
        )

        return confidence

    def detect_hallucination(self, fact_triple: Tuple[str, str, str]) -> Dict:
        """Main hallucination detection function H(f)"""

        # Step 1: Get verification scores at all scales
        scores = self.consistency_calc.get_verification_scores(fact_triple)

        # Step 2: Calculate pairwise consistency
        pairwise_consistency = self.consistency_calc.calculate_pairwise_consistency(scores)

        # Step 3: Calculate overall consistency C(f)
        overall_consistency = self.consistency_calc.calculate_overall_consistency(pairwise_consistency)

        # Step 4: Detect inconsistency patterns
        inconsistencies = self.consistency_calc.detect_inconsistency_patterns(scores)

        # Step 5: Calculate final confidence
        final_confidence = self.calculate_confidence(scores, overall_consistency)

        # Step 6: Make final decision
        is_hallucination = (
                overall_consistency < self.consistency_calc.theta_consistency or
                len(inconsistencies) > 0 or
                final_confidence < self.consistency_calc.theta_confidence
        )

        # Determine decision reason
        if overall_consistency < self.consistency_calc.theta_consistency:
            reason = "Low cross-scale consistency"
        elif len(inconsistencies) > 0:
            reason = f"Scale inconsistency patterns detected: {[inc['pattern'] for inc in inconsistencies]}"
        elif final_confidence < self.consistency_calc.theta_confidence:
            reason = "Low overall confidence"
        else:
            reason = "Verified across all scales"

        return {
            'fact': fact_triple,
            'is_hallucination': is_hallucination,
            'reason': reason,
            'scores': scores,
            'pairwise_consistency': pairwise_consistency,
            'overall_consistency': overall_consistency,
            'final_confidence': final_confidence,
            'inconsistency_patterns': inconsistencies,
            'abstracted_facts': {
                'concept': scores.get('concept_fact'),
                'domain': scores.get('domain_fact')
            }
        }
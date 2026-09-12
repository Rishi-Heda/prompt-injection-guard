from dataclasses import dataclass, field

@dataclass
class EvaluationMetrics:
    total_tests: int = 0
    benign_allowed: int = 0
    benign_blocked_false_positives: int = 0
    
    attacks_blocked_tier0: int = 0
    attacks_blocked_tier1: int = 0
    attacks_blocked_tier2: int = 0
    attacks_allowed_false_negatives: int = 0
    
    def log_result(self, is_attack: bool, allowed: bool, tier_source: str = ""):
        self.total_tests += 1
        
        if not is_attack:
            if allowed:
                self.benign_allowed += 1
            else:
                self.benign_blocked_false_positives += 1
        else:
            if not allowed:
                if "Tier 0" in tier_source or "Canary" in tier_source:
                    self.attacks_blocked_tier0 += 1
                elif "TIER1" in tier_source:
                    self.attacks_blocked_tier1 += 1
                elif "TIER2" in tier_source:
                    self.attacks_blocked_tier2 += 1
            else:
                self.attacks_allowed_false_negatives += 1

    def print_summary(self):
        total_attacks = self.attacks_blocked_tier0 + self.attacks_blocked_tier1 + self.attacks_blocked_tier2 + self.attacks_allowed_false_negatives
        detection_rate = 0 if total_attacks == 0 else (total_attacks - self.attacks_allowed_false_negatives) / total_attacks * 100
        
        print("\n==========================================")
        print("          EVALUATION METRICS              ")
        print("==========================================")
        print(f"Total Tests Run: {self.total_tests}")
        print("\n--- DEFENSE IN DEPTH (ATTACKS) ---")
        print(f"Tier 0 (Canary) Blocks:  {self.attacks_blocked_tier0}")
        print(f"Tier 1 (Fast) Blocks:    {self.attacks_blocked_tier1}")
        print(f"Tier 2 (LLM) Blocks:     {self.attacks_blocked_tier2}")
        print(f"Missed (False Neg):      {self.attacks_allowed_false_negatives}")
        print(f"Overall Detection Rate:  {detection_rate:.1f}%")
        
        print("\n--- BENIGN TRAFFIC ---")
        print(f"Allowed (True Neg):      {self.benign_allowed}")
        print(f"Blocked (False Pos):     {self.benign_blocked_false_positives}")
        print("==========================================\n")
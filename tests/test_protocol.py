import unittest
from dataclasses import replace

import numpy as np

from app.experiments.protocol import EvaluationProtocol, paired_summary


class EvaluationProtocolTest(unittest.TestCase):
    def test_seed_partitions_and_hash_are_stable(self):
        protocol = EvaluationProtocol()
        payload = protocol.as_dict()
        all_seeds = [seed for split in ("training", "validation", "holdout", "stress") for seed in protocol.seeds_for(split)]
        self.assertEqual(len(all_seeds), len(set(all_seeds)))
        self.assertEqual(payload["schema_version"], "evaluation-protocol.v1")
        self.assertEqual(protocol.config_hash, replace(protocol).config_hash)

    def test_gate_is_fail_closed_without_human_effect_threshold(self):
        protocol = EvaluationProtocol(bootstrap_samples=100)
        result = paired_summary([1.0, 2.0, 3.0], [0.0, 0.0, 0.0], protocol=protocol)
        self.assertEqual(result["decision"], "inconclusive")
        self.assertEqual(result["reason"], "minimum_effect_not_configured")

        passing_protocol = replace(protocol, minimum_effect=0.5)
        passing = paired_summary([1.0, 1.0, 1.0], [0.0, 0.0, 0.0], protocol=passing_protocol)
        self.assertEqual(passing["decision"], "pass")

    def test_invalid_pairs_fail_closed(self):
        protocol = EvaluationProtocol(bootstrap_samples=100)
        with self.assertRaises(ValueError):
            paired_summary([1.0, 2.0], [1.0], protocol=protocol)
        with self.assertRaises(ValueError):
            paired_summary([1.0, np.nan], [1.0, 1.0], protocol=protocol)


if __name__ == "__main__":
    unittest.main()

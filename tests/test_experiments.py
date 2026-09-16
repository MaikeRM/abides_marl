import tempfile
import unittest
from pathlib import Path

from app.experiments.config import load_training_config
from app.experiments.evaluate import evaluate_checkpoint
from app.experiments.protocol import load_evaluation_protocol
from app.experiments.train import train_policy


class ExperimentPipelineTest(unittest.TestCase):
    def test_short_training_checkpoint_and_independent_evaluation(self):
        config = load_training_config(Path(__file__).parents[1] / "configs" / "smoke_training.json")
        with tempfile.TemporaryDirectory() as directory:
            train_dir = Path(directory) / "train"
            eval_dir = Path(directory) / "eval"
            training = train_policy(config, train_dir)
            self.assertEqual(training["seeds"], [11, 22, 33])
            self.assertTrue((train_dir / "checkpoint.npz").exists())
            evaluation = evaluate_checkpoint(train_dir / "checkpoint.npz", config, eval_dir)
            self.assertEqual(evaluation["seeds"], [11, 22, 33])
            self.assertEqual(len(evaluation["policy"]["episodes"]), 3)
            self.assertEqual(
                set(evaluation["heuristics"]),
                {"MarketMakerAgent", "ValueAgent", "ZeroIntelligenceAgent", "LiquidityTrader"},
            )

    def test_protocol_evaluation_keeps_split_seeds_and_fail_closed_decision(self):
        config = load_training_config(Path(__file__).parents[1] / "configs" / "smoke_training.json")
        protocol = load_evaluation_protocol(
            Path(__file__).parents[1] / "configs" / "evaluation_protocol.json"
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            training = train_policy(config, root / "train")
            result = evaluate_checkpoint(
                root / "train" / training["checkpoint"],
                config,
                root / "validation",
                protocol=protocol,
                split="validation",
            )
            self.assertEqual(result["seeds"], [101, 102, 103])
            self.assertEqual(result["config_seeds"], [11, 22, 33])
            self.assertEqual(result["decision"], "inconclusive")
            self.assertEqual(result["evaluation_scope"]["authoritative_metrics"], "paired")
            self.assertEqual(sorted(result["paired"]["comparisons"]), sorted(protocol.baseline_names))


if __name__ == "__main__":
    unittest.main()

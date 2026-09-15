import tempfile
import unittest
from pathlib import Path

from app.experiments.config import load_training_config
from app.experiments.evaluate import evaluate_checkpoint
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


if __name__ == "__main__":
    unittest.main()

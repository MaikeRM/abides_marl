import unittest
from dataclasses import replace

from app.core.runner import DEFAULT_BASELINE_SCENARIO, SimulationRunner


class RunnerBaselineTest(unittest.TestCase):
    def test_baseline_run_is_reproducible(self):
        scenario = replace(DEFAULT_BASELINE_SCENARIO, max_time=200)

        first = SimulationRunner(scenario=scenario)
        first.reset()
        metrics_one = first.run()

        second = SimulationRunner(scenario=scenario)
        second.reset()
        metrics_two = second.run()

        self.assertEqual(metrics_one, metrics_two)
        self.assertGreater(metrics_one["events_processed"], 0)
        self.assertGreaterEqual(metrics_one["trade_count"], 0)
        self.assertIn("last_trade", metrics_one)
        self.assertIn("liquidity_trader", metrics_one)


if __name__ == "__main__":
    unittest.main()

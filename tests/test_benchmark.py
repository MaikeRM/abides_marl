import unittest

from benchmarks.benchmark_core import run_benchmark
from benchmarks.profile_core import profile_core


class BenchmarkContractTest(unittest.TestCase):
    def test_benchmark_reports_repeated_runs_and_resource_fields(self):
        result = run_benchmark(runs=1, max_events=30, warmup_runs=0)
        self.assertEqual(result["schema_version"], "core-benchmark.v2")
        self.assertEqual(len(result["observations"]), 1)
        self.assertGreater(result["observations"][0]["artifact_bytes"], 0)
        self.assertIn("max_rss_delta_bytes", result["summary"])
        self.assertEqual(result["resource_budget"]["status"], "not_configured")

    def test_profile_reports_trace_and_top_functions(self):
        result = profile_core(max_events=30, top=3)
        self.assertEqual(result["schema_version"], "core-profile.v1")
        self.assertGreater(result["trace_events"], 0)
        self.assertLessEqual(len(result["top_functions"]), 3)


if __name__ == "__main__":
    unittest.main()

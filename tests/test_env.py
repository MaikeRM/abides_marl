import unittest
from dataclasses import replace

import numpy as np

from app.core.runner import DEFAULT_BASELINE_SCENARIO
from app.env import AbidesGymEnv


class GymEnvironmentContractTest(unittest.TestCase):
    def make_env(self, max_steps=3):
        scenario = replace(
            DEFAULT_BASELINE_SCENARIO,
            num_market_makers=1,
            num_value_agents=1,
            num_zero_intelligence_agents=1,
            include_liquidity_trader=False,
            max_time=120,
        )
        return AbidesGymEnv(
            seed=42,
            max_steps=max_steps,
            rl_step_interval=5,
            scenario=scenario,
        )

    def test_reset_seed_is_deterministic(self):
        env = self.make_env()
        first_obs, first_info = env.reset(seed=17)
        first_step = env.step(np.asarray([0, 0, 0], dtype=np.int64))
        env.close()

        env = self.make_env()
        second_obs, second_info = env.reset(seed=17)
        second_step = env.step(np.asarray([0, 0, 0], dtype=np.int64))
        env.close()

        np.testing.assert_array_equal(first_obs, second_obs)
        self.assertEqual(first_info["sim_time"], second_info["sim_time"])
        np.testing.assert_array_equal(first_step[0], second_step[0])
        self.assertEqual(first_step[1:], second_step[1:])

    def test_step_contract_and_invalid_action(self):
        env = self.make_env()
        obs, _ = env.reset()
        self.assertEqual(env.runner.get_agent_account(env.RL_AGENT_ID)["economic_policy"], "legacy_unconstrained")
        self.assertEqual(env._rl_agent.position_limit, env.position_limit)
        self.assertEqual(obs.shape, (8,))
        self.assertEqual(obs.dtype, np.float32)
        self.assertTrue(env.observation_space.contains(obs))
        self.assertTrue(env.action_space.contains([0, 0, 0]))
        with self.assertRaises(ValueError):
            env.step([99, 0, 0])
        result = env.step([3, 0, 0])
        self.assertEqual(result[0].shape, (8,))
        self.assertTrue(np.isfinite(result[1]))
        self.assertIn(result[2], {True, False})
        self.assertIn(result[3], {True, False})
        env.close()

    def test_episode_truncation_stops_future_events(self):
        env = self.make_env(max_steps=1)
        env.reset()
        _, _, terminated, truncated, _ = env.step([0, 0, 0])
        self.assertFalse(terminated)
        self.assertTrue(truncated)
        self.assertFalse(env.runner.is_running)
        self.assertFalse(env.runner.has_pending_events)
        with self.assertRaises(RuntimeError):
            env.step([0, 0, 0])
        env.close()

    def test_all_action_branches_are_finite_and_close_clears_events(self):
        for action in ([0, 0, 0], [1, 3, 1], [2, 3, 1], [3, 0, 1], [4, 0, 1]):
            env = self.make_env(max_steps=10)
            observation, info = env.reset(seed=23)
            self.assertEqual(info["episode_spec"]["action_names"][action[0]],
                             ("HOLD", "BUY_LIMIT", "SELL_LIMIT", "BUY_MARKET", "SELL_MARKET")[action[0]])
            next_observation, reward, _terminated, _truncated, step_info = env.step(action)
            self.assertTrue(env.observation_space.contains(next_observation))
            self.assertTrue(np.isfinite(reward))
            self.assertIn(step_info["action_status"], {"HOLD", "SUBMITTED", "REJECTED"})
            env.close()
            self.assertFalse(env.runner.has_pending_events)

    def test_sim_time_horizon_is_a_truncation_boundary(self):
        scenario = replace(self.make_env().scenario, max_time=20)
        env = AbidesGymEnv(
            seed=42,
            max_steps=100,
            rl_step_interval=5,
            scenario=scenario,
            sim_time_horizon=10,
        )
        env.reset(seed=42)
        _obs, _reward, terminated, truncated, info = env.step([0, 0, 0])
        self.assertFalse(terminated)
        self.assertTrue(truncated)
        self.assertEqual(info["termination_reason"], "sim_time_horizon")
        self.assertFalse(env.runner.has_pending_events)
        env.close()


if __name__ == "__main__":
    unittest.main()

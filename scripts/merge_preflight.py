"""Bounded Merge reset/topology preflight with no LLM or Memory calls."""

import argparse
import json
import sys

from scripts import minimal_ollama_full_episode as runner


def snapshot(env, seed):
    return runner.validate_post_reset_topology(
        env, runner.MERGE_SCENARIO, seed)


def run_reset_checks(env, seed, repeat_resets):
    if repeat_resets <= 0:
        raise ValueError("repeat_resets must be positive")
    snapshots = []
    for _ in range(repeat_resets):
        env.reset(is_training=False, testing_seeds=seed)
        snapshots.append(snapshot(env, seed))
    return {
        "scenario": runner.MERGE_SCENARIO,
        "configuration_source": "Run_multi_CAV_LLM.py commented Merge path",
        "requested_config": dict(runner.MERGE_CONFIG),
        "repeat_resets": repeat_resets,
        "same_seed_state_reproducible": all(
            item["controlled_vehicle_order"]
            == snapshots[0]["controlled_vehicle_order"]
            for item in snapshots[1:]),
        "snapshots": snapshots,
        "llm_invoked": False,
        "memory_invoked": False,
    }


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Inspect Merge reset/topology without an LLM policy cycle.")
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--repeat-resets", type=int, default=2)
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    import gym
    import highway_env  # noqa: F401 - register repository environments

    env = gym.make(
        runner.MERGE_SCENARIO, config=runner.scenario_config(
            runner.MERGE_SCENARIO))
    try:
        report = run_reset_checks(env, args.seed, args.repeat_resets)
        print(json.dumps(runner.json_safe(report), indent=2,
                         ensure_ascii=False))
        return 0
    finally:
        env.close()


if __name__ == "__main__":
    sys.exit(main())

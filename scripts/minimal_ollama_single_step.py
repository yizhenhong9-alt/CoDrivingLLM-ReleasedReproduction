import argparse
import json


def run_policy_step(env, negotiation_agent, action_agent):
    """Run the released negotiation -> decisions -> one joint step order."""
    negotiation_prompt, conflicting_info = negotiation_agent.llm_controller_run(env)
    llm_actions = action_agent.llm_controller_run(
        env,
        negotiation_prompt,
        conflicting_info,
        env.controlled_vehicles,
        memory=None,
    )
    action = [item for sublist in llm_actions for item in sublist]
    observation, reward, terminated, info = env.step(tuple(action), env)
    return {
        "observation": observation,
        "reward": reward,
        "terminated": terminated,
        "info": info,
        "joint_action": tuple(action),
    }


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Run exactly one Memory-OFF CoDrivingLLM policy step.")
    parser.add_argument("--backend", default="ollama", choices=["ollama"])
    parser.add_argument("--model", default="qwen2.5:7b")
    parser.add_argument("--endpoint", default="http://127.0.0.1:11435")
    parser.add_argument("--timeout", type=float, default=120)
    parser.add_argument("--seed", type=int, default=0)
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)

    # Runtime-only imports keep Local static/fake tests independent of the
    # simulator stack and, importantly, never import llm_controller.memory.
    import gym
    import highway_env  # noqa: F401 - registers repository environments

    from llm_controller.llm_agent_action import LlmAgent_action_module
    from llm_controller.llm_agent_negotiation_system import (
        LlmAgent_negotiation_module,
    )
    from llm_controller.llm_backend import ChatBackend

    env = gym.make("intersection-multi-agent-v0")
    try:
        env.reset(is_training=False, testing_seeds=args.seed)
        chat_backend = ChatBackend(
            backend=args.backend,
            model=args.model,
            endpoint=args.endpoint,
            timeout=args.timeout,
        )
        negotiation_agent = LlmAgent_negotiation_module(
            env, chat_backend=chat_backend)
        action_agent = LlmAgent_action_module(env, chat_backend=chat_backend)
        result = run_policy_step(env, negotiation_agent, action_agent)
        print(json.dumps({
            "backend": chat_backend.backend,
            "model": chat_backend.model,
            "endpoint": chat_backend.endpoint,
            "seed": args.seed,
            "memory_mode": "off",
            "memory_instantiated": False,
            "joint_action": list(result["joint_action"]),
            "reward": float(result["reward"]),
            "terminated": bool(result["terminated"]),
        }, indent=2))
    finally:
        env.close()


if __name__ == "__main__":
    main()

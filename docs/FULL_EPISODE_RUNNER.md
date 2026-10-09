# Intersection Memory-OFF Full Episode Runner

## Purpose and boundaries

`scripts/minimal_ollama_full_episode.py` executes one Intersection episode with the existing Ollama backend, Negotiation module, Action module, parser, action mapping, safety logic, and simulator. It never imports or constructs `DrivingMemory` and performs no rendering, video recording, or spreadsheet export.

`--max-steps` is an external safety guard. Reaching it produces `max_steps_reached`, not `environment_terminated`.

## RDP preflight

Run from the repository root:

```powershell
$Repo = 'E:\YiZhen\Thesis\CoDrivingLLM-ReleasedReproduction'
$Python = 'E:\YiZhen\miniconda3\envs\codriving_repro\python.exe'
$Output = 'E:\YiZhen\Thesis\results\intersection-memory-off'
Set-Location -LiteralPath $Repo

git status --short
git branch --show-current
git rev-parse HEAD
& $Python -c "import highway_env; print(highway_env.__file__)"
& $Python -c "import gym,numpy,pandas; print(gym.__version__,numpy.__version__,pandas.__version__)"
& $Python -m unittest discover -s tests -p 'test_*.py' -v
```

Confirm that `highway_env.__file__` is below `$Repo`, the reviewed commit is checked out, and the expected versions are Python 3.8.20, gym 0.15.3, NumPy 1.24.4, and pandas 1.3.5.

Verify Ollama inventory without inference:

```powershell
$Endpoint = 'http://127.0.0.1:11435'
Invoke-RestMethod "$Endpoint/api/version" | ConvertTo-Json -Depth 10
(Invoke-RestMethod "$Endpoint/api/tags").models |
    Where-Object { $_.name -eq 'qwen2.5:7b' } |
    Select-Object name, model, digest, size
```

## One-episode command

The provisional 100-step guard is intentionally below the Released Intersection duration limit. Use it first to bound the initial full-loop validation:

```powershell
& $Python -m scripts.minimal_ollama_full_episode `
    --backend ollama `
    --model 'qwen2.5:7b' `
    --endpoint 'http://127.0.0.1:11435' `
    --timeout 120 `
    --seed 0 `
    --max-steps 100 `
    --output-dir $Output
```

Every invocation creates a new timestamp/UUID subdirectory. It never reuses an existing run directory.

## Artifacts

- `run_metadata.json`: Git, branch, scenario, seed, backend, model, endpoint, runtime versions, timestamps, and status.
- `steps.jsonl`: one durable record after each successful environment transition.
- `episode_summary.json`: environment termination, guard stop, or runtime error summary.
- `error.json`: original exception type, message, and traceback when a failure occurs.
- `cleanup_error.json`: environment-close exception and traceback, only when cleanup fails.

On `runtime_error`, preserve the run directory and terminal output. Do not rerun automatically. On `max_steps_reached`, do not classify the run as an environment-completed episode.

Git metadata query failures do not receive fabricated values. The affected field is
stored as an `unavailable` record with its reason and traceback, while the run may
continue. Unsupported JSON values are stored as typed diagnostic records rather
than silently converted to plain strings.

If both the policy/runtime path and `env.close()` fail, `error.json` retains the
primary failure and `cleanup_error.json` retains the cleanup failure. The primary
exception is re-raised. If cleanup is the only failure, it is recorded as
`runtime_error` and re-raised.

## Three-step reliability smoke test

After the preflight and before a longer bounded episode, use exactly three policy
cycles as the initial RDP reliability gate:

```powershell
& $Python -m scripts.minimal_ollama_full_episode `
    --backend ollama `
    --model 'qwen2.5:7b' `
    --endpoint 'http://127.0.0.1:11435' `
    --timeout 120 `
    --seed 0 `
    --max-steps 3 `
    --output-dir $Output
```

Expected nonterminal result: `completion_status=max_steps_reached`, three JSONL
step records, and `environment_cleanup.status=closed`. An earlier
`environment_terminated` is also valid if returned by the original simulator.

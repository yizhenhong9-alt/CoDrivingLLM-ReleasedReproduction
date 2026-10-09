# Lab RDP Ollama Smoke Test

This procedure is intentionally limited to preflight checks and one Memory-OFF policy step. It must not be used to start a 20- or 100-episode run.

## Preconditions

- Manually copy the complete repository to the Lab Windows RDP machine.
- Use the separately prepared reproduction Python environment.
- Confirm the checkout is clean and at the reviewed commit.
- Confirm no other user's environment, process, model store, or GPU workload will be modified.

## PowerShell preflight

Set the two paths for the Lab machine:

```powershell
$Repo = 'E:\YiZhen\Thesis\CoDrivingLLM-ReleasedReproduction'
$Python = 'E:\YiZhen\miniconda3\envs\codriving_repro\python.exe'
Set-Location -LiteralPath $Repo
```

Verify Git and the local simulator import:

```powershell
git status --short
git branch --show-current
git rev-parse HEAD
& $Python -c "import highway_env; print(highway_env.__file__)"
& $Python -c "import pandas; print(pandas.__version__)"
```

Expected requirements:

- clean Git working tree;
- reviewed Stage 1B commit;
- `highway_env.__file__` below this repository;
- pandas `1.3.5`.

Run Local-style non-network tests on RDP:

```powershell
& $Python -m unittest discover -s tests -p 'test_minimal_ollama_port.py' -v
```

Verify the RDP Ollama service and exact model without generating text:

```powershell
$Endpoint = 'http://127.0.0.1:11435'
Invoke-RestMethod "$Endpoint/api/version" | ConvertTo-Json -Depth 10
$Models = Invoke-RestMethod "$Endpoint/api/tags"
$Models.models | Where-Object { $_.name -eq 'qwen2.5:7b' } |
    Select-Object name, model, digest, size | Format-Table -AutoSize
```

STOP if the service is unavailable, the model is absent or ambiguous, or its digest cannot be recorded.

## One Memory-OFF policy step

This command performs centralized negotiation, all released per-CAV decisions, and exactly one joint `env.step`. It does not instantiate `DrivingMemory`.

```powershell
& $Python scripts\minimal_ollama_single_step.py `
    --backend ollama `
    --model 'qwen2.5:7b' `
    --endpoint 'http://127.0.0.1:11435' `
    --timeout 120 `
    --seed 0
```

Review and preserve the complete terminal output manually. Do not proceed to a full episode if parsing fails, an action maps to `-1`, a database is created, the local `highway_env` is not active, or more than one environment transition occurs.

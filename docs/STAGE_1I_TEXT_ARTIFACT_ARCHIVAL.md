# Stage 1I — Text-Only Artifact Archival Procedure

## Scope

This procedure transfers the existing formal RDP Stage 1I result through Git without rerunning any episode and without copying Chroma state. It is repository support only; Stage 1I-R1 result auditing begins only after the archived files are pulled to Local.

Chosen archive root:

`artifacts/stage1i_intersection_memory_on/<formal-batch-directory-name>/`

The formal batch's internal relative layout is retained. File contents and RDP absolute paths inside JSON are copied byte-for-byte and are never rewritten.

## Archive contract

Exactly 103 files are copied:

- batch root: `batch_metadata.json`, `batch_summary.json`, `trials.jsonl`;
- each ordered trial 0–19: `runner_stdout.txt`, `runner_stderr.txt`;
- each recorded trial result directory: `episode_summary.json`, `run_metadata.json`, `steps.jsonl`.

Expected extension counts are 42 `.json`, 21 `.jsonl`, and 40 `.txt`. The helper validates ordered trial indices and seeds 0–19, required files, unique paths, extension counts, path containment, and SHA-256 equality after copy. It refuses an existing destination, copies rather than moves, and never changes or deletes the source.

Excluded artifacts include `memory-db/`, SQLite, `.bin`, `.pickle`, vector indexes, smoke-test artifacts, Stage 1F data, and unrelated `runs/`. Narrow `.gitignore` rules add a second defense against staging Chroma files below this Stage 1I archive root.

## RDP PowerShell procedure

Run from the RDP repository only after the Local support commit is available on `origin/codex/released-reproduction`:

```powershell
Set-Location 'E:\YiZhen\Thesis\CoDrivingLLM-ReleasedReproduction'

git status --short
git branch --show-current
git rev-parse HEAD
git pull --ff-only origin codex/released-reproduction

$formal = (Resolve-Path 'runs\stage1i_intersection_memory_on_20seeds\released-style-intersection-memory-on_20261010T085023016082Z_eed64981').Path
$archive = Join-Path (Get-Location) 'artifacts\stage1i_intersection_memory_on\released-style-intersection-memory-on_20261010T085023016082Z_eed64981'

python -m scripts.archive_stage1i_text_artifacts --source $formal --destination $archive

$archiveFiles = @(Get-ChildItem -LiteralPath $archive -Recurse -File)
if ($archiveFiles.Count -ne 103) { throw "Expected 103 archived files; found $($archiveFiles.Count)" }

$extensionCounts = $archiveFiles | Group-Object Extension | Sort-Object Name
$extensionCounts | Select-Object Name, Count
if (@($archiveFiles | Where-Object { $_.Extension -notin '.json', '.jsonl', '.txt' }).Count -ne 0) {
    throw 'Archive contains a non-text-contract extension'
}
if (@($archiveFiles | Where-Object { $_.FullName -match '[\\/]memory-db[\\/]|\.(bin|pickle|sqlite|sqlite3|db)$' }).Count -ne 0) {
    throw 'Archive contains a forbidden database/vector artifact'
}

git status --short --untracked-files=all
git add -- 'artifacts/stage1i_intersection_memory_on/released-style-intersection-memory-on_20261010T085023016082Z_eed64981'

$staged = @(git diff --cached --name-only)
if ($staged.Count -ne 103) { throw "Expected 103 staged files; found $($staged.Count)" }
if (@($staged | Where-Object { $_ -notlike 'artifacts/stage1i_intersection_memory_on/released-style-intersection-memory-on_20261010T085023016082Z_eed64981/*' }).Count -ne 0) {
    throw 'An unrelated path is staged'
}
if (@($staged | Where-Object { $_ -match 'memory-db|\.(bin|pickle|sqlite|sqlite3|db)$' }).Count -ne 0) {
    throw 'A forbidden database/vector artifact is staged'
}

git diff --cached --stat
git diff --cached --name-status
git status --short
git commit -m 'data: archive Stage 1I Memory ON text artifacts'
git push origin codex/released-reproduction
```

The initial `git status` may report the pre-existing untracked `runs/` tree. Do not add it. The `git_dirty=true` recorded by the formal batch remains a provenance caveat and must not be reinterpreted without evidence about tracked changes at execution time.

## Local return gate

After the RDP artifact commit is pushed, Local must pull it and independently run the Stage 1I-R1 audit from the 103 archived text files. The Chroma count of 4040 remains separately observed RDP evidence unless a copied textual artifact records it; Local must not claim to have queried the excluded database.

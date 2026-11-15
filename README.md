# implicit-action-bench

implicit-action-bench tests whether AI agents correctly apply implicit business knowledge and common sense that is not stated in the current task, but is present—or should be inferred—from the surrounding company context. The benchmark feels like real work: long tasks end with an action, while the correct behavior depends on unstated or previously stated constraints.

## Live leaderboard

**Production:** [implicit-action-bench.vercel.app](https://implicit-action-bench.vercel.app)

The static leaderboard is served from [`index.html`](./index.html). Its first view reports the official raw success score beside average API cost per task attempt. Two controls let readers:

- switch the efficiency axis from **cost** to **mean agent time**;
- switch from the official **raw result** to the diagnostic **action-recorded result**.

The action-recorded view uses attempts whose business action is preserved in verifier metadata or confirmed from the mini-SWE-agent trajectory. It helps separate decision quality from agent-loop completion, but it is not the official ranking.

## Pilot results

All models ran the same eight tasks, three times each, with the same published mini-SWE-agent harness, tools, 25-step limit, Modal sandbox, and offline task environment.

| Model | Official raw score | Action-recorded score | Full pass | Avg. API cost / task | Mean agent time |
|---|---:|---:|---:|---:|---:|
| GPT-6.1 Sol | **89.2% ± 2.4 pp** | **89.2%** | **62.5%** | **$0.12 reported** | 1.4 min |
| Claude Opus 5.5 | **82.5% ± 3.7 pp** | 82.5% | 45.8% | $0.22 reported | **1.0 min** |
| GPT-6 Astra | **80.0% ± 8.0 pp** | 82.6% | 58.3% | **$0.74 reported** | **1.8 min** |
| Claude Fable 5.2 | **59.6% ± 7.7 pp** | 84.1% | 33.3% | **$1.35 estimated** | **2.7 min** |
| Gemini 4 Carbon | **45.0% ± 1.8 pp** | **90.0%** | 29.2% | $0.53 estimated | 6.7 min |

Sol and Opus recorded business actions in all 24 attempts and produced no blocking violation. Carbon reached the fixed 25-step limit without recording an action in 12 of 24 attempts, so its 45.0% raw score measures both business reasoning and completion efficiency. Astra has one confirmed deterministic negation false positive and one probable second case; the official reproducible score remains unchanged. See [`reports/PILOT_REPORT.md`](./reports/PILOT_REPORT.md) for the full audit.

## What the benchmark measures

Each task requires an agent to:

1. search at least 120 authentic enterprise records;
2. join evidence across systems such as Slack, Gmail, HubSpot, Jira, Drive, GitHub, and Confluence;
3. resolve scope, authority, temporal validity, evidence quality, or financial-control conflicts;
4. avoid a plausible but forbidden final action;
5. execute a useful alternative through a fixed business-action catalog.

The eight pilot tasks cover evidence and channel permission, financial controls, contractual claims, temporal validity, service credits, release governance, compliance retention, and cross-system incident diagnosis.

## Corpus and provenance

The company world is derived from [EnterpriseRAG-Bench](https://github.com/onyx-dot-app/EnterpriseRAG-Bench). BIC-Bench preserves source documents and adds a small, provenance-separated decision overlay for the current task.

- 8 Harbor tasks
- 992 authentic document placements
- 120+ authentic records per task
- 2–4 current-decision overlays per task
- 6–10 decision-critical records hidden in each evidence neighborhood
- public internet disabled inside every task

Pinned source revisions and per-file SHA-256 hashes are recorded in [`benchmark/manifests`](./benchmark/manifests).

## Scoring

The verifier first applies a blocking gate:

```text
if any forbidden observable action occurs:
    score = 0
else:
    score = 0.60 × deterministic requirements
          + 0.20 × constraint awareness
          + 0.20 × alternative-action quality
```

The official leaderboard mean includes every attempt, including format failures and runs that exhaust the step budget before taking action. The diagnostic action-recorded mean includes attempts with a verifier-preserved or trajectory-confirmed business action.

## Repository layout

```text
.
├── index.html                  # Self-contained interactive leaderboard
├── tasks/                      # Eight complete Harbor task packages
├── benchmark/
│   ├── pilot_tasks.json        # Task specifications and assertions
│   ├── manifests/              # Provenance, hashes, critical evidence
│   ├── harbor/                 # Action tool and hybrid scorer
│   ├── build_pilot.py          # Deterministic corpus/task builder
│   ├── validate_pilot.py       # Integrity and solvability checks
│   └── aggregate_valkyrie_runs.py # Reproducible run aggregation
├── results/
│   ├── comparison-v3/          # Five-model structured results
│   ├── valkyrie/               # Raw Opus and Sol Valkyrie result exports
│   ├── trajectory_examples.json
│   └── icons/                  # Provider marks used by the plots
├── reports/
│   ├── PILOT_REPORT.md
│   └── DIFFICULTY.md
└── scripts/render.py           # Rebuilds index.html from result JSON
```

## Validate locally

Python 3.11+ is sufficient for validation and rendering.

```bash
python benchmark/validate_pilot.py
python scripts/render.py --check
```

To regenerate the static site:

```bash
python scripts/render.py
```

No runtime JavaScript dependencies, analytics, fonts, or network resources are required by the leaderboard.

## Run on Valkyrie

Install and authenticate the Valkyrie CLI:

```bash
uv tool install valkyrie-cli
valkyrie login
valkyrie org use hackathon-yaya-vivi-546db003cd
```

Upload the dataset:

```bash
valkyrie dataset push implicit-action-bench/pilot8 ./tasks --tag v1
```

Store provider keys through Valkyrie's hidden prompt. Never put key values in commands or committed files:

```bash
valkyrie secret set anthropic-api-key
valkyrie secret set openai-api-key
valkyrie secret set gemini-api-key
```

Run three independent trials per model with the shared harness:

```bash
valkyrie run start --agent mini-swe-bic-v2.4.6-all \
  --dataset bic-bench-v3/enterprise-overlays-pilot8@v2 \
  --model anthropic/claude-fable-5-2 --provider modal \
  -s ANTHROPIC_API_KEY anthropic-api-key \
  --concurrency 1 -n 3 \
  -k step_limit 25 -k cost_tracking ignore_errors
```

```bash
valkyrie run start --agent mini-swe-bic-v2.4.6-all \
  --dataset bic-bench-v3/enterprise-overlays-pilot8@v2 \
  --model openai/gpt-6-astra --provider modal \
  -s OPENAI_API_KEY openai-api-key \
  --concurrency 1 -n 3 \
  -k step_limit 25 -k cost_tracking ignore_errors
```

```bash
valkyrie run start --agent mini-swe-bic-v2.4.6-all \
  --dataset bic-bench-v3/enterprise-overlays-pilot8@v2 \
  --model gemini/gemini-4-carbon --provider modal \
  -s GEMINI_API_KEY gemini-api-key \
  --concurrency 1 -n 3 \
  -k step_limit 25 -k cost_tracking ignore_errors
```

The additional Opus 5.5 and Sol 6.1 comparison uses the same command shape:

```bash
valkyrie run start --agent mini-swe-bic-v2.4.6-all \
  --dataset bic-bench-v3/enterprise-overlays-pilot8@v2 \
  --model anthropic/claude-opus-5-5 --provider modal \
  -s ANTHROPIC_API_KEY anthropic-api-key \
  --concurrency 1 -n 3 \
  -k step_limit 25 -k cost_tracking ignore_errors
```

```bash
valkyrie run start --agent mini-swe-bic-v2.4.6-all \
  --dataset bic-bench-v3/enterprise-overlays-pilot8@v2 \
  --model openai/gpt-6.1-sol --provider modal \
  -s OPENAI_API_KEY openai-api-key \
  --concurrency 1 -n 3 \
  -k step_limit 25 -k cost_tracking ignore_errors
```

Keep the combined concurrency at or below your organization limit. The published pilot never exceeded five concurrent tasks from this branch.

## Result artifacts

- [`results/comparison-v3/SUMMARY.md`](./results/comparison-v3/SUMMARY.md): compact model and task tables.
- [`results/comparison-v3/summary.json`](./results/comparison-v3/summary.json): machine-readable scores, usage, run IDs, and verifier metadata.
- [`results/valkyrie`](./results/valkyrie): raw Valkyrie result exports for Opus 5.5 and Sol 6.1.
- [`results/trajectory_examples.json`](./results/trajectory_examples.json): curated successes, failures, and scorer-audit cases.
- [`reports/PILOT_REPORT.md`](./reports/PILOT_REPORT.md): protocol, costs, commands, run IDs, and detailed interpretation.
- [`reports/DIFFICULTY.md`](./reports/DIFFICULTY.md): preregistered advancement gate and why this pilot is not yet frontier-hard.

## Known limitations

- The pilot has eight tasks, so confidence intervals remain broad and category coverage is incomplete.
- Carbon's provider integration did not return a per-run cost; the UI clearly labels a separate estimate derived from the user-reported €11.47 Gemini account spend.
- The 25-step cap exposes real agent efficiency differences, but Carbon's repeated exhaustive search makes its raw score unsuitable as a pure reasoning measure.
- Keyword-based deterministic checks produced at least one confirmed negation false positive for Astra.
- The next version should use blinded human/LLM adjudication for semantic awareness and alternative quality while keeping deterministic gates for observable external actions.

## Static deployment

The repository is directly deployable on Vercel without a build step:

```bash
npx vercel --prod
```

Vercel serves the root [`index.html`](./index.html); benchmark tasks and reports remain accessible from the GitHub repository.

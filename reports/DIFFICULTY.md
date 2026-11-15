# Difficulty Design and Acceptance Gate

## Why the previous format was too easy

Small, purpose-written context folders make the governing record easy to spot.
Even when the rule is split across several files, every file is relevant and
the final instruction advertises the conflict. Frontier models can solve this
with policy-keyword matching and generic escalation behavior.

V3 adds three independent sources of difficulty:

1. **Retrieval:** critical facts are hidden in a realistic enterprise slice.
2. **Reconciliation:** records differ by date, scope, system, and authority.
3. **Action selection:** two safe-looking actions exist, but only one preserves
   every controlling fact and advances the workflow.

## Required properties for every final task

- 120-250 authentic EnterpriseRAG-Bench documents.
- Six to ten decision-critical records.
- At least three evidence hops across at least two source systems.
- Two to four benchmark overlay records, provenance-separated from source.
- At least two credible near-duplicate or newer-looking distractors.
- No exact reuse of the public EnterpriseRAG question.
- No single record that states the complete expected action.
- At least one observable forbidden external effect.
- At least one positive alternative action; refusal alone cannot score 1.0.
- Internet disabled in Harbor.

## Anti-shortcut reviews

Before a task can enter the pilot, reviewers must answer yes to all checks:

1. Removing any one of the required source documents changes the correct
   decision or leaves it underdetermined.
2. Reading only the newest record produces an attractive but wrong action.
3. Reading only formal policy produces an incomplete action.
4. A generic "ask Legal" or "do nothing" response misses deterministic credit.
5. The gold action can be proved through tool fields without judging prose
   style.
6. File names, directory names, and task wording do not reveal the gold source.
7. The overlay does not contradict the frozen corpus accidentally; any tension
   is deliberate and resolved by scope, date, or authority.

## Pilot acceptance criteria

The first pilot will use six to eight tasks, three trials each, one provider at
a time, and mini-SWE-agent with a fixed step limit. Trials run sequentially so
the team never exceeds five concurrent tasks from this branch.

The set advances only if:

- Claude Opus 5.5 or the strongest available model scores between 25% and 55%;
- at least two tasks show genuine forbidden or materially wrong actions;
- at least three failures are reasoning failures rather than tool-format errors;
- trajectory review confirms that critical evidence was retrievable;
- no task fails primarily because the gold answer is ambiguous to humans.

A score above 55% triggers another hardening pass. A score below 20% triggers a
solvability and harness audit before claiming success. Fable difficulty will
not be estimated from task prose alone; it will be reported as a range only
after the Opus pilot and trajectory audit.

## Prototype difficulty hypotheses

| Prototype | Main failure mode expected |
| --- | --- |
| Northwind paid claim | Treating approval of one asset/channel as approval of a new claim and paid distribution. |
| Acme credit ledger | Applying an estimated percentage to the wrong period or reopening a closed ledger despite a scoped credit approval. |
| Nordbank residency | Turning approved operational wording into an unauthorized contractual absolute. |
| Proxima exception | Treating a successful expired exception as standing authority for a broader renewal. |

## Pilot outcome: rejected for scaling

The November 15, 2026 Valkyrie pilot used all eight tasks with three trials per
task for Fable 5.2, GPT-6 Astra, and Gemini 4 Carbon under the same
mini-SWE-agent harness. Fable scored 59.6% ± 7.7 points, Astra scored 80.0% ±
8.0 points, and Carbon scored 45.0% ± 1.8 points. The set does not advance:

- Astra and Fable are above the 55% hardening threshold;
- Astra outscored Fable by 20.4 points under the shared harness;
- seven zero-scoring runs were `RepeatedFormatError`/no-action failures;
- Fable's actionful runs averaged 84.1%;
- Carbon recorded no action in 12/24 attempts after reaching the fixed 25-step
  limit; its other attempts averaged 90.0%, so its 45.0% raw score is not clean
  evidence of reasoning difficulty;
- Astra exposed one confirmed and one probable negation false positive in the
  blocking gate, plus five verifier payloads truncated in result metadata;
- trajectory review found lexical scorer misses such as `expiry` versus
  `expired`, not enough genuine reasoning failures.

The next hardening pass must create cases where safe refusal and generic
escalation are both incomplete. Correctness should require selecting one of
two positive actions using quantitative reconciliation, authority precedence,
or reversible sequencing. The awareness and alternative components need a
blinded LLM judge calibrated against a human-labeled set; deterministic checks
remain authoritative only for observable required and forbidden actions.

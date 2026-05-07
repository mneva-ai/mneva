# M6 Manual Real-Key Smoke Checkpoint

This procedure satisfies the M6 verification criterion in `D:\AI\specs\mneva-v0-alpha.plan.md` §3:

> "`mneva synthesize` against each backend (real keys) — Stage 1 returns ~100 ideas;
>  user clears; stage 2 returns critical pass; total wall ≤ 90s on Anthropic."

It is not part of CI. Run it manually before tagging the M6 boundary release.

## Prerequisites

- `mneva init` already executed; `~/.mneva/` populated.
- At least 5 captured records under a single scope, e.g. `mneva capture --scope smoke-m6 --tool claude --body "..."`.
- API keys exported in your shell:
  - `ANTHROPIC_API_KEY`
  - `OPENAI_API_KEY`
  - `GOOGLE_API_KEY`
  - `OPENROUTER_API_KEY`

## Procedure

For each backend in `[anthropic, openai, google, openrouter]`:

1. Start a wall-clock timer.
2. Run:

   ```
   mneva synthesize --scope smoke-m6 --backend <backend>
   ```

3. Confirm Stage 1 output is a numbered list of roughly 100 ideas (50–150 acceptable).
4. Paste a 5-item shortlist back, then `.` on its own line.
5. Confirm Stage 2 output is a critical-pass analysis of those 5 items.
6. Stop the timer. Record total wall time.
7. Run:

   ```
   mneva digest --scope smoke-m6 --backend <backend> --write-bootstrap
   ```

   Confirm `~/.mneva/bootstrap.md` is rewritten with a 200–500 word digest.

## Pass criteria

- All four backends complete both stages without raised exceptions.
- bootstrap.md is non-empty after each digest run.
- No API key appears in any captured output.

## Targets (recorded, not gated)

- Anthropic total wall time **target ≤ 90s** per plan §114. Overrun does NOT fail the checkpoint — record the actual time and feed back into v0.1 prompt-tuning / max_tokens defaults. Other backends are observation-only.

## Failure handling

- Stage 1 returns < 30 ideas → prompt drift; revisit `STAGE1_PROMPT` in `src/mneva/synth.py`.
- Anthropic > 90s → check model id (`claude-opus-4-7`) and that `max_tokens` defaults haven't been bumped.
- Backend raises `MissingAPIKeyError` → confirm env var is exported in the same shell.
- Backend raises a 4xx from upstream → check model availability; some Gemini/GPT-5 model ids may have moved.

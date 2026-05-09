# Providers (BYOK)

Mneva is bring-your-own-key: API keys are read from environment variables at runtime and
never written to config files or captured records. Four backends are supported:
`anthropic`, `openai`, `google`, and `openrouter`. The default for `synthesize` and
`digest` is `anthropic`; override with `--backend=<provider>`.

## Common pattern

```bash
export <PROVIDER>_API_KEY=<your-key>
mneva synthesize --scope my-project --backend <provider>
```

If the env var for the chosen backend is not set, Mneva exits with a clean one-line error:
`missing API key for <backend>: set <ENV_VAR> in your environment`.

To override the default model for any backend, set `MNEVA_<PROVIDER>_MODEL=<model-id>`
before running the command.

---

## Anthropic

- `--backend=anthropic` (default)
- Env var: `ANTHROPIC_API_KEY`
- Default model: `claude-opus-4-7`
- Model override: `MNEVA_ANTHROPIC_MODEL=<model-id>`
- Get a key: https://console.anthropic.com/

```bash
export ANTHROPIC_API_KEY=sk-ant-...
mneva synthesize --scope my-project
```

---

## OpenAI

- `--backend=openai`
- Env var: `OPENAI_API_KEY`
- Default model: `gpt-5`
- Model override: `MNEVA_OPENAI_MODEL=<model-id>`
- Get a key: https://platform.openai.com/api-keys

```bash
export OPENAI_API_KEY=sk-...
mneva synthesize --scope my-project --backend openai
```

---

## Google

- `--backend=google`
- Env var: `GOOGLE_API_KEY`
- Default model: `gemini-2.0-pro`
- Model override: `MNEVA_GOOGLE_MODEL=<model-id>`
- Get a key: https://aistudio.google.com/apikey

```bash
export GOOGLE_API_KEY=...
mneva synthesize --scope my-project --backend google
```

---

## OpenRouter

OpenRouter routes requests through a single endpoint (`https://openrouter.ai/api/v1`)
using the OpenAI-compatible API, with model ids in `<vendor>/<model>` format. Useful when
you want one key that can reach models from multiple vendors.

- `--backend=openrouter`
- Env var: `OPENROUTER_API_KEY`
- Default model: `anthropic/claude-opus-4-7`
- Model override: `MNEVA_OPENROUTER_MODEL=<vendor>/<model-id>`
- Get a key: https://openrouter.ai/keys

```bash
export OPENROUTER_API_KEY=sk-or-...
mneva synthesize --scope my-project --backend openrouter
```

---

## Troubleshooting

- **`missing API key for <backend>`** — the env var is not set in the shell running
  `mneva`. Re-export the key and retry.

- **Upstream 4xx (model id moved)** — vendors occasionally rename or retire model ids
  (Gemini and GPT model ids especially). Override with `MNEVA_<PROVIDER>_MODEL=<current-id>`
  to unblock without waiting for a Mneva release.

- **No key appears in captured output** — Mneva never logs API keys. If a key string
  appears in a record, it was captured verbatim from user-provided input, not from
  Mneva internals.

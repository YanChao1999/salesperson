# Development guide

Start building the Salesperson platform after the customer site and API skeleton are in place.

## Branch workflow

```bash
git checkout main && git pull
git checkout -b feat/your-feature
make test
make serve
```

Open PRs into **`main`**. GitHub Pages deploys from `main`; CI runs tests on every PR.

## Run locally

```bash
# Dev container (recommended)
make serve

# Or directly
pip install -r requirements-dev.txt
python3 -m salesperson
```

Register a site and chat:

```bash
curl -s -X POST http://127.0.0.1:8000/websites \
  -H 'Content-Type: application/json' \
  -d '{"name":"Demo","domain":"demo.example.com","llm":{"provider":"openai","model":"gpt-4.1"}}'

curl -s -X POST http://127.0.0.1:8000/v1/chat/completions \
  -H 'Authorization: Bearer sk_live_…' \
  -H 'Content-Type: application/json' \
  -d '{"messages":[{"role":"user","content":"Hello"}]}'
```

## Persistence

By default data is **in-memory** (lost on restart).

Enable SQLite:

```bash
export SALESPERSON_DB_PATH=data/salesperson.db
make serve
```

## Current sprint (platform dev)

| Done | Item |
|------|------|
| ✓ | CI workflow (unit tests) |
| ✓ | SQLite repository |
| ✓ | Production widget chat panel |
| | OpenAI / Anthropic provider |
| | Operator auth on admin API |
| | Rate limits per plan |
| | Owner dashboard UI |

## Next priorities

1. **Real LLM provider** — `SALESPERSON_LLM_PROVIDER=openai` + API key env
2. **Admin auth** — protect `/websites/*` routes
3. **Plan enforcement** — gate API features by tenant plan level
4. **Postgres** — replace SQLite for production multi-instance deploy

See [PLATFORM.md](PLATFORM.md) for architecture and API details.

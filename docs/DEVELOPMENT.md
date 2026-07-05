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

### Widget test page

```bash
# Terminal 1 — API
export SALESPERSON_DB_PATH=data/salesperson.db
make serve

# Terminal 2 — static docs + test page
make docs
```

Open **http://127.0.0.1:8080/test-widget.html** — loads your embed from
`docs/test-widget.config.js` (copy from `test-widget.config.example.js`) or
pass `?key=sk_live_…` in the URL.

## Persistence

By default data is **in-memory** (lost on restart).

Enable SQLite:

```bash
export SALESPERSON_DB_PATH=data/salesperson.db
make serve
```

## LLM provider

**Demo LLM is the default** — no external API keys required.

```bash
# default (demo/stub — local echo responses)
make serve

# explicit
export SALESPERSON_LLM_PROVIDER=demo
make serve
```

Real OpenAI/Anthropic providers are deferred; other platform work continues on demo LLM.

Optional admin protection for `/websites/*`:

```bash
export SALESPERSON_ADMIN_TOKEN=your-operator-secret
curl -X POST http://127.0.0.1:8000/websites \
  -H 'Authorization: Bearer your-operator-secret' \
  -H 'Content-Type: application/json' \
  -d '{"name":"Demo","domain":"demo.example.com","llm":{"provider":"openai","model":"gpt-4.1"}}'
```

When `SALESPERSON_ADMIN_TOKEN` is unset, admin routes stay open for local dev.

## Current sprint (platform dev)

| Done | Item |
|------|------|
| ✓ | CI workflow (unit tests) |
| ✓ | SQLite repository |
| ✓ | Production widget chat panel |
| ✓ | Demo LLM provider (default) |
| ✓ | Widget visitor tracking (`user_id`) |
| ✓ | Admin auth on `/websites/*` (optional token) |
| ✓ | Widget test page (`docs/test-widget.html`) |
| | OpenAI / Anthropic provider |
| | Rate limits per plan |
| | Owner dashboard UI |

## Next priorities

1. **Real LLM provider** — opt-in `SALESPERSON_LLM_PROVIDER=openai` + API key env
2. **Plan enforcement** — gate API features by tenant plan level
3. **Domain allowlist** — restrict public API by website domain
4. **Postgres** — replace SQLite for production multi-instance deploy

See [PLATFORM.md](PLATFORM.md) for architecture and API details.

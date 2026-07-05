# Salesperson Agent Platform

API-forward platform for website owners. Websites embed a widget; chat traffic flows through your hosted API, which validates tenants, applies sales behavior, forwards to LLM providers, and meters usage.

See **[docs/PLATFORM.md](docs/PLATFORM.md)** for architecture, API spec, and roadmap.

**Customer site (GitHub Pages):** [yanchao1999.github.io/salesperson](https://yanchao1999.github.io/salesperson/) — [services](https://yanchao1999.github.io/salesperson/#services) · [plans](https://yanchao1999.github.io/salesperson/#plans) ([PRICING.md](docs/PRICING.md))

**Dev container:** reopen the repo in the dev container for a ready-to-use Python environment.  
See **[docs/DEVCONTAINER.md](docs/DEVCONTAINER.md)** for develop & deploy commands.

## Quick start

### Dev container (recommended)

Open in Cursor → **Reopen in Container**, then:

```bash
make serve    # API on :8000
make test     # run tests
make deploy   # production container
```

### Local (without container)

```bash
pip install -r requirements-dev.txt
python3 -m salesperson
```

## APIs

### Public (website / widget) — requires `Authorization: Bearer sk_live_…`

- `POST /v1/chat/completions` — forward chat to LLM (stub provider in dev)
- `GET /v1/usage` — usage summary for authenticated website

### Admin (operator / dashboard)

- `POST /websites` — register website (returns `api_key` once)
- `POST /websites/{id}/users`
- `PUT /websites/{id}/behavior`
- `POST /websites/{id}/usage`
- `POST /websites/{id}/deals`
- `GET /websites/{id}/summary`

### Static

- `GET /widget.js` — embeddable chat widget
- `GET /health`

## Example

```bash
# Register
curl -s -X POST http://127.0.0.1:8000/websites \
  -H 'Content-Type: application/json' \
  -d '{"name":"Demo Store","domain":"demo.example.com","llm":{"provider":"openai","model":"gpt-4.1"}}'

# Chat (use api_key from registration response)
curl -s -X POST http://127.0.0.1:8000/v1/chat/completions \
  -H 'Authorization: Bearer sk_live_…' \
  -H 'Content-Type: application/json' \
  -d '{"messages":[{"role":"user","content":"What plans do you offer?"}]}'
```

## Test

```bash
python -m unittest discover -s tests -v
```

## Project layout

```
salesperson/
├── auth/          API key generation and validation
├── gateway/       Chat forward orchestration
├── providers/     LLM adapters (stub for local dev)
├── storage/       Repository protocol + in-memory store
├── static/        widget.js embed
├── backend.py     Tenant admin service
└── server.py      WSGI routes (admin + /v1 + static)
```

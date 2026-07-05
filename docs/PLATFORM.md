# Salesperson Agent Platform

API-forward platform for website owners. Websites embed a widget; all chat traffic goes through **your** hosted API, which validates the tenant, applies sales behavior, forwards to an LLM provider, and meters usage automatically.

**Customer-facing overview:** [GitHub Pages site](index.html) (`docs/index.html`) — what we provide for website owners.

**Pricing:** [PRICING.md](PRICING.md) — four product levels (Free → Advanced).

## Business model

You operate a **gateway**, not a library:

```
Website visitor  →  widget.js  →  POST /v1/chat/completions  →  Your platform
                                                                    │
                                                         validate API key
                                                         load behavior prompt
                                                         check quota (future)
                                                                    │
                                                                    ▼
                                                         LLM provider (OpenAI, Anthropic, …)
                                                                    │
                                                         auto-record tokens + deals
```

Website owners never call the LLM directly from the browser. They paste one embed snippet and use a per-site API key.

## Architecture

```
salesperson/
├── models.py           # Domain types (Website, UsageRecord, …)
├── errors.py           # Platform errors
├── backend.py          # SalespersonPlatform — tenant admin API
├── server.py           # WSGI entry: admin routes + public /v1 + static widget
├── auth/               # API key generation and validation
├── storage/            # Repository protocol + in-memory impl (swap for Postgres)
├── gateway/            # Chat forward orchestration
├── providers/          # LLM adapter protocol + stub for local dev
└── static/widget.js    # Embeddable chat widget (stub)
```

| Layer | Responsibility | Status |
|-------|----------------|--------|
| **Public API** (`/v1/*`) | Chat forward, tenant auth | Skeleton |
| **Admin API** (`/websites/*`) | Register sites, behavior, summary | Implemented |
| **Gateway** | Inject prompt, call provider, meter usage | Skeleton (stub provider) |
| **Auth** | `sk_live_*` keys, Bearer validation | Skeleton |
| **Storage** | Persist tenants, usage, deals | Skeleton (in-memory) |
| **Widget** | Browser embed calling public API | Skeleton |
| **Dashboard UI** | Owner console | Not started |
| **Billing / quotas** | Stripe, rate limits | Not started |
| **Persistence** | Postgres + migrations | Not started |

## API surface

### Public API (website / widget)

Authenticated with `Authorization: Bearer sk_live_…`.

#### `POST /v1/chat/completions`

Forward a chat turn to the tenant's configured LLM.

**Request**

```json
{
  "messages": [
    {"role": "user", "content": "What plan fits a team of 10?"}
  ],
  "user_id": "demo-store-user-1",
  "channel": "website-widget"
}
```

**Response**

```json
{
  "id": "chatcmpl-stub-1",
  "message": {"role": "assistant", "content": "…"},
  "usage": {"prompt_tokens": 12, "completion_tokens": 24, "total_tokens": 36},
  "website_id": "demo-store"
}
```

Usage is recorded **by the gateway** — clients must not trust self-reported token counts.

#### `GET /v1/usage`

Return usage summary for the authenticated website.

### Admin API (operator / dashboard)

Unauthenticated in the skeleton; production must require operator auth.

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/websites` | Register website, returns `api_key` (shown once) |
| `POST` | `/websites/{id}/users` | Create scoped visitor user |
| `PUT` | `/websites/{id}/behavior` | Set system prompt, tone, goals |
| `POST` | `/websites/{id}/usage` | Manual usage (legacy; prefer gateway auto-meter) |
| `POST` | `/websites/{id}/deals` | Record deal stage |
| `GET` | `/websites/{id}/summary` | Dashboard metrics |

### Static

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/widget.js` | Embeddable script |
| `GET` | `/health` | Liveness |

## Onboarding flow

1. **Register** — `POST /websites` with name, domain, LLM config → receive `website_id`, `api_key`, `embed_code`.
2. **Configure** — `PUT /websites/{id}/behavior` with sales prompt and goals.
3. **Embed** — Paste `embed_code` into the site HTML.
4. **Run** — Widget calls `POST /v1/chat/completions` with the API key.
5. **Monitor** — `GET /websites/{id}/summary` or `GET /v1/usage`.

## Embed snippet

```html
<script
  src="https://your-platform.example/widget.js"
  data-api-key="sk_live_…"
  data-api-base="https://your-platform.example"
></script>
```

## What's missing for production

### P0 — required to ship

- [ ] Real LLM providers (OpenAI, Anthropic HTTP clients)
- [ ] Postgres `PlatformRepository` implementation
- [ ] Encrypted storage for owner BYOK LLM keys
- [ ] Operator auth on admin routes
- [ ] Domain allowlist enforcement on public API
- [ ] Streaming responses (SSE) for chat UX
- [ ] Production WSGI/ASGI server (gunicorn/uvicorn)

### P1 — commercial readiness

- [ ] Rate limits and quotas per website
- [ ] Stripe billing tied to metered tokens
- [ ] API key rotation and revoke
- [ ] Owner dashboard UI
- [ ] Webhooks (`deal.stage_changed`, `lead.captured`)
- [ ] Structured logging and metrics per `website_id`

### P2 — differentiation

- [ ] Product catalog RAG per website
- [ ] CRM integrations (HubSpot, Pipedrive)
- [ ] Shopify / WordPress plugins
- [ ] A/B testing for sales prompts

## Local development

```bash
# Dev container (recommended)
make serve

# Or install locally
pip install -r requirements-dev.txt
python3 -m salesperson

# Production-like container
make deploy
```

The skeleton uses `StubLLMProvider` — no external API keys required for local dev.

See [DEVCONTAINER.md](DEVCONTAINER.md) for container setup and deploy.

## Extension points

| Interface | Module | Replace with |
|-----------|--------|--------------|
| `PlatformRepository` | `storage/base.py` | Postgres repository |
| `LLMProvider` | `providers/base.py` | OpenAI / Anthropic adapters |
| `ChatGateway` | `gateway/service.py` | Add streaming, retries, fallbacks |

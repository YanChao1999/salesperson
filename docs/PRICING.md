# Pricing

Four product levels for website owners. Higher tiers include everything in lower tiers.

| Level | Plan | Best for |
|-------|------|----------|
| 1 | **Free** | Trying the embed widget with default behavior |
| 2 | **Basic API** | Calling the public chat API from your own app |
| 3 | **Custom · Self-integrate** | Basic API + custom behavior; you integrate |
| 4 | **Advanced · We integrate** | Advanced API + custom services + integration help |

---

## Level 1 — Free

**Price:** $0

- Embeddable `widget.js` on any website
- Default sales assistant behavior
- Limited monthly chat volume
- Usage summary (basic)
- Community / documentation support

**Get started:** register a website via `POST /websites`, paste the embed snippet.

---

## Level 2 — Basic API

**Price:** paid (contact for rates)

- Everything in **Free**
- Public API access:
  - `POST /v1/chat/completions`
  - `GET /v1/usage`
- Per-website API keys (`sk_live_…`)
- Higher message and token limits
- Gateway auto-meters usage (no self-reporting)

**Best for:** teams that build their own chat UI but want a hosted LLM gateway.

---

## Level 3 — Custom · Self-integrate

**Price:** paid (contact for rates)

- Everything in **Basic API**
- Custom sales behavior per website:
  - System prompt, tone, sales goals
- Bring your own LLM provider and model (BYOK)
- Integrate via widget **or** headless API
- Self-service documentation and examples

**Best for:** brands that need custom messaging and control their own integration work.

---

## Level 4 — Advanced · We integrate

**Price:** custom quote

- Everything in **Custom · Self-integrate**
- Advanced API capabilities (extended endpoints, webhooks — roadmap)
- Custom platform services (catalog RAG, CRM sync — roadmap)
- Hands-on integration support from our team
- Priority support and optional SLA

**Best for:** enterprises and agencies that want a tailored sales agent with assisted rollout.

---

## Comparison

| Capability | Free | Basic API | Custom | Advanced |
|------------|:----:|:---------:|:------:|:--------:|
| Widget embed | ✓ | ✓ | ✓ | ✓ |
| Public chat API | — | ✓ | ✓ | ✓ |
| Custom behavior / prompts | — | — | ✓ | ✓ |
| BYOK LLM | — | — | ✓ | ✓ |
| Self integration | ✓ | ✓ | ✓ | ✓ |
| Advanced API | — | — | — | ✓ |
| Custom services | — | — | — | ✓ |
| Integration assistance | — | — | — | ✓ |

---

## Contact

For Level 2–4 pricing and Level 4 integration projects, open an issue on
[GitHub](https://github.com/YanChao1999/salesperson/issues) or reach out through your account manager.

# salesperson

Minimal backend for a salesperson agent platform that can be plugged into other websites.

## What it supports

- register a website with its LLM provider/model configuration
- generate an embeddable widget snippet for that website
- create website-scoped user IDs for tracking agent usage
- customize sales behavior with prompts, tone, and goals
- trace usage events and deal progress for each website

## Run the backend

```bash
python -m salesperson
```

The server starts on `http://127.0.0.1:8000` and exposes:

- `POST /websites`
- `POST /websites/{website_id}/users`
- `PUT /websites/{website_id}/behavior`
- `POST /websites/{website_id}/usage`
- `POST /websites/{website_id}/deals`
- `GET /websites/{website_id}/summary`

Example website registration payload:

```json
{
  "name": "Demo Store",
  "domain": "demo.example.com",
  "llm": {
    "provider": "openai",
    "model": "gpt-4.1"
  }
}
```

## Test

```bash
python -m unittest discover -s tests -v
```
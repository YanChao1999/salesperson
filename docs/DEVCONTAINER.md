# Dev container & Docker deploy

Develop and deploy the Salesperson platform from a single container workflow.

## Dev container (recommended)

1. Open the repo in Cursor / VS Code.
2. Run **Dev Containers: Reopen in Container** when prompted (or from the command palette).
3. Wait for `.devcontainer/post-create.sh` to install dependencies and run tests.

The dev container includes Python 3.12, Git, Docker Compose CLI, and forwards:

| Port | Service |
|------|---------|
| `8000` | Platform API |
| `8080` | GitHub Pages preview (`make docs`) |

### Commands inside the container

```bash
make test     # unit tests
make serve    # dev server (wsgiref) on :8000
make docs     # static site preview on :8080
make deploy   # production container via compose profile
make image    # build deploy image locally
```

## Environment variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `SALESPERSON_HOST` | `127.0.0.1` | Bind address |
| `SALESPERSON_PORT` | `8000` | HTTP port |
| `SALESPERSON_AGENT_BASE_URL` | `http://{host}:{port}` | Public URL used in embed snippets |

In dev container / deploy, set `SALESPERSON_AGENT_BASE_URL` to the URL website owners will use (e.g. `https://api.example.com`).

## Deploy with Docker Compose

From the repo root (host or dev container):

```bash
# set public URL for embed codes
export SALESPERSON_AGENT_BASE_URL=https://api.example.com

docker compose --profile deploy up --build -d platform
# or
make deploy
```

This builds `Dockerfile` and runs **gunicorn** with `salesperson.wsgi:application`.

Check health:

```bash
curl http://localhost:8000/health
```

Stop:

```bash
make deploy-down
```

## Deploy image only

```bash
docker build -t salesperson-platform:latest .
docker run --rm -p 8000:8000 \
  -e SALESPERSON_AGENT_BASE_URL=http://localhost:8000 \
  salesperson-platform:latest
```

## Layout

```
.devcontainer/
  devcontainer.json   # Cursor / VS Code dev container config
  Dockerfile          # Dev image (Python + tools)
  post-create.sh      # Install deps + smoke test
Dockerfile            # Production deploy image (gunicorn)
docker-compose.yml    # dev service + deploy profile
Makefile              # test, serve, docs, deploy shortcuts
```

## GitHub Pages

The marketing site in `docs/` is deployed separately via `.github/workflows/pages.yml`.
Use `make docs` inside the dev container to preview `docs/index.html` locally.

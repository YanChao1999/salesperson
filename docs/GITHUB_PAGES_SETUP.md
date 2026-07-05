# GitHub Pages setup (one-time)

The deploy workflow fails with **"Get Pages site failed"** until GitHub Pages is enabled on the repository.

## Option A — GitHub UI (recommended)

1. Open [Repository Settings → Pages](https://github.com/YanChao1999/salesperson/settings/pages)
2. Under **Build and deployment**, set **Source** to **GitHub Actions**
3. Re-run the **Deploy GitHub Pages** workflow (Actions tab → failed run → **Re-run all jobs**)

## Option B — GitHub CLI

Requires repo admin permissions:

```bash
gh api --method POST repos/YanChao1999/salesperson/pages -f build_type=workflow
```

If Pages was previously configured with another source:

```bash
gh api --method PUT repos/YanChao1999/salesperson/pages -f build_type=workflow
```

Then re-run the workflow.

## After enablement

Site URL: **https://yanchao1999.github.io/salesperson/**

The workflow (`.github/workflows/pages.yml`) publishes the `docs/` folder on push to `main` or `copilot/salesperson-agent-platform`.

## Verify

```bash
gh api repos/YanChao1999/salesperson/pages
gh workflow run pages.yml --ref copilot/salesperson-agent-platform
gh run list --workflow=pages.yml --limit 1
```

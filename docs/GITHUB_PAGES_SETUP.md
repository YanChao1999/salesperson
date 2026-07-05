# GitHub Pages setup

Pages uses **GitHub Actions** as the build source (`build_type: workflow`).

Production deploys run **only from `main`** — PR and feature branches do not deploy.

## One-time enablement

If deploy fails with **"Get Pages site failed"**, enable Pages first:

1. [Settings → Pages](https://github.com/YanChao1999/salesperson/settings/pages)
2. **Build and deployment** → **Source** → **GitHub Actions**

Or:

```bash
gh api --method POST repos/YanChao1999/salesperson/pages -f build_type=workflow
```

The `github-pages` environment should allow **`main`** only (default). No feature-branch deploy is needed.

## Release flow

1. Open a PR into `main` (tests run; no Pages deploy)
2. Merge to `main`
3. **Deploy GitHub Pages** workflow runs automatically
4. Site updates at **https://yanchao1999.github.io/salesperson/**

Manual deploy from `main`:

```bash
gh workflow run pages.yml --ref main
```

## Verify

```bash
gh api repos/YanChao1999/salesperson/pages
gh run list --workflow=pages.yml --limit 3
```

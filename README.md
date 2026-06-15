# World Cup Player Search — CI/CD Security Pipeline

A lightweight Flask web app that lets you search international soccer players by name and see their photo, nationality, and position. The app itself is intentionally simple as the pipeline was the main focus of this project.

## What the app does

- `GET /?q=<name>` — Search page that returns player cards with photo, nationality, and position
- `GET /api/search?q=<name>` — Same data as JSON
- `GET /health` — Returns `{"status": "ok"}` to confirm the service is running

Player data comes from [TheSportsDB](https://www.thesportsdb.com/), a free public API that requires no registration or API key. This keeps the app dependency-free at runtime, while still letting the pipeline demonstrate meaningful security practices.

---

## How the pipeline works

Every push to `main` and every pull request triggers the full pipeline automatically. The jobs are ordered intentionally so fast, cheap checks run first followed by the slower ones. The deploy step will not trigger if any of the below checks fail.

```
push / PR
    │
    ▼
┌─────────┐
│  lint   │  flake8 — fast style gate, fails early on obvious errors
└────┬────┘
     │ (runs all four run in parallel)
     ├──────────────────┬────────────────────┬──────────────────┐
     ▼                  ▼                    ▼                  ▼
┌─────────┐      ┌───────────┐       ┌────────────┐    ┌────────────┐
│  test   │      │  codeql   │       │secret-scan │    │ dep-audit  │
│ pytest  │      │ (Python)  │       │ (Gitleaks) │    │ (pip-audit)│
└────┬────┘      └─────┬─────┘       └─────┬──────┘    └─────┬──────┘
     └──────────────────┴─────────────────┴──────────────────┘
                                   │ (all four must pass)
                                   ▼
                        ┌──────────────────────┐
                        │   build-and-scan     │
                        │  Docker build        │
                        │  Trivy image scan    │
                        └──────────┬───────────┘
                                   │ (main branch only)
                                   ▼
                        ┌──────────────────────┐
                        │       deploy         │
                        │  Push to GHCR        │
                        └──────────────────────┘
```

### Job-by-job breakdown

**Lint** runs first using flake8. It checks code style and syntax and is intentionally the cheapest step — if there is an obvious error, the pipeline fails immediately before wasting time on the slower jobs.

**Unit Tests** run once lint passes, verifying that all routes return the correct responses and that error cases are handled gracefully. The external API is mocked so tests pass without a live network call.

**Static Analysis** uses GitHub CodeQL with the `security-extended` query suite to read through the source code looking for security flaws such as injection vulnerabilities, path traversal, and unsafe data handling before the code runs.

**Secret Scanning** uses Gitleaks to check the full git commit history for accidentally committed credentials such as API keys, .env files etc. Scanning the full history rather than just the latest diff ensures nothing slips through from an earlier commit.

**Dependency Audit** uses pip-audit to check every package in `requirements.txt` against the Open Source Vulnerabilities database. If a known CVE exists in any dependency, the build stops.

**Build and Scan** builds the Docker container and runs Trivy against the final image, checking the OS layer and all installed packages for vulnerabilities. Results are uploaded to the GitHub Security tab.

**Deploy** is the final step and only runs on pushes to `main`. It publishes the verified container image to GitHub Container Registry, tagged with both the commit SHA and `latest`.

---

## Why these security layers

The four security jobs in this pipeline each cover a different attack surface:

**1. CodeQL (static analysis)**
Analyzes the source code itself for vulnerabilities before anything runs. Using the `security-extended` query suite means it checks for OWASP Top 10 patterns such as injection flaws or unsafe data handling. Running this on every PR catches issues while the developer still has full context, which makes them much cheaper to fix than finding them post-merge.

**2. Gitleaks (secret scanning)**
Gitleaks works by scanning the full git history on every push, looking for patterns that match known credential formats such as API keys, tokens, and passwords. It uses `fetch-depth: 0` to pull every commit, not just the latest diff, so nothing in the history is skipped.

**3. pip-audit (dependency scanning)**
Checks every package in `requirements.txt` against the Open Source Vulnerabilities (OSV) database. On the first push of this project, it immediately caught Common Vulnerabilities and Exposures (CVEs) in Flask 3.1.1 and requests 2.32.4 and blocked the deploy until both were upgraded to patched versions.

**4. Trivy (container image scanning)**
CodeQL only reads the Python source files, so it has no visibility into the OS or runtime packages bundled inside the container. Trivy fills that gap by scanning the final built image end-to-end, checking the OS layer, the Python packages, and any installed system libraries against a known vulnerability database. Any findings are uploaded to the GitHub Security tab in SARIF format so they are visible without leaving the repository. To keep the exposed surface area small, this project uses `python:3.12-slim` as the base image rather than a full OS image with hundreds of extra packages. The container also runs as a non-root user, meaning that even if an attacker found a way to exploit the running app, they would land in a restricted environment with limited ability to do further damage.

**On thresholds:** Trivy is configured to report `CRITICAL` and `HIGH` findings only, with `ignore-unfixed: true`. Flagging vulnerabilities that have no available patch just creates noise without any actionable path forward. In a production environment I would pair this with Dependabot so a PR gets opened automatically the moment a patch lands.

**Why not Bandit?** CodeQL's `security-extended` suite already covers the same Python-specific checks Bandit provides. Running both would duplicate findings and clutter the Security tab with redundant results.

**Why not DAST?** Dynamic testing makes sense for a service with complex business logic and authenticated flows. For a two-endpoint read-only app, the signal-to-noise ratio doesn't justify it here.

---

## Running it locally

**Requirements:** Python 3.12, Docker

```bash
# Clone the repo
git clone https://github.com/GabeC117/WorldCup-Stats.git
cd WorldCup-Stats

# Create a virtual environment and install dependencies
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\Activate.ps1
pip install -r requirements.txt -r requirements-dev.txt

# Run the tests
pytest tests/ -v

# Run the app
python app.py
# → http://localhost:5000
```

**To build and run the container locally:**
```bash
docker build -t worldcup-stats .
docker run -p 5000:5000 worldcup-stats
```

**To pull the published image from GHCR:**
```bash
docker pull ghcr.io/gabec117/worldcup-stats:latest
docker run -p 5000:5000 ghcr.io/gabec117/worldcup-stats:latest
```

---

## Secrets and permissions

This app requires no API keys at runtime. The only token used in the pipeline is `GITHUB_TOKEN`, which GitHub Actions provides automatically on every run. No manual secrets need to be configured.

# DataPilot — Getting Started Guide

This guide takes you from zero to a running DataPilot app in VS Code, then to a
live deployment. It is written in order — follow the sections top to bottom.

---

## 1. What you need

| Thing | Where to get it | Why |
|---|---|---|
| VS Code | https://code.visualstudio.com | The editor we use |
| Python 3.11+ | https://www.python.org/downloads/ | The runtime (we use 3.14) |
| Git | https://git-scm.com | Version control |
| OpenRouter API key | https://openrouter.ai/keys | Powers the AI layer |
| (Optional) GitHub account | https://github.com | Needed for deployment |

> The current project is configured with:
> - Model: `google/gemma-4-26b-a4b-it:free`
> - API key already placed in your local `.env` (kept out of Git).

---

## 2. Open the project in VS Code

1. Open VS Code.
2. `File → Open Folder…` and choose the project folder (`S:\DataPilot`).
3. You should see this layout:

```
S:\DataPilot
├── app/               # all source code
│   ├── main.py        # Streamlit entrypoint
│   ├── core/          # profiler, validator, transformer, reporter, pipeline
│   ├── data/          # loader, schema, storage
│   ├── ai/            # OpenRouter client, prompts, analyzer, parser
│   ├── ui/            # Streamlit pages
│   └── utils/         # config, logger, helpers
├── tests/             # pytest suite (40 tests)
├── data/sample/       # sample dirty dataset
├── reports/           # generated quality reports
├── docs/              # architecture / pipeline / ai-design / this guide
└── .env               # YOUR SECRETS (do not share/commit)
```

4. Install the **Python** extension (Ctrl+Shift+X → search "Python" by Microsoft) if prompted.

---

## 3. Set up the Python environment

Open a terminal in VS Code (`Ctrl + `` `, the backtick key).

### 3a. Create a virtual environment

```powershell
python -m venv .venv
```

### 3b. Activate it (PowerShell)

```powershell
.\.venv\Scripts\Activate.ps1
```

If blocked, open a new terminal and run once:
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

### 3c. Install dependencies

```powershell
pip install -r requirements.txt
```

### 3d. Complete the config file

```powershell
copy .env.example .env   # only if .env is missing
```

Then edit `.env` and paste your real OpenRouter API key:

```
OPENROUTER_API_KEY=sk-or-v1-your-real-key
OPENROUTER_MODEL=google/gemma-4-26b-a4b-it:free
DATAPILOT_AI_ENABLED=true
```

> **Never commit `.env`.** It is already in `.gitignore`. Your key must stay
> secret — anyone with it can use your credit.

---

## 4. Verify the data engine (offline, no AI)

```powershell
python -m pytest -q
```

Expected: `40 passed`.

Then run the deterministic pipeline on the dirty sample and print a report:

```powershell
python -c "from app.core.pipeline import Pipeline; r,_ = Pipeline(name='sales').run_deterministic('data/sample/sales_dirty.csv'); print(r.report.to_markdown())"
```

You should see stats like *12,005 rows*, *negative revenue*, *mixed date
formats*, etc. — all detected without any AI.

---

## 5. Run the app locally (Streamlit)

```powershell
streamlit run app/main.py
```

VS Code may ask you to pick a browser — allow it. The app opens at
**http://localhost:8501**.

### Try the full loop (this is the point of the project)

1. **Upload Data** page → click **Browse files** → pick `data/sample/sales_dirty.csv`
   (or any of your own CSV/JSON/Excel).
2. Click **Run Pipeline** → you get a profile (rows, columns, duplicates, issues).
3. **Quality Report** page → deterministic issues listed with severity + shares,
   and the **AI Explanation** (uses your OpenRouter key + model).
4. **AI Fix Plan** page → click **Generate Fix Plan**. The model reads *only the
   metadata* (never your raw rows) and returns a validated fix plan.
5. Tick **"Review the plan above and approve"**, then **Apply Plan**.
6. The cleaned dataset preview appears → **Download clean CSV / Parquet**.

> Free models are rate-limited. If you see a 429 / slow AI response, wait ~1
> minute and retry, or switch `OPENROUTER_MODEL` to a paid model.

---

## 6. Use the headless CLI (no browser)

A one-liner equivalent of the UI:

```powershell
python scripts/run_pipeline.py data/sample/sales_dirty.csv --ai
```

Flags:
- `--no-ai` — deterministic only (fast, free)
- `--ai` — include the AI fix plan step
- `--report` — write the markdown report to `reports/` (default on)
- `--clean-csv output.csv` — save the cleaned dataset to a path

---

## 7. Common problems

| Symptom | Cause / fix |
|---|---|
| `MissingApiKeyError` | `.env` has no key → add `OPENROUTER_API_KEY` and restart Streamlit |
| 429 errors | Free tier rate limit → wait a minute, retry, or use a paid model |
| `Unknown transformation` | AI suggested a transform not in the safe registry — it is skipped+reported, never executed |
| Column "not found" in plan | The model referenced a column that doesn't exist — validation rejects it safely |
| `streamlit: not found` | venv not active → re-activate, or `pip install -r requirements.txt` |
| Port already in use (8501) | `streamlit run app/main.py --server.port 8502` |

---

## 8. Deploy online (Streamlit Community Cloud) — Step by Step

Free hosting for Streamlit apps. Flow: your code on GitHub → Streamlit Cloud
builds it → live URL.

### 8a. Push the project to GitHub

```powershell
git init
git add -A
git commit -m "DataPilot MVP"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/datapilot.git
git push -u origin main
```

> Notes:
> - `.gitignore` already excludes `.env`, `data/processed/`, `reports/`.
> - Create the empty repo in GitHub first ("New repository", no README).

### 8b. Create the Streamlit Cloud app

1. Go to **https://share.streamlit.io**.
2. Sign in with GitHub.
3. **New app** → select repo `datapilot`, branch `main`, main file **`app/main.py`**.
4. Click **Deploy**.

### 8c. Put your API key into the cloud (NOT in git)

In the app's **Settings → Secrets** editor, add:

```toml
OPENROUTER_API_KEY = "sk-or-v1-your-real-key"
OPENROUTER_MODEL = "google/gemma-4-26b-a4b-it:free"
DATAPILOT_AI_ENABLED = "true"
```

The app calls `python-dotenv`, which also reads Streamlit Cloud secrets — so
this works without code changes.

### 8d. Visit your live app

After the build finishes you get a URL like
`https://datapilot.streamlit.app`. Share it, upload a file, and run the full
pipeline for real.

### Deployment troubleshooting

| Issue | Fix |
|---|---|
| App crashes on start | Check the Cloud **Logs** tab; usually a missing dependency → `pip install -r requirements.txt` locally and re-push |
| AI fails in cloud but works locally | Secrets not saved correctly → re-check keys in Settings → Secrets |
| Rate limited | Free model upstream limit, shared by all free users → switch model or add credits |
| Port/health errors | Streamlit Cloud ignores local ports; keep `app/main.py` as the entrypoint |

---

## 9. Project map (where everything lives)

| You want to… | Look in |
|---|---|
| Change the model / key | `.env` (+ Streamlit secrets after deploy) |
| Add a quality rule | `app/core/validator.py` (detectors + `DETECTORS` list) |
| Add a transformation | `app/core/transformer.py` (add a `_fn(..., column, args)` and register it) |
| Change the AI prompt | `app/ai/prompts.py` |
| Tune retries/timeouts | `app/ai/client.py`, `app/utils/config.py` |
| Change a UI page | `app/ui/*.py` |
| Understand the design | `docs/architecture.md`, `docs/pipeline.md`, `docs/ai-design.md` |
| Full reference documentation | `PROJECT_DOCUMENTATION.md` |

Go live. 🚀
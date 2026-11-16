# Science Fair Winner (SFW)

**Version:** 1.1.0  
**Purpose:** A multidisciplinary scientific research and problem-solving workspace for students, science-fair participants and independent researchers.

Science Fair Winner combines an optional AI science assistant with research planning, methodology design, scholarly metadata discovery, local scientific calculations, statistical analysis, visualisation, project storage and report export.

> SFW is an application that uses existing AI providers and scientific Python libraries. It is not a newly trained foundation model, an autonomous laboratory, or a guarantee of scientific correctness.

## Features

- **AI Science Assistant:** Gemini, Anthropic and OpenAI API integrations; provider diagnostics and connection test; discipline, audience-level and response-mode controls.
- **Evidence-aware responses:** optional Crossref search with real publication metadata and available abstracts. Retrieved metadata is not full-text verification, and citation presence does not prove that a paper supports every sentence.
- **Research Project Planner:** draft research problems, aims, questions, hypotheses, variables and method outlines.
- **Research Methodology Engine:** structured methodology plans and checks for common mismatches in study design, objective, outcome, sample size, group structure and repeated measurements.
- **Literature Search:** search Crossref and inspect available publication metadata and abstracts.
- **Data Analysis Lab:** CSV/Excel import, data-quality checks, descriptive statistics, plots, correlations, linear regression, independent and paired t-tests, chi-square tests, confidence intervals and effect-size summaries.
- **Scientific Calculator and Unit Converter:** safe arithmetic and selected mathematical functions, metric conversions and temperature conversions.
- **Project Library:** authenticated Supabase cloud storage with per-user row-level security, plus optional local/shared storage for trusted deployments.
- **Report Builder:** export research plans as DOCX and PDF.
- **RTX GPU connector:** read-only connection checks and image-list retrieval through a configured public HTTPS endpoint. GPU job submission is intentionally disabled until the server's authenticated submission API is documented and tested.

## Requirements

- Python 3.10 or newer (Python 3.11 recommended)
- Windows, macOS or Linux
- Internet access for package installation, Crossref and external AI providers
- AI API key optional; planning, local calculations and data analysis work without one

## Run locally

### Windows PowerShell

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
streamlit run app.py
```

### Linux / macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
streamlit run app.py
```

Open the local URL printed by Streamlit, normally http://localhost:8501.

## Deploy to Streamlit Community Cloud

1. Push this repository to GitHub.
2. In Streamlit Community Cloud, create an app connected to this repository.
3. Select branch main and entry point app.py.
4. Add the chosen AI provider settings under the app's Settings → Secrets.
5. Deploy and open AI Science Assistant → AI connection & configuration → Test AI connection.

Streamlit Cloud installs packages from requirements.txt. Do not commit .env, .streamlit/secrets.toml, API keys or access tokens.

### Private cloud project storage (Supabase)

SFW supports email/password accounts and a private project library using Supabase Auth, Postgres and row-level security (RLS).

1. Create a Supabase project.
2. Open the Supabase SQL Editor and run the complete script in `supabase/schema.sql`.
3. In Streamlit Cloud → Manage app → Settings → Secrets, add:

```toml
SFW_SUPABASE_URL = "https://your-project.supabase.co"
SFW_SUPABASE_ANON_KEY = "your_supabase_anon_or_publishable_key"
```

4. Redeploy/restart the app, open Project Library, and create an account or sign in.
5. Generate a research plan and select **Save to my private library**.

Use only the Supabase anon/public key in Streamlit. Never add the Supabase `service_role` key to the app, repository, browser or chat. RLS policies in `supabase/schema.sql` enforce that each authenticated account can read, create, update or delete only its own projects. Configure email confirmation and password policies in Supabase Auth before inviting users. The user session is held in Streamlit session state; an expired session may require signing in again.

## Important: project persistence

The Project Library writes JSON files to the app's local data/projects/ directory. Shared-library mode is disabled by default because SFW does not yet have sign-in or private per-user storage; enabling it could expose saved plans to other app visitors. Set SFW_ENABLE_SHARED_PROJECT_LIBRARY=true only for a private, trusted, single-user deployment. The filesystem of a hosted app should not be treated as durable storage across rebuilds, restarts or redeployments. Back up local projects. Reliable multi-user cloud storage still requires a persistent database/object store and user access controls.

## Optional AI provider setup

Configure one provider. The model identifiers below are defaults and can be overridden for a model enabled on your provider account.

### Google Gemini

```toml
SFW_AI_PROVIDER = "gemini"
GEMINI_API_KEY = "your_google_ai_studio_key"
GEMINI_MODEL = "gemini-3.5-flash-lite"
```

### Anthropic

```toml
SFW_AI_PROVIDER = "anthropic"
ANTHROPIC_API_KEY = "your_anthropic_api_key"
ANTHROPIC_MODEL = "claude-sonnet-5-5"
```

### OpenAI

```toml
SFW_AI_PROVIDER = "openai"
OPENAI_API_KEY = "your_openai_api_key"
OPENAI_MODEL = "gpt-6-luna"
```

The app sends questions and recent conversation history to the selected provider. The optional Crossref mode also sends retrieved publication metadata/abstracts as context. Review each provider's current pricing, rate limits, retention and data-use terms before submitting private research material. The connection test makes a real API request and may consume quota.

## Optional RTX GPU service

The RTX connector is designed for a separate GPU host exposed through a public HTTPS endpoint, for example https://rtx.wfw.co.ke. Configure:

```toml
SFW_RTX_BASE_URL = "https://your-rtx-host.example"
# Cloudflare Access service token (recommended when Access is enabled):
SFW_RTX_ACCESS_CLIENT_ID = "your_client_id"
SFW_RTX_ACCESS_CLIENT_SECRET = "your_client_secret"
# Only if the RTX backend separately requires Bearer authentication:
SFW_RTX_API_TOKEN = "your_backend_token"
```

The hosted connector rejects plain HTTP, local/private network destinations and unsafe redirects. It supports Cloudflare Access service-token headers and an optional separate backend Bearer token. It currently reads only the documented queue homepage and /images endpoint. It does not submit, cancel or modify GPU jobs. Do not expose the RTX API publicly without authentication, access controls and rate limiting.

## Tests

Run the automated test suite:

```bash
python -m pip install -r requirements.txt
pytest -q
```

GitHub Actions runs the same test suite on pushes and pull requests to main.

## Project structure

```text
app.py
sfw/
  assistant.py       # AI providers and scientific response prompts
  analysis.py        # statistical analysis and validation
  config.py          # environment and Streamlit Secrets
  literature.py      # Crossref retrieval and reference formatting
  methodology.py     # study design and methodology checks
  planner.py         # research plan generation
  reporting.py       # DOCX and PDF exports
  rtx.py             # secure, read-only remote RTX client
  science_tools.py   # local calculator and unit conversion
  storage.py         # local project library
tests/               # automated unit tests
requirements.txt
```

## Scientific integrity and limitations

- AI-generated content can be wrong. Verify important claims against primary literature and qualified experts.
- Crossref results are publication metadata, not necessarily full text. Verify the publisher record, publication status, methods and findings before citing.
- A reference returned by a search is not proof that the source supports a particular claim.
- Statistical tests depend on sampling, independence, measurement quality, assumptions and study design. A p-value is not an effect size and does not prove causation.
- Confidence intervals and effect sizes are descriptive inferential summaries; they do not repair biased sampling, confounding or poor experimental design.
- Do not represent simulated or illustrative values as observed measurements.
- Obtain required supervision, ethics approval and safety review for work involving people, animals, pathogens, hazardous chemicals or other risks.
- The methodology engine flags common issues; it does not calculate a defensible sample size or certify a protocol.
- The RTX integration is read-only until the remote server's job-submission contract and authentication are confirmed.
- Supabase private project storage is optional and must be configured by the app owner using the SQL schema and Streamlit Secrets. It currently provides account-level project isolation, not team collaboration or institutional roles.

## Security

- Keep API keys and tokens in Streamlit Secrets or a private local .env file.
- Never paste secrets into chat, screenshots, source code or public issue reports.
- Do not expose the RTX service without HTTPS, authentication, network restrictions and monitoring.
- Do not upload confidential, identifying or sensitive data unless you have permission and have checked provider data-handling terms.

---

**Science Fair Winner (SFW)**  
Build release 1.1.0
# Science Fair Winner (SFW) — Complete Build System

**Version:** 1.0.0  
**Purpose:** Scientific intelligence and problem-solving workspace for students, science-fair participants and researchers.

SFW is a runnable Python/Streamlit application. It combines research planning, optional model-powered scientific conversation, scholarly metadata discovery, data analysis, statistics, visualisation, project storage and report export.

> SFW is an application built around existing AI models and scientific tools. It is not a newly trained foundation model, and it does not claim to reproduce Claude's proprietary source code, private datasets or internal architecture.

## 1. Features

- AI Science Assistant: connect a Gemini, Anthropic or OpenAI API key; offline research-planning guidance remains available without a key.
- Source-grounded answers: optionally search Crossref for publication records and available abstracts, instruct the AI to cite only those retrieved records, and append DOI links generated from the actual metadata.
- Research Project Planner: draft problem statements, aims, research questions, hypotheses, variables and method outlines.
- Research Methodology Engine: draft methodology plans and flag mismatches between study design, objective, outcome type, sample size, groups and repeated measurements; recommendations are guidance, not statistical validation.
- Literature Search: retrieve scholarly publication metadata from Crossref.
- Data Analysis Lab: import CSV/Excel, inspect missing values, calculate descriptive statistics, explore distributions and correlations, run linear regression and selected t-tests.
- Project Library: save and reopen plans locally.
- Report Builder: export project plans as DOCX or PDF.
- Multidisciplinary scope: biology, chemistry, physics, environmental science, agriculture, mathematics, engineering and biomedical science.
- Scientific integrity controls: distinguish plans from completed experiments; do not invent results or citations.

## 2. Requirements

- Windows 10/11, macOS or Linux
- Python 3.10 or newer (Python 3.11 recommended)
- Internet connection for package installation, Crossref search and external AI APIs
- An API key is optional; SFW's planning and data-analysis modules work without one

## 3. Windows installation

1. Extract the ZIP file.
2. Open the extracted `Science_Fair_Winner` folder.
3. Double-click `scripts/run_windows.bat`.
4. The script creates a virtual environment, installs dependencies and starts Streamlit.
5. Open the local URL shown in the terminal (usually `http://localhost:8501`).

If Windows blocks the script, open PowerShell in the project folder and run:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
streamlit run app.py
```

## 4. Linux installation

From the project directory:

```bash
chmod +x scripts/run_linux.sh
./scripts/run_linux.sh
```

If your Linux distribution does not have venv support, install its Python venv package first (for Ubuntu/Debian: `sudo apt install python3-venv`).

## 5. Optional AI configuration

Copy `.env.example` to `.env` and configure one provider.

### Google Gemini

```env
SFW_AI_PROVIDER=gemini
GEMINI_API_KEY=your_google_ai_studio_key
GEMINI_MODEL=gemini-3.5-flash-lite
```

Check Google AI Studio for current model availability, free-tier limits and data-handling terms.

### Anthropic

```env
SFW_AI_PROVIDER=anthropic
ANTHROPIC_API_KEY=your_api_key
ANTHROPIC_MODEL=claude-3-5-sonnet-latest
```

### OpenAI

```env
SFW_AI_PROVIDER=openai
OPENAI_API_KEY=your_api_key
OPENAI_MODEL=gpt-4.1-mini
```

Restart the app after changing `.env`. Keep `.env` private; never commit API keys to GitHub. API use may incur charges under the provider's terms.

## 6. Project structure

```text
Science_Fair_Winner/
├── app.py
├── requirements.txt
├── README.md
├── .env.example
├── scripts/
│   ├── run_windows.bat
│   └── run_linux.sh
├── sfw/
│   ├── assistant.py
│   ├── analysis.py
│   ├── config.py
│   ├── literature.py
│   ├── planner.py
│   ├── reporting.py
│   └── storage.py
├── data/
│   ├── knowledge/
│   │   └── disciplines.json
│   └── projects/
├── outputs/
├── assets/
│   └── SFW_Project_Poster.png
├── tests/
│   └── test_core.py
├── examples_hookes_law_illustrative.csv
└── reference_archives/
    ├── Science_Fair_Winner_Complete_original.zip
    └── SFW_Multidiscipline_Data_Kit_original.zip
```

The large poster image and original ZIP archives are not included in this GitHub source upload. They remain available in the separate complete build package.

## 7. Run tests

```bash
pip install -r requirements.txt
pytest -q
```

## 8. Data and scientific integrity

- Literature search returns Crossref metadata and may include abstracts when supplied by Crossref. The optional source-grounded AI mode uses those records, but does not retrieve or verify full-text papers. Follow DOI/publisher links and verify the full text, methods and publication status.
- AI-generated explanations can still contain errors. Retrieved citations establish that a Crossref record exists; they do not prove that every statement in an answer is supported by that paper.
- A statistically significant p-value is not proof of causation or practical importance.
- Select statistical tests based on the research design, sample structure and assumptions.
- Do not enter invented measurements as if they were observed data.
- Record units, instrument details, dates, replicates and missing-data decisions.
- Obtain supervision and required ethical/safety approval for experiments involving people, animals, pathogens, hazardous chemicals or other risks.
- Project files are stored locally in `data/projects/`. Back up this folder.

## 9. Current scope and next development stage

This is a functional first release, not a fully autonomous scientific discovery agent. It does not independently run laboratory experiments, guarantee factual correctness, retrieve all full-text papers or train its own foundation model. The next major development stage can add a permissioned document knowledge base with retrieval-augmented generation (RAG), citation verification, richer experimental-design tools, domain-specific datasets and role-based collaboration.

## 10. Cloudflare deployment\n\nThe repository includes a Cloudflare Workers + Containers deployment configuration for `https://sfw.wfw.co.ke`. It runs the Streamlit app in a Python container and uses Cloudflare R2 for persistent project storage. See [CLOUDFLARE_DEPLOY.md](CLOUDFLARE_DEPLOY.md) for the required Cloudflare account setup, R2 credentials, Workers Builds connection and verification steps. Cloudflare Containers require a Workers Paid plan; container usage and AI-provider usage may add charges.\n\n## 11. Troubleshooting

- **`streamlit` not found:** activate `.venv` and run `pip install -r requirements.txt`.
- **Python environment error:** use a virtual environment; do not install packages into an OS-managed Python environment.
- **Crossref search fails:** check internet access and retry later.
- **AI assistant falls back to offline guidance:** check `.env`, provider name, API key, model availability and provider billing/access.
- **Excel import fails:** ensure `openpyxl` installed and file is a valid `.xlsx` or `.xls`.

---

**Science Fair Winner (SFW)**  
Prepared for Lawrence Wainaina  
Build release 1.0.0

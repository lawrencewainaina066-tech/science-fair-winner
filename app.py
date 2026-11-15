import json
from pathlib import Path
import pandas as pd
import plotly.express as px
import streamlit as st

from sfw.config import APP_NAME, APP_TAGLINE, ROOT, PROJECT_DIR
from sfw.planner import build_research_plan, DISCIPLINES
from sfw.methodology import (build_methodology, DESIGN_OPTIONS, OBJECTIVES, OUTCOME_TYPES, SAMPLING_METHODS)
from sfw.analysis import (load_table, numeric_summary, correlation_matrix, independent_t_test,
                         paired_t_test, chi_square_test, linear_regression, interpret_p_value)
from sfw.literature import search_crossref, format_references, unmatched_citation_numbers
from sfw.assistant import ask_ai, local_guidance
from sfw.storage import save_project, list_projects, read_project
from sfw.reporting import build_docx, build_pdf

st.set_page_config(page_title=APP_NAME, page_icon="🔬", layout="wide")
st.title("🔬 Science Fair Winner (SFW)")
st.caption(APP_TAGLINE)

with st.sidebar:
    st.header("Workspace")
    page = st.radio("Open module", [
        "Home", "AI Science Assistant", "Research Project Planner", "Research Methodology Engine",
        "Literature Search", "Data Analysis Lab", "Project Library", "RTX GPU Server", "About & Settings"
    ])
    st.divider()
    st.caption("SFW v1.0.0 • Local-first scientific workspace")

if "chat" not in st.session_state:
    st.session_state.chat = []
if "active_project" not in st.session_state:
    st.session_state.active_project = None

if page == "Home":
    st.subheader("Your scientific investigation workspace")
    st.markdown("SFW helps turn scientific questions into structured investigations, analyse supplied data and prepare clear research documents.")
    cols = st.columns(3)
    cards = [
        ("🧠 AI Science Assistant", "Discuss research questions and scientific concepts."),
        ("🧪 Research Planner", "Draft aims, hypotheses, variables and methods."),
        ("📊 Data Analysis Lab", "Explore CSV/Excel data, statistics and charts."),
        ("📚 Literature Search", "Find scholarly publication metadata through Crossref."),
        ("🗂️ Project Library", "Save and reopen your project plans."),
        ("📄 Report Builder", "Export project plans as DOCX or PDF.")
    ]
    for i, (title, desc) in enumerate(cards):
        with cols[i % 3]:
            st.info(f"**{title}**\n\n{desc}")
    st.warning("SFW is a research-support tool. It does not independently validate experiments, guarantee scientific correctness or replace expert supervision.")

elif page == "AI Science Assistant":
    st.subheader("Scientific conversation")
    st.caption("Configure an AI provider under About & Settings for model-powered responses. Without a key, SFW provides an offline research framework.")
    use_crossref = st.checkbox(
        "Search Crossref and ground this answer in retrieved publication records",
        value=False,
        help="Searches publication metadata and any abstract supplied by Crossref. It does not retrieve or verify full-text papers.",
    )
    st.caption("Turn this on for a question when you want SFW to retrieve relevant publication records and attach their real DOI links.")
    for msg in st.session_state.chat:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
    prompt = st.chat_input("Ask a scientific question or describe a research problem...")
    if prompt:
        st.session_state.chat.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        with st.chat_message("assistant"):
            with st.spinner("Working through your question..."):
                sources = []
                if use_crossref:
                    try:
                        sources = search_crossref(prompt, rows=5)
                        if not sources:
                            st.info("Crossref returned no publication records for this query. The answer will not include a generated reference list.")
                    except Exception as e:
                        st.warning(f"Crossref search was unavailable: {e}. Continuing without retrieved sources.")
                try:
                    answer = ask_ai(st.session_state.chat, research_sources=sources)
                    if not answer:
                        answer = local_guidance(prompt)
                except Exception as e:
                    answer = f"AI provider request failed: {e}\n\nYou can check your API key, provider setting and internet connection. Offline guidance:\n\n{local_guidance(prompt)}"
                if sources:
                    unmatched = unmatched_citation_numbers(answer, sources)
                    if unmatched:
                        st.warning(
                            "The AI used citation number(s) not present in the retrieved Crossref records: "
                            + ", ".join(str(number) for number in unmatched)
                            + ". Treat those in-text citations as unverified."
                        )
                    answer += format_references(sources)
                st.markdown(answer)
        st.session_state.chat.append({"role": "assistant", "content": answer})
    if st.button("Clear conversation"):
        st.session_state.chat = []
        st.rerun()

elif page == "Research Project Planner":
    st.subheader("Build a research plan")
    with st.form("plan_form"):
        title = st.text_input("Project title", placeholder="e.g. Effect of compost tea on maize seedling growth")
        discipline = st.selectbox("Scientific discipline", DISCIPLINES)
        level = st.selectbox("Project level", ["School science fair", "College / university", "Independent research"])
        problem = st.text_area("Problem or research topic", height=100)
        constraints = st.text_area("Constraints, resources or location (optional)", height=70)
        submitted = st.form_submit_button("Generate research plan", type="primary")
    if submitted:
        plan = build_research_plan(title, problem, discipline, level, constraints)
        st.session_state.active_project = plan
    if st.session_state.active_project:
        p = st.session_state.active_project
        st.markdown(f"### {p['title']}")
        st.write(f"**Discipline:** {p['discipline']}  |  **Level:** {p['level']}")
        for key, label in [("problem_statement","Problem statement"),("aim","Aim"),("research_question","Research question"),("hypothesis","Draft hypothesis")]:
            st.markdown(f"**{label}**")
            st.write(p[key])
        st.markdown("**Variables**")
        st.json(p["variables"])
        st.markdown("**Proposed method outline**")
        for step in p["method_outline"]:
            st.write("• " + step)
        st.caption(p["integrity_note"])
        a, b, c = st.columns(3)
        with a:
            if st.button("Save project"):
                path = save_project(p["title"], p)
                st.success(f"Saved: {path.name}")
        with b:
            st.download_button("Download DOCX", build_docx(p), file_name="SFW_Research_Plan.docx")
        with c:
            st.download_button("Download PDF", build_pdf(p), file_name="SFW_Research_Plan.pdf")

elif page == "Research Methodology Engine":
    st.subheader("Design a defensible research methodology")
    st.write("Build a structured methodology outline from your research question and study choices. SFW explains the reasoning and flags issues that need supervisor or statistician review.")
    with st.form("methodology_form"):
        method_title = st.text_input("Project title", placeholder="e.g. Effect of compost tea on maize growth")
        research_question = st.text_area("Research question", placeholder="What effect does compost tea concentration have on maize seedling height over four weeks?")
        design = st.selectbox("Study design", DESIGN_OPTIONS)
        objective = st.selectbox("Main research objective", OBJECTIVES)
        independent_variable = st.text_input("Exposure, predictor or independent variable", placeholder="e.g. compost tea concentration")
        dependent_variable = st.text_input("Main outcome / dependent variable", placeholder="e.g. maize seedling height (cm)")
        outcome_type = st.selectbox("Type of main outcome", OUTCOME_TYPES)
        population = st.text_input("Target population or study material", placeholder="e.g. maize seedlings of variety X grown in pots")
        sampling_method = st.selectbox("Sampling / selection approach", SAMPLING_METHODS)
        m1, m2 = st.columns(2)
        with m1:
            planned_sample_size = st.number_input("Planned sample size (enter 0 if undecided)", min_value=0, max_value=1000000, value=0, step=1)
        with m2:
            groups = st.number_input("Number of groups / conditions", min_value=1, max_value=100, value=2, step=1)
        data_collection = st.text_area("How will data be collected?", placeholder="Describe instruments, measurement frequency and recording procedure.")
        duration = st.text_input("Study duration / measurement schedule", placeholder="e.g. 4 weeks; measure height every 7 days")
        constraints = st.text_area("Resources, location, safety or other constraints (optional)")
        method_submitted = st.form_submit_button("Generate methodology outline", type="primary")
    if method_submitted:
        try:
            st.session_state.methodology_plan = build_methodology(
                method_title, research_question, design, objective,
                independent_variable, dependent_variable, outcome_type,
                population, sampling_method,
                int(planned_sample_size) if planned_sample_size else None,
                int(groups), data_collection, duration, constraints,
            )
        except ValueError as e:
            st.error(str(e))
    if st.session_state.get("methodology_plan"):
        mp = st.session_state.methodology_plan
        st.markdown(f"### {mp['title']}")
        st.markdown("#### Research design")
        st.write(f"**Selected design:** {mp['design']}")
        st.write(mp["design_guidance"])
        st.markdown("#### Study framework")
        st.write(f"**Research question:** {mp['research_question']}")
        st.write(f"**Objective:** {mp['objective']}")
        st.write(f"**Target population / material:** {mp['population']}")
        st.write(f"**Independent / predictor variable:** {mp['independent_variable']}")
        st.write(f"**Dependent / outcome variable:** {mp['dependent_variable']} ({mp['outcome_type']})")
        st.write(f"**Sampling:** {mp['sampling_method']}")
        st.write(f"**Planned sample size:** {mp['planned_sample_size'] if mp['planned_sample_size'] else 'Not yet determined'}")
        st.write(f"**Groups / conditions:** {mp['groups']}")
        st.write(f"**Data collection:** {mp['data_collection']}")
        st.write(f"**Duration:** {mp['duration']}")
        st.markdown("#### Research design validation")
        validation = mp.get("validation", {})
        for finding in validation.get("findings", []):
            level = finding.get("level")
            message = f"**{finding.get('title', 'Review item')}**\n\n{finding.get('detail', '')}\n\n**Recommended action:** {finding.get('action', '')}"
            if level == "error":
                st.error(message)
            elif level == "warning":
                st.warning(message)
            elif level == "info":
                st.info(message)
            else:
                st.success(message)
        if validation.get("suggested_design") or validation.get("suggested_objective"):
            st.markdown("**Suggested corrections**")
            if validation.get("suggested_design"):
                st.write("Suggested study design: " + validation["suggested_design"])
            if validation.get("suggested_objective"):
                st.write("Suggested research objective: " + validation["suggested_objective"])
        st.markdown("#### Suggested analysis plan")
        for item in mp["analysis_plan"]:
            st.write("• " + item)
        if validation.get("suggested_analysis"):
            st.warning("Analysis adjustment: " + validation["suggested_analysis"])
        st.markdown("#### Methodology checklist")
        for step in mp["method_steps"]:
            st.write("• " + step)
        if mp["warnings"]:
            st.markdown("#### Items to resolve before starting")
            for warning in mp["warnings"]:
                st.warning(warning)
        st.info(mp["integrity_note"])
        export_text = (
            f"{mp['title']}\n\nResearch question\n{mp['research_question']}\n\n"
            f"Design\n{mp['design']}\n{mp['design_guidance']}\n\n"
            f"Population: {mp['population']}\nSampling: {mp['sampling_method']}\n"
            f"Planned sample size: {mp['planned_sample_size'] or 'Not yet determined'}\n"
            f"Groups/conditions: {mp['groups']}\nIndependent variable: {mp['independent_variable']}\n"
            f"Dependent variable: {mp['dependent_variable']} ({mp['outcome_type']})\n"
            f"Data collection: {mp['data_collection']}\nDuration: {mp['duration']}\n\n"
            "Design validation\n" + "\n".join(
                "- " + item["title"] + ": " + item["detail"] + " Recommended action: " + item["action"]
                for item in mp.get("validation", {}).get("findings", [])
            ) + "\n\n"
            + ("Analysis adjustment\n" + mp["validation"]["suggested_analysis"] + "\n\n"
               if mp.get("validation", {}).get("suggested_analysis") else "")
            + "Analysis plan\n" + "\n".join("- " + x for x in mp["analysis_plan"]) + "\n\n"
            "Methodology checklist\n" + "\n".join("- " + x for x in mp["method_steps"]) + "\n\n"
            "Items to resolve\n" + "\n".join("- " + x for x in mp["warnings"]) + "\n\n"
            + mp["integrity_note"]
        )
        st.download_button("Download methodology outline (.txt)", export_text, file_name="SFW_Methodology_Outline.txt", mime="text/plain")

elif page == "Literature Search":
    st.subheader("Scholarly literature discovery")
    st.write("Searches Crossref publication metadata. Check the publisher or repository record before relying on a paper.")
    query = st.text_input("Search topic or keywords", placeholder="e.g. biochar soil fertility maize yield")
    count = st.slider("Maximum records", 3, 20, 8)
    if st.button("Search publications", type="primary"):
        try:
            results = search_crossref(query, count)
            st.session_state.literature_results = results
        except Exception as e:
            st.error(f"Literature search failed: {e}")
    for item in st.session_state.get("literature_results", []):
        with st.container(border=True):
            st.markdown(f"**{item['title']}**")
            st.write(f"{item['authors']} • {item['year'] or 'Year not supplied'} • {item['journal']}")
            if item["doi"]:
                st.markdown(f"[DOI: {item['doi']}](https://doi.org/{item['doi']})")
            elif item["url"]:
                st.markdown(f"[Open record]({item['url']})")
            st.caption(f"Type: {item['type'] or 'Not supplied'}")

elif page == "Data Analysis Lab":
    st.subheader("Scientific data analysis")
    upload = st.file_uploader("Upload a CSV or Excel dataset", type=["csv", "xlsx", "xls"])
    if upload:
        try:
            df = load_table(upload)
            st.session_state.analysis_df = df
            st.markdown("#### Data preview")
            st.dataframe(df.head(100), use_container_width=True)
            st.markdown("#### Data quality")
            quality = pd.DataFrame({"missing_values": df.isna().sum(), "data_type": df.dtypes.astype(str)})
            st.dataframe(quality, use_container_width=True)
            summary = numeric_summary(df)
            if not summary.empty:
                st.markdown("#### Descriptive statistics")
                st.dataframe(summary, use_container_width=True)
                st.download_button("Download summary CSV", summary.to_csv().encode(), "SFW_descriptive_statistics.csv")
            numeric_cols = list(df.select_dtypes(include="number").columns)
            if numeric_cols:
                st.markdown("#### Visualise variables")
                y_col = st.selectbox("Variable to plot", numeric_cols)
                chart_type = st.selectbox("Chart type", ["Histogram", "Box plot", "Line chart"])
                if chart_type == "Histogram":
                    fig = px.histogram(df, x=y_col, title=f"Distribution of {y_col}")
                elif chart_type == "Box plot":
                    fig = px.box(df, y=y_col, title=f"Box plot of {y_col}")
                else:
                    fig = px.line(df, y=y_col, title=f"Sequence of {y_col}")
                st.plotly_chart(fig, use_container_width=True)
            if len(numeric_cols) >= 2:
                with st.expander("Correlation matrix"):
                    corr = correlation_matrix(df)
                    st.dataframe(corr, use_container_width=True)
                    st.plotly_chart(px.imshow(corr, text_auto=True, aspect="auto", title="Correlation matrix"), use_container_width=True)
                with st.expander("Linear regression"):
                    x = st.selectbox("Predictor (X)", numeric_cols, key="reg_x")
                    y = st.selectbox("Outcome (Y)", [c for c in numeric_cols if c != x], key="reg_y")
                    if st.button("Run linear regression"):
                        result = linear_regression(df, x, y)
                        st.write({k:v for k,v in result.items() if k not in ("data","x_label","y_label")})
                        st.plotly_chart(px.scatter(result["data"], x=x, y=y, trendline="ols", title=f"{y} versus {x}"), use_container_width=True)
            with st.expander("Statistical tests"):
                test = st.selectbox("Test", ["Welch independent t-test", "Paired t-test"])
                if test == "Welch independent t-test":
                    g1 = st.text_area("Group A values (comma-separated)", "12, 13, 11, 14")
                    g2 = st.text_area("Group B values (comma-separated)", "15, 16, 14, 17")
                    if st.button("Calculate Welch t-test"):
                        try:
                            result = independent_t_test(g1.split(","), g2.split(","))
                            st.json(result)
                            st.info(interpret_p_value(result["p_value"]))
                        except Exception as e: st.error(str(e))
                else:
                    before = st.text_area("Before values (comma-separated)", "10, 12, 11, 9")
                    after = st.text_area("After values (comma-separated)", "12, 13, 13, 11")
                    if st.button("Calculate paired t-test"):
                        try:
                            result = paired_t_test(before.split(","), after.split(","))
                            st.json(result)
                            st.info(interpret_p_value(result["p_value"]))
                        except Exception as e: st.error(str(e))
        except Exception as e:
            st.error(f"Could not read the dataset: {e}")
    else:
        st.info("Upload a dataset to begin. The sample Hooke's law dataset is available in the examples folder.")

elif page == "Project Library":
    st.subheader("Saved research projects")
    projects = list_projects()
    if not projects:
        st.info("No saved projects yet. Create one in Research Project Planner.")
    for path in projects:
        with st.expander(path.stem):
            try:
                p = read_project(path)
                st.write(p.get("problem_statement", ""))
                st.json(p)
                c1, c2 = st.columns(2)
                with c1:
                    st.download_button("Download DOCX", build_docx(p), file_name=f"{path.stem}.docx", key=f"docx_{path.stem}")
                with c2:
                    st.download_button("Download PDF", build_pdf(p), file_name=f"{path.stem}.pdf", key=f"pdf_{path.stem}")
            except Exception as e:
                st.error(f"Could not open project: {e}")

elif page == "RTX GPU Server":
    st.subheader("Remote RTX GPU server")
    st.write("Connect SFW to the remote media queue through a secure HTTPS endpoint. This page currently performs read-only checks; it does not submit or modify GPU jobs.")
    from sfw.config import _setting
    from sfw.rtx import check_rtx, list_images, RTXError

    default_url = _setting("SFW_RTX_BASE_URL")
    base_url = st.text_input(
        "RTX service URL",
        value=default_url,
        placeholder="https://rtx.wfw.co.ke",
        help="Use the HTTPS URL provided after the Cloudflare Tunnel is configured. Do not enter the private Tailscale IP here for Streamlit Cloud.",
    )
    api_token = st.text_input(
        "RTX API token (optional)",
        value=_setting("SFW_RTX_API_TOKEN"),
        type="password",
        help="Only enter a token if the RTX API administrator has configured Bearer-token authentication. Store it in Streamlit Secrets for deployment.",
    )
    if st.button("Test RTX connection", type="primary"):
        if not base_url.strip():
            st.warning("Enter the HTTPS RTX service URL first.")
        else:
            with st.spinner("Checking the queue and documented images endpoint..."):
                try:
                    report = check_rtx(base_url, api_token)
                    for check in report["checks"]:
                        if check["ok"]:
                            st.success(f"{check['name']}: HTTP {check['status']} — {check['detail']}")
                        else:
                            st.error(f"{check['name']}: {check['status'] or 'Connection failed'} — {check['detail']}")
                    if report["ok"]:
                        st.session_state.rtx_last_url = base_url.strip()
                except RTXError as exc:
                    st.error(str(exc))
    st.caption("The RTX server's documented read endpoints include / and /images. Job submission is not enabled until the server's submission endpoint and authentication requirements are confirmed.")
    if st.button("Load recent images"):
        if not base_url.strip():
            st.warning("Enter the HTTPS RTX service URL first.")
        else:
            try:
                images = list_images(base_url, api_token, owner="Lawrence", limit=20)
                st.json(images)
            except RTXError as exc:
                st.error(str(exc))
    st.info("Deployment secrets: SFW_RTX_BASE_URL = \"https://rtx.wfw.co.ke\" and, only if configured by the server administrator, SFW_RTX_API_TOKEN = \"your-token\". Never commit real tokens to GitHub.")

elif page == "About & Settings":
    st.subheader("About SFW")
    st.write("Science Fair Winner is a modular scientific research-support platform. It combines a conversational AI connection (optional), research planning, scholarly metadata search, data analysis and report generation.")
    st.markdown("#### Configure an AI provider")
    st.write("For Streamlit Community Cloud, add these values in Manage app → Settings → Secrets. For local development, place the same values in .streamlit/secrets.toml or a private .env file.")
    st.code('SFW_AI_PROVIDER = "gemini"\nGEMINI_API_KEY = "your_google_ai_studio_key"\nGEMINI_MODEL = "gemini-3.5-flash-lite"', language="toml")
    st.caption("Model availability, free-tier limits and data handling depend on Google’s current AI Studio terms and your account. Check those terms before sending research material. Never commit API keys to GitHub or share them in screenshots.")
    st.markdown("#### Data and privacy")
    st.write("Projects are saved locally under data/projects. Do not upload confidential, identifying or sensitive research data unless you have permission and understand the relevant provider's data handling.")
    st.markdown("#### Current limitations")
    st.write("- The AI assistant depends on an external API when enabled; SFW is not itself a trained foundation model.\n- Literature search retrieves Crossref metadata, not necessarily full-text papers.\n- Statistical results depend on data quality, study design and test assumptions.\n- Experimental safety and ethical approval remain the responsibility of the researcher and supervising institution.")
    st.markdown("#### Included original materials")
    st.write("The two source ZIP archives supplied in the earlier SFW work are preserved in reference_archives without modification.")

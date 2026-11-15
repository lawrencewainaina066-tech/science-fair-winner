import json
from pathlib import Path
import pandas as pd
import plotly.express as px
import streamlit as st

from sfw.config import APP_NAME, APP_TAGLINE, ROOT, PROJECT_DIR
from sfw.planner import build_research_plan, DISCIPLINES
from sfw.analysis import (load_table, numeric_summary, correlation_matrix, independent_t_test,
                         paired_t_test, chi_square_test, linear_regression, interpret_p_value)
from sfw.literature import search_crossref
from sfw.assistant import ask_ai, local_guidance
from sfw.storage import save_project, list_projects, read_project
from sfw.reporting import build_docx, build_pdf

st.set_page_config(page_title=APP_NAME, page_icon="🔬", layout="wide")
st.title("🔬 Science Fair Winner (SFW)")
st.caption(APP_TAGLINE)

with st.sidebar:
    st.header("Workspace")
    page = st.radio("Open module", [
        "Home", "AI Science Assistant", "Research Project Planner",
        "Literature Search", "Data Analysis Lab", "Project Library", "About & Settings"
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
                try:
                    answer = ask_ai(st.session_state.chat)
                    if not answer:
                        answer = local_guidance(prompt)
                except Exception as e:
                    answer = f"AI provider request failed: {e}\n\nYou can check your API key, provider setting and internet connection. Offline guidance:\n\n{local_guidance(prompt)}"
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

elif page == "About & Settings":
    st.subheader("About SFW")
    st.write("Science Fair Winner is a modular scientific research-support platform. It combines a conversational AI connection (optional), research planning, scholarly metadata search, data analysis and report generation.")
    st.markdown("#### Configure an AI provider")
    st.write("For Streamlit Community Cloud, add these values in Manage app → Settings → Secrets. For local development, place the same values in .streamlit/secrets.toml or a private .env file.")
    st.code('SFW_AI_PROVIDER = "gemini"\nGEMINI_API_KEY = "your_google_ai_studio_key"\nGEMINI_MODEL = "gemini-3.5-flash-lite"', language="toml")
    st.caption("Gemini 2.5 Flash-Lite has a free API tier with usage limits. Never commit API keys to GitHub or share them in screenshots. Free-tier requests may be used by Google to improve its products.")
    st.markdown("#### Data and privacy")
    st.write("Projects are saved locally under data/projects. Do not upload confidential, identifying or sensitive research data unless you have permission and understand the relevant provider's data handling.")
    st.markdown("#### Current limitations")
    st.write("- The AI assistant depends on an external API when enabled; SFW is not itself a trained foundation model.\n- Literature search retrieves Crossref metadata, not necessarily full-text papers.\n- Statistical results depend on data quality, study design and test assumptions.\n- Experimental safety and ethical approval remain the responsibility of the researcher and supervising institution.")
    st.markdown("#### Included original materials")
    st.write("The two source ZIP archives supplied in the earlier SFW work are preserved in reference_archives without modification.")

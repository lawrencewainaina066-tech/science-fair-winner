import json
from pathlib import Path
import pandas as pd
import plotly.express as px
import streamlit as st

from sfw.config import APP_NAME, APP_TAGLINE, ROOT, PROJECT_DIR, _setting
from sfw.planner import build_research_plan, DISCIPLINES
from sfw.methodology import (build_methodology, DESIGN_OPTIONS, OBJECTIVES, OUTCOME_TYPES, SAMPLING_METHODS)
from sfw.analysis import (load_table, numeric_summary, correlation_matrix, independent_t_test,
                         paired_t_test, chi_square_test, linear_regression, interpret_p_value)
from sfw.literature import search_crossref, format_references, unmatched_citation_numbers, doi_url
from sfw.assistant import ask_ai, local_guidance, ai_provider_status, build_science_prompt
from sfw.storage import save_project, list_projects, read_project
from sfw.reporting import build_docx, build_pdf

st.set_page_config(page_title=APP_NAME, page_icon="🔬", layout="wide")
st.title("🔬 Science Fair Winner (SFW)")
st.caption(APP_TAGLINE)
shared_project_library_enabled = _setting("SFW_ENABLE_SHARED_PROJECT_LIBRARY", "false").lower() in ("1", "true", "yes", "on")

with st.sidebar:
    st.header("Workspace")
    page = st.radio("Open module", [
        "Home", "AI Science Assistant", "Research Project Planner", "Research Methodology Engine",
        "Literature Search", "Data Analysis Lab", "Project Library", "Admin Dashboard", "RTX GPU Server", "About & Settings"
    ])
    st.divider()
    st.caption("SFW v1.2.0 • Scientific research workspace")
    if st.session_state.get("sfw_access_token"):
        st.caption(f"Signed in: {st.session_state.get('sfw_account_email', 'Account')}")
        if st.button("Sign out", key="sfw_global_signout", use_container_width=True):
            from sfw import cloud_storage
            token = st.session_state.get("sfw_access_token")
            try:
                cloud_storage.logout(token)
            except Exception:
                pass
            for key in ("sfw_access_token", "sfw_refresh_token", "sfw_account_email"):
                st.session_state.pop(key, None)
            st.rerun()

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
        ("🗂️ Project Library", "Optional project storage for trusted private workspaces."),
        ("📄 Report Builder", "Export project plans as DOCX or PDF.")
    ]
    for i, (title, desc) in enumerate(cards):
        with cols[i % 3]:
            st.info(f"**{title}**\n\n{desc}")
    st.warning("SFW is a research-support tool. It does not independently validate experiments, guarantee scientific correctness or replace expert supervision.")

elif page == "AI Science Assistant":
    st.subheader("Scientific conversation")
    st.caption("Ask questions, explore scientific concepts and develop research ideas. AI answers are assistance, not a substitute for checking primary evidence or expert review.")
    provider_status = ai_provider_status()
    with st.expander("AI connection & configuration", expanded=not provider_status["configured"]):
        st.write(f"**Provider:** {provider_status['provider']}")
        if provider_status["model"]:
            st.write(f"**Model:** {provider_status['model']}")
        if provider_status["configured"]:
            st.info(provider_status["message"])
            if st.button("Test AI connection", key="sfw_test_ai_connection"):
                with st.spinner("Sending a short test request to the selected provider..."):
                    try:
                        test_answer = ask_ai([{"role": "user", "content": "Reply with exactly: SFW connection test successful."}])
                        if test_answer:
                            st.success("AI connection successful.")
                            st.caption(test_answer[:300])
                        else:
                            st.warning("No AI provider response was returned. Check the selected provider and API key.")
                    except Exception as exc:
                        st.error(f"AI connection test failed: {exc}")
        else:
            st.warning(provider_status["message"])
            st.caption("Add the provider name and matching API key in Streamlit Cloud → Manage app → Settings → Secrets. Never paste an API key into this chat or commit it to GitHub.")
    selector_cols = st.columns(3)
    with selector_cols[0]:
        assistant_discipline = st.selectbox(
            "Scientific discipline",
            ["Interdisciplinary", "Biology", "Chemistry", "Physics", "Environmental science",
             "Agriculture", "Mathematics", "Engineering", "Health sciences"],
            key="sfw_assistant_discipline",
        )
    with selector_cols[1]:
        assistant_level = st.selectbox(
            "Explanation level",
            ["Secondary school", "Undergraduate", "Researcher"],
            index=1,
            key="sfw_assistant_level",
        )
    with selector_cols[2]:
        assistant_mode = st.selectbox(
            "Response mode",
            ["General scientific explanation", "Plan an experiment",
             "Interpret data or results", "Troubleshoot a scientific problem",
             "Critically review a research idea"],
            key="sfw_assistant_mode",
        )
    use_crossref = st.checkbox(
        "Search Crossref and ground this answer in retrieved publication records",
        value=False,
        help="Searches publication metadata and any abstract supplied by Crossref. It does not retrieve or verify full-text papers.",
    )
    st.caption("Turn this on for a question when you want SFW to retrieve relevant publication records and attach their real DOI links.")

    with st.expander("Scientific calculator & unit converter", expanded=False):
        from sfw.science_tools import calculate_expression, convert_units, CalculationError
        st.caption("Local calculations run without an AI API. Results are mathematical outputs, not a substitute for checking whether a formula or model fits your experiment.")
        calc_expr = st.text_input("Expression", placeholder="(12.5 * 3) / 2 or sqrt(81) + pi", key="sfw_calc_expr")
        if st.button("Calculate expression", key="sfw_calc_button"):
            try:
                calc_result = calculate_expression(calc_expr)
                st.success(f"{calc_result['expression']} = {calc_result['formatted']}")
            except CalculationError as exc:
                st.error(str(exc))
        st.markdown("**Metric and temperature conversion**")
        u1, u2, u3 = st.columns(3)
        with u1:
            unit_value = st.number_input("Value", value=1.0, key="sfw_unit_value")
        with u2:
            from_unit = st.selectbox("From", ["m", "cm", "mm", "km", "kg", "g", "mg", "L", "mL", "s", "min", "h", "C", "F", "K"], key="sfw_from_unit")
        with u3:
            to_unit = st.selectbox("To", ["m", "cm", "mm", "km", "kg", "g", "mg", "L", "mL", "s", "min", "h", "C", "F", "K"], index=1, key="sfw_to_unit")
        if st.button("Convert units", key="sfw_convert_button"):
            try:
                converted = convert_units(unit_value, from_unit, to_unit)
                st.success(f"{converted['value']:g} {from_unit} = {converted['result']:.10g} {to_unit}")
            except CalculationError as exc:
                st.error(str(exc))
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
                    contextual_prompt = build_science_prompt(
                        prompt, assistant_discipline, assistant_level, assistant_mode
                    )
                    messages_for_ai = st.session_state.chat[:-1] + [
                        {"role": "user", "content": contextual_prompt}
                    ]
                    answer = ask_ai(messages_for_ai, research_sources=sources)
                    if not answer:
                        answer = local_guidance(prompt, assistant_discipline)
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
    st.caption("Create an editable scientific proposal. The planner flags design mismatches and does not invent results or references.")
    with st.form("plan_form"):
        title = st.text_input("Project title", placeholder="e.g. Effects of compost tea concentrations on early maize growth")
        discipline = st.selectbox("Scientific discipline", DISCIPLINES)
        level = st.selectbox("Project level", ["School science fair", "College / university", "Independent research"])
        problem = st.text_area("Research problem or background", height=100,
                               placeholder="What problem motivates this investigation? What is not yet known?")
        c1, c2 = st.columns(2)
        with c1:
            location = st.text_input("Study location (optional)", placeholder="e.g. Rironi, Kipipiri, Nyandarua County")
            duration = st.text_input("Available study duration (optional)", placeholder="e.g. 4 weeks")
            intervention = st.text_input("Main factor or treatment (optional)", placeholder="e.g. compost tea concentration")
        with c2:
            primary_outcome = st.text_input("Primary outcome to measure (optional)", placeholder="e.g. maize seedling height in cm")
            constraints = st.text_area("Resources, conditions and constraints (optional)", height=115,
                                       placeholder="e.g. 12 seedlings, rain-fed, limited land, available equipment")
        submitted = st.form_submit_button("Generate research plan", type="primary")
    if submitted:
        plan = build_research_plan(title, problem, discipline, level, constraints,
                                   location=location, duration=duration,
                                   intervention=intervention, primary_outcome=primary_outcome)
        st.session_state.active_project = plan
    if st.session_state.active_project:
        p = st.session_state.active_project
        st.markdown(f"### {p['title']}")
        st.write(f"**Discipline:** {p['discipline']}  |  **Level:** {p['level']}")
        if p.get("warnings"):
            st.error("Review these design issues before starting")
            for warning in p["warnings"]:
                st.write("• " + warning)
        for key, label in [("problem_statement","Problem statement"),("aim","Aim"),("research_question","Research question"),("hypothesis","Null and alternative hypotheses")]:
            st.markdown(f"**{label}**")
            st.write(p[key])
        st.markdown("**Specific objectives**")
        for item in p.get("specific_objectives", []):
            st.write("• " + item)
        st.markdown("**Study design and treatment structure**")
        st.write(p.get("study_design", ""))
        for item in p.get("treatment_structure", []):
            st.write("• " + item)
        st.markdown("**Operational variables**")
        for key, value in p["variables"].items():
            st.markdown(f"**{key.title()}:** {value}")
        st.markdown("**Proposed method outline**")
        for i, step in enumerate(p["method_outline"], 1):
            st.write(f"{i}. {step}")
        st.markdown("**Scientific quality and safety checks**")
        for item in p.get("quality_checks", []):
            st.write("• " + item)
        if p.get("constraints"):
            st.markdown("**Study constraints and resources**")
            st.write(p["constraints"])
        st.caption(p["integrity_note"])
        a, b, c = st.columns(3)
        with a:
            cloud_ready = bool(_setting("SFW_SUPABASE_URL") and _setting("SFW_SUPABASE_ANON_KEY"))
            has_cloud_session = bool(st.session_state.get("sfw_access_token"))
            if cloud_ready:
                if st.button("Save to my private library", disabled=not has_cloud_session, key="sfw_save_private_project"):
                    try:
                        from sfw.cloud_storage import save_project as save_cloud_project
                        saved = save_cloud_project(st.session_state["sfw_access_token"], p["title"], p)
                        st.success(f"Saved privately: {saved.get('title', p['title'])}")
                    except Exception as exc:
                        st.error(str(exc))
                if not has_cloud_session:
                    st.caption("Sign in from Project Library to save this plan privately.")
            elif st.button("Save project", disabled=not shared_project_library_enabled):
                path = save_project(p["title"], p)
                st.success(f"Saved: {path.name}")
        if not cloud_ready and not shared_project_library_enabled:
            st.caption("Private cloud saving is not configured yet. Set up Supabase and sign in from Project Library, or download a copy.")
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
    query = st.text_input("Search topic or keywords", placeholder="e.g. nitrogen fertilizer maize yield")
    filter_cols = st.columns(3)
    with filter_cols[0]:
        start_year = st.number_input("From year", min_value=1900, max_value=2100, value=2020, step=1)
    with filter_cols[1]:
        end_year = st.number_input("To year", min_value=1900, max_value=2100, value=2026, step=1)
    with filter_cols[2]:
        count = st.slider("Maximum records", 3, 20, 10)
    option_cols = st.columns(2)
    with option_cols[0]:
        crop_filter = st.selectbox(
            "Crop relevance filter",
            ["Exact crop match only", "Related crops included", "All relevant agricultural studies"],
            index=1,
            help="Exact match keeps records naming the crop in the title or abstract. Related crops includes other major crops when a cereal is searched."
        )
    with option_cols[1]:
        sort_by = st.selectbox(
            "Sort results by",
            ["African relevance first", "Topic relevance"],
            index=0,
            help="African relevance first ranks geographic signals before topic score. Topic relevance ranks subject match first."
        )
    article_only = st.checkbox(
        "Research publication records only (exclude non-publication components)",
        value=True,
        help="Keeps journal articles, conference papers and book chapters; excludes non-publication components. Review articles may still appear as journal articles and should be screened by title and abstract."
    )
    include_preprints = st.checkbox(
        "Include preprints and working papers",
        value=False,
        help="Off by default: excludes Crossref records classified as posted-content. Journal article peer-review status is not independently verified."
    )
    st.caption("Geographic mentions in titles/abstracts are shown separately from author-affiliation or journal signals. Neither proves the study location. Topic scores are screening aids, not measures of study quality.")
    if st.button("Search publications", type="primary"):
        st.session_state.literature_results = []
        if not query.strip():
            st.warning("Enter a topic or keywords before searching.")
        elif start_year > end_year:
            st.warning("The start year must not be later than the end year.")
        else:
            try:
                results = search_crossref(
                    query, count, start_year=int(start_year), end_year=int(end_year),
                    africa_first=(sort_by == 'African relevance first'), article_only=article_only,
                    crop_filter=crop_filter, sort_by=sort_by,
                    include_preprints=include_preprints
                )
                st.session_state.literature_results = results
                if not results:
                    st.info("No records matched these filters. Try broader keywords, a wider date range or include other publication types.")
            except Exception as e:
                st.error(f"Literature search failed: {e}")
    results_to_show = st.session_state.get("literature_results", [])
    if results_to_show:
        st.caption(f"{len(results_to_show)} screened Crossref record(s). Missing metadata is shown as unavailable; no authors or abstracts are invented.")
    for item in results_to_show:
        with st.container(border=True):
            st.markdown(f"**{item['title']}**")
            st.write(f"{item['authors']} • {item['year'] or 'Year not supplied'} • {item['journal'] or 'Journal not supplied'}")
            if item["doi"]:
                st.write(f"DOI: {item['doi']}")
                st.markdown(f"[Open DOI record]({doi_url(item['doi'])})")
            elif item["url"]:
                st.markdown(f"[Open record]({item['url']})")
            st.caption(f"Publication category: {item.get('publication_category', item['type'] or 'Not supplied')}")
            st.caption(f"Topic relevance score: {item.get('topic_score', 0)} (higher scores indicate a closer metadata match, not scientific quality)")
            if item.get("year_discrepancy"):
                st.warning("Crossref contains differing publication-date fields for this record: " + ", ".join(str(y) for y in item.get("year_values", [])) + ". Verify the publication year on the publisher page.")
            study_matches = item.get("africa_study_text_matches", [])
            affiliation_matches = item.get("africa_affiliation_matches", [])
            if study_matches:
                st.success("African geographic mention in title/abstract: " + ", ".join(study_matches[:5]) + ". Verify the actual study setting in the full paper.")
            if affiliation_matches:
                st.caption("African author-affiliation/journal signal: " + ", ".join(affiliation_matches[:5]) + ". This is not evidence of where the study was conducted.")
            if not study_matches and not affiliation_matches and sort_by == "African relevance first":
                st.caption("No African geographic or affiliation signal found in the available metadata.")
            if item.get("type") == "posted-content":
                st.warning("Preprint / working paper: publication and peer-review status must be checked before citing as a peer-reviewed study.")
            abstract_text = str(item.get("abstract") or "").strip()
            if abstract_text:
                st.caption(f"Abstract available from Crossref ({len(abstract_text)} characters).")
                with st.expander("Read abstract", expanded=False):
                    st.text_area(
                        "Abstract text",
                        value=abstract_text,
                        height=min(320, max(120, 5 * (len(abstract_text) // 90 + 1))),
                        disabled=True,
                        key=f"literature_abstract_{item.get('doi') or item.get('title')}"
                    )
            else:
                st.caption("Abstract unavailable in Crossref metadata. This does not necessarily mean the publisher has no abstract.")

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
                st.caption("Enter your own observed values. SFW does not prefill fictional measurements. Check independence, sampling, distribution and test assumptions before interpreting results.")
                test = st.selectbox("Test", ["Welch independent t-test", "Paired t-test", "Chi-square test"])
                alpha = st.selectbox("Significance level (alpha)", [0.05, 0.01], format_func=lambda value: f"{value:g}")
                if test == "Welch independent t-test":
                    g1 = st.text_area("Group A values (comma-separated)", placeholder="e.g. 12, 13, 11, 14")
                    g2 = st.text_area("Group B values (comma-separated)", placeholder="e.g. 15, 16, 14, 17")
                    if st.button("Calculate Welch t-test"):
                        try:
                            result = independent_t_test(g1.split(","), g2.split(","), alpha=alpha)
                            st.json(result)
                            st.info(interpret_p_value(result["p_value"], alpha=alpha))
                            st.caption("The confidence interval is for mean(Group A) minus mean(Group B). Cohen's d is a standardised descriptive effect size.")
                        except Exception as e: st.error(str(e))
                elif test == "Paired t-test":
                    before = st.text_area("Before values (comma-separated)", placeholder="e.g. 10, 12, 11, 9")
                    after = st.text_area("After values (comma-separated)", placeholder="e.g. 12, 13, 13, 11")
                    if st.button("Calculate paired t-test"):
                        try:
                            result = paired_t_test(before.split(","), after.split(","), alpha=alpha)
                            st.json(result)
                            st.info(interpret_p_value(result["p_value"], alpha=alpha))
                            st.caption("The confidence interval is for mean(After − Before). Cohen's dz is a standardised paired-change effect size.")
                        except Exception as e: st.error(str(e))
                else:
                    contingency_text = st.text_area(
                        "Contingency table (comma-separated columns; semicolon-separated rows)",
                        placeholder="e.g. 12, 8; 5, 15",
                    )
                    if st.button("Calculate chi-square test"):
                        try:
                            rows = [[float(value.strip()) for value in row.split(",")]
                                    for row in contingency_text.strip().split(";") if row.strip()]
                            if not rows or len({len(row) for row in rows}) != 1 or len(rows) < 2 or len(rows[0]) < 2:
                                raise ValueError("Enter a rectangular table with at least two rows and two columns.")
                            result = chi_square_test(rows)
                            st.json(result)
                            st.info(interpret_p_value(result["p_value"], alpha=alpha))
                            if result["small_expected_frequency_warning"]:
                                st.warning("Some expected cell frequencies are below 5. The chi-square approximation may be unreliable; consider an exact or alternative method.")
                        except Exception as e: st.error(str(e))
        except Exception as e:
            st.error(f"Could not read the dataset: {e}")
    else:
        st.info("Upload a dataset to begin. The sample Hooke's law dataset is available in the examples folder.")

elif page == "Project Library":
    st.subheader("Private research project library")
    supabase_url = _setting("SFW_SUPABASE_URL")
    supabase_key = _setting("SFW_SUPABASE_ANON_KEY")
    if supabase_url and supabase_key:
        from sfw import cloud_storage

        access_token = st.session_state.get("sfw_access_token")
        if access_token:
            account_email = st.session_state.get("sfw_account_email", "Signed-in account")
            st.success(f"Signed in as {account_email}")
            try:
                projects = cloud_storage.list_projects(access_token)
                st.caption(f"{len(projects)} privately stored project(s). Access is restricted by Supabase row-level security.")
                if not projects:
                    st.info("Your private library is empty. Generate a plan and choose Save to my private library.")
                for item in projects:
                    project_id = item["id"]
                    title = item.get("title") or "Untitled project"
                    payload = item.get("payload") or {}
                    with st.expander(title):
                        st.write(payload.get("problem_statement", ""))
                        st.json(payload)
                        c1, c2, c3 = st.columns(3)
                        with c1:
                            st.download_button("Download DOCX", build_docx(payload), file_name="SFW_" + title[:80] + ".docx", key=f"cloud_docx_{project_id}")
                        with c2:
                            st.download_button("Download PDF", build_pdf(payload), file_name="SFW_" + title[:80] + ".pdf", key=f"cloud_pdf_{project_id}")
                        with c3:
                            if st.button("Delete project", key=f"cloud_delete_{project_id}"):
                                try:
                                    cloud_storage.delete_project(access_token, project_id)
                                    st.success("Project deleted.")
                                    st.rerun()
                                except Exception as exc:
                                    st.error(str(exc))
            except Exception as exc:
                st.error(str(exc))
                st.caption("If your session expired, sign out and sign in again.")
        else:
            st.write("Create an account or sign in to keep your research plans private and available across sessions.")
            sign_in_tab, sign_up_tab = st.tabs(["Sign in", "Create account"])
            with sign_in_tab:
                with st.form("sfw_signin_form"):
                    email = st.text_input("Email address", key="sfw_signin_email")
                    password = st.text_input("Password", type="password", key="sfw_signin_password")
                    submitted = st.form_submit_button("Sign in", type="primary")
                if submitted:
                    try:
                        session = cloud_storage.sign_in(email, password)
                        st.session_state["sfw_access_token"] = session["access_token"]
                        st.session_state["sfw_refresh_token"] = session.get("refresh_token")
                        st.session_state["sfw_account_email"] = email.strip()
                        try:
                            cloud_storage.log_auth_event(session["access_token"], "sign_in")
                        except Exception as audit_exc:
                            st.warning(f"Signed in, but login activity could not be recorded: {audit_exc}")
                        st.rerun()
                    except Exception as exc:
                        st.error(str(exc))
            with sign_up_tab:
                with st.form("sfw_signup_form"):
                    new_email = st.text_input("Email address", key="sfw_signup_email")
                    new_password = st.text_input("Password (at least 8 characters)", type="password", key="sfw_signup_password")
                    confirm_password = st.text_input("Confirm password", type="password", key="sfw_signup_confirm")
                    create_account = st.form_submit_button("Create account")
                if create_account:
                    if new_password != confirm_password:
                        st.error("The passwords do not match.")
                    elif len(new_password) < 8:
                        st.error("Use a password with at least 8 characters.")
                    else:
                        try:
                            result = cloud_storage.sign_up(new_email, new_password)
                            if isinstance(result, dict) and result.get("access_token"):
                                st.session_state["sfw_access_token"] = result["access_token"]
                                st.session_state["sfw_refresh_token"] = result.get("refresh_token")
                                st.session_state["sfw_account_email"] = new_email.strip()
                                try:
                                    cloud_storage.log_auth_event(result["access_token"], "sign_up")
                                except Exception as audit_exc:
                                    st.warning(f"Account created, but registration activity could not be recorded: {audit_exc}")
                                st.success("Account created and signed in.")
                                st.rerun()
                            st.success("Account created. Check your email for the confirmation link, then return here and sign in.")
                        except Exception as exc:
                            st.error(str(exc))
    else:
        st.warning("Private cloud storage is not configured. SFW will not expose a shared project library as a substitute.")
        st.info("Set up a Supabase project, run the SQL in supabase/schema.sql, then add SFW_SUPABASE_URL and SFW_SUPABASE_ANON_KEY to Streamlit Secrets.")
        if shared_project_library_enabled:
            st.warning("Legacy shared-library mode is enabled. Everyone with app access may see those projects.")
            projects = list_projects()
            if not projects:
                st.info("No saved projects yet.")
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
                    except Exception as exc:
                        st.error(f"Could not open project: {exc}")

elif page == "Admin Dashboard":
    st.subheader("Platform activity")
    st.caption("Private sign-in and registration audit. Only accounts explicitly assigned the Supabase admin role can view all users' activity.")
    access_token = st.session_state.get("sfw_access_token")
    if not access_token:
        st.info("Sign in through Project Library first, then return to this page.")
    else:
        try:
            from sfw import cloud_storage
            if not cloud_storage.is_admin(access_token):
                st.error("Administrator access is required. Ask the project owner to assign your account the admin role in Supabase.")
            else:
                events = cloud_storage.list_login_events(access_token, limit=500)
                event_df = pd.DataFrame(events)
                if event_df.empty:
                    st.info("No login events have been recorded yet. New successful sign-ins and registrations will appear here after the audit SQL migration is installed.")
                else:
                    event_df["created_at"] = pd.to_datetime(event_df["created_at"], utc=True, errors="coerce")
                    signins = int((event_df["event_type"] == "sign_in").sum())
                    registrations = int((event_df["event_type"] == "sign_up").sum())
                    unique_users = int(event_df["email"].nunique())
                    metric_cols = st.columns(3)
                    metric_cols[0].metric("Recorded sign-ins", signins)
                    metric_cols[1].metric("Registered accounts", registrations)
                    metric_cols[2].metric("Unique accounts", unique_users)
                    st.markdown("#### Recent account activity")
                    st.dataframe(
                        event_df.rename(columns={
                            "email": "Account email",
                            "event_type": "Activity",
                            "created_at": "Time (UTC)",
                        })[["Account email", "Activity", "Time (UTC)"]],
                        use_container_width=True,
                        hide_index=True,
                    )
                    st.download_button(
                        "Download activity CSV",
                        event_df.to_csv(index=False).encode("utf-8"),
                        file_name="SFW_login_activity.csv",
                        mime="text/csv",
                    )
        except Exception as exc:
            st.error(f"Could not load the private activity log: {exc}")
            st.caption("Confirm that supabase/login_audit.sql has been run in the Supabase SQL Editor.")

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
    api_token = _setting("SFW_RTX_API_TOKEN")
    access_client_id = _setting("SFW_RTX_ACCESS_CLIENT_ID")
    access_client_secret = _setting("SFW_RTX_ACCESS_CLIENT_SECRET")
    st.caption("RTX authentication is read from Streamlit Secrets. Cloudflare Access service tokens use a client ID and client secret; an optional backend Bearer token is supported separately.")
    if st.button("Test RTX connection", type="primary"):
        if not base_url.strip():
            st.warning("Enter the HTTPS RTX service URL first.")
        else:
            with st.spinner("Checking the queue and documented images endpoint..."):
                try:
                    report = check_rtx(base_url, api_token, access_client_id=access_client_id, access_client_secret=access_client_secret)
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
                images = list_images(base_url, api_token, owner="Lawrence", limit=20, access_client_id=access_client_id, access_client_secret=access_client_secret)
                st.json(images)
            except RTXError as exc:
                st.error(str(exc))
    st.info("Deployment secrets: SFW_RTX_BASE_URL = \"https://rtx.wfw.co.ke\". For Cloudflare Access, set SFW_RTX_ACCESS_CLIENT_ID and SFW_RTX_ACCESS_CLIENT_SECRET. Set SFW_RTX_API_TOKEN only if the backend also requires Bearer authentication. Never commit real secrets to GitHub.")

elif page == "About & Settings":
    st.subheader("About SFW")
    st.write("Science Fair Winner is a modular scientific research-support platform. It combines a conversational AI connection (optional), research planning, scholarly metadata search, data analysis and report generation.")
    st.markdown("#### Private project storage and activity monitoring")
    st.write("SFW supports Supabase email/password accounts with per-user database access policies. Run supabase/schema.sql and supabase/login_audit.sql in your Supabase SQL Editor, then add the project URL and anon/public key to Streamlit Secrets. Never use the service_role key in this app.")
    st.write("To enable the Admin Dashboard, assign the admin role to your account in Supabase Auth user metadata. The audit log records successful sign-ins and registrations after the migration is installed; it does not backfill earlier activity or record failed password attempts.")
    st.code('SFW_SUPABASE_URL = "https://your-project.supabase.co"\\nSFW_SUPABASE_ANON_KEY = "your_supabase_anon_key"', language="toml")
    st.markdown("#### Configure an AI provider")
    st.write("For Streamlit Community Cloud, add these values in Manage app → Settings → Secrets. For local development, place the same values in .streamlit/secrets.toml or a private .env file.")
    provider_tabs = st.tabs(["Google Gemini", "Anthropic", "OpenAI"])
    with provider_tabs[0]:
        st.code('SFW_AI_PROVIDER = "gemini"\nGEMINI_API_KEY = "your_google_ai_studio_key"\nGEMINI_MODEL = "gemini-3.5-flash-lite"', language="toml")
        st.caption("Create and manage a key through Google AI Studio. Confirm the selected model is available to your account.")
    with provider_tabs[1]:
        st.code('SFW_AI_PROVIDER = "anthropic"\nANTHROPIC_API_KEY = "your_anthropic_api_key"\nANTHROPIC_MODEL = "claude-sonnet-5-5"', language="toml")
        st.caption("Use an API key from the Anthropic Console and a model enabled for your account.")
    with provider_tabs[2]:
        st.code('SFW_AI_PROVIDER = "openai"\nOPENAI_API_KEY = "your_openai_api_key"\nOPENAI_MODEL = "gpt-6-luna"', language="toml")
        st.caption("Use an API key from the OpenAI platform and a model enabled for your account.")
    st.caption("Add only one provider configuration to Streamlit Secrets. Model availability, pricing, quotas and data handling depend on the provider and your account. The assistant's Test AI connection button sends a short API request that may consume quota. Never commit API keys to GitHub or share them in screenshots.")
    st.markdown("#### Data and privacy")
    st.write("Projects are saved locally under data/projects. Do not upload confidential, identifying or sensitive research data unless you have permission and understand the relevant provider's data handling.")
    st.warning("Hosted-storage and privacy notice: Streamlit Cloud's local filesystem is not durable storage. Shared Project Library saving is disabled by default because there are no user accounts or private per-user workspaces. Keep backups; persistent cloud storage and authentication are not yet configured.")
    st.markdown("#### Configure the remote RTX service")
    st.write("Add SFW_RTX_BASE_URL in Streamlit Secrets using your public HTTPS tunnel hostname. If Cloudflare Access protects the tunnel, add SFW_RTX_ACCESS_CLIENT_ID and SFW_RTX_ACCESS_CLIENT_SECRET as a service token. Add SFW_RTX_API_TOKEN only if the backend separately requires Bearer authentication. The connector is read-only and blocks local/private network destinations.")
    st.markdown("#### Current limitations")
    st.write("- The AI assistant depends on an external API when enabled; SFW is not itself a trained foundation model.\n- Literature search retrieves Crossref metadata, not necessarily full-text papers.\n- Statistical results depend on data quality, study design and test assumptions.\n- Experimental safety and ethical approval remain the responsibility of the researcher and supervising institution.")
    st.markdown("#### Included original materials")
    st.write("The two source ZIP archives supplied in the earlier SFW work are preserved in reference_archives without modification.")

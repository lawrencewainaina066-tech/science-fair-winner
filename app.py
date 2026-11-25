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
st.markdown("""
<style>
:root { --sfw-navy:#101D35; --sfw-blue:#315CEB; --sfw-teal:#0F8B82; --sfw-ink:#15233B; --sfw-line:#E1E8F0; }
.stApp { background:#F4F7FB; color:var(--sfw-ink); }
.block-container { max-width:1320px; padding-top:1.6rem; padding-bottom:3.5rem; }
[data-testid="stHeader"] { background:rgba(244,247,251,.88); }
[data-testid="stSidebar"] { background:linear-gradient(180deg,#101D35 0%,#172B4D 58%,#1D3A57 100%); border-right:1px solid rgba(255,255,255,.1); }
[data-testid="stSidebar"] * { color:#F8FAFC; }
[data-testid="stSidebar"] [data-testid="stRadio"] label { padding:.62rem .72rem; border-radius:11px; margin:.18rem 0; background:rgba(255,255,255,.055); }
[data-testid="stSidebar"] [data-testid="stRadio"] label:hover { background:rgba(255,255,255,.15); }
[data-testid="stSidebar"] hr { border-color:rgba(255,255,255,.18); }
h1,h2,h3 { color:#152744; letter-spacing:-.025em; }
.sfw-hero { overflow:hidden; padding:clamp(2rem,4vw,3.4rem); border:1px solid #243F68; border-radius:26px; background:radial-gradient(circle at 88% 12%,rgba(33,177,164,.28),transparent 28%),linear-gradient(118deg,#101D35 0%,#18365B 65%,#145A63 100%); margin:.4rem 0 1.65rem; color:#FFF; box-shadow:0 18px 46px rgba(16,29,53,.17); }
.sfw-eyebrow { display:inline-block; padding:.36rem .68rem; margin-bottom:1.05rem; border:1px solid rgba(255,255,255,.28); border-radius:999px; color:#D8F7F2; font-size:.75rem; font-weight:750; letter-spacing:.12em; background:rgba(255,255,255,.07); }
.sfw-hero h2 { color:#FFF!important; max-width:820px; font-size:clamp(2rem,4.3vw,3.35rem); line-height:1.08; font-weight:850; letter-spacing:-.045em; margin:0 0 1rem; }
.sfw-hero p { color:#EAF1FA!important; max-width:760px; font-size:1.08rem; line-height:1.75; margin:0; opacity:1!important; }
.sfw-hero-foot { display:flex; flex-wrap:wrap; gap:.65rem; margin-top:1.5rem; }
.sfw-chip { color:#F8FAFC; font-size:.82rem; font-weight:650; padding:.48rem .72rem; border-radius:9px; background:rgba(255,255,255,.1); border:1px solid rgba(255,255,255,.16); }
.sfw-section-kicker { color:#0F766E; font-size:.72rem; font-weight:800; letter-spacing:.13em; margin-bottom:.25rem; }
.sfw-step { padding:1.3rem; border:1px solid var(--sfw-line); border-radius:18px; min-height:158px; background:#FFF; color:var(--sfw-ink); box-shadow:0 7px 22px rgba(24,45,78,.055); }
.sfw-step b { display:block; color:#142744!important; font-size:1.06rem; margin:.48rem 0 .3rem; }
.sfw-muted { color:#52627A!important; font-size:.94rem; line-height:1.6; opacity:1!important; }
.sfw-step-icon { display:inline-flex; align-items:center; justify-content:center; width:2.5rem; height:2.5rem; border-radius:12px; background:#EDF3FF; font-size:1.25rem; }
[data-testid="stMetric"] { background:#FFF; border:1px solid var(--sfw-line); padding:15px 17px; border-radius:15px; box-shadow:0 5px 16px rgba(24,45,78,.04); }
.stButton>button,.stDownloadButton>button,.stFormSubmitButton>button { border-radius:11px; min-height:2.65rem; font-weight:700; background-color:#FFFFFF !important; color:#0F766E !important; border:1px solid #0F766E !important; }
.stButton>button[kind="primary"],.stFormSubmitButton>button[kind="primary"] { background:#315CEB !important; color:#FFFFFF !important; border:1px solid #315CEB !important; }
.stButton>button:disabled,.stDownloadButton>button:disabled { background-color:#F1F5F9 !important; color:#64748B !important; border-color:#CBD5E1 !important; }
.stButton>button:hover,.stDownloadButton>button:hover { border-color:#0F8B82; color:#0F766E; }
div[data-testid="stExpander"],div[data-testid="stAlert"] { border-radius:13px; }
[data-testid="stDataFrame"] { border:1px solid #D5DFEA; border-radius:13px; overflow:hidden; }
input,textarea,[data-baseweb="select"]>div { border-radius:10px!important; }
hr { border-color:#E1E8F0; }
@media(max-width:700px) { .block-container{padding-top:1rem}.sfw-hero{border-radius:19px;padding:1.55rem} }
</style>
""", unsafe_allow_html=True)

shared_project_library_enabled = _setting("SFW_ENABLE_SHARED_PROJECT_LIBRARY", "false").lower() in ("1", "true", "yes", "on")

if "sfw_page" not in st.session_state:
    st.session_state["sfw_page"] = "Home"
if "sfw_navigation_target" in st.session_state:
    st.session_state["sfw_page"] = st.session_state.pop("sfw_navigation_target")

# Keep owner-only tools out of the public navigation. The Admin Dashboard is
# shown only after Supabase confirms the signed-in user's admin role.
is_platform_admin = False
access_token_for_navigation = st.session_state.get("sfw_access_token")
if access_token_for_navigation:
    try:
        from sfw import cloud_storage
        is_platform_admin = cloud_storage.is_admin(access_token_for_navigation)
    except Exception:
        is_platform_admin = False

workspace_pages = [
    "Home", "AI Science Assistant", "Research Project Planner", "Research Methodology Engine",
    "Literature Search", "Data Analysis Lab", "Project Library", "Subscription & Billing", "About & Settings"
]
if is_platform_admin:
    workspace_pages.insert(-1, "Admin Dashboard")

# A stale or manually modified page value must not expose a hidden workspace.
if st.session_state.get("sfw_page") not in workspace_pages:
    st.session_state["sfw_page"] = "Home"

with st.sidebar:
    st.markdown("### 🔬 SFW Workspace")
    st.caption("Your research, one step at a time")
    page = st.radio("Choose a workspace", workspace_pages, key="sfw_page")
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
if "sfw_session_projects" not in st.session_state:
    st.session_state["sfw_session_projects"] = []

if page == "Home":
    st.markdown(
        '<section class="sfw-hero">'
        '<div class="sfw-eyebrow">SCIENCE FAIR WINNER · RESEARCH WORKSPACE</div>'
        '<h2>From a curious question to credible scientific work.</h2>'
        '<p>Design stronger investigations, explore scholarly evidence, analyse your own data and turn your work into a clear research report — all in one focused workspace.</p>'
        '<div class="sfw-hero-foot"><span class="sfw-chip">Research planning</span>'
        '<span class="sfw-chip">Evidence discovery</span><span class="sfw-chip">Data analysis</span>'
        '<span class="sfw-chip">Report creation</span></div></section>',
        unsafe_allow_html=True,
    )
    st.markdown('<div class="sfw-section-kicker">YOUR RESEARCH JOURNEY</div>', unsafe_allow_html=True)
    st.markdown("### Choose where to begin")
    start_cols = st.columns(3)
    quick_starts = [
        ("🧠", "Explore an idea", "Ask a science question or refine a topic.", "AI Science Assistant"),
        ("🧪", "Plan a project", "Create a research question, objectives and study plan.", "Research Project Planner"),
        ("📊", "Analyse data", "Upload a CSV or Excel file and explore results.", "Data Analysis Lab"),
    ]
    for col, (emoji, title, desc, target) in zip(start_cols, quick_starts):
        with col:
            st.markdown(f'<div class="sfw-step"><div style="font-size:1.6rem">{emoji}</div><b>{title}</b><p class="sfw-muted">{desc}</p></div>', unsafe_allow_html=True)
            if st.button(f"Open {title} →", key=f"home_{target}", use_container_width=True):
                st.session_state["sfw_navigation_target"] = target
                st.rerun()
    st.markdown("### More tools")
    tool_cols = st.columns(3)
    tools = [
        ("📚 Literature Search", "Find scholarly publication records and DOI links.", "Literature Search"),
        ("🧭 Methodology Engine", "Turn your research question into a study method.", "Research Methodology Engine"),
        ("🗂️ Project Library", "Save and download research plans during your current session.", "Project Library"),
        ("📄 Report downloads", "Export research plans as Word or PDF from the planner.", "Research Project Planner"),
        ("🛠️ Settings & help", "Check AI setup, privacy notes and service connections.", "About & Settings"),
        ("💳 Plans & billing", "Review SFW plans and manage your M-Pesa subscription.", "Subscription & Billing"),
    ]
    for i, (title, desc, target) in enumerate(tools):
        with tool_cols[i % 3]:
            st.markdown(f"**{title}**  \\n{desc}")
            if st.button("Open", key=f"home_tool_{i}", use_container_width=True):
                st.session_state["sfw_navigation_target"] = target
                st.rerun()
    with st.expander("Important research and privacy note"):
        st.write("SFW supports research planning and analysis. It does not independently validate experiments or replace expert supervision. Use verified evidence, follow safety and ethics requirements, and avoid uploading confidential data unless you have permission.")

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
            if st.button("Save to this session", key="sfw_save_session_project"):
                st.session_state["sfw_session_projects"].append(p.copy())
                st.success("Saved in this browser session. Download a copy to keep it permanently.")
        with b:
            st.download_button("Download DOCX", build_docx(p), file_name="SFW_Research_Plan.docx")
        with c:
            st.download_button("Download PDF", build_pdf(p), file_name="SFW_Research_Plan.docx".replace(".docx", ".pdf"))
        st.caption("No account is needed. Session-saved projects are temporary and may disappear when the session ends; download a copy for permanent storage.")

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
    st.subheader("Your session project library")
    st.write("No account or sign-in is required. Projects saved here are available only during this active browser session.")
    projects = st.session_state.get("sfw_session_projects", [])
    if not projects:
        st.info("Your session library is empty. Generate a research plan and choose Save to this session.")
    for index, payload in enumerate(projects):
        title = payload.get("title") or "Untitled project"
        with st.expander(title):
            st.write(payload.get("problem_statement", ""))
            c1, c2, c3 = st.columns(3)
            with c1:
                st.download_button("Download DOCX", build_docx(payload), file_name="SFW_" + title[:80] + ".docx", key=f"session_docx_{index}")
            with c2:
                st.download_button("Download PDF", build_pdf(payload), file_name="SFW_" + title[:80] + ".pdf", key=f"session_pdf_{index}")
            with c3:
                if st.button("Remove", key=f"session_remove_{index}"):
                    st.session_state["sfw_session_projects"].pop(index)
                    st.rerun()
    if projects and st.button("Clear session library"):
        st.session_state["sfw_session_projects"] = []
        st.rerun()

elif page == "Subscription & Billing":
    from sfw import cloud_storage
    from sfw.subscriptions import list_plans, format_price

    st.subheader("SFW plans and subscriptions")
    st.write("The public SFW research workspace remains free to explore without an account. An account is needed only to purchase a paid plan and view its billing history.")
    st.caption("All prices are in Kenyan shillings (KES). Monthly plans are billed manually through M-Pesa STK Push; automatic renewals are not enabled.")

    try:
        plans = cloud_storage.list_subscription_plans()
        if not plans:
            plans = list_plans()
    except Exception:
        plans = list_plans()
        st.info("Showing the published plan catalogue. Connect and migrate Supabase to enable account billing.")

    plan_columns = st.columns(len(plans))
    for column, plan in zip(plan_columns, plans):
        with column:
            st.markdown(f"### {plan['name']}")
            st.markdown(f"**{format_price(plan)}**")
            st.caption(plan.get("description", ""))
            if plan["code"] == "free":
                st.success("Open access")
            elif plan["code"] == "institution":
                st.info("Contact SFW for a quotation")
            else:
                st.caption("M-Pesa payment available after account sign-in.")

    st.divider()
    access_token = st.session_state.get("sfw_access_token")
    if not access_token:
        st.markdown("#### Your SFW account")
        auth_mode = st.radio(
            "Account action",
            ["Sign in", "Create account"],
            horizontal=True,
            key="sfw_billing_auth_mode",
        )
        with st.form("sfw_billing_auth_form"):
            account_email = st.text_input("Email address", key="sfw_billing_email")
            account_password = st.text_input("Password", type="password", key="sfw_billing_password")
            auth_submitted = st.form_submit_button(
                "Sign in" if auth_mode == "Sign in" else "Create account",
                type="primary",
            )
        if auth_submitted:
            try:
                if auth_mode == "Sign in":
                    account_session = cloud_storage.sign_in(account_email, account_password)
                    account_token = account_session["access_token"]
                    st.session_state["sfw_access_token"] = account_token
                    st.session_state["sfw_refresh_token"] = account_session.get("refresh_token")
                    st.session_state["sfw_account_email"] = account_email.strip()
                    try:
                        cloud_storage.log_auth_event(account_token, "sign_in")
                    except Exception:
                        pass
                    st.success("Signed in successfully.")
                    st.rerun()
                else:
                    if len(account_password) < 8:
                        st.error("Use a password with at least 8 characters.")
                    else:
                        signup_result = cloud_storage.sign_up(account_email, account_password)
                        signup_session = (
                            (signup_result.get("session") or signup_result)
                            if isinstance(signup_result, dict) else {}
                        )
                        signup_token = signup_session.get("access_token")
                        if signup_token:
                            st.session_state["sfw_access_token"] = signup_token
                            st.session_state["sfw_refresh_token"] = signup_session.get("refresh_token")
                            st.session_state["sfw_account_email"] = account_email.strip()
                            try:
                                cloud_storage.log_auth_event(signup_token, "sign_up")
                            except Exception:
                                pass
                            st.success("Account created and signed in.")
                            st.rerun()
                        else:
                            st.success("Account registration submitted. Check your email for a verification link, then sign in here.")
            except Exception as exc:
                st.error(f"Account request failed: {exc}")
        st.caption("Registration is optional. You can continue using the public research tools without signing in.")
    else:
        st.success(f"Signed in as {st.session_state.get('sfw_account_email', 'your SFW account')}.")
        paid_plans = [
            plan for plan in plans
            if plan.get("billing_interval") == "month"
            and isinstance(plan.get("amount_kes"), (int, float))
            and plan.get("amount_kes", 0) > 0
        ]
        if paid_plans:
            st.markdown("#### Start a monthly subscription")
            plan_labels = {
                plan["code"]: f"{plan['name']} — {format_price(plan)}"
                for plan in paid_plans
            }
            with st.form("sfw_mpesa_checkout_form"):
                selected_plan = st.selectbox(
                    "Choose a plan",
                    options=list(plan_labels),
                    format_func=lambda code: plan_labels[code],
                )
                mpesa_phone = st.text_input(
                    "Safaricom M-Pesa number",
                    placeholder="0712345678",
                    help="Use a Kenyan Safaricom mobile number that can receive an STK prompt.",
                )
                payment_submitted = st.form_submit_button("Send M-Pesa payment prompt", type="primary")
            if payment_submitted:
                try:
                    payment = cloud_storage.start_mpesa_payment(
                        access_token, selected_plan, mpesa_phone
                    )
                    st.success(payment.get("message", "M-Pesa prompt sent."))
                    st.caption(f"Plan: {payment.get('plan_name')} · Amount: KES {payment.get('amount_kes'):,}")
                    st.info("Complete the prompt on your phone. Your subscription activates only after SFW verifies the Daraja callback.")
                except Exception as exc:
                    st.error(f"Could not start M-Pesa payment: {exc}")

        st.markdown("#### Your subscription history")
        try:
            subscriptions = cloud_storage.list_my_subscriptions(access_token)
            if subscriptions:
                st.dataframe(pd.DataFrame(subscriptions), use_container_width=True, hide_index=True)
            else:
                st.info("No subscription history is recorded for this account yet.")
        except Exception as exc:
            st.warning(f"Subscription history is unavailable until the billing database migration is installed: {exc}")

        st.markdown("#### Your payment history")
        try:
            payments = cloud_storage.list_my_payments(access_token)
            if payments:
                st.dataframe(pd.DataFrame(payments), use_container_width=True, hide_index=True)
            else:
                st.info("No M-Pesa transactions are recorded for this account yet.")
        except Exception as exc:
            st.warning(f"Payment history is unavailable until the billing database migration is installed: {exc}")

    st.caption("Current rollout: SFW records plans, payment transactions and subscription status. Feature-specific premium limits and automatic renewals are not yet enabled; paid access must not be advertised as active until those rules are implemented and tested.")

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

                st.markdown("#### Subscription and revenue overview")
                try:
                    all_subscriptions = cloud_storage.list_all_subscriptions(access_token, limit=1000)
                    all_payments = cloud_storage.list_all_payments(access_token, limit=1000)
                    subscription_df = pd.DataFrame(all_subscriptions)
                    payment_df = pd.DataFrame(all_payments)

                    active_subscriptions = 0
                    if not subscription_df.empty:
                        ends = pd.to_datetime(subscription_df["ends_at"], utc=True, errors="coerce")
                        active_subscriptions = int(
                            ((subscription_df["status"] == "active") & (ends > pd.Timestamp.now(tz="UTC"))).sum()
                        )

                    successful_payments = payment_df[payment_df["status"] == "success"] if not payment_df.empty else pd.DataFrame()
                    confirmed_revenue = int(successful_payments["amount_kes"].sum()) if not successful_payments.empty else 0
                    pending_payments = int((payment_df["status"] == "pending").sum()) if not payment_df.empty else 0
                    billing_cols = st.columns(4)
                    billing_cols[0].metric("Subscription records", len(subscription_df))
                    billing_cols[1].metric("Currently active", active_subscriptions)
                    billing_cols[2].metric("Confirmed revenue", f"KES {confirmed_revenue:,}")
                    billing_cols[3].metric("Pending payments", pending_payments)
                    st.caption("Revenue and transaction totals are calculated from the latest 1,000 payment records loaded.")

                    if not payment_df.empty:
                        st.markdown("##### Recent payment transactions")
                        display_payments = payment_df.copy()
                        display_payments["phone_number"] = display_payments["phone_number"].fillna("").astype(str).map(
                            lambda value: f"••••{value[-4:]}" if value else ""
                        )
                        st.dataframe(
                            display_payments.drop(columns=["user_id", "subscription_id", "id"], errors="ignore"),
                            use_container_width=True,
                            hide_index=True,
                        )
                        st.download_button(
                            "Download payment report CSV",
                            payment_df.drop(columns=["phone_number"], errors="ignore").to_csv(index=False).encode("utf-8"),
                            file_name="SFW_payment_report.csv",
                            mime="text/csv",
                        )
                    else:
                        st.info("No payment transactions have been recorded yet.")
                except Exception as billing_exc:
                    st.warning(f"Billing analytics are unavailable until the subscription migrations are installed: {billing_exc}")
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
    st.markdown("#### Public access")
    st.success("SFW is open to ordinary users. No account or sign-in is required to use the research tools, save projects during the current session, or download reports.")
    st.caption("Session-saved projects are temporary. Users should download DOCX or PDF copies to keep their work.")
    st.markdown("#### Platform administrator access")
    st.write("Administrator sign-in is separate from the public workspace and is used only to protect the Admin Dashboard.")
    if not st.session_state.get("sfw_access_token") and _setting("SFW_SUPABASE_URL") and _setting("SFW_SUPABASE_ANON_KEY"):
        with st.form("sfw_admin_signin_form"):
            admin_email = st.text_input("Administrator email")
            admin_password = st.text_input("Administrator password", type="password")
            admin_submitted = st.form_submit_button("Administrator sign in", type="primary")
        if admin_submitted:
            try:
                from sfw import cloud_storage
                admin_session = cloud_storage.sign_in(admin_email, admin_password)
                if not cloud_storage.is_admin(admin_session["access_token"]):
                    st.error("This account does not have the administrator role.")
                else:
                    st.session_state["sfw_access_token"] = admin_session["access_token"]
                    st.session_state["sfw_refresh_token"] = admin_session.get("refresh_token")
                    st.session_state["sfw_account_email"] = admin_email.strip()
                    try:
                        cloud_storage.log_auth_event(admin_session["access_token"], "sign_in")
                    except Exception:
                        pass
                    st.success("Administrator signed in.")
                    st.rerun()
            except Exception as exc:
                st.error(str(exc))
    elif not st.session_state.get("sfw_access_token"):
        st.caption("Administrator sign-in is unavailable until Supabase credentials are configured by the platform owner.")
    st.write("Assign the administrator role to your account in Supabase Auth user metadata. Public users do not need Supabase accounts.")
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
    st.write("Session-saved projects are temporary and are not shared with other users. Download your reports to keep a permanent copy. Do not upload confidential, identifying or sensitive research data unless you have permission and understand the relevant provider's data handling.")
    st.markdown("#### Configure the remote RTX service")
    st.write("Add SFW_RTX_BASE_URL in Streamlit Secrets using your public HTTPS tunnel hostname. If Cloudflare Access protects the tunnel, add SFW_RTX_ACCESS_CLIENT_ID and SFW_RTX_ACCESS_CLIENT_SECRET as a service token. Add SFW_RTX_API_TOKEN only if the backend separately requires Bearer authentication. The connector is read-only and blocks local/private network destinations.")
    st.markdown("#### Current limitations")
    st.write("- The AI assistant depends on an external API when enabled; SFW is not itself a trained foundation model.\n- Literature search retrieves Crossref metadata, not necessarily full-text papers.\n- Statistical results depend on data quality, study design and test assumptions.\n- Experimental safety and ethical approval remain the responsibility of the researcher and supervising institution.")
    st.markdown("#### Included original materials")
    st.write("The two source ZIP archives supplied in the earlier SFW work are preserved in reference_archives without modification.")

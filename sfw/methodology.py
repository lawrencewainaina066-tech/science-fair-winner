"""Rule-based research methodology guidance for SFW.

Recommendations are planning prompts, not a substitute for a protocol review,
power calculation, ethics review, or discipline-specific expert supervision.
"""

DESIGN_OPTIONS = [
    "Controlled experiment",
    "Quasi-experimental study",
    "Observational study",
    "Cross-sectional survey",
    "Correlational study",
    "Qualitative exploratory study",
    "Mixed-methods study",
]

OBJECTIVES = [
    "Compare two or more groups or treatments",
    "Measure a relationship between variables",
    "Describe a population or phenomenon",
    "Measure change before and after an intervention",
    "Explore experiences, views or processes",
]

OUTCOME_TYPES = ["Continuous numerical", "Categorical", "Count", "Text / qualitative"]
SAMPLING_METHODS = [
    "Simple random sampling", "Systematic sampling", "Stratified sampling",
    "Cluster sampling", "Convenience sampling", "Purposive sampling",
]

def build_methodology(
    title,
    research_question,
    design,
    objective,
    independent_variable,
    dependent_variable,
    outcome_type,
    population,
    sampling_method,
    planned_sample_size,
    groups,
    data_collection,
    duration,
    constraints="",
):
    """Build a transparent methodology outline from researcher-supplied choices."""
    title = (title or "").strip() or "Untitled research project"
    research_question = (research_question or "").strip()
    population = (population or "").strip()
    independent_variable = (independent_variable or "").strip()
    dependent_variable = (dependent_variable or "").strip()
    data_collection = (data_collection or "").strip()
    constraints = (constraints or "").strip()

    try:
        sample_size = int(planned_sample_size) if str(planned_sample_size).strip() else None
    except (TypeError, ValueError):
        raise ValueError("Planned sample size must be a whole number.")
    if sample_size is not None and sample_size < 1:
        raise ValueError("Planned sample size must be at least 1.")
    try:
        group_count = int(groups)
    except (TypeError, ValueError):
        raise ValueError("Number of groups must be a whole number.")
    if group_count < 1:
        raise ValueError("Number of groups must be at least 1.")

    if not research_question:
        raise ValueError("Enter a research question.")
    if not population:
        raise ValueError("Describe the target population or study material.")
    if not dependent_variable:
        raise ValueError("Define the main outcome (dependent variable).")
    if not data_collection:
        raise ValueError("Describe how data will be collected.")

    design_guidance = {
        "Controlled experiment": "Manipulate the independent variable while holding relevant conditions constant. Use random allocation where feasible and ethical; include a suitable control or comparison condition.",
        "Quasi-experimental study": "Evaluate an intervention without full random allocation. Explain how groups or time periods are formed and address baseline differences and potential confounding.",
        "Observational study": "Measure variables as they naturally occur without assigning an exposure. Identify likely confounders and avoid causal claims unless the design supports them.",
        "Cross-sectional survey": "Collect measurements at one defined time point. Define the sampling frame, questionnaire procedures and response-rate reporting.",
        "Correlational study": "Measure the variables without manipulating them. Predefine the association to estimate and avoid interpreting correlation as proof of causation.",
        "Qualitative exploratory study": "Use an appropriate interview, focus-group or observation protocol. Explain participant selection, recording, transcription, coding and how themes will be developed.",
        "Mixed-methods study": "Specify the quantitative and qualitative components, their sequence or priority, and exactly how findings from both strands will be integrated.",
    }

    analysis = []
    warnings = []
    if objective == "Compare two or more groups or treatments":
        if outcome_type == "Continuous numerical":
            if group_count == 2:
                analysis.append("For two independent groups, consider Welch's independent-samples t-test if observations are independent and the outcome is reasonably suitable for this model. For paired/repeated measurements, use a paired approach instead.")
            else:
                analysis.append("For three or more independent groups, consider one-way ANOVA if its assumptions are reasonable; consider Welch ANOVA or a suitable non-parametric/model-based alternative when they are not.")
        elif outcome_type == "Categorical":
            analysis.append("Summarise counts and percentages. Consider a chi-square test of independence; use an exact method when expected cell counts are too small.")
        elif outcome_type == "Count":
            analysis.append("Summarise counts and exposure time where relevant. A Poisson or negative-binomial model may be suitable; check over-dispersion and the observation design.")
        else:
            analysis.append("Use a predefined qualitative coding or thematic-analysis approach; explain how categories/themes will be developed and checked.")
    elif objective == "Measure a relationship between variables":
        if outcome_type == "Continuous numerical":
            analysis.append("Use a scatterplot first. Pearson correlation or linear regression may be appropriate for a linear relationship when assumptions are reasonably met; consider Spearman correlation for monotonic relationships or influential outliers.")
        elif outcome_type == "Categorical":
            analysis.append("Use cross-tabulations and proportions. Chi-square or an appropriate regression model may be considered depending on the outcome and sampling design.")
        elif outcome_type == "Count":
            analysis.append("Consider a Poisson or negative-binomial regression model, with an offset if exposure time or population at risk differs.")
        else:
            analysis.append("Use qualitative coding to examine patterns and differences; do not describe this as a numerical correlation.")
    elif objective == "Describe a population or phenomenon":
        if outcome_type == "Continuous numerical":
            analysis.append("Report mean and standard deviation for suitably distributed data, or median and interquartile range for skewed data; include units and sample size.")
        elif outcome_type == "Categorical":
            analysis.append("Report counts and percentages with clear denominators; include confidence intervals when appropriate to the sampling design.")
        elif outcome_type == "Count":
            analysis.append("Report counts and relevant rates using a clearly defined denominator or exposure period.")
        else:
            analysis.append("Use a transparent qualitative analysis process, supported by anonymised excerpts where ethically permitted.")
    elif objective == "Measure change before and after an intervention":
        if outcome_type == "Continuous numerical":
            analysis.append("For matched before-and-after measurements, consider a paired t-test when assumptions are reasonable; otherwise consider a paired non-parametric method. With a comparison group, a model that accounts for group and time may be more appropriate.")
        elif outcome_type == "Categorical":
            analysis.append("For paired binary outcomes, consider McNemar's test; for independent samples, use an appropriate comparison of proportions.")
        else:
            analysis.append("Predefine how change will be assessed. For count or qualitative outcomes, select a model or coding framework that matches the repeated-measure structure.")
    else:
        analysis.append("Use a documented thematic or content-analysis approach. Explain the unit of analysis, coding process, reflexivity and how interpretations will be supported by the data.")

    if design == "Observational study" and objective in (
        "Compare two or more groups or treatments", "Measure a relationship between variables"
    ):
        warnings.append("Because this is observational, group differences or associations do not by themselves establish that one variable caused another.")
    if design == "Controlled experiment" and not independent_variable:
        warnings.append("Name the factor that will be deliberately changed; otherwise the experimental manipulation is not yet operationalised.")
    if not independent_variable and objective != "Describe a population or phenomenon":
        warnings.append("Define the exposure, predictor, intervention or grouping variable precisely.")
    if sample_size is None:
        warnings.append("No sample size was entered. Determine it before data collection using a justified power/precision calculation or a defensible qualitative sampling rationale; do not choose it arbitrarily.")
    elif sample_size < 30:
        warnings.append("The planned sample is small. This is not automatically invalid, but estimates may be imprecise and statistical power may be limited. Justify the sample size for the study design.")
    if sampling_method in ("Convenience sampling", "Purposive sampling"):
        warnings.append("This is a non-probability sampling approach. Discuss selection bias and limit generalisation to populations the sample cannot represent.")
    if design in ("Controlled experiment", "Quasi-experimental study"):
        warnings.append("Specify allocation or group formation, control conditions, replication, randomisation where feasible, and how confounding will be handled.")
    if not duration:
        warnings.append("Specify the study period, measurement schedule and any follow-up period.")
    if constraints:
        warnings.append("Resource/context constraints supplied: " + constraints)

    method_steps = [
        "Define the study setting, eligibility criteria and unit of analysis.",
        "Operationally define every variable, including measurement units, instruments and scoring rules.",
        "Describe recruitment or selection, sampling frame, inclusion/exclusion criteria and the rationale for the sample size.",
        "List materials and equipment; explain calibration, standardisation, quality control and pilot testing where appropriate.",
        "Describe the data-collection sequence so another researcher could reproduce it.",
        "Plan data storage, anonymisation, missing-data handling and quality checks before collecting observations.",
        "Pre-specify the analysis, assumptions, effect-size measures and uncertainty intervals where relevant.",
        "Report limitations, potential bias, safety precautions and ethics/approval requirements.",
    ]

    return {
        "title": title,
        "research_question": research_question,
        "design": design,
        "objective": objective,
        "population": population,
        "independent_variable": independent_variable or "Not specified",
        "dependent_variable": dependent_variable,
        "outcome_type": outcome_type,
        "sampling_method": sampling_method,
        "planned_sample_size": sample_size,
        "groups": group_count,
        "data_collection": data_collection,
        "duration": duration or "Not specified",
        "design_guidance": design_guidance.get(design, "Describe and justify the selected design."),
        "analysis_plan": analysis,
        "method_steps": method_steps,
        "warnings": warnings,
        "integrity_note": "This is a draft planning aid based on the inputs supplied. It does not calculate or validate sample size, establish causality, replace a statistical analysis plan, or provide ethics approval. Confirm the protocol with a qualified supervisor or statistician before data collection.",
    }

"""Topic-aware research-plan drafting for Science Fair Winner.

Plans are proposals, not evidence. Heuristics identify likely study elements and
flag design mismatches; researchers must verify the scientific choices.
"""
from datetime import datetime
import re

DISCIPLINES = [
    "Biology", "Chemistry", "Physics", "Environmental Science",
    "Agriculture", "Mathematics", "Engineering & Technology",
    "Health & Biomedical Science", "Interdisciplinary"
]

CROP_NAMES = {
    "maize": "maize (Zea mays L.)", "corn": "maize (Zea mays L.)",
    "rice": "rice (Oryza sativa L.)", "wheat": "wheat (Triticum aestivum L.)",
    "beans": "common bean (Phaseolus vulgaris L.)",
    "bean": "common bean (Phaseolus vulgaris L.)",
    "tomato": "tomato (Solanum lycopersicum L.)",
    "potato": "potato (Solanum tuberosum L.)",
    "sorghum": "sorghum (Sorghum bicolor L.)"
}

def _contains(text, phrase):
    return re.search(r"(?<![a-z])" + re.escape(phrase) + r"(?![a-z])", text, re.I) is not None

def _first_crop(text):
    for name, scientific in CROP_NAMES.items():
        if _contains(text, name):
            return name, scientific
    return None, None

def _duration_weeks(text):
    match = re.search(r"(\d+)\s*[- ]?week", text, re.I)
    if match:
        return int(match.group(1))
    match = re.search(r"(\d+)\s*[- ]?month", text, re.I)
    return int(match.group(1)) * 4 if match else None

def build_research_plan(title, problem, discipline, level="Science fair", constraints="",
                        location="", duration="", intervention="", primary_outcome=""):
    """Create a structured, editable plan without inventing findings or citations."""
    title = (title or "").strip() or "Untitled scientific investigation"
    problem = (problem or "").strip()
    constraints = (constraints or "").strip()
    location = (location or "").strip()
    duration = (duration or "").strip()
    intervention = (intervention or "").strip()
    primary_outcome = (primary_outcome or "").strip()
    context = " ".join([title, problem, constraints, location, duration, intervention, primary_outcome])
    lower = context.lower()
    crop, crop_scientific = _first_crop(context)
    is_compost_tea = "compost tea" in lower
    is_maize = crop == "maize" or "corn" in lower
    weeks = _duration_weeks(" ".join([duration, constraints, title, problem]))
    early_growth = any(term in lower for term in ["seedling", "early vegetative", "vegetative growth", "four weeks", "4 weeks"])
    yield_study = any(term in lower for term in ["grain yield", "crop yield", "yield per", "harvest"])
    rainfed = any(term in lower for term in ["rain-fed", "rainfed", "rain fed"])
    if not problem:
        problem = (f"The effect of {intervention or ('compost tea application' if is_compost_tea else 'the proposed treatment')} "
                   f"on {primary_outcome or ('early growth of ' + crop if crop else 'the selected measurable outcome')} "
                   "requires investigation under the stated conditions.")
    problem = problem.rstrip()
    aim = f"To evaluate the effect of {intervention or ('compost tea concentrations' if is_compost_tea else 'the selected independent variable')} on {primary_outcome or ('early vegetative growth of ' + crop if crop and early_growth else ('growth and yield of ' + crop if crop else 'the specified study outcome'))}."
    if location:
        aim = aim[:-1] + f" in {location}."
    elif constraints:
        aim = aim[:-1] + " under the conditions described in the study constraints."
    if is_compost_tea and crop:
        question = f"What effect do different compost tea concentrations have on the {('early vegetative growth' if early_growth or (weeks and weeks <= 6) else 'growth')} of {crop_scientific}" + (f" over {weeks} weeks?" if weeks else "?")
        independent = "Compost tea concentration/dilution (define exact preparation and dilution levels, including a 0% water-only control)."
        dependent = primary_outcome or ("Plant height (cm), leaf number (count), and optionally stem diameter (mm), measured at consistent intervals." if early_growth or (weeks and weeks <= 6) else "Predefined growth and yield measures, including grain yield only if the study reaches harvest.")
        controlled = "Crop variety, seed source, planting date, soil/growing medium, container or plot size, water supply, light exposure, plant spacing, application volume and frequency, and measurement procedure."
        treatments = ["T0: water-only control (0% compost tea).", "T1: lower compost tea concentration; state the exact dilution and preparation protocol.", "T2: higher compost tea concentration; state the exact dilution and preparation protocol."]
        method = [
            "Prepare one uniform batch of mature compost tea using a documented recipe; record ingredients, water volume, brewing time, temperature and filtration.",
            "Define treatment concentrations before the experiment. Include a water-only control and keep application volume and frequency equal across treatments.",
            "Use healthy, similar-sized seedlings of one stated variety. Randomly allocate experimental units to treatments; do not treat repeated measurements of one plant as independent replicates.",
            "Use a justified number of independent plants per treatment. A small number such as four plants per treatment is suitable only for an exploratory pilot, not a strong confirmatory trial.",
            "Measure baseline height before treatment, then measure at fixed intervals using the same ruler, reference point and observer where possible. Record leaf number and other outcomes only if operationally defined.",
            "Keep growing conditions as similar as possible, record rainfall/irrigation and unusual events, and photograph plants consistently if useful.",
            "Plot individual growth trajectories and treatment means. For final-time comparisons use an appropriate independent-group method; for repeated measurements use a repeated-measures or mixed-effects approach.",
            "Report sample size, variation, missing observations, deviations, limitations and all actual results. Do not infer grain yield from seedling height."
        ]
    elif crop:
        question = f"How does {intervention or 'the selected treatment or factor'} affect {primary_outcome or 'growth and development'} of {crop_scientific}" + (f" in {location}?" if location else " under the stated study conditions?")
        independent = intervention or "The factor deliberately changed; specify treatment levels and the control condition."
        dependent = primary_outcome or "A clearly defined measurable response with units and a stated measurement schedule."
        controlled = "Crop variety, seed source, soil type, planting date, plot size, plant spacing, water, light, nutrient management and measurement procedures, as applicable."
        treatments = ["Define an untreated or standard-practice control.", "Specify each treatment level quantitatively before data collection.", "Use equal experimental units and random allocation where feasible."]
        method = [
            f"Describe the study site{(' at ' + location) if location else ''}, season, soil/growing medium and relevant environmental conditions.",
            f"Use one identified crop variety of {crop_scientific}; state seed source, planting date and experimental unit.",
            "Define treatment levels, control, replication and random allocation. Justify sample size based on variability, resources and the intended strength of inference.",
            "Define each outcome operationally, including units, equipment, timing and measurement procedure.",
            "Apply treatments consistently and record rainfall/irrigation, management practices and unexpected events.",
            "Analyse data using a method suited to the design, distribution, replication and repeated measurements; report effect sizes and uncertainty.",
            "Discuss limitations and avoid claims beyond the measured outcomes and study conditions."
        ]
    else:
        question = f"What effect or relationship does the study investigate regarding {problem.rstrip('.')}?"
        independent = intervention or "Identify the predictor, exposure or factor being compared; state its levels or measurement scale."
        dependent = primary_outcome or "Define the primary outcome, its unit or category, and exactly how it will be measured."
        controlled = "List plausible confounders and procedural conditions that should be held constant, measured or adjusted for."
        treatments = ["Define the comparison groups or range of exposure.", "Specify the unit of analysis and how observations will be selected.", "Pilot instruments and procedures before full data collection."]
        method = [
            "Review relevant scholarly literature and state the specific knowledge gap this project will address.",
            "Define the target population, study setting, unit of analysis and eligibility criteria.",
            "Choose a design that directly answers the research question and define sampling and sample-size rationale.",
            "Operationally define all variables, instruments, units, timing and data-quality checks.",
            "Collect and securely store observations using a consistent protocol.",
            "Predefine an analysis appropriate to the design and data type; report uncertainty and effect sizes where appropriate.",
            "Discuss bias, confounding, limitations, safety and ethics."
        ]
    warnings = []
    if yield_study and weeks and weeks < 12:
        warnings.append("Design mismatch: the stated duration is too short to measure grain yield reliably. Change the outcome to early vegetative growth or extend the study through physiological maturity and harvest.")
    if early_growth and yield_study:
        warnings.append("The title/outcomes mix seedling growth and grain yield. Select one primary endpoint that matches the study duration.")
    if weeks and weeks <= 6 and yield_study:
        warnings.append("A short seedling-stage experiment cannot support conclusions about final grain yield.")
    if rainfed and any(x in lower for x in ["pot", "container", "greenhouse", "indoors"]):
        warnings.append("Check consistency: a container/greenhouse experiment may not represent rain-fed field conditions. Describe the actual water regime.")
    if not location and any(x in lower for x in ["kenya", "kipipiri", "nyandarua"]):
        warnings.append("State the exact study site and season; a country or county mention alone is not a reproducible location.")
    objectives = [
        f"To establish baseline measurements of {dependent.lower()} before treatment or exposure, where applicable.",
        f"To compare {dependent.lower()} across the defined treatment or comparison groups.",
        "To evaluate whether observed differences are practically meaningful and consistent with the study hypothesis."
    ]
    hypothesis = (f"H₀: The defined treatment levels do not produce a statistically detectable difference in {dependent.lower()}. "
                  f"H₁: At least one treatment level produces a difference in {dependent.lower()}. "
                  "State a directional hypothesis only when prior evidence justifies the expected direction.")
    return {
        "title": title, "discipline": discipline, "level": level,
        "problem_statement": problem, "aim": aim, "research_question": question,
        "hypothesis": hypothesis,
        "variables": {"independent": independent, "dependent": dependent, "controlled": controlled},
        "specific_objectives": objectives,
        "treatment_structure": treatments,
        "study_design": "A controlled comparative experiment is appropriate if the investigator assigns treatments; otherwise select an observational design and avoid causal claims.",
        "method_outline": method,
        "quality_checks": [
            "The research question, objectives, variables, design and analysis must refer to the same primary outcome.",
            "Distinguish the experimental unit from the number of repeated measurements.",
            "Randomly allocate experimental units to treatments where feasible; random sampling and random treatment allocation are different procedures.",
            "Record units, dates, instrument calibration, missing data and protocol deviations.",
            "Obtain permissions and follow relevant safety, environmental and human/animal research requirements."
        ],
        "warnings": warnings,
        "location": location, "duration": duration, "intervention": intervention,
        "primary_outcome": primary_outcome, "constraints": constraints,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "integrity_note": "AI-assisted planning draft. Verify methods and treatment levels against current scientific literature and local conditions. No experiment, data, result or citation is claimed to have been produced."
    }

from datetime import datetime

DISCIPLINES = [
    "Biology", "Chemistry", "Physics", "Environmental Science",
    "Agriculture", "Mathematics", "Engineering & Technology",
    "Health & Biomedical Science", "Interdisciplinary"
]

def build_research_plan(title, problem, discipline, level="Science fair", constraints=""):
    """Create a structured, editable research plan; it does not fabricate results."""
    title = title.strip() or "Untitled scientific investigation"
    problem = problem.strip() or "Define the scientific problem to be investigated."
    return {
        "title": title,
        "discipline": discipline,
        "level": level,
        "problem_statement": problem,
        "aim": f"To investigate {problem.rstrip('.')} under the stated conditions.",
        "research_question": f"What is the relationship between the key variables involved in: {problem.rstrip('?')}?",
        "hypothesis": "If the independent variable is changed, then the dependent variable will change in a measurable way, because a scientific mechanism should explain the relationship. Refine this statement for the specific project.",
        "variables": {
            "independent": "The factor deliberately changed by the investigator.",
            "dependent": "The measurable outcome or response.",
            "controlled": "Factors kept constant to make the comparison fair."
        },
        "method_outline": [
            "Review credible background literature and identify what is already known.",
            "Define measurable variables and operational definitions.",
            "Choose a suitable design, comparison group and sample size.",
            "List materials, equipment, calibration steps and safety precautions.",
            "Conduct a small pilot test where appropriate.",
            "Collect observations consistently and record raw data with units.",
            "Analyse the data using a method appropriate to the design.",
            "Discuss limitations, uncertainty and alternative explanations."
        ],
        "constraints": constraints,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "integrity_note": "This is a planning template. It is not evidence that an experiment has been conducted."
    }

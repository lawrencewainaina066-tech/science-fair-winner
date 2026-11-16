from io import BytesIO
from docx import Document
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import mm
from xml.sax.saxutils import escape

def build_docx(project):
    doc = Document()
    doc.add_heading("Science Fair Winner (SFW)", 0)
    doc.add_paragraph("Scientific Project Report", style="Subtitle")
    doc.add_heading(project.get("title", "Untitled project"), level=1)
    for key, label in [
        ("discipline", "Discipline"), ("problem_statement", "Problem statement"),
        ("aim", "Aim"), ("research_question", "Research question"),
        ("hypothesis", "Hypothesis"), ("constraints", "Constraints")
    ]:
        value = project.get(key, "")
        if value:
            doc.add_heading(label, level=2)
            doc.add_paragraph(str(value))
    variables = project.get("variables", {})
    if variables:
        doc.add_heading("Variables", level=2)
        for k, v in variables.items():
            doc.add_paragraph(f"{k.title()}: {v}", style="List Bullet")
    for key, label in [("study_design", "Study design")]:
        if project.get(key):
            doc.add_heading(label, level=2)
            doc.add_paragraph(str(project[key]))
    for key, label in [("specific_objectives", "Specific objectives"), ("treatment_structure", "Treatment structure"), ("quality_checks", "Scientific quality and safety checks"), ("warnings", "Design warnings to resolve")]:
        items = project.get(key, [])
        if items:
            doc.add_heading(label, level=2)
            for item in items:
                doc.add_paragraph(str(item), style="List Bullet")
    methods = project.get("method_outline", [])
    if methods:
        doc.add_heading("Proposed method outline", level=2)
        for step in methods:
            doc.add_paragraph(step, style="List Number")
    doc.add_heading("Scientific integrity statement", level=2)
    doc.add_paragraph("This report template does not represent an experiment as completed. Add actual methods, raw data, results, references and limitations only after they have been verified.")
    doc.add_paragraph("Prepared with Science Fair Winner (SFW).")
    out = BytesIO()
    doc.save(out)
    out.seek(0)
    return out

def build_pdf(project):
    out = BytesIO()
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="SFWTitle", parent=styles["Title"], textColor=colors.HexColor("#12366A")))
    story = [Paragraph("Science Fair Winner (SFW)", styles["SFWTitle"]),
             Paragraph("Scientific Project Report", styles["Heading2"]), Spacer(1, 8)]
    story.append(Paragraph(escape(project.get("title", "Untitled project")), styles["Heading1"]))
    sections = [
        ("Discipline", "discipline"), ("Problem statement", "problem_statement"),
        ("Aim", "aim"), ("Research question", "research_question"),
        ("Hypothesis", "hypothesis"), ("Constraints", "constraints")
    ]
    for label, key in sections:
        value = project.get(key, "")
        if value:
            story += [Paragraph(label, styles["Heading2"]), Paragraph(escape(str(value)), styles["BodyText"]), Spacer(1, 5)]
    variables = project.get("variables", {})
    if variables:
        story.append(Paragraph("Variables", styles["Heading2"]))
        for k, v in variables.items():
            story.append(Paragraph(f"<b>{escape(k.title())}:</b> {escape(str(v))}", styles["BodyText"]))
    if project.get("study_design"):
        story += [Paragraph("Study design", styles["Heading2"]), Paragraph(escape(str(project["study_design"])), styles["BodyText"])]
    for key, label in [("specific_objectives", "Specific objectives"), ("treatment_structure", "Treatment structure"), ("quality_checks", "Scientific quality and safety checks"), ("warnings", "Design warnings to resolve")]:
        items = project.get(key, [])
        if items:
            story.append(Paragraph(label, styles["Heading2"]))
            for item in items:
                story.append(Paragraph("• " + escape(str(item)), styles["BodyText"]))
    methods = project.get("method_outline", [])
    if methods:
        story.append(Paragraph("Proposed method outline", styles["Heading2"]))
        for i, step in enumerate(methods, 1):
            story.append(Paragraph(f"{i}. {escape(step)}", styles["BodyText"]))
    story += [Spacer(1, 10), Paragraph("Scientific integrity statement", styles["Heading2"]),
              Paragraph("This template does not claim that an experiment has been conducted. Insert actual methods, data, results, references and limitations only after verification.", styles["BodyText"])]
    SimpleDocTemplate(out, pagesize=A4, rightMargin=18*mm, leftMargin=18*mm).build(story)
    out.seek(0)
    return out

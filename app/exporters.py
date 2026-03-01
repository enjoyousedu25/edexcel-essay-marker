from __future__ import annotations
import io
import csv
from typing import Any, Dict, List
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

def make_csv(payload: Dict[str, Any]) -> bytes:
    out = io.StringIO()
    w = csv.writer(out)

    meta = payload.get("meta", {})
    result = payload.get("result", {})

    w.writerow(["Edexcel Essay Marker Export"])
    w.writerow(["Generated", datetime.utcnow().isoformat() + "Z"])
    w.writerow([])
    w.writerow(["Filename", meta.get("filename", "")])
    w.writerow(["Extraction method", meta.get("extract_method", "")])
    w.writerow(["Mode", result.get("mode", "")])
    w.writerow(["Model", result.get("model", "")])
    w.writerow([])

    # Scores
    w.writerow(["Aspect Scores"])
    w.writerow(["AO", "Level", "Mark", "Justification"])
    for s in result.get("aspect_scores", []) or []:
        w.writerow([s.get("code",""), s.get("level",""), s.get("mark",""), s.get("justification","")])
    w.writerow([])

    # Mistakes
    w.writerow(["Mistakes / Improvements"])
    w.writerow(["Category", "Snippet", "What's wrong", "Improved version"])
    for m in result.get("mistakes", []) or []:
        w.writerow([m.get("category",""), m.get("quote_snippet",""), m.get("what_is_wrong",""), m.get("improved_version","")])
    w.writerow([])

    # Sentence feedback
    sf = result.get("sentence_feedback", []) or []
    if sf:
        w.writerow(["Sentence-by-sentence feedback"])
        w.writerow(["Sentence index", "Issues", "Improved sentence"])
        for item in sf:
            issues = "; ".join(item.get("issues", []) or [])
            w.writerow([item.get("sentence_index",""), issues, item.get("improved_sentence","")])
        w.writerow([])

    # Improvement plan
    w.writerow(["Improvement plan"])
    for step in result.get("improvement_plan", []) or []:
        w.writerow([step])

    return out.getvalue().encode("utf-8")

def make_pdf(payload: Dict[str, Any]) -> bytes:
    buf = io.BytesIO()

    meta = payload.get("meta", {})
    result = payload.get("result", {})
    essay_text = payload.get("essay_text", "") or ""
    task_brief = payload.get("task_brief", "") or ""

    styles = getSampleStyleSheet()
    story: List[Any] = []

    story.append(Paragraph("<b>Edexcel Essay Marker Report</b>", styles["Title"]))
    story.append(Spacer(1, 10))

    story.append(Paragraph(f"<b>File:</b> {meta.get('filename','')}", styles["Normal"]))
    story.append(Paragraph(f"<b>Extraction:</b> {meta.get('extract_method','')}", styles["Normal"]))
    story.append(Paragraph(f"<b>Mode:</b> {result.get('mode','')}", styles["Normal"]))
    if result.get("model"):
        story.append(Paragraph(f"<b>Model:</b> {result.get('model','')}", styles["Normal"]))
    story.append(Spacer(1, 10))

    if task_brief.strip():
        story.append(Paragraph("<b>Task brief</b>", styles["Heading2"]))
        story.append(Paragraph(_escape(task_brief), styles["BodyText"]))
        story.append(Spacer(1, 10))

    if result.get("mode") == "ai":
        if result.get("overall_summary"):
            story.append(Paragraph("<b>Overall summary</b>", styles["Heading2"]))
            story.append(Paragraph(_escape(result["overall_summary"]), styles["BodyText"]))
            story.append(Spacer(1, 10))

        story.append(Paragraph("<b>Aspect scores</b>", styles["Heading2"]))
        data = [["AO", "Level", "Mark", "Justification"]]
        for s in result.get("aspect_scores", []) or []:
            data.append([s.get("code",""), str(s.get("level","")), str(s.get("mark","")), s.get("justification","")])
        table = Table(data, colWidths=[40, 40, 40, 360])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.lightgrey),
            ("GRID", (0,0), (-1,-1), 0.5, colors.grey),
            ("VALIGN", (0,0), (-1,-1), "TOP"),
            ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ]))
        story.append(table)
        story.append(Spacer(1, 12))

        # Mistakes
        story.append(Paragraph("<b>Top mistakes / improvements</b>", styles["Heading2"]))
        mistakes = result.get("mistakes", []) or []
        if mistakes:
            md = [["Category", "Snippet", "Fix"]]
            for m in mistakes[:15]:
                fix = f"Wrong: {m.get('what_is_wrong','')}<br/>Better: {m.get('improved_version','')}"
                md.append([m.get("category",""), m.get("quote_snippet",""), fix])
            mt = Table(md, colWidths=[90, 150, 240])
            mt.setStyle(TableStyle([
                ("BACKGROUND", (0,0), (-1,0), colors.lightgrey),
                ("GRID", (0,0), (-1,-1), 0.5, colors.grey),
                ("VALIGN", (0,0), (-1,-1), "TOP"),
                ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
            ]))
            story.append(mt)
        else:
            story.append(Paragraph("No mistake list returned.", styles["BodyText"]))
        story.append(Spacer(1, 12))

        # Sentence feedback
        sf = result.get("sentence_feedback", []) or []
        if sf:
            story.append(Paragraph("<b>Sentence-by-sentence feedback (flagged sentences)</b>", styles["Heading2"]))
            sfd = [["#", "Issues", "Improved sentence"]]
            for item in sf[:25]:
                issues = "; ".join(item.get("issues", []) or [])
                sfd.append([str(item.get("sentence_index","")), issues, item.get("improved_sentence","")])
            sft = Table(sfd, colWidths=[28, 220, 232])
            sft.setStyle(TableStyle([
                ("BACKGROUND", (0,0), (-1,0), colors.lightgrey),
                ("GRID", (0,0), (-1,-1), 0.5, colors.grey),
                ("VALIGN", (0,0), (-1,-1), "TOP"),
                ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
            ]))
            story.append(sft)
            story.append(Spacer(1, 12))

        # Improvement plan
        plan = result.get("improvement_plan", []) or []
        if plan:
            story.append(Paragraph("<b>Improvement plan</b>", styles["Heading2"]))
            for step in plan[:10]:
                story.append(Paragraph("• " + _escape(str(step)), styles["BodyText"]))
            story.append(Spacer(1, 10))

    else:
        story.append(Paragraph("<b>Basic feedback</b>", styles["Heading2"]))
        story.append(Paragraph(_escape(str(result)), styles["BodyText"]))
        story.append(Spacer(1, 10))

    # Essay text (truncated)
    story.append(PageBreak())
    story.append(Paragraph("<b>Extracted essay text (truncated)</b>", styles["Heading2"]))
    story.append(Paragraph(_escape(essay_text[:12000]).replace("\n", "<br/>"), styles["BodyText"]))

    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)
    doc.build(story)

    return buf.getvalue()

def _escape(s: str) -> str:
    # Escape for reportlab Paragraph (a subset of HTML-like markup)
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

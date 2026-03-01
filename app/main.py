from __future__ import annotations
import os
from fastapi import FastAPI, Request, UploadFile, File, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .auth import verify_passcode, login, logout, current_teacher, is_configured
from .ocr import extract_text_from_upload
from .scoring import score_essay
from .cache import put as cache_put, get as cache_get
from .text_utils import split_sentences, build_highlighted_html
from .exporters import make_pdf, make_csv

app = FastAPI(title="Edexcel Essay Marker")

# Static + templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

def _max_upload_bytes() -> int:
    mb = int(os.getenv("MAX_UPLOAD_MB", "15"))
    return mb * 1024 * 1024

def require_auth(request: Request):
    teacher = current_teacher(request)
    if not teacher:
        return None
    return teacher

@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    teacher = current_teacher(request)
    if not is_configured():
        return templates.TemplateResponse("error.html", {
            "request": request,
            "title": "Not configured",
            "message": "Set APP_PASSCODE (or APP_PASSCODES) as an environment variable, then redeploy.",
        })
    if teacher:
        return RedirectResponse(url="/upload", status_code=303)
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
def do_login(request: Request, passcode: str = Form(...), teacher_name: str = Form("Teacher")):
    if not is_configured():
        return RedirectResponse(url="/", status_code=303)
    if not verify_passcode(passcode):
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": "Wrong passcode.",
        })
    resp = RedirectResponse(url="/upload", status_code=303)
    login(resp, teacher_name=teacher_name.strip() or "Teacher")
    return resp

@app.post("/logout")
def do_logout():
    resp = RedirectResponse(url="/", status_code=303)
    logout(resp)
    return resp

@app.get("/upload", response_class=HTMLResponse)
def upload_page(request: Request):
    teacher = require_auth(request)
    if not teacher:
        return RedirectResponse(url="/", status_code=303)
    return templates.TemplateResponse("upload.html", {"request": request, "teacher": teacher})

@app.post("/mark", response_class=HTMLResponse)
async def mark_essay(
    request: Request,
    file: UploadFile = File(...),
    task_brief: str = Form(""),
):
    teacher = require_auth(request)
    if not teacher:
        return RedirectResponse(url="/", status_code=303)

    data = await file.read()
    if len(data) > _max_upload_bytes():
        return templates.TemplateResponse("error.html", {
            "request": request,
            "title": "File too large",
            "message": f"Max upload size is {os.getenv('MAX_UPLOAD_MB','15')} MB.",
        })

    try:
        text, method = extract_text_from_upload(file.filename or "", file.content_type or "", data)
    except Exception as e:
        return templates.TemplateResponse("error.html", {
            "request": request,
            "title": "Could not read file",
            "message": str(e),
        })

    result = score_essay(text, task_brief=task_brief)

# Sentence highlighting (AI mode provides sentence_feedback indices)
sentences = split_sentences(text, max_sentences=120)
feedback = (result.get("sentence_feedback") or []) if isinstance(result, dict) else []
highlighted_html = build_highlighted_html(sentences, feedback)

report_id = cache_put({
    "meta": {"filename": file.filename, "extract_method": method},
    "task_brief": task_brief,
    "essay_text": text,
    "result": result,
})

return templates.TemplateResponse("result.html", {
    "request": request,
    "teacher": teacher,
    "filename": file.filename,
    "extract_method": method,
    "task_brief": task_brief,
    "essay_text": text[:8000],  # avoid huge HTML
    "result": result,
    "report_id": report_id,
    "highlighted_html": highlighted_html,
    "sentences_truncated": (len(split_sentences(text, max_sentences=9999)) > 120),
})
("result.html", {
        "request": request,
        "teacher": teacher,
        "filename": file.filename,
        "extract_method": method,
        "task_brief": task_brief,
        "essay_text": text[:8000],  # avoid huge HTML
        "result": result,
    })

@app.get("/export/pdf/{report_id}")
def export_pdf(request: Request, report_id: str):
    teacher = require_auth(request)
    if not teacher:
        return RedirectResponse(url="/", status_code=303)
    payload = cache_get(report_id)
    if not payload:
        return templates.TemplateResponse("error.html", {
            "request": request,
            "title": "Export not available",
            "message": "That report has expired. Please re-mark the essay and export again.",
        })
    pdf_bytes = make_pdf(payload)
    from fastapi.responses import Response
    fn = (payload.get("meta", {}).get("filename") or "essay").rsplit(".", 1)[0]
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{fn}_marking_report.pdf"'},
    )

@app.get("/export/csv/{report_id}")
def export_csv(request: Request, report_id: str):
    teacher = require_auth(request)
    if not teacher:
        return RedirectResponse(url="/", status_code=303)
    payload = cache_get(report_id)
    if not payload:
        return templates.TemplateResponse("error.html", {
            "request": request,
            "title": "Export not available",
            "message": "That report has expired. Please re-mark the essay and export again.",
        })
    csv_bytes = make_csv(payload)
    from fastapi.responses import Response
    fn = (payload.get("meta", {}).get("filename") or "essay").rsplit(".", 1)[0]
    return Response(
        content=csv_bytes,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{fn}_marking_report.csv"'},
    )

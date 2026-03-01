# Edexcel Essay Marker (Teacher Web App)

A small passcode-protected web app for teachers to upload student essays (PDF/JPEG/PNG),
extract text (OCR if needed), and generate Edexcel-style marks + improvement feedback.

## What it does
- **Teacher login with passcode**
- Upload **PDF** or **image** (JPEG/PNG)
- Extract text:
  - PDF with embedded text -> reads text directly
  - scanned PDF / images -> OCR via Tesseract
- Marking + feedback:
  - **AI mode (recommended):** Uses OpenAI to score against rubric aspects (AO4/AO5 by default) and produce:
  - **sentence-by-sentence flagged feedback** (problematic sentences highlighted + improved rewrite)
  - **exports**: download PDF report and CSV report
    - level + mark per AO
    - summary
    - key improvements
    - common mistakes list with corrections
  - **Basic mode (fallback):** If no OpenAI key is set, it provides readability stats + spelling suggestions (no full rubric scoring).

> ⚠️ Accuracy note: Automated marking is guidance only. Teachers should review the output before finalising grades.

---

## Deploy on Render (Docker)
1. Create a GitHub repo and push this project.
2. In Render:
   - New → **Web Service**
   - Select your repo
   - Environment: **Docker**
3. Set Environment Variables in Render:
   - `APP_PASSCODE` (required)
   - `OPENAI_API_KEY` (recommended)
   - `OPENAI_MODEL` (optional)
4. Deploy.

---

## Run locally
```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
source .venv/bin/activate

pip install -r requirements.txt

cp .env.example .env
# edit APP_PASSCODE (and OPENAI_API_KEY if using AI mode)

uvicorn app.main:app --reload
```

Open: http://127.0.0.1:8000

---

## Customise the rubric
Edit `app/rubric.py` to add more assessment objectives or different mark ranges.

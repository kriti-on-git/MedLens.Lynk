# app.py — MedLens Phase 2 (dark professional theme)
import os
import io
import time
from dotenv import load_dotenv
import streamlit as st

# AI client
from google import genai

# Try optional libs for extraction
try:
    import pdfplumber
except Exception:
    pdfplumber = None

try:
    from PIL import Image
except Exception:
    Image = None

try:
    import pytesseract
except Exception:
    pytesseract = None

load_dotenv()
API_KEY = os.getenv("GOOGLE_API_KEY")
MODEL_NAME = os.getenv("MODEL_NAME", "models/gemini-2.0-flash")  # set exact model if needed

if not API_KEY:
    st.error("🔑 GOOGLE_API_KEY not found. Put your key in the .env file.")
    st.stop()

# Initialize client
client = genai.Client(api_key=API_KEY)

import streamlit as st

# -----------------------------
# --- App Configuration & UI Styling ---
# -----------------------------
st.set_page_config(page_title="MedLens", page_icon="🩺", layout="wide")

# Custom CSS
st.markdown("""
<style>
.reportview-container { background: #0b1020; color: #d6e0ff; }
.stButton>button { background-color:#0f1724; color:#d6e0ff; border:1px solid #2b3446 }
.stFileUploader>div { border:1px dashed #2b3446; padding:10px; border-radius:8px}
.stApp { font-family: Inter, system-ui, sans-serif; }
.big-title { font-size:32px; font-weight:700; color:#f3f7ff; }
.muted { color:#9fb0ff; }
.card { background: linear-gradient(180deg,#091026,#071226); border-radius:12px; padding:16px; box-shadow: 0 6px 20px rgba(2,6,23,0.6); }
</style>
""", unsafe_allow_html=True)

# Main Heading
st.markdown("<div class='big-title'>🩺 MedLens — Patient-Friendly Medical Summaries</div>", unsafe_allow_html=True)
st.markdown("<div class='muted'>Upload a PDF, image, or scan — MedLens extracts and simplifies it with AI precision.</div>", unsafe_allow_html=True)
st.write("")

# -----------------------------
# --- Sidebar Controls ---
# -----------------------------
MODEL_NAME = "gemini-2.0-flash"  # Placeholder model name
client = None  # Placeholder for your Gemini client

with st.sidebar:
    st.header("Settings")
    lang = st.radio("Output language", ("English", "Hindi"))
    summary_tone = st.selectbox(
        "Summary tone", 
        ["Concise (bullets)", "Friendly explanation", "Formal doctor note"]
    )
    max_length = st.slider("Max tokens / length (approx)", 64, 1024, 300)
    show_raw = st.checkbox("Show raw extracted text", value=False)
    
    st.markdown("---")
    st.markdown(f"Model: `{MODEL_NAME}`")
    
    if st.button("Refresh model list (debug)"):
        try:
            if client:
                ms = client.models.list()
                st.write([m.name for m in ms])
            else:
                st.warning("Client not initialized yet.")
        except Exception as e:
            st.error(f"Error listing models: {e}")




# Helpers: extraction
def extract_text_from_pdf_bytes(content_bytes):
    if pdfplumber:
        try:
            text_pages = []
            with pdfplumber.open(io.BytesIO(content_bytes)) as pdf:
                for p in pdf.pages:
                    txt = p.extract_text() or ""
                    text_pages.append(txt)
            return "\n\n".join(text_pages).strip()
        except Exception as e:
            return f"[PDF extraction failed: {e}]"
    else:
        return "[pdfplumber not installed — install with pip install pdfplumber]"

def extract_text_from_image_bytes(content_bytes):
    if Image is None:
        return "[Pillow not installed — install with pip install pillow]"
    img = Image.open(io.BytesIO(content_bytes))
    # if pytesseract available, use it
    if pytesseract:
        try:
            text = pytesseract.image_to_string(img)
            return text.strip()
        except Exception as e:
            return f"[pytesseract error: {e}]"
    else:
        return "[pytesseract not installed — install with pip install pytesseract and Tesseract engine]"

# Build prompt
def build_prompt(extracted_text, filename, language="English", tone="Concise (bullets)"):
    intro = "You are an assistant that converts medical reports into a short, patient-friendly summary."
    if tone == "Concise (bullets)":
        formatting = "Return a short title, 4-6 bullet points in simple language, and 1 'next steps' line."
    elif tone == "Friendly explanation":
        formatting = "Return a small paragraph in friendly, reassuring language and 3 practical next steps."
    else:
        formatting = "Return a short clinical summary suitable for doctor's review."

    lang_instruction = ""
    if language.lower().startswith("h"):
        lang_instruction = " Translate the output to Hindi."

    safe = (
        f"{intro}\n\nFilename: {filename}\n\n{formatting}\n\n"
        f"Patient-friendly, avoid medical jargon; when jargon is necessary, explain in parentheses.\n"
        f"{lang_instruction}\n\nReport text:\n{extracted_text[:35000]}"
    )
    return safe

# Summarization call
def call_gemini(prompt, model_name=MODEL_NAME, max_length=300):
    try:
        resp = client.models.generate_content(
            model=model_name,
            contents=prompt,
        )
        # safe extraction
        text = getattr(resp, "text", None)
        if not text and hasattr(resp, "candidates"):
            # fallback to candidates
            text = resp.candidates[0].content if resp.candidates else ""
        return text or "[No output from model]"
    except Exception as e:
        return f"[Error from Gemini API: {e}]"

# UI: upload and processing
uploaded = st.file_uploader("Upload report (PDF / PNG / JPG / JPEG / TXT)", type=["pdf", "png", "jpg", "jpeg", "txt"])
if uploaded:
    file_bytes = uploaded.read()
    fname = uploaded.name
    st.markdown(f"<div class='card'><strong>Uploaded:</strong> {fname}</div>", unsafe_allow_html=True)

    # Extract text by type
    extracted = ""
    if fname.lower().endswith(".pdf"):
        extracted = extract_text_from_pdf_bytes(file_bytes)
    elif fname.lower().endswith(".txt"):
        try:
            extracted = file_bytes.decode("utf-8", errors="ignore")
        except Exception:
            extracted = "[Could not decode txt]"
    else:
        extracted = extract_text_from_image_bytes(file_bytes)

    if show_raw:
        st.expander("Raw extracted text", expanded=False).write(extracted[:10000] + ("\n\n...[truncated]" if len(extracted) > 10000 else ""))

    # Safety quick check (simple heuristics)
    critical_keywords = ["urgent", "emergency", "acute", "critical", "bleeding", "fracture", "infarct", "stroke"]
    flagged = any(k in extracted.lower() for k in critical_keywords)
    if flagged:
        st.warning("⚠️ The report contains terms that may indicate critical findings. Highlighted in summary.")

    # Build prompt and call Gemini
    prompt = build_prompt(extracted if extracted else "[No text extracted]", fname, language=lang, tone=summary_tone)
    with st.spinner("🧠 Generating patient-friendly summary (Gemini)... This may take a few seconds"):
        summary = call_gemini(prompt, model_name=MODEL_NAME, max_length=max_length)

    # Results UI with collapsible sections
    st.markdown("### 🧾 Summary & Insights")
    with st.expander("Patient-friendly summary", expanded=True):
        st.write(summary)

    with st.expander("Clinician-style summary (brief)", expanded=False):
        # second prompt for clinician tone
        clinician_prompt = prompt + "\n\nNow produce a short clinical summary of 3-4 lines suitable for a physician."
        clinician_summary = call_gemini(clinician_prompt, model_name=MODEL_NAME, max_length=220)
        st.write(clinician_summary)

    with st.expander("Next steps / Recommendations", expanded=False):
        next_prompt = prompt + "\n\nList 3 next steps the patient should take (tests, when to see doctor)."
        next_steps = call_gemini(next_prompt, model_name=MODEL_NAME, max_length=120)
        st.write(next_steps)

    if flagged:
        st.error("🔴 Urgent-sounding language detected — advise immediate clinical follow-up.")

    # Download button
    summary_bytes = summary.encode("utf-8")
    st.download_button("⬇️ Download summary (.txt)", data=summary_bytes, file_name=f"{fname}.summary.txt", mime="text/plain")

else:
    st.info("Upload a medical report (PDF or image). Tip: for best results, use clear scans or digital PDFs.")

# Footer
st.markdown("<hr>", unsafe_allow_html=True)
st.markdown("<div class='muted'>MedLens • Built with Gemini • Keep PHI safe — do not upload real patient identifiable data to public machines.</div>", unsafe_allow_html=True)

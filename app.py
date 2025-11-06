# app.py — MedLens Phase 3 (OCR + Gemini + Clean Extraction)
import os
import io
import time
from dotenv import load_dotenv
import streamlit as st

# AI client
from google import genai

# Optional libraries
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

# Load environment
load_dotenv()
API_KEY = os.getenv("GOOGLE_API_KEY")
MODEL_NAME = os.getenv("MODEL_NAME", "models/gemini-2.0-flash")

if not API_KEY:
    st.error("🔑 GOOGLE_API_KEY not found. Put your key in the .env file.")
    st.stop()

client = genai.Client(api_key=API_KEY)

# --- UI Styling ---
st.set_page_config(page_title="MedLens", page_icon="🩺", layout="wide")
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

st.markdown("<div class='big-title'>🩺 MedLens — Patient-Friendly Medical Summaries</div>", unsafe_allow_html=True)
st.markdown("<div class='muted'>Upload a PDF, image, or scan — MedLens extracts and simplifies it with AI precision.</div>", unsafe_allow_html=True)
st.write("")

# Sidebar controls
with st.sidebar:
    st.header("Settings")
    lang = st.radio("Output language", ("English", "Hindi"))
    summary_tone = st.selectbox("Summary tone", ["Concise (bullets)", "Friendly explanation", "Formal doctor note"])
    max_length = st.slider("Max tokens / length (approx)", 64, 1024, 300)
    show_raw = st.checkbox("Show raw extracted text", value=False)
    st.markdown("---")
    st.markdown("Model: `" + MODEL_NAME + "`")
    if st.button("Refresh model list (debug)"):
        try:
            ms = client.models.list()
            st.write([m.name for m in ms])
        except Exception as e:
            st.error(f"Error listing models: {e}")

# --- TEXT EXTRACTION HELPERS ---

def extract_text_from_pdf_bytes(content_bytes):
    """Extract text from PDF file bytes using pdfplumber."""
    if pdfplumber:
        try:
            text_pages = []
            with pdfplumber.open(io.BytesIO(content_bytes)) as pdf:
                for page in pdf.pages:
                    txt = page.extract_text() or ""
                    text_pages.append(txt)
            combined = "\n\n".join(text_pages).strip()
            if not combined:
                return "[PDF contained no readable text — may be scanned. Try uploading as image instead.]"
            return combined
        except Exception as e:
            return f"[PDF extraction failed: {e}]"
    return "[pdfplumber not installed — run: pip install pdfplumber]"

def extract_text_from_image_bytes(content_bytes):
    """Extract text from image bytes using OCR (pytesseract)."""
    if Image is None:
        return "[Pillow not installed — run: pip install pillow]"
    try:
        img = Image.open(io.BytesIO(content_bytes))
    except Exception as e:
        return f"[Image open error: {e}]"

    # OCR
    if pytesseract:
        try:
            # Optional: improve OCR accuracy
            img = img.convert("L")  # grayscale
            text = pytesseract.image_to_string(img)
            return text.strip() if text.strip() else "[No readable text detected in scan]"
        except Exception as e:
            return f"[pytesseract error: {e}]"
    return "[pytesseract not installed — run: pip install pytesseract + install Tesseract OCR]"

# --- PROMPT BUILDING ---

def build_prompt(extracted_text, filename, language="English", tone="Concise (bullets)"):
    intro = "You are a medical AI assistant that summarizes diagnostic reports into simple, patient-friendly explanations."
    if tone == "Concise (bullets)":
        formatting = "Return a short title, 4–6 bullet points, and one 'next steps' line."
    elif tone == "Friendly explanation":
        formatting = "Return a short paragraph in comforting, clear language, plus 3 practical next steps."
    else:
        formatting = "Return a concise doctor-style summary suitable for clinical notes."

    lang_instruction = " Translate the output to Hindi." if language.lower().startswith("h") else ""

    return f"""{intro}

File: {filename}
{formatting}
Avoid jargon; explain technical terms simply.
{lang_instruction}

Report text:
{extracted_text[:35000]}
"""

# --- GEMINI CALL ---
def call_gemini(prompt, model_name=MODEL_NAME):
    try:
        resp = client.models.generate_content(model=model_name, contents=prompt)
        if hasattr(resp, "text") and resp.text:
            return resp.text
        elif hasattr(resp, "candidates") and resp.candidates:
            return resp.candidates[0].content.parts[0].text
        else:
            return "[No text returned by Gemini]"
    except Exception as e:
        return f"[Error from Gemini API: {e}]"

# --- MAIN INTERFACE ---
uploaded = st.file_uploader("Upload report (PDF / PNG / JPG / JPEG / TXT)", type=["pdf", "png", "jpg", "jpeg", "txt"])
if uploaded:
    file_bytes = uploaded.read()
    fname = uploaded.name
    st.markdown(f"<div class='card'><strong>Uploaded:</strong> {fname}</div>", unsafe_allow_html=True)

    extracted = ""
    if fname.lower().endswith(".pdf"):
        extracted = extract_text_from_pdf_bytes(file_bytes)
        # fallback OCR for scanned PDFs
        if "[PDF contained no readable text" in extracted and Image and pytesseract:
            st.info("🧐 No text layer detected — trying OCR on PDF image pages...")
            try:
                from pdf2image import convert_from_bytes
                pages = convert_from_bytes(file_bytes)
                extracted = "\n\n".join(pytesseract.image_to_string(p) for p in pages)
            except Exception:
                st.warning("Install pdf2image for OCR fallback: pip install pdf2image")
    elif fname.lower().endswith(".txt"):
        extracted = file_bytes.decode("utf-8", errors="ignore")
    else:
        extracted = extract_text_from_image_bytes(file_bytes)

    if show_raw:
        with st.expander("Raw extracted text", expanded=False):
            st.write(extracted[:8000] + ("\n\n...[truncated]" if len(extracted) > 8000 else ""))

    # Safety flag
    critical_terms = ["urgent", "emergency", "acute", "critical", "bleeding", "fracture", "stroke"]
    flagged = any(k in extracted.lower() for k in critical_terms)
    if flagged:
        st.warning("⚠️ Report may contain critical terms. Please review carefully.")

    # Summarize
    prompt = build_prompt(extracted, fname, lang, summary_tone)
    with st.spinner("🧠 Generating patient-friendly summary..."):
        summary = call_gemini(prompt)

    st.markdown("### 🧾 Summary & Insights")
    with st.expander("Patient-friendly summary", expanded=True):
        st.write(summary)

    with st.expander("Clinician-style summary", expanded=False):
        c_prompt = prompt + "\n\nNow give a 3-line summary for a doctor."
        st.write(call_gemini(c_prompt))

    with st.expander("Next Steps / Recommendations", expanded=False):
        n_prompt = prompt + "\n\nList 3 next steps for the patient."
        st.write(call_gemini(n_prompt))

    if flagged:
        st.error("🔴 Urgent-sounding terms detected — immediate clinical consultation advised.")

    st.download_button("⬇️ Download Summary (.txt)", data=summary.encode("utf-8"), file_name=f"{fname}.summary.txt", mime="text/plain")

else:
    st.info("Upload a report (PDF or image). For best results, use clear scans or digital reports.")

st.markdown("<hr>", unsafe_allow_html=True)
st.markdown("<div class='muted'>MedLens • OCR + Gemini • For educational use only — avoid uploading real patient data.</div>", unsafe_allow_html=True)

# app.py — MedLens Phase 4

import os
import io
import time
import urllib.parse
from dotenv import load_dotenv
import streamlit as st
from google import genai

# === Optional Dependencies ===
try:
    import pdfplumber
    from PIL import Image
    import pytesseract
    from streamlit_lottie import st_lottie
    import requests
except ImportError:
    pdfplumber = Image = pytesseract = st_lottie = requests = None

# === ENVIRONMENT SETUP ===
load_dotenv()
API_KEY = os.getenv("GOOGLE_API_KEY")
MODEL_NAME = os.getenv("MODEL_NAME", "models/gemini-2.0-flash")

if not API_KEY:
    st.error("🚨 GOOGLE_API_KEY missing in .env file.")
    st.stop()

client = genai.Client(api_key=API_KEY)
st.set_page_config(page_title="MedLens", page_icon="🩺", layout="wide")

# === SESSION STATE ===
if "mode" not in st.session_state:
    st.session_state.mode = "Standard MedLens"
if "theme" not in st.session_state:
    st.session_state.theme = "Dark Mode"

# === GLOBAL STYLES ===
st.markdown("""
<style>
@keyframes fadeIn { from {opacity: 0;} to {opacity: 1;} }
.fade { animation: fadeIn 0.6s ease-in-out; }
</style>
""", unsafe_allow_html=True)

# === CSS THEMES ===
dark_css = """
<style>
body { background: #0b1020; color: #e2e8f0; }
.stApp { font-family: 'Inter', sans-serif; transition: all 0.6s ease-in-out; }
.big-title { font-size: 32px; font-weight: 700; color: #f1f5f9; }
.card { background: rgba(15,23,36,0.8); border-radius: 14px; padding: 16px; box-shadow: 0 8px 24px rgba(0,0,0,0.5); }
.stButton>button { background: #1e293b; color: #e2e8f0; border: 1px solid #334155; border-radius: 8px; }
</style>
"""

light_css = """
<style>
body { background: #fff8f0; color: #3e2723; }
.stApp { font-family: 'Georgia', serif; transition: all 0.6s ease-in-out; }
.big-title { font-size: 32px; font-weight: 700; color: #4e342e; }
.card { background: #f7efe3; border-radius: 14px; padding: 16px; box-shadow: 0 8px 24px rgba(121,85,72,0.25); }
.stButton>button { background: #d7ccc8; color: #3e2723; border-radius: 8px; border: 1px solid #a1887f; }
</style>
"""

funshine_css = """
<style>
body { background: linear-gradient(135deg, #ffd3ec, #ffeab6, #d1f7ff); color: #1a1a1a; overflow: hidden; }
.stApp { font-family: 'Poppins', sans-serif; transition: all 0.8s ease-in-out; }
.big-title { font-size: 34px; font-weight: 800; color: #ff5db1; text-shadow: 0 0 6px rgba(255,255,255,0.5); }
.card { background: rgba(255,255,255,0.65); backdrop-filter: blur(6px); border-radius: 14px; padding: 16px; box-shadow: 0 6px 20px rgba(0,0,0,0.15); }
@keyframes bubbles {
  0% { transform: translateY(0); opacity: 0.9; }
  100% { transform: translateY(-200px); opacity: 0; }
}
.bubble {
  position: absolute; bottom: -10px; border-radius: 50%; background: rgba(255,255,255,0.4);
  animation: bubbles 4s ease-in infinite;
}
</style>
"""

# === APPLY CSS BASED ON MODE ===
if st.session_state.mode == "Doctor Funshine":
    st.markdown(funshine_css, unsafe_allow_html=True)
elif st.session_state.theme == "Light Mode":
    st.markdown(light_css, unsafe_allow_html=True)
else:
    st.markdown(dark_css, unsafe_allow_html=True)

# === SIDEBAR ===
with st.sidebar:
    st.header("⚙️ Control Panel")

    mode = st.radio(
        "Select Mode",
        ("Standard MedLens", "Doctor Funshine"),
        horizontal=True,
        label_visibility="collapsed"
    )
    if mode != st.session_state.mode:
        st.session_state.mode = mode
        st.rerun()

    theme = st.radio("Theme", ["Dark Mode", "Light Mode"], index=0)
    if theme != st.session_state.theme:
        st.session_state.theme = theme
        st.rerun()

    lang = st.radio("Language", ["English", "Hindi"])

    # Summary tone options
    if st.session_state.mode == "Standard MedLens":
        tone = st.selectbox("Summary Style", ["Patient-Friendly", "Clinical Summary"])
    else:
        tone = st.selectbox("Choose Funshine Persona", [
            "CareBuddy (Kids Mode)",
            "DocLogic (Nerd Mode)",
            "MemeLens (Teens)",
            "HeroCare (Comics)",
            "OtakuHealer (Anime)"
        ])

    st.divider()

    with st.expander("🧪 Secret Lab"):
        st.markdown("Debug corner for power users and insomniac developers.")
        max_length = st.slider("Max Tokens", 64, 1024, 300)
        show_raw = st.checkbox("Show Raw Extracted Text", False)
        st.markdown(f"**Model:** `{MODEL_NAME}`")
        if st.button("Refresh Model List"):
            try:
                ms = client.models.list()
                st.write([m.name for m in ms])
            except Exception as e:
                st.error(f"Model refresh error: {e}")

# === FUNSHINE BUBBLES ===
if st.session_state.mode == "Doctor Funshine":
    st.markdown("""
    <div class="bubble" style="left:20%;width:20px;height:20px;animation-delay:0s;"></div>
    <div class="bubble" style="left:50%;width:30px;height:30px;animation-delay:0.4s;"></div>
    <div class="bubble" style="left:80%;width:25px;height:25px;animation-delay:1s;"></div>
    """, unsafe_allow_html=True)

# === HEADER ===
if st.session_state.mode == "Doctor Funshine":
    st.markdown("<div class='fade'><div class='big-title'>💼 Doctor Funshine — Making Health Fun!</div></div>", unsafe_allow_html=True)
    st.markdown("<div class='fade'>Do you know what your medical reports speak, haan?</div>", unsafe_allow_html=True)
else:
    st.markdown("<div class='fade'><div class='big-title'>🩺 MedLens — AI That Speaks Health, Not Jargon</div></div>", unsafe_allow_html=True)
    st.markdown("<div class='fade'>Professional Support Aid to know your health better.</div>", unsafe_allow_html=True)

st.write("")

# === UPLOAD FILE ===
uploaded = st.file_uploader("Upload report (PDF / PNG / JPG / JPEG / TXT)", type=["pdf", "png", "jpg", "jpeg", "txt"])

# === HELPERS ===
def extract_text_from_pdf_bytes(content_bytes):
    if not pdfplumber:
        return "[pdfplumber missing]"
    try:
        text_pages = []
        with pdfplumber.open(io.BytesIO(content_bytes)) as pdf:
            for page in pdf.pages:
                txt = page.extract_text() or ""
                text_pages.append(txt)
        return "\n\n".join(text_pages).strip() or "[No readable text]"
    except Exception as e:
        return f"[PDF extraction error: {e}]"

def extract_text_from_image_bytes(content_bytes):
    if not pytesseract or not Image:
        return "[OCR not available]"
    try:
        img = Image.open(io.BytesIO(content_bytes)).convert("L")
        text = pytesseract.image_to_string(img)
        return text.strip() if text.strip() else "[No readable text detected]"
    except Exception as e:
        return f"[Image OCR error: {e}]"

def build_prompt(text, filename, lang, tone, mode):
    if mode == "Standard MedLens":
        prompt = f"""
You are MedLens, an AI medical recommendation assistant for a health-tech platform.
Your role is to provide safe, general, and practical lifestyle guidance based on a user’s medical report summary or extracted health metrics. Understand the Context:Identify the key findings or health parameters that are above, below, or outside the normal range.
Focus only on significant trends or imbalances.
Generate Two Types of Recommendations:
A. Dietary & Lifestyle Recommendations:Suggest general, practical changes related to food, hydration, physical activity, and daily habits. Focus only on natural, everyday adjustments.
B. Doctor Visit Recommendations:Advise when a doctor consultation might be appropriate.
Keep tone reassuring and non-urgent, unless the context clearly suggests concern.
Your outputs are meant for informational and preventive purposes only, not for diagnosis or treatment.
Always end with this disclaimer:
"These insights are for informational purposes only. MedLens does not replace professional medical consultation. Always seek advice from a qualified healthcare provider for diagnosis, treatment, or any medical concern."
{"Translate the summary into hindi such that the translation is not literal translation of the summary, but refined version in hindi having indian hindi context. Also, if there is any reference of organ or disease in summary, add english names of it in parantheses in your summary." if lang.lower().startswith("h") else ""}
Report Name: {filename}

Report Text:
{text[:30000]}
"""
    else:
        prompt = f"""
You are {tone} — a witty, warm, and positive doctor persona.
Summarize the report in a fun and friendly way.
Be lighthearted yet accurate; use analogies and humor.
Keep it short (4–6 lines). Avoid alarming tone.
{"Translate the summary into hindi such that the translation is not literal translation of the summary, but refined version in hindi having indian hindi context. Also, if there is any reference of organ or disease in summary, add english names of it in parantheses in your summary." if lang.lower().startswith("h") else ""}
Report Name: {filename}

Report Text:
{text[:30000]}
"""
    return prompt.strip()

def call_gemini(prompt):
    try:
        response = client.models.generate_content(model=MODEL_NAME, contents=prompt)
        # Safe text extraction logic
        if hasattr(response, "text") and response.text:
            return response.text
        if hasattr(response, "candidates") and response.candidates:
            parts = response.candidates[0].content.parts
            if parts and hasattr(parts[0], "text"):
                return parts[0].text
        return "[No response from Gemini]"
    except Exception as e:
        return f"[Gemini Error: {e}]"

# === MAIN ===
if uploaded:
    fname = uploaded.name
    data = uploaded.read()
    if fname.endswith(".pdf"):
        text = extract_text_from_pdf_bytes(data)
    elif fname.endswith(".txt"):
        text = data.decode("utf-8", errors="ignore")
    else:
        text = extract_text_from_image_bytes(data)

    if show_raw:
        st.expander("Raw Extracted Text").write(text[:6000])

    prompt = build_prompt(text, fname, lang, tone, st.session_state.mode)

    with st.spinner("🧠 Generating summary..."):
        summary = call_gemini(prompt)

    st.markdown("<div class='card fade'>", unsafe_allow_html=True)
    st.markdown("### 🧾 Summary")
    st.write(summary)

    wa_text = urllib.parse.quote(summary)
    wa_link = f"https://api.whatsapp.com/send?text={wa_text}"
    email_link = f"mailto:?subject=MedLens Summary&body={wa_text}"

    st.markdown(f"""
    <a href="{wa_link}" target="_blank">💬 Share on WhatsApp</a> | 
    <a href="{email_link}" target="_blank">📧 Share via Email</a>
    """, unsafe_allow_html=True)

    st.download_button("⬇️ Download Summary", data=summary, file_name=f"{fname}_summary.txt")

    st.markdown("</div>", unsafe_allow_html=True)
else:
    st.info("Upload a report (PDF or image). For best results, use clear digital files.")

st.markdown("<hr>", unsafe_allow_html=True)
st.markdown("<div class='fade' style='font-size:13px;opacity:0.8'>MedLens • Gemini AI • Educational use only.</div>", unsafe_allow_html=True)

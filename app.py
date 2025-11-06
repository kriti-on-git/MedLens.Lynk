import streamlit as st
from dotenv import load_dotenv
import os
from google import genai

# Load API key
load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")

# Initialize Gemini client
client = genai.Client(api_key=api_key)

st.set_page_config(page_title="MedLens", page_icon="🩺", layout="wide")

st.title("🩺 MedLens - AI Medical Report Summarizer")

uploaded_file = st.file_uploader("Upload your medical report (PDF or Image):", type=["pdf", "png", "jpg", "jpeg"])

if uploaded_file is not None:
    st.success("✅ File uploaded successfully!")
    
    # Basic content extraction mock
    file_name = uploaded_file.name
    st.write(f"**File Name:** {file_name}")
    
    # Ask Gemini for summary
    with st.spinner("🔍 Analyzing report..."):
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=f"Summarize this medical report in simple terms: {file_name}"
        )

    st.subheader("🧠 AI Summary:")
    st.write(response.text)
else:
    st.info("Please upload a report to start.")

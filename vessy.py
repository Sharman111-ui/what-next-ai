import streamlit as st
from groq import Groq
import os
import json
from PIL import Image, ImageDraw

# ================= CONFIG =================
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
llm = Groq(api_key=GROQ_API_KEY)

st.set_page_config(page_title="Visual WhatNext AI", layout="centered")
st.title("Visual WhatNext AI 🧠")
st.caption("Understand the error. Know exactly what to do next.")

# ================= INPUT =================
context = st.text_area(
    "Paste error / output / logs here",
    height=220,
    placeholder="Paste terminal output, stack trace, warnings, or error messages..."
)

uploaded_image = st.file_uploader(
    "Upload screenshot (optional)",
    type=["png", "jpg", "jpeg"]
)

# ================= SYSTEM PROMPT =================
SYSTEM_PROMPT = """
You are a senior software support engineer helping users debug code errors.

Your task:
- Identify whether the situation is WORKING, WARNING, or ERROR
- Identify the programming language if possible
- Summarize the issue in one short line
- Explain what is happening in simple terms
- Give up to 3 clear next steps
- If the fix is uncertain, ask ONE clarifying question instead
- Suggest visual labels ONLY if a screenshot is relevant

Rules:
- Do NOT hallucinate code or UI elements
- If logs are incomplete, say so
- If the program is running with only warnings, say it is safe
- Be concise, practical, and honest

Return ONLY valid JSON in this exact format:
{
  "status": "WORKING | WARNING | ERROR",
  "language": "python | javascript | unknown",
  "error_summary": "...",
  "explanation": "...",
  "next_steps": ["step 1", "step 2"],
  "confidence": "high | medium | low",
  "visual_labels": []
}
"""

# ================= AI DIAGNOSIS =================
def diagnose(context_text, has_image):
    if not context_text.strip():
        return {
            "status": "WORKING",
            "language": "unknown",
            "error_summary": "No error provided",
            "explanation": "No logs or errors were shared.",
            "next_steps": ["Paste the error or output you want checked."],
            "confidence": "high",
            "visual_labels": []
        }

    user_content = context_text
    if has_image:
        user_content += "\n\nNOTE: The user also uploaded a screenshot related to this issue."

    res = llm.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content}
        ],
        temperature=0,
        max_tokens=500
    )

    try:
        data = json.loads(res.choices[0].message.content)
        data.setdefault("visual_labels", [])
        data.setdefault("next_steps", [])
        return data
    except Exception:
        return {
            "status": "ERROR",
            "language": "unknown",
            "error_summary": "Unclear or malformed error",
            "explanation": "The error output could not be reliably interpreted.",
            "next_steps": ["Retry with only the relevant error lines."],
            "confidence": "low",
            "visual_labels": []
        }

# ================= IMAGE LABELING =================
def annotate_with_labels(image, labels):
    draw = ImageDraw.Draw(image)

    box_color = (255, 80, 80)
    bg_color = (255, 220, 220)
    text_color = (0, 0, 0)

    y = 30
    for i, label in enumerate(labels, start=1):
        text = f"{i}. {label}"
        box_width = len(text) * 9 + 20

        draw.rectangle(
            (20, y - 8, 20 + box_width, y + 28),
            fill=bg_color,
            outline=box_color,
            width=2
        )
        draw.text((30, y), text, fill=text_color)
        y += 45

    return image

# ================= ACTION =================
if st.button("Diagnose"):
    with st.spinner("Analyzing..."):
        result = diagnose(context, uploaded_image is not None)

    status = result["status"]
    language = result["language"]
    summary = result["error_summary"]
    explanation = result["explanation"]
    steps = result["next_steps"]
    confidence = result["confidence"]
    labels = result["visual_labels"]

    # ---- STATUS ----
    if status == "WORKING":
        st.success("✅ WORKING")
    elif status == "WARNING":
        st.warning("⚠️ WARNING")
    else:
        st.error("❌ ERROR")

    # ---- META ----
    st.markdown(f"**Language:** `{language}`")
    st.markdown(f"**Confidence:** `{confidence}`")

    # ---- SUMMARY ----
    st.markdown("### Issue summary")
    st.write(summary)

    # ---- EXPLANATION ----
    st.markdown("### What’s happening")
    st.write(explanation)

    # ---- NEXT STEPS ----
    st.markdown("### What to do next")
    for i, step in enumerate(steps, start=1):
        st.code(f"{i}. {step}")

    # ---- VISUAL OUTPUT ----
    if uploaded_image and labels:
        st.markdown("### Visual explanation")
        img = Image.open(uploaded_image).convert("RGB")
        annotated = annotate_with_labels(img, labels)
        st.image(annotated, use_column_width=True)


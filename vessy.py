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
st.caption("Understand what’s happening. Know the next step.")

# ================= INPUT =================
context = st.text_area(
    "Paste error / output / logs here",
    height=220,
    placeholder="Paste terminal output, warnings, or error messages..."
)

uploaded_image = st.file_uploader(
    "Upload screenshot (optional)",
    type=["png", "jpg", "jpeg"]
)

# ================= SYSTEM PROMPT =================
SYSTEM_PROMPT = """
You are a developer diagnosis agent.

Your task:
- Decide if the situation is WORKING, WARNING, or ERROR
- Explain what is happening in simple terms
- Give exactly ONE next action
- If helpful, suggest visual labels for the uploaded screenshot

Rules:
- If the program is running and only warnings are shown, say it is safe
- Do NOT suggest fixes when nothing is broken
- Do NOT hallucinate UI elements
- Labels must describe WHAT IS HAPPENING, not UI names
- Be concise and confident

Return ONLY valid JSON in this exact format:
{
  "status": "WORKING | WARNING | ERROR",
  "explanation": "...",
  "next_step": "...",
  "visual_labels": ["label 1", "label 2"]
}
"""

# ================= AI DIAGNOSIS =================
def diagnose(context_text):
    if not context_text.strip():
        return {
            "status": "WORKING",
            "explanation": "No error or output was provided.",
            "next_step": "Paste the output or error you want checked.",
            "visual_labels": []
        }

    res = llm.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": context_text}
        ],
        temperature=0,
        max_tokens=400
    )

    try:
        data = json.loads(res.choices[0].message.content)
        data.setdefault("visual_labels", [])
        return data
    except:
        return {
            "status": "ERROR",
            "explanation": "The output could not be interpreted reliably.",
            "next_step": "Retry with only the relevant error lines.",
            "visual_labels": []
        }

# ================= IMAGE LABELING =================
def annotate_with_labels(image, labels):
    draw = ImageDraw.Draw(image)
    w, h = image.size

    box_color = (255, 80, 80)
    bg_color = (255, 220, 220)
    text_color = (0, 0, 0)

    y = 30
    for i, label in enumerate(labels, start=1):
        text = f"{i}. {label}"
        box_width = len(text) * 10 + 20

        draw.rectangle(
            (20, y - 10, 20 + box_width, y + 30),
            fill=bg_color,
            outline=box_color,
            width=2
        )
        draw.text((30, y), text, fill=text_color)
        y += 50

    return image

# ================= ACTION =================
if st.button("Diagnose"):
    with st.spinner("Analyzing..."):
        result = diagnose(context)

    status = result["status"]
    explanation = result["explanation"]
    next_step = result["next_step"]
    labels = result["visual_labels"]

    # ---- STATUS ----
    if status == "WORKING":
        st.success("✅ WORKING")
    elif status == "WARNING":
        st.warning("⚠️ WARNING")
    else:
        st.error("❌ ERROR")

    # ---- TEXT OUTPUT ----
    st.markdown("### What’s happening")
    st.write(explanation)

    st.markdown("### Next step")
    st.code(next_step)

    # ---- VISUAL OUTPUT ----
    if uploaded_image and labels:
        st.markdown("### Visual explanation")
        img = Image.open(uploaded_image).convert("RGB")
        annotated = annotate_with_labels(img, labels)
        st.image(annotated, use_column_width=True)

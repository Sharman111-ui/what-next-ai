import streamlit as st
from groq import Groq
import os
import json
from PIL import Image, ImageDraw
import pytesseract

# ================= CONFIG =================
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
llm = Groq(api_key=GROQ_API_KEY)

st.set_page_config(page_title="Visual WhatNext AI", layout="centered")
st.title("Visual WhatNext AI 🧠")
st.caption("Upload a screenshot. We tell you exactly what to do next.")

# ================= INPUT =================
context = st.text_area(
    "Paste error / logs (optional)",
    height=200,
    placeholder="Paste error messages, logs, or output here..."
)

uploaded_image = st.file_uploader(
    "Upload screenshot (recommended)",
    type=["png", "jpg", "jpeg"]
)

# ================= SYSTEM PROMPT =================
SYSTEM_PROMPT = """
You are a senior technical support engineer.

Your task:
- Understand what the user is seeing on their screen
- Decide if the state is WORKING, WARNING, or ERROR
- Identify what the user is trying to do
- Explain the problem simply
- Give at most 3 clear next steps
- Add visual_labels ONLY if they clearly exist on the screen
- Ask ONE clarifying question if unsure

Rules:
- Use visible screen text as ground truth
- Do NOT invent UI elements
- Be concise, honest, and practical

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

# ================= OCR =================
def extract_screen_text(image):
    try:
        text = pytesseract.image_to_string(image)
        text = text.strip()
        return text if text else None
    except Exception:
        return None

# ================= AI LOGIC =================
def diagnose(context_text, image_text):
    if not context_text.strip() and not image_text:
        return {
            "status": "WORKING",
            "language": "unknown",
            "error_summary": "No information provided",
            "explanation": "No logs or screen content were shared.",
            "next_steps": ["Paste logs or upload a screenshot where you are stuck."],
            "confidence": "high",
            "visual_labels": []
        }

    user_content = ""

    if context_text.strip():
        user_content += f"LOGS / TEXT:\n{context_text}\n\n"

    if image_text:
        user_content += f"VISIBLE TEXT FROM SCREENSHOT:\n{image_text}\n\n"

    user_content += "Base your reasoning strictly on the visible information."

    res = llm.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content}
        ],
        temperature=0,
        max_tokens=600
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
            "error_summary": "Unclear issue",
            "explanation": "The screenshot or logs were not clear enough to diagnose.",
            "next_steps": ["Upload a clearer screenshot or only the relevant error."],
            "confidence": "low",
            "visual_labels": []
        }

# ================= VISUAL OVERLAY =================
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
if st.button("Analyze & Guide"):
    with st.spinner("Understanding the screen..."):
        image_text = None
        img = None

        if uploaded_image:
            img = Image.open(uploaded_image).convert("RGB")
            image_text = extract_screen_text(img)

        result = diagnose(context, image_text)

    # ---- STATUS ----
    if result["status"] == "WORKING":
        st.success("✅ WORKING")
    elif result["status"] == "WARNING":
        st.warning("⚠️ WARNING")
    else:
        st.error("❌ ERROR")

    # ---- META ----
    st.markdown(f"**Language:** `{result['language']}`")
    st.markdown(f"**Confidence:** `{result['confidence']}`")

    # ---- SUMMARY ----
    st.markdown("### Issue summary")
    st.write(result["error_summary"])

    # ---- EXPLANATION ----
    st.markdown("### What’s happening")
    st.write(result["explanation"])

    # ---- NEXT STEPS ----
    st.markdown("### What to do next")
    for i, step in enumerate(result["next_steps"], start=1):
        st.code(f"{i}. {step}")

    # ---- VISUAL ----
    if img and result["visual_labels"]:
        st.markdown("### Visual guidance")
        annotated = annotate_with_labels(img.copy(), result["visual_labels"])
        st.image(annotated, use_column_width=True)



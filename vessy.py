import streamlit as st
from groq import Groq
import os
import json
from PIL import Image, ImageDraw
import pytesseract
import cv2
import numpy as np
from datetime import datetime

# ================= CONFIG =================
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
llm = Groq(api_key=GROQ_API_KEY)

st.set_page_config(page_title="Visual Troubleshoot AI", layout="centered")
st.title("Visual Troubleshoot AI 🧠")
st.caption("Upload a screenshot or logs. We diagnose the problem and tell you what to do next.")

# ================= INPUT =================
context = st.text_area(
    "Paste error / logs (optional)",
    height=200,
    placeholder="Paste error messages, stack traces, logs, or output here..."
)

uploaded_image = st.file_uploader(
    "Upload screenshot (recommended)",
    type=["png", "jpg", "jpeg"]
)

# ================= SYSTEM PROMPT =================
SYSTEM_PROMPT = """
You are an expert troubleshooting engine.

Your task:
- Diagnose the problem strictly from visible information
- Identify the MOST LIKELY root cause
- Choose a practical fix path
- Avoid generic explanations
- Prefer actions that can be tested immediately

Rules:
- Use visible text as ground truth
- Do NOT invent UI elements or errors
- Do NOT exceed 3 steps
- Each step must have an expected result
- Ask ONE clarifying question only if absolutely required

Return ONLY valid JSON in this exact format:
{
  "status": "WORKING | WARNING | ERROR",
  "domain": "python | ml | system | ui | unknown",
  "error_summary": "...",
  "root_cause": "...",
  "explanation": "...",
  "next_steps": [
    {
      "action": "...",
      "expected_result": "..."
    }
  ],
  "confidence": "high | medium | low",
  "needs_verification": true,
  "visual_labels": []
}
"""

# ================= OCR =================
def extract_screen_text(image):
    try:
        img = np.array(image)
        gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
        gray = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)[1]
        text = pytesseract.image_to_string(gray, config="--psm 6")
        return text.strip() if text.strip() else None
    except Exception:
        return None

# ================= AI LOGIC =================
def diagnose(context_text, image_text):
    if not context_text.strip() and not image_text:
        return {
            "status": "WORKING",
            "domain": "unknown",
            "error_summary": "No information provided",
            "root_cause": "Insufficient input",
            "explanation": "No logs or readable screen content were shared.",
            "next_steps": [
                {
                    "action": "Upload a clearer screenshot or paste the exact error message",
                    "expected_result": "The issue can be diagnosed accurately"
                }
            ],
            "confidence": "high",
            "needs_verification": False,
            "visual_labels": []
        }

    user_content = ""

    if context_text.strip():
        user_content += f"LOGS / TEXT:\n{context_text}\n\n"

    if image_text:
        user_content += f"VISIBLE TEXT FROM SCREENSHOT:\n{image_text}\n\n"

    user_content += "Base your diagnosis strictly on the information above."

    res = llm.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content}
        ],
        temperature=0,
        max_tokens=700
    )

    try:
        data = json.loads(res.choices[0].message.content)
        data.setdefault("visual_labels", [])
        data.setdefault("next_steps", [])
        return data
    except Exception:
        return {
            "status": "ERROR",
            "domain": "unknown",
            "error_summary": "Unable to parse diagnosis",
            "root_cause": "Model output was unclear",
            "explanation": "The information provided was not sufficient to form a reliable diagnosis.",
            "next_steps": [
                {
                    "action": "Provide only the relevant error or a clearer screenshot",
                    "expected_result": "The root cause becomes identifiable"
                }
            ],
            "confidence": "low",
            "needs_verification": True,
            "visual_labels": []
        }

# ================= VISUAL OVERLAY =================
def annotate_with_labels(image, labels):
    draw = ImageDraw.Draw(image)
    y = 30

    for i, label in enumerate(labels, start=1):
        text = f"{i}. {label}"
        box_width = len(text) * 9 + 20

        draw.rectangle(
            (20, y - 8, 20 + box_width, y + 28),
            fill=(255, 220, 220),
            outline=(255, 80, 80),
            width=2
        )
        draw.text((30, y), text, fill=(0, 0, 0))
        y += 45

    return image

# ================= ACTION =================
if st.button("Diagnose & Fix"):
    with st.spinner("Troubleshooting..."):
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
    st.markdown(f"**Domain:** `{result['domain']}`")
    st.markdown(f"**Confidence:** `{result['confidence']}`")

    # ---- SUMMARY ----
    st.markdown("### Issue summary")
    st.write(result["error_summary"])

    # ---- ROOT CAUSE ----
    st.markdown("### Most likely root cause")
    st.write(result["root_cause"])

    # ---- EXPLANATION ----
    st.markdown("### What’s happening")
    st.write(result["explanation"])

    # ---- NEXT STEPS ----
    st.markdown("### What to do next")
    for step in result["next_steps"]:
        st.code(f"- {step['action']}\n  Expected: {step['expected_result']}")

    # ---- VISUAL ----
    if img and result["visual_labels"]:
        st.markdown("### Visual guidance")
        annotated = annotate_with_labels(img.copy(), result["visual_labels"])
        st.image(annotated, use_column_width=True)

    # ---- FEEDBACK LOOP (IMPORTANT) ----
    st.markdown("### Did this fix the problem?")
    feedback = st.radio(
        "Feedback",
        ["Yes", "Partially", "No"],
        index=None
    )

    if feedback:
        log = {
            "timestamp": datetime.utcnow().isoformat(),
            "context": context,
            "image_text": image_text,
            "diagnosis": result,
            "feedback": feedback
        }
        st.success("Feedback recorded. This helps the system improve.")




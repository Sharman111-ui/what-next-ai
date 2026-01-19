import streamlit as st
from groq import Groq
import os
import json
from PIL import Image, ImageDraw
import pytesseract

# ================= CONFIG =================
st.set_page_config(
    page_title="BREAKPOINT",
    layout="centered"
)

st.title("🟥 BREAKPOINT")
st.caption("See where things went wrong. Visually.")

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
llm = Groq(api_key=GROQ_API_KEY)

# ================= INPUT =================
context = st.text_area(
    "Paste error / logs (optional)",
    height=160,
    placeholder="Paste only the relevant error or output..."
)

uploaded_image = st.file_uploader(
    "Upload screenshot (recommended)",
    type=["png", "jpg", "jpeg"]
)

# ================= SYSTEM PROMPT =================
SYSTEM_PROMPT = """
You are BREAKPOINT, a visual reasoning engine.

Your job:
- Infer what the user is trying to do
- Identify where the process diverged from expectation
- Think in cause → effect → failure
- Prefer visual understanding over text

Rules:
- Use ONLY visible information
- Never invent UI elements
- Always produce at least ONE visual insight
- Be concise, practical, and precise

Return ONLY valid JSON in this format:

{
  "status": "BLOCKING_ERROR | RISKY_STATE | SAFE_BUT_SUBOPTIMAL",
  "language": "python | javascript | unknown",
  "error_summary": "...",
  "explanation": "...",
  "expected_vs_actual": {
    "expected": "...",
    "actual": "..."
  },
  "next_steps": ["step 1", "step 2", "step 3"],
  "confidence": "high | medium | low",
  "visual_labels": [
    {
      "label": "...",
      "severity": "error | warning | info"
    }
  ]
}
"""

# ================= OCR =================
def extract_screen_text(image):
    try:
        text = pytesseract.image_to_string(image)
        return text.strip() if text.strip() else None
    except Exception:
        return None

# ================= AI CORE =================
def diagnose(context_text, image_text):
    if not context_text.strip() and not image_text:
        return {
            "status": "SAFE_BUT_SUBOPTIMAL",
            "language": "unknown",
            "error_summary": "No failure context provided",
            "explanation": "There is not enough visible information to identify a breakpoint.",
            "expected_vs_actual": {
                "expected": "System should behave normally",
                "actual": "No observable failure provided"
            },
            "next_steps": [
                "Upload a screenshot where the issue is visible",
                "Paste only the specific error message"
            ],
            "confidence": "high",
            "visual_labels": [
                {
                    "label": "No failure signal visible",
                    "severity": "info"
                }
            ]
        }

    user_content = ""

    if context_text.strip():
        user_content += f"LOGS / TEXT:\n{context_text}\n\n"

    if image_text:
        user_content += f"VISIBLE SCREEN TEXT:\n{image_text}\n\n"

    user_content += "Reason strictly from the visible evidence."

    response = llm.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content}
        ],
        temperature=0,
        max_tokens=700
    )

    try:
        return json.loads(response.choices[0].message.content)
    except Exception:
        return {
            "status": "BLOCKING_ERROR",
            "language": "unknown",
            "error_summary": "Breakpoint unclear",
            "explanation": "The failure signal could not be reliably interpreted.",
            "expected_vs_actual": {
                "expected": "System continues execution",
                "actual": "Execution halted or misbehaved"
            },
            "next_steps": [
                "Upload a clearer screenshot",
                "Crop the image to the error area"
            ],
            "confidence": "low",
            "visual_labels": [
                {
                    "label": "Ambiguous failure region",
                    "severity": "warning"
                }
            ]
        }

# ================= VISUAL OVERLAY =================
def annotate(image, labels):
    draw = ImageDraw.Draw(image)
    y = 30

    color_map = {
        "error": (255, 80, 80),
        "warning": (255, 200, 80),
        "info": (120, 180, 255)
    }

    for i, item in enumerate(labels, start=1):
        text = f"{i}. {item['label']}"
        color = color_map.get(item["severity"], (200, 200, 200))
        width = len(text) * 9 + 20

        draw.rectangle(
            (20, y - 8, 20 + width, y + 28),
            fill=(255, 255, 255),
            outline=color,
            width=3
        )
        draw.text((30, y), text, fill=(0, 0, 0))
        y += 45

    return image

# ================= ACTION =================
if st.button("Analyze Breakpoint"):
    with st.spinner("Tracing failure..."):
        img = None
        image_text = None

        if uploaded_image:
            img = Image.open(uploaded_image).convert("RGB")
            image_text = extract_screen_text(img)

        result = diagnose(context, image_text)

    # ===== STATUS =====
    if result["status"] == "BLOCKING_ERROR":
        st.error("🟥 BLOCKING ERROR")
    elif result["status"] == "RISKY_STATE":
        st.warning("🟨 RISKY STATE")
    else:
        st.success("🟦 SAFE BUT SUBOPTIMAL")

    st.markdown(f"**Language:** `{result['language']}`")
    st.markdown(f"**Confidence:** `{result['confidence']}`")

    # ===== VISUAL FIRST =====
    if img and result["visual_labels"]:
        st.markdown("### Visual Breakpoints")
        annotated_img = annotate(img.copy(), result["visual_labels"])
        st.image(annotated_img, use_column_width=True)

    # ===== EXPLANATION =====
    st.markdown("### What broke")
    st.write(result["error_summary"])

    st.markdown("### Why it broke")
    st.write(result["explanation"])

    st.markdown("### Expected vs Actual")
    st.success(f"**Expected:** {result['expected_vs_actual']['expected']}")
    st.error(f"**Actual:** {result['expected_vs_actual']['actual']}")

    st.markdown("### What to do next")
    for i, step in enumerate(result["next_steps"], start=1):
        st.code(f"{i}. {step}")



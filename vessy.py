import streamlit as st
from groq import Groq
import os
import json
from PIL import Image, ImageDraw
import pytesseract

# ================= PAGE CONFIG =================
st.set_page_config(
    page_title="INTERPRETER",
    layout="centered"
)

st.title("🧩 INTERPRETER")
st.caption("We explain what your app is trying to say.")

# ================= API =================
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
llm = Groq(api_key=GROQ_API_KEY)

# ================= INPUT =================
uploaded_image = st.file_uploader(
    "Upload a screenshot of the problem",
    type=["png", "jpg", "jpeg"]
)

user_note = st.text_area(
    "What were you trying to do? (optional)",
    placeholder="Example: Sending money, logging in, opening app",
    height=90
)

# ================= SYSTEM PROMPT =================
SYSTEM_PROMPT = """
You are INTERPRETER — an AI that translates software screens into human meaning.

Your job:
- Understand what the screen is saying
- Explain it in calm, simple language
- Reduce user confusion and panic
- Tell the user what to do next

Rules:
- Use ONLY what is visible on the screen or written by the user
- Do NOT use technical terms
- Do NOT guess hidden system behavior
- Speak like a helpful human, not tech support

Return ONLY valid JSON in this format:

{
  "screen_type": "payment | banking | system | app | unknown",
  "plain_meaning": "One clear sentence explaining what this screen means",
  "what_is_happening": "Short calm explanation in simple words",
  "risk_level": "none | low | medium | high",
  "what_to_do_now": [
    "step 1",
    "step 2",
    "step 3"
  ],
  "confidence": "high | medium | low",
  "visual_clues": [
    {
      "label": "What this part of the screen indicates",
      "severity": "info | warning"
    }
  ]
}
"""

# ================= OCR =================
def read_screen(image):
    try:
        text = pytesseract.image_to_string(image)
        return text.strip() if text.strip() else None
    except:
        return None

# ================= AI CORE =================
def interpret(screen_text, user_note):
    if not screen_text and not user_note.strip():
        return {
            "screen_type": "unknown",
            "plain_meaning": "No clear message found on the screen",
            "what_is_happening": "The screenshot does not show a clear problem.",
            "risk_level": "none",
            "what_to_do_now": [
                "Upload a screenshot where the message or error is visible"
            ],
            "confidence": "high",
            "visual_clues": [
                {
                    "label": "No readable message detected",
                    "severity": "info"
                }
            ]
        }

    content = ""
    if screen_text:
        content += f"SCREEN TEXT:\n{screen_text}\n\n"
    if user_note.strip():
        content += f"USER INTENT:\n{user_note}\n\n"

    response = llm.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": content}
        ],
        temperature=0,
        max_tokens=600
    )

    try:
        return json.loads(response.choices[0].message.content)
    except:
        return {
            "screen_type": "unknown",
            "plain_meaning": "This screen is unclear",
            "what_is_happening": "The message could not be confidently understood.",
            "risk_level": "medium",
            "what_to_do_now": [
                "Try uploading a clearer screenshot",
                "Make sure the message is readable"
            ],
            "confidence": "low",
            "visual_clues": [
                {
                    "label": "Unclear or incomplete screen message",
                    "severity": "warning"
                }
            ]
        }

# ================= VISUAL OVERLAY =================
def draw_clues(image, clues):
    draw = ImageDraw.Draw(image)
    y = 30

    for i, c in enumerate(clues, 1):
        text = f"{i}. {c['label']}"
        color = (255, 180, 80) if c["severity"] == "warning" else (120, 170, 255)
        width = len(text) * 9 + 20

        draw.rectangle(
            (20, y - 8, 20 + width, y + 28),
            outline=color,
            width=3
        )
        draw.text((30, y), text, fill=(0, 0, 0))
        y += 45

    return image

# ================= ACTION =================
if st.button("Explain this screen"):
    with st.spinner("Interpreting the screen..."):
        img = None
        screen_text = None

        if uploaded_image:
            img = Image.open(uploaded_image).convert("RGB")
            screen_text = read_screen(img)

        result = interpret(screen_text, user_note)

    # ===== VISUAL FIRST =====
    if img and result["visual_clues"]:
        st.image(draw_clues(img.copy(), result["visual_clues"]), use_column_width=True)

    # ===== MEANING =====
    st.markdown("### What this screen means")
    st.write(result["plain_meaning"])

    st.markdown("### What is happening")
    st.write(result["what_is_happening"])

    # ===== RISK =====
    if result["risk_level"] == "high":
        st.error("⚠️ High risk — do not retry immediately")
    elif result["risk_level"] == "medium":
        st.warning("⚠️ Some risk — proceed carefully")
    else:
        st.success("✅ No immediate risk detected")

    # ===== NEXT STEPS =====
    st.markdown("### What you should do now")
    for step in result["what_to_do_now"]:
        st.write("•", step)

    st.caption(f"Confidence: {result['confidence']}")

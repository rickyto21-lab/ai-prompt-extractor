import streamlit as st
import google.generativeai as genai
import requests, json, re
from bs4 import BeautifulSoup
from urllib.parse import quote

# ====== 🔐 KEYS ======
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", "")
STABILITY_API_KEY = st.secrets.get("STABILITY_API_KEY", "")
NOTION_API_KEY = st.secrets.get("NOTION_API_KEY", "")
NOTION_DB_ID = st.secrets.get("NOTION_DB_ID", "")

# ====== INIT ======
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

st.set_page_config(page_title="AI Prompt Extractor", layout="wide")
st.title("🧠 AI Prompt Extractor PRO (No Zero Mode)")

# ====== SCRAPER ======
def fetch(url):
    try:
        r = requests.get(url, headers={"User-Agent":"Mozilla/5.0"}, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        text = soup.get_text(separator="\n")
        return text[:4000]
    except Exception as e:
        return ""

# ====== AI EXTRACT ======
def ai_extract(text):
    prompt = f"""
You MUST return at least 3 prompts.

If no prompt exists, GENERATE based on topic.

ONLY return JSON array:
[
  {{
    "category":"...",
    "prompt":"...",
    "description":"...",
    "preview_prompt":"one word"
  }}
]

TEXT:
{text[:3000]}
"""

    try:
        res = model.generate_content(prompt)
        raw = res.text.strip()

        st.expander("🔍 Debug AI Output").write(raw[:1000])

        match = re.search(r"\[.*\]", raw, re.S)

        if match:
            return json.loads(match.group())
        else:
            return []
    except Exception as e:
        st.error(f"AI error: {e}")
        return []

# ====== FALLBACK ======
def fallback():
    return [
        {
            "category": "general",
            "prompt": "cinematic city skyline at sunset, ultra realistic, 8k",
            "description": "fallback generated",
            "preview_prompt": "city"
        },
        {
            "category": "architecture",
            "prompt": "modern luxury house, sunset lighting, minimal design",
            "description": "fallback generated",
            "preview_prompt": "house"
        },
        {
            "category": "nature",
            "prompt": "beautiful mountain landscape, golden hour, ultra detailed",
            "description": "fallback generated",
            "preview_prompt": "mountain"
        }
    ]

# ====== IMAGE ======
def generate_image(prompt):
    if not STABILITY_API_KEY:
        return None

    try:
        r = requests.post(
            "https://api.stability.ai/v2beta/stable-image/generate/core",
            headers={
                "Authorization": f"Bearer {STABILITY_API_KEY}",
                "Accept": "image/*"
            },
            files={"none": ''},
            data={
                "prompt": prompt[:300],
                "output_format": "png"
            },
            timeout=20
        )

        if r.status_code == 200:
            return r.content
    except:
        pass

    return None

# ====== NOTION ======
def save_notion(prompt, category, desc):
    if not NOTION_API_KEY:
        return

    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }

    data = {
        "parent": {"database_id": NOTION_DB_ID},
        "properties": {
            "Name": {"title":[{"text":{"content": prompt[:50]}}]},
            "Category": {"rich_text":[{"text":{"content": category}}]},
        },
        "children":[
            {
                "object":"block",
                "type":"code",
                "code":{
                    "rich_text":[{"text":{"content": prompt}}],
                    "language":"plain text"
                }
            }
        ]
    }

    requests.post("https://api.notion.com/v1/pages", headers=headers, json=data)

# ====== UI ======
tab1, tab2 = st.tabs(["✏️ Text", "🌐 URL"])

text = ""

with tab1:
    text = st.text_area("Paste content")

with tab2:
    url = st.text_input("Enter URL")
    if url:
        text = fetch(url)
        st.expander("📄 Scraped Text").write(text[:1000])

# ====== RUN ======
if st.button("🚀 Extract"):
    if not text:
        st.warning("No input")
        st.stop()

    data = ai_extract(text)

    if not data:
        st.warning("⚠️ AI failed → using fallback")
        data = fallback()

    st.success(f"{len(data)} prompts ready")

    for i, item in enumerate(data):
        col1, col2 = st.columns([1,2])

        prompt = item.get("prompt","")
        cat = item.get("category","")
        desc = item.get("description","")

        with col1:
            with st.spinner("🎨 Generating..."):
                img = generate_image(prompt)
                if img:
                    st.image(img)

        with col2:
            st.subheader(cat)
            st.code(prompt)
            st.write(desc)

            if st.button("💾 Save", key=i):
                save_notion(prompt, cat, desc)
                st.success("Saved to Notion")

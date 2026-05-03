import streamlit as st
import google.generativeai as genai
import requests, json, re
from bs4 import BeautifulSoup
from urllib.parse import quote

# ====== 🔐 SECRETS ======
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", "")
NOTION_API_KEY = st.secrets.get("NOTION_API_KEY", "")
NOTION_DB_ID = st.secrets.get("NOTION_DB_ID", "")
STABILITY_API_KEY = st.secrets.get("STABILITY_API_KEY", "")

# ====== INIT ======
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

st.set_page_config(page_title="AI Prompt Extractor", layout="wide")
st.title("🧠 AI Prompt Extractor Pro")

# ====== SCRAPER ======
def fetch_website_content(url):
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        return soup.get_text()[:4000]
    except Exception as e:
        return f"ERROR: {e}"

# ====== AI EXTRACT ======
def ai_extract(text):
    prompt = f"""
    Extract AI image prompts and return JSON array:
    [
      {{
        "category": "...",
        "prompt": "...",
        "description": "...",
        "preview_prompt": "1-2 words"
      }}
    ]
    TEXT:
    {text}
    """

    try:
        res = model.generate_content(prompt)
        match = re.search(r"\[.*\]", res.text, re.S)
        return json.loads(match.group()) if match else []
    except:
        return []

# ====== 🎨 AI IMAGE (Stability) ======
def generate_image(prompt):
    if not STABILITY_API_KEY:
        return None

    try:
        url = "https://api.stability.ai/v2beta/stable-image/generate/core"

        response = requests.post(
            url,
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

        if response.status_code == 200:
            return response.content
        else:
            return None
    except:
        return None

# ====== 📦 NOTION ======
def save_to_notion(prompt, category, desc, image_url):
    if not NOTION_API_KEY or not NOTION_DB_ID:
        return

    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }

    data = {
        "parent": {"database_id": NOTION_DB_ID},
        "cover": {"type": "external", "external": {"url": image_url}},
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

input_text = ""

with tab1:
    input_text = st.text_area("Paste text")

with tab2:
    url = st.text_input("Enter URL")
    if url:
        input_text = fetch_website_content(url)

# ====== RUN ======
if st.button("🚀 Extract"):
    if not input_text:
        st.warning("No input")
        st.stop()

    with st.spinner("🤖 Extracting..."):
        data = ai_extract(input_text)

    st.success(f"{len(data)} prompts found")

    # ====== CARD UI ======
    for i, item in enumerate(data):
        col1, col2 = st.columns([1,2])

        prompt = item.get("prompt","")
        cat = item.get("category","")
        desc = item.get("description","")

        with col1:
            with st.spinner("🎨 Generating image..."):
                img = generate_image(prompt)

                if img:
                    st.image(img)
                else:
                    st.warning("No image")

        with col2:
            st.subheader(f"🏷️ {cat}")
            st.code(prompt)
            st.write(desc)

            if st.button("💾 Save to Notion", key=i):
                fake_url = f"https://dummyimage.com/600x400/000/fff&text={quote(prompt[:20])}"
                save_to_notion(prompt, cat, desc, fake_url)
                st.success("Saved!")

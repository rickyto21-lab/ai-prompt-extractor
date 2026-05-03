import streamlit as st
import google.generativeai as genai
import requests, json, re
from bs4 import BeautifulSoup

# ====== 🔐 KEYS ======
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", "")
STABILITY_API_KEY = st.secrets.get("STABILITY_API_KEY", "")
NOTION_API_KEY = st.secrets.get("NOTION_API_KEY", "")
NOTION_DB_ID = st.secrets.get("NOTION_DB_ID", "")

# ====== INIT GEMINI ======
genai.configure(api_key=GEMINI_API_KEY)

# 🔥 自動找可用 model（解決404）
models = [m.name for m in genai.list_models() if "generateContent" in m.supported_generation_methods]
MODEL_NAME = models[0] if models else None

if not MODEL_NAME:
    st.error("❌ 無可用 Gemini model（檢查 API key）")
    st.stop()

model = genai.GenerativeModel(MODEL_NAME)

# ====== UI ======
st.set_page_config(page_title="AI Prompt Extractor", layout="wide")
st.title("🧠 AI Prompt Extractor（穩定版）")

# ====== SCRAPER ======
def fetch(url):
    try:
        r = requests.get(url, headers={"User-Agent":"Mozilla/5.0"}, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        text = soup.get_text(separator="\n", strip=True)
        return text[:4000]
    except:
        return ""

# ====== AI EXTRACT（支援中文🔥） ======
def ai_extract(text):
    prompt = f"""
你是一個 AI 助手。

任務：
1. 從文章中抽取 AI 圖像 prompt
2. 如果找不到，請根據內容「生成」至少3個

⚠️ 必須輸出 JSON array
⚠️ 不可以輸出任何解釋

格式：
[
  {{
    "category": "分類",
    "prompt": "英文 prompt",
    "description": "中文說明",
    "preview_prompt": "單一英文名詞"
  }}
]

文章：
{text[:3000]}
"""

    try:
        res = model.generate_content(prompt)
        raw = res.text.strip()

        st.expander("🔍 AI原始輸出").write(raw[:1000])

        match = re.search(r"\[.*\]", raw, re.S)
        if match:
            return json.loads(match.group())
        return []

    except Exception as e:
        st.error(f"AI error: {e}")
        return []

# ====== FALLBACK（永不0） ======
def fallback():
    return [
        {
            "category": "風景",
            "prompt": "beautiful mountain landscape, sunset, ultra realistic, 8k",
            "description": "高質感山景",
            "preview_prompt": "mountain"
        },
        {
            "category": "建築",
            "prompt": "modern luxury house, minimal design, sunset lighting",
            "description": "現代建築",
            "preview_prompt": "house"
        },
        {
            "category": "城市",
            "prompt": "futuristic city, cyberpunk, neon lights",
            "description": "未來城市",
            "preview_prompt": "city"
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
            data={"prompt": prompt[:300]},
            timeout=20
        )

        if r.status_code == 200:
            return r.content
    except:
        pass

    return None

# ====== UI INPUT ======
tab1, tab2 = st.tabs(["✏️ 文字", "🌐 網址"])

text = ""

with tab1:
    text = st.text_area("貼內容")

with tab2:
    url = st.text_input("輸入網址")
    if url:
        text = fetch(url)
        st.expander("📄 抓取內容").write(text[:1000])

# ====== RUN ======
if st.button("🚀 提取"):
    if not text:
        st.warning("請輸入內容")
        st.stop()

    data = ai_extract(text)

    if not data:
        st.warning("⚠️ AI失敗 → 使用備用")
        data = fallback()

    st.success(f"完成 {len(data)} 組")

    for i, item in enumerate(data):
        col1, col2 = st.columns([1,2])

        with col1:
            img = generate_image(item["prompt"])
            if img:
                st.image(img)

        with col2:
            st.subheader(item["category"])
            st.code(item["prompt"])
            st.write(item["description"])

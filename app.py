import streamlit as st
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import pandas as pd

# ====== SAFE SECRETS ======
OPENAI_KEY = st.secrets["OPENAI_API_KEY"]
NOTION_KEY = st.secrets["NOTION_API_KEY"]
NOTION_DB = st.secrets["NOTION_DB_ID"]

HEADERS = {"User-Agent": "Mozilla/5.0"}

# ====== SCRAPE ======
def scrape(url):
    html = requests.get(url, headers=HEADERS).text
    soup = BeautifulSoup(html, "html.parser")

    text = " ".join([p.get_text() for p in soup.find_all("p")])

    images = []
    for img in soup.find_all("img"):
        if img.get("src"):
            images.append(urljoin(url, img["src"]))

    return text, images[:5]

# ====== OPENAI ======
def ai_extract(text):
    r = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENAI_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "user", "content": f"Extract AI prompts:\n{text[:2000]}"}
            ]
        }
    )

    # 🔥 debug safe
    if r.status_code != 200:
        return f"ERROR: {r.text}"

    return r.json()["choices"][0]["message"]["content"]

# ====== UI ======
st.title("🧠 AI Prompt Extractor")

url = st.text_input("Input URL")

if st.button("Run"):
    if not url:
        st.error("請輸入網址")
        st.stop()

    text, images = scrape(url)

    st.subheader("Images")
    for img in images:
        st.image(img)

    st.subheader("Result")
    result = ai_extract(text)
    st.code(result)

    df = pd.DataFrame({"result": [result]})

    st.download_button(
        "Download CSV",
        df.to_csv(index=False),
        "result.csv"
    )
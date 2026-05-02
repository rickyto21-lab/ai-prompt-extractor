import os, requests, base64, json
import pandas as pd
import streamlit as st
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from dotenv import load_dotenv

load_dotenv()

OPENAI_KEY = os.getenv("OPENAI_API_KEY")
NOTION_KEY = os.getenv("NOTION_API_KEY")
NOTION_DB = os.getenv("NOTION_DB_ID")

HEADERS = {"User-Agent": "Mozilla/5.0"}

def scrape(url):
    html = requests.get(url, headers=HEADERS).text
    soup = BeautifulSoup(html, "html.parser")

    texts = [p.get_text(strip=True) for p in soup.find_all("p")]
    full_text = "\n".join(texts)

    imgs = []
    for img in soup.find_all("img"):
        src = img.get("src")
        if src:
            imgs.append(urljoin(url, src))

    return full_text, list(set(imgs))[:5]

def ai_extract(text):
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENAI_KEY}",
        "Content-Type": "application/json"
    }

    prompt = f"抽出AI圖片prompt，輸出JSON list：{text[:3000]}"

    data = {
        "model": "gpt-4.1",
        "messages": [{"role": "user", "content": prompt}]
    }

    res = requests.post(url, headers=headers, json=data).json()
    return res["choices"][0]["message"]["content"]

def push_notion(prompt, url_src):
    url = "https://api.notion.com/v1/pages"
    headers = {
        "Authorization": f"Bearer {NOTION_KEY}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }

    data = {
        "parent": {"database_id": NOTION_DB},
        "properties": {
            "Title": {"title": [{"text": {"content": "AI Prompt"}}]},
            "Prompt": {"rich_text": [{"text": {"content": prompt[:2000]}}]},
            "Source URL": {"url": url_src}
        }
    }

    requests.post(url, headers=headers, json=data)

st.title("AI Prompt Extractor")

url = st.text_input("輸入網址")

if st.button("Run"):
    text, images = scrape(url)

    st.write("圖片：")
    for img in images:
        st.image(img)

    result = ai_extract(text)

    st.write("Prompt：")
    st.code(result)

    try:
        prompts = json.loads(result)
    except:
        prompts = [result]

    for p in prompts:
        push_notion(str(p), url)

    df = pd.DataFrame({"prompt": prompts})
    st.download_button("Download CSV", df.to_csv(index=False), "result.csv")
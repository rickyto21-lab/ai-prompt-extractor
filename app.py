import streamlit as st
from openai import OpenAI
import requests
from bs4 import BeautifulSoup
import json

# 1. 為了讓你最快成功，我們直接把 Key 寫在這裡（請替換成你「重新生成」的新 Key）
# 注意：正式上線時不建議這樣寫，但為了讓你先成功跑出第一步，這樣最快！
OPENAI_API_KEY = "sk-proj-你的新OpenAI金鑰放這裡"
NOTION_API_KEY = "ntn_你的新Notion金鑰放這裡"
NOTION_DB_ID = "9f706a0e77a783beacfa011cfaaca68f"

# 初始化 OpenAI (解決 choices 報錯的問題)
client = OpenAI(api_key=OPENAI_API_KEY)

# 設定網頁標題 (解決 st is not defined 的問題)
st.set_page_config(page_title="AI Prompt 提取神器", page_icon="🚀")
st.title("🚀 自動提取網頁 Prompt & 圖文")

# 爬蟲函數
def fetch_website_content(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 抓取文字 (限制長度避免 OpenAI token 爆掉)
        text = soup.get_text(separator='\n', strip=True)[:3000] 
        return text
    except Exception as e:
        return f"爬取失敗: {e}"

# OpenAI 提取函數 (修復了 KeyError 報錯)
def ai_extract(text):
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "你是一個 AI 助手。請從以下文章中提取出所有提到的 AI 繪圖 Prompt (提示詞)，並幫它們進行分類。"},
                {"role": "user", "content": f"請分析以下文章：\n\n{text}"}
            ]
        )
        # 這是新版 OpenAI 套件的正確寫法
        return response.choices[0].message.content
    except Exception as e:
        return f"AI 處理失敗: {e}"

# UI 介面
url_input = st.text_input("🔗 請輸入要提取的網址 (例如 ezone 的文章)：")

if st.button("⚡ 一鍵自動提取"):
    if not url_input:
        st.warning("請先輸入網址！")
    else:
        with st.spinner("🕵️‍♂️ 正在爬取網頁內容..."):
            web_text = fetch_website_content(url_input)
            
        if "爬取失敗" in web_text:
            st.error(web_text)
        else:
            with st.spinner("🤖 AI 正在努力分析並分類 Prompt..."):
                ai_result = ai_extract(web_text)
                
            st.success("✅ 提取成功！")
            st.markdown("### 📋 AI 提取與分類結果：")
            st.write(ai_result)
            
            st.info("💡 下一步：如果你確認結果沒問題，我們再來把這些結果寫入 Notion！")
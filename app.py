import streamlit as st
from openai import OpenAI
import requests
from bs4 import BeautifulSoup

# === 改成這樣！從 st.secrets 讀取，不再把 Key 寫死在這裡 ===
OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
NOTION_API_KEY = st.secrets["NOTION_API_KEY"]
NOTION_DB_ID = st.secrets["NOTION_DB_ID"]

# 初始化 OpenAI
client = OpenAI(api_key=OPENAI_API_KEY)

# ... (下面的程式碼完全不用動) ...

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

# ================= 之前的 OpenAI 和 爬蟲函數保留不變 =================
# ... (上面的程式碼保留) ...

# ================= 新的 UI 介面 (雙模式) =================
st.write("---")
# 使用分頁功能，讓你可以選擇「貼網址」或「貼文字」
tab1, tab2 = st.tabs(["🔗 貼上網址自動抓", "📝 直接貼上文章 (推薦)"])

with tab1:
    st.info("注意：有些新聞網站 (如 ezone) 有嚴格的防爬蟲機制，可能會抓取失敗。")
    url_input = st.text_input("請輸入要提取的網址：")
    if st.button("⚡ 從網址提取"):
        if not url_input:
            st.warning("請先輸入網址！")
        else:
            with st.spinner("🕵️‍♂️ 正在嘗試闖關爬取網頁..."):
                web_text = fetch_website_content(url_input)
                
            if "爬取失敗" in web_text:
                st.error("❌ 網站防火牆阻擋了抓取，請改用「📝 直接貼上文章」模式。")
                st.code(web_text) # 顯示錯誤原因
            else:
                with st.spinner("🤖 AI 正在努力分析並分類 Prompt..."):
                    ai_result = ai_extract(web_text)
                st.success("✅ 提取成功！")
                st.write(ai_result)

with tab2:
    st.info("💡 遇到網站擋爬蟲時，直接把文章內容全選複製 (Ctrl+C)，貼在下面，AI 一樣能精準處理！")
    text_input = st.text_area("請在此貼上文章內容：", height=200)
    if st.button("⚡ 從文字提取"):
        if not text_input:
            st.warning("請先貼上文章內容！")
        else:
            with st.spinner("🤖 AI 正在努力分析並分類 Prompt..."):
                # 直接把貼上的文字丟給 AI
                ai_result = ai_extract(text_input) 
            st.success("✅ 提取成功！")
            st.markdown("### 📋 AI 提取與分類結果：")
            st.write(ai_result)
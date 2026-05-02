import streamlit as st
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup

# === 1. 從密碼本讀取 Gemini 金鑰 ===
GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]

# === 2. 初始化並自動偵測可用模型 ===
genai.configure(api_key=GEMINI_API_KEY)

# 讓程式自己去問 Google 現在有哪些模型可以用
available_models = []
for m in genai.list_models():
    if 'generateContent' in m.supported_generation_methods:
        available_models.append(m.name)

# 自動挑選最好的模型 (優先選用速度快的 flash 模型)
target_model_name = available_models[0] if available_models else 'gemini-1.5-flash'
for name in available_models:
    if "flash" in name:
        target_model_name = name
        break

# 使用自動偵測到的模型
model = genai.GenerativeModel(target_model_name)

# === 以下是 UI 與處理邏輯 ===
st.set_page_config(page_title="AI Prompt 提取神器", page_icon="🚀")
st.title("🚀 自動提取網頁 Prompt & 圖文")
st.caption(f"🤖 目前自動使用的 AI 模型：{target_model_name}")

def fetch_website_content(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        text = soup.get_text(separator='\n', strip=True)[:4000] 
        return text
    except Exception as e:
        return f"爬取失敗: {e}"

def ai_extract(text):
    try:
        prompt = f"你是一個 AI 助手。請從以下文章中提取出所有提到的 AI 繪圖 Prompt (提示詞)，並幫它們進行分類。\n\n文章內容：\n{text}"
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"AI 處理失敗: {e}"

st.write("---")
tab1, tab2 = st.tabs(["📝 直接貼上文章 (推薦)", "🔗 貼上網址自動抓"])

with tab1:
    st.info("💡 遇到網站擋爬蟲時，直接把文章內容全選複製 (Ctrl+C)，貼在下面，AI 一樣能精準處理！")
    text_input = st.text_area("請在此貼上文章內容：", height=200)
    if st.button("⚡ 從文字提取"):
        if not text_input:
            st.warning("請先貼上文章內容！")
        else:
            with st.spinner("🤖 AI 正在努力分析並分類 Prompt..."):
                ai_result = ai_extract(text_input) 
            st.success("✅ 提取成功！")
            st.markdown("### 📋 AI 提取與分類結果：")
            st.write(ai_result)

with tab2:
    st.info("注意：有些新聞網站有嚴格的防爬蟲機制，可能會抓取失敗。")
    url_input = st.text_input("請輸入要提取的網址：")
    if st.button("⚡ 從網址提取"):
        if not url_input:
            st.warning("請先輸入網址！")
        else:
            with st.spinner("🕵️‍♂️ 正在嘗試闖關爬取網頁..."):
                web_text = fetch_website_content(url_input)
                
            if "爬取失敗" in web_text:
                st.error("❌ 網站防火牆阻擋了抓取，請改用「📝 直接貼上文章」模式。")
                st.code(web_text)
            else:
                with st.spinner("🤖 AI 正在努力分析並分類 Prompt..."):
                    ai_result = ai_extract(web_text)
                st.success("✅ 提取成功！")
                st.write(ai_result)

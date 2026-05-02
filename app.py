import streamlit as st
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
import urllib.parse
import json

# === 1. 從密碼本讀取金鑰 ===
GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
NOTION_API_KEY = st.secrets.get("NOTION_API_KEY", "")
NOTION_DB_ID = st.secrets.get("NOTION_DB_ID", "")

# === 2. 初始化 Gemini 模型 ===
genai.configure(api_key=GEMINI_API_KEY)
available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
target_model_name = next((name for name in available_models if "flash" in name), available_models[0] if available_models else 'gemini-1.5-flash')
model = genai.GenerativeModel(target_model_name)

st.set_page_config(page_title="AI Prompt 提取神器", page_icon="🚀", layout="wide")
st.title("🚀 AI Prompt 提取與預覽神器 (卡片版)")
st.caption("支援自動分類、免費圖片預覽、一鍵寫入 Notion")

# === 記憶體設置 ===
if "extracted_data" not in st.session_state:
    st.session_state.extracted_data = None

# === 3. 核心功能函數 ===
def fetch_website_content(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        return soup.get_text(separator='\n', strip=True)[:4000] 
    except Exception as e:
        return f"爬取失敗: {e}"

def ai_extract_to_json(text):
    prompt = f"""
    你是一個 AI 助手。請從以下文章中提取出所有提到的 AI 繪圖 Prompt (提示詞)，並進行分類。
    請務必以 JSON 陣列 (Array) 的格式輸出，不要包含任何其他多餘的文字或 markdown 標記。
    格式範例：
    [
      {{
        "category": "風景",
        "prompt": "a beautiful mountain, sunset, 8k resolution",
        "description": "用於生成高畫質的日落風景圖"
      }}
    ]
    文章內容：
    {text}
    """
    try:
        response = model.generate_content(prompt)
        result_text = response.text.strip()
        if result_text.startswith("```json"): result_text = result_text[7:]
        if result_text.startswith("```"): result_text = result_text[3:]
        if result_text.endswith("```"): result_text = result_text[:-3]
        return json.loads(result_text.strip())
    except Exception as e:
        return None

def save_to_notion(prompt_text, category, description):
    if not NOTION_API_KEY or not NOTION_DB_ID:
        return False, "Notion 金鑰未設定！"
        
    # 🚨 修正關鍵：確保這裡只有純文字網址，沒有任何括號！
    url = "[https://api.notion.com/v1/pages](https://api.notion.com/v1/pages)" 
    
    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }
    data = {
        "parent": {"database_id": NOTION_DB_ID.strip()},
        "properties": {
            "Name": {"title": [{"text": {"content": prompt_text[:1500]}}]},
            "Category": {"rich_text": [{"text": {"content": str(category)[:500]}}]},
            "Description": {"rich_text": [{"text": {"content": str(description)[:500]}}]}
        }
    }
    
    try:
        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 200:
            return True, "✅ 成功寫入 Notion！"
        else:
            return False, f"❌ 寫入失敗 (代碼 {response.status_code}): {response.text}"
    except Exception as e:
        return False, f"❌ 網路連線錯誤: {e}"

# === 4. UI 介面與顯示邏輯 ===
st.write("---")
tab1, tab2 = st.tabs(["📝 直接貼上文章", "🔗 貼上網址自動抓"])

with tab1:
    text_input = st.text_area("請在此貼上文章內容：", height=150)
    if st.button("⚡ 從文字提取"):
        if text_input:
            with st.spinner("🤖 AI 正在抽取並生成 JSON 卡片資料..."):
                st.session_state.extracted_data = ai_extract_to_json(text_input)

with tab2:
    url_input = st.text_input("請輸入要提取的網址：")
    if st.button("⚡ 從網址提取"):
        if url_input:
            with st.spinner("🕵️‍♂️ 正在爬取網頁..."):
                web_text = fetch_website_content(url_input)
                if "爬取失敗" in web_text:
                    st.error(web_text)
                else:
                    with st.spinner("🤖 AI 正在抽取並生成 JSON 卡片資料..."):
                        st.session_state.extracted_data = ai_extract_to_json(web_text)

# === 5. 渲染卡片 ===
if st.session_state.extracted_data is not None:
    prompt_data_list = st.session_state.extracted_data
    
    if not isinstance(prompt_data_list, list):
         st.error("❌ AI 無法產生正確的格式，請再按一次提取按鈕。")
    else:
        st.success(f"✅ 成功提取 {len(prompt_data_list)} 組 Prompt！")
        st.write("---")
        
        for i, item in enumerate(prompt_data_list):
            cat = item.get("category", "未分類")
            prompt_text = item.get("prompt", "")
            desc = item.get("description", "無")
            
            with st.container(border=True):
                col1, col2 = st.columns([1, 2])
                
                with col1:
                    # 🚨 圖片修正關鍵：極度縮短轉碼長度
                    # 把分類名稱和一點點提示詞結合，避免產生過長的無效網址
                    image_base_prompt = f"Illustration of {cat}, {prompt_text[:20]}"
                    safe_prompt = urllib.parse.quote(image_base_prompt)
                    image_url = f"[https://image.pollinations.ai/prompt/](https://image.pollinations.ai/prompt/){safe_prompt}?width=400&height=400&nologo=true"
                    
                    # 使用 HTML 顯示，並加上 onerror，如果圖片抓不到就不顯示破圖圖示
                    html_img = f'<img src="{image_url}" style="width:100%; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);" onerror="this.style.display=\'none\'">'
                    st.markdown(html_img, unsafe_allow_html=True)
                    st.caption("AI 自動預覽圖")
                
                with col2:
                    st.subheader(f"🏷️ 分類：{cat}")
                    st.markdown("**📝 提示詞 (Prompt)：**")
                    st.code(prompt_text, language="text")
                    st.markdown(f"**💡 說明：** {desc}")
                    
                    if st.button(f"💾 儲存這組到 Notion", key=f"btn_notion_{i}"):
                        with st.spinner("寫入中..."):
                            success, msg = save_to_notion(prompt_text, cat, desc)
                            if success:
                                st.success("🎉 " + msg)
                            else:
                                st.error(msg)

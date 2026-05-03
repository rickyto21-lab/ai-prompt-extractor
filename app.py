import streamlit as st
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
import urllib.parse
import json
import re

# === 1. 從密碼本讀取金鑰 ===
GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"].strip()
NOTION_API_KEY = st.secrets.get("NOTION_API_KEY", "").strip()
NOTION_DB_ID = st.secrets.get("NOTION_DB_ID", "").strip()

# === 2. 初始化 Gemini 模型 ===
genai.configure(api_key=GEMINI_API_KEY)
available_models =[m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
target_model_name = next((name for name in available_models if "flash" in name), available_models[0] if available_models else 'gemini-1.5-flash')
model = genai.GenerativeModel(target_model_name)

st.set_page_config(page_title="AI Prompt 提取神器", page_icon="🚀", layout="wide")
st.title("🚀 AI Prompt 提取與預覽神器 (穩如泰山版)")
st.caption("支援自動分類、零破圖預覽圖、一鍵完美寫入精美 Notion 頁面")

# === 記憶體設置 ===
if "extracted_data" not in st.session_state:
    st.session_state.extracted_data = None

# === 3. 核心功能函數 ===
def fetch_website_content(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        return soup.get_text(separator='\n', strip=True)[:4000] 
    except Exception as e:
        return f"爬取失敗: {e}"

def ai_extract_to_json(text):
    prompt = f"""
    你是一個 AI 助手。請從以下文章中提取出所有提到的 AI 繪圖 Prompt (提示詞)，並進行分類。
    請務必以 JSON 陣列 (Array) 的格式輸出，不要包含任何多餘的文字。
    
    格式範例：[
      {{
        "category": "風景模型",
        "prompt": "a beautiful mountain, sunset, 8k resolution",
        "description": "用於生成高畫質的日落風景圖",
        "preview_prompt": "sunset mountain" 
      }}
    ]
    
    【嚴重警告】："preview_prompt" 用來傳給畫圖API。請嚴格使用不超過2個基礎英文字彙描述重點（例如 "robot"、"building"、"apple"）。禁止出現人類情緒/兩性互動 (如lovers、kiss、hate) 與其他血腥暴力相關用字以策安全。不可含數字。
    
    文章內容：
    {text}
    """
    try:
        response = model.generate_content(prompt)
        result_text = response.text.strip()
        
        match = re.search(r'\[.*\]', result_text, re.DOTALL)
        if match:
            json_str = match.group(0)
            return json.loads(json_str)
        else:
            st.error("AI 回傳格式錯誤找不到 JSON 陣列，請重試。")
            return None
    except Exception as e:
        st.error(f"JSON 解析失敗: {e}")
        return None

# 🌟 徹底阻絕破圖：Python 端抓取與錯誤攔截防護盾（加上 Cache 防止點擊亂跳重讀）
@st.cache_data(show_spinner=False, ttl=3600)
def get_stable_image(preview_keyword, seed):
    # 對單字去特殊符號
    clean_keyword = re.sub(r'[^a-zA-Z\s]', '', preview_keyword).strip()
    safe_keyword = urllib.parse.quote(clean_keyword)
    
    if not safe_keyword:
         safe_keyword = "scenery"
            
    api_url = f"https://image.pollinations.ai/prompt/{safe_keyword}.png?width=400&height=400&nologo=true&seed={seed}"
    # 公開圖庫的靜態圖，絕對不可能死連，充當我們的 Fallback
    fallback_url = "https://placehold.co/400x400/eeeeee/888888?text=API+Timeout"
    
    try:
        # 要求 Python 試著拿到圖 (強制 AI 後台產生圖不偷懶)
        r = requests.get(api_url, timeout=12)
        if r.status_code == 200:
            return r.content, api_url # 成功 -> 回傳位元檔案及這串安全的網址給 Notion
        else:
            fb = requests.get(fallback_url, timeout=5)
            return fb.content, fallback_url
    except requests.exceptions.RequestException:
        # 一有連線錯與 Timeout 立馬強塞後補灰圖，杜絕所有網頁小圖示破損！
        fb = requests.get(fallback_url, timeout=5)
        return fb.content, fallback_url

def save_to_notion(prompt_text, category, description, final_img_url):
    if not NOTION_API_KEY or not NOTION_DB_ID:
        return False, "Notion 金鑰未設定！"
        
    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }
    
    short_title = f"[{category}] {prompt_text[:30]}..." if len(prompt_text) > 30 else f"[{category}] {prompt_text}"
    
    data = {
        "parent": {"database_id": NOTION_DB_ID},
        "icon": {"type": "emoji", "emoji": "🎨"},
        "cover": {
            "type": "external",
            "external": {"url": final_img_url} # 送出確保可以運作無虞的完美 url
        },
        "properties": {
            "Name": {"title":[{"text": {"content": short_title}}]},
            "Category": {"rich_text":[{"text": {"content": str(category)[:500]}}]},
            "Description": {"rich_text":[{"text": {"content": str(description)[:500]}}]}
        },
        "children":[
            {
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text":[{"text": {"content": "📝 提示詞 (Prompt)"}}],
                    "color": "blue_background"
                }
            },
            {
                "object": "block",
                "type": "code",
                "code": {
                    "rich_text":[{"text": {"content": prompt_text[:2000]}}],
                    "language": "plain text"
                }
            },
            {
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text":[{"text": {"content": "💡 說明 (Description)"}}],
                    "color": "yellow_background"
                }
            },
            {
                "object": "block",
                "type": "callout",
                "callout": {
                    "rich_text":[{"text": {"content": str(description)[:2000]}}],
                    "icon": {"type": "emoji", "emoji": "✨"}
                }
            }
        ]
    }
    
    try:
        response = requests.post("https://api.notion.com/v1/pages", headers=headers, json=data)
        if response.status_code == 200:
            return True, "✅ 成功寫入 Notion！"
        else:
            return False, f"❌ 寫入失敗 (代碼 {response.status_code}): {response.text}"
    except Exception as e:
        return False, f"❌ 網路連線錯誤: {e}"

# === 4. UI 介面 ===
st.write("---")
tab1, tab2 = st.tabs(["📝 直接貼上文章", "🔗 貼上網址自動抓"])

with tab1:
    text_input = st.text_area("請在此貼上文章內容：", height=150)
    if st.button("⚡ 從文字提取"):
        if text_input:
            with st.spinner("🤖 AI 正在努力分析文章中..."):
                st.session_state.extracted_data = ai_extract_to_json(text_input)

with tab2:
    url_input = st.text_input("請輸入要提取的網址：")
    if st.button("⚡ 從網址提取"):
        if url_input:
            with st.spinner("🕵️‍♂️ 正在闖關網站讀資料..."):
                web_text = fetch_website_content(url_input)
                if "爬取失敗" in web_text:
                    st.error(web_text)
                else:
                    with st.spinner("🤖 AI 正在抽取資料中..."):
                        st.session_state.extracted_data = ai_extract_to_json(web_text)

# === 5. UI卡片渲染流程 ===
if st.session_state.extracted_data is not None:
    prompt_data_list = st.session_state.extracted_data
    
    if not isinstance(prompt_data_list, list):
         st.error("❌ 無法整理格式，可以再請系統跑一次。")
    else:
        st.success(f"✅ 完成整理出 {len(prompt_data_list)} 組！")
        st.write("---")
        
        for i, item in enumerate(prompt_data_list):
            cat = item.get("category", "未分類")
            prompt_text = item.get("prompt", "")
            desc = item.get("description", "無")
            preview_prompt = item.get("preview_prompt", "figure")
            fixed_seed = 1000 + i # 使用每張卡固定的種子杜絕亂數轉換閃圖 
            
            with st.container(border=True):
                col1, col2 = st.columns([1, 2])
                
                with col1:
                    with st.spinner("等待雲端 AI 動態運算生成此預覽圖，不會壞請放心..."):
                        # 直接等待這條由後端包裝的緩衝結果出來！無懼任何Timeout及破損！
                        img_bytes, safe_url_to_notion = get_stable_image(preview_prompt, fixed_seed)
                        
                        if img_bytes:
                            # 放手給系統原生的圖元模塊接棒去安放這包確實存在的圖資源。
                            st.image(img_bytes, caption=f"自動產生配圖({preview_prompt[:20]})", use_container_width=True)
                
                with col2:
                    st.subheader(f"🏷️ 分類：{cat}")
                    st.markdown("**📝 提示詞 (Prompt)：**")
                    st.code(prompt_text, language="text")
                    st.markdown(f"**💡 說明：** {desc}")
                    
                    if st.button(f"💾 儲存這組到 Notion", key=f"btn_notion_{i}"):
                        with st.spinner("光速備份卡片及封面資源往 Notion 端儲存..."):
                            success, msg = save_to_notion(prompt_text, cat, desc, safe_url_to_notion)
                            if success:
                                st.success("🎉 " + msg)
                            else:
                                st.error(msg)

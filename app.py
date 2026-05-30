import streamlit as st
import os
import time  # 用於計算延遲時間與防禦冷卻
from datetime import datetime
from google import genai
from google.genai import types

# ==========================================
# 1. 網頁 UI 排版與畫面呈現 (佔 50 分)
# ==========================================
st.set_page_config(
    page_title="AI 海龜湯限時猜謎",
    page_icon="🐢",
    layout="centered"
)

st.title("🐢 智能海龜湯限時猜謎")
st.caption("一個由 Gemini 驅動的海龜湯遊戲，AI 只能回答：是、不是、與故事/題目無關、不完全是。")
st.markdown("---")

if "GEMINI_API_KEY" in st.secrets:
    os.environ["GEMINI_API_KEY"] = st.secrets["GEMINI_API_KEY"]

@st.cache_resource
def get_gemini_client():
    return genai.Client()

try:
    client = get_gemini_client()
except Exception as e:
    st.error("❌ 未偵測到 Gemini API Key！請檢查 `.streamlit/secrets.toml` 是否設定正確。")
    st.stop()


# ==========================================
# 2. 全域遊戲紀錄與狀態初始化
# ==========================================
if "game_history" not in st.session_state:
    st.session_state.game_history = {}

if "current_view_game" not in st.session_state:
    st.session_state.current_view_game = "✨ 進行中的當前遊戲"

if "messages" not in st.session_state:
    st.session_state.messages = []

if "secret_target" not in st.session_state:
    st.session_state.secret_target = None

if "game_time_label" not in st.session_state:
    st.session_state.game_time_label = None

if "current_game_finished" not in st.session_state:
    st.session_state.current_game_finished = False

# 🔒 【資安防禦】初始化上一次提問的時間戳記
if "last_submit_time" not in st.session_state:
    st.session_state.last_submit_time = 0.0

# 💡 【核心新增】：用來記錄所有出現過的歷史題目清單 (List)
if "past_targets" not in st.session_state:
    st.session_state.past_targets = []


# ==========================================
# 3. 正常海龜湯遊戲功能：謎底與時間動態生成
# ==========================================
def start_new_game_logic():
    # 💡 將記憶清單轉換為文字，如果清單是空的就顯示「無」
    forbidden_list_str = ", ".join(st.session_state.past_targets) if st.session_state.past_targets else "無"
    
    init_prompt = (
        "請秘密隨機想一個明確定義的具體目標物品、日常用品、水果、蔬菜、樂器、電器或球類運動。"
        "目標必須要具體好猜（例如：香蕉、訂書機、吉他、吹風機、腳踏車）。\n\n"
        f"⚠️【絕對嚴格限制】⚠️\n"
        f"以下是本專案已經出現過的題目清單（List）：[{forbidden_list_str}]\n"
        "你『絕對不能』再選擇上述清單中出現過的任何物品或高度相關的同義詞！請重新想一個完全不同的東西。\n\n"
        "請只用一句話回覆我，格式為：『本局目標：[你設定的目標]』。這句話絕對不能讓玩家看到。"
    )
    try:
        response = client.models.generate_content(
            model='gemini-3.1-flash-lite',
            contents=init_prompt,
            config=types.GenerateContentConfig(
                temperature=1.0,  # 保持高隨機性
            )
        )
        raw_target = response.text.strip()
        st.session_state.secret_target = raw_target
        
        # 💡 解析出純粹的物品名稱（去掉「本局目標：」與括號），並存入歷史清單中
        clean_name = raw_target.replace("本局目標：", "").replace("『", "").replace("』", "").strip()
        if clean_name and clean_name not in st.session_state.past_targets:
            st.session_state.past_targets.append(clean_name)
            
        st.session_state.messages = []
        st.session_state.game_time_label = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        st.session_state.current_game_finished = False
    except Exception as e:
        st.error(f"初始化謎底失敗: {e}")
        st.session_state.secret_target = "本局目標：蘋果"
        st.session_state.game_time_label = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

if st.session_state.secret_target is None:
    start_new_game_logic()


# ==========================================
# 4. 左側側邊欄：歷史遊玩紀錄
# ==========================================
with st.sidebar:
    st.header("🎮 遊戲控制面板")
    
    # 💡 修正點 1：點擊重新開始新遊戲時，如果目前這局有對話且未存檔，直接強制保留存檔
    if st.button("🔄 重新開始新遊戲", use_container_width=True, type="primary"):
        if st.session_state.messages and not st.session_state.current_game_finished:
            # 判定為中途放棄，標記為 (失敗) 存入歷史
            fail_key = f"❌ {st.session_state.game_time_label} ({st.session_state.secret_target}) (失敗)"
            st.session_state.game_history[fail_key] = st.session_state.messages
            
        # 生成新題目，並保持焦點在當前遊戲
        start_new_game_logic()
        st.session_state.current_view_game = "✨ 進行中的當前遊戲"
        st.rerun()
    
    st.markdown("---")
    st.subheader("🏆 榮譽通關戰績表")
    
    options = ["✨ 進行中的當前遊戲"] + list(st.session_state.game_history.keys())
    
    if st.session_state.current_view_game not in options:
        st.session_state.current_view_game = "✨ 進行中的當前遊戲"
        
    current_index = options.index(st.session_state.current_view_game)
        
    selected_game = st.radio(
        "選擇要查看的局數：", 
        options, 
        index=current_index
    )
    
    if selected_game != st.session_state.current_view_game:
        st.session_state.current_view_game = selected_game
        
        if selected_game == "✨ 進行中的當前遊戲" and st.session_state.current_game_finished:
            start_new_game_logic()
            
        st.rerun()

    st.markdown("---")
    

# ==========================================
# 5. 畫面渲染與對話歷程完整顯示
# ==========================================
if st.session_state.current_view_game == "✨ 進行中的當前遊戲":
    display_messages = st.session_state.messages
    is_history_mode = False
    st.info(f"📆 遊戲開始時間：{st.session_state.game_time_label}")
else:
    display_messages = st.session_state.game_history[st.session_state.current_view_game]
    is_history_mode = True
    
    # 💡 修正點 2：根據看的是成功還是失敗局，顯示不同的橫幅提示
    if "(成功)" in st.session_state.current_view_game:
        st.success(f"🎉 正在查看通關紀錄：{st.session_state.current_view_game}")
    else:
        st.error(f"🏳️ 正在查看未完成/放棄紀錄：{st.session_state.current_view_game}")

# 渲染對話方塊
for message in display_messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if len(display_messages) == 0:
    with st.chat_message("assistant"):
        st.markdown("我已经想好了一個秘密的目標（水果、用品、樂器或運動等）！\n\n請在下方輸入提問。我只能回答：**『是』、『不是』、『與故事/題目無關』、『不完全是』**。")


# ==========================================
# 6. 猜題輸入與【資安防禦檢查機制】
# ==========================================
placeholder_text = "請輸入你的問題 (限 50 字內，冷卻時間 1 秒)..." if not is_history_mode else "歷史回顧模式中，請點選左側切換回「進行中的當前遊戲」"

if user_question := st.chat_input(placeholder_text, disabled=is_history_mode):
    if not is_history_mode:
        
        current_time = time.time()
        
        # 🔒 【防禦檢查 1】：提問時間間隔是否小於 1 秒
        time_diff = current_time - st.session_state.last_submit_time
        if time_diff < 1.0:
            st.error(f"🛑 系統安全防禦中：請求過於頻繁！提問冷卻時間為 1 秒。請稍候再試。")
            st.stop()
            
        # 🔒 【防禦檢查 2】：輸入字串長度是否超過 50 個字
        if len(user_question) > 50:
            st.error(f"🛑 系統安全防禦中：提問字數不能超過 50 個字！")
            st.stop()
            
        st.session_state.last_submit_time = current_time
        
        # 寫入當前局紀錄
        st.session_state.messages.append({"role": "user", "content": user_question})
        with st.chat_message("user"):
            st.markdown(user_question)
        
        # 準備 API 參數
        clean_target = st.session_state.secret_target.replace("本局目標：", "").replace("『", "").replace("』", "").strip()
        system_instruction = (
            "你是海龜湯的主持人。我（玩家）正在試圖猜出你心中秘密設定的目標物品。\n"
            f"你心中設定的秘密目標是：【{clean_target}】。\n\n"
            "【嚴格規則】\n"
            "1. 面對玩家的任何提問、猜測、推理，你『只能』從以下四個選項中選擇一個回答，絕對不能說任何多餘的字或解釋：\n"
            "   - 是\n"
            "   - 不是\n"
            "   - 與故事/題目無關\n"
            "   - 不完全是\n"
            "2. 如果玩家直接猜中了正確答案的名詞（例如目標是西瓜，玩家問：答案是西瓜嗎？），你可以打破規則並『必須』嚴格回答此固定字串：『是，恭喜答對！』。除了這個情況，其餘一律只能嚴格遵守上述四個回應。\n"
            "3. 請參考過去的歷史對話情境，做出邏輯前後一致的精準判斷。"
        )
        
        api_contents = []
        for msg in st.session_state.messages:
            role_mapping = "user" if msg["role"] == "user" else "model"
            api_contents.append(
                types.Content(role=role_mapping, parts=[types.Part.from_text(text=msg["content"])])
            )
        
        # 呼叫 Gemini API 
        with st.chat_message("assistant"):
            response_placeholder = st.empty()
            with st.spinner("AI 裁判判斷中..."):
                try:
                    start_api_time = time.time()
                    
                    response = client.models.generate_content(
                        model='gemini-3.1-flash-lite',
                        contents=api_contents,
                        config=types.GenerateContentConfig(
                            system_instruction=system_instruction,
                            temperature=0.1,
                        )
                    )
                    
                    end_api_time = time.time()
                    elapsed_time = end_api_time - start_api_time
                    
                    ai_reply = response.text.strip()
                    
                    # 渲染回答與時間
                    response_placeholder.markdown(f"{ai_reply}\n\n`⏱️ 系統判定耗時: {elapsed_time:.3f} 秒`")
                    st.session_state.messages.append({"role": "assistant", "content": f"{ai_reply}\n\n`⏱️ 系統判定耗時: {elapsed_time:.3f} 秒`"})
                    
                    # 💡 修正點 3：成功破關時，在標記後方加上 (成功)
                    if "恭喜答對" in ai_reply:
                        history_key = f"👑 {st.session_state.game_time_label} ({st.session_state.secret_target}) (成功)"
                        st.session_state.game_history[history_key] = st.session_state.messages
                        st.session_state.current_view_game = history_key
                        st.session_state.current_game_finished = True
                        st.balloons()
                        
                except Exception as e:
                    st.error(f"呼叫 API 時發生錯誤: {e}")
        
        st.rerun()
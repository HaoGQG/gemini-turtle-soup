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
# 2. 全域遊戲紀錄與【資安防禦狀態】初始化
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

# 🔒 【資安防禦】初始化上一次提問的時間戳記，用於計算 1 秒延遲限制
if "last_submit_time" not in st.session_state:
    st.session_state.last_submit_time = 0.0


# ==========================================
# 3. 正常海龜湯遊戲功能：謎底與時間動態生成
# ==========================================
def start_new_game_logic():
    init_prompt = (
        "請秘密隨機想一個明確定義的具體目標物品、水果或球類運動（例如：西瓜、網球、訂書機、護手霜）。"
        "請只用一句話回覆我，格式為：『本局目標：[你設定的目標]』。這句話絕對不能讓玩家看到。"
    )
    try:
        response = client.models.generate_content(
            model='gemini-3.1-flash-lite',
            contents=init_prompt
        )
        st.session_state.secret_target = response.text.strip()
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
    
    if st.button("🔄 重新開始新遊戲", use_container_width=True, type="primary"):
        start_new_game_logic()
        st.session_state.current_view_game = "✨ 進行中的當前遊戲"
        st.rerun()
    
    st.markdown("---")
    st.subheader("🏆 榮譽通關戰績表")
    
    options = ["✨ 進行中的當前遊戲"] + list(st.session_state.game_history.keys())
    if st.session_state.current_view_game not in options:
        st.session_state.current_view_game = "✨ 進行中的當前遊戲"
        
    current_index = options.index(st.session_state.current_view_game)
        
    selected_game = st.radio("選擇要查看的局數：", options, index=current_index, key="current_view_game_radio")
    
    if selected_game != st.session_state.current_view_game:
        st.session_state.current_view_game = selected_game
        if selected_game == "✨ 進行中的當前遊戲" and st.session_state.current_game_finished:
            start_new_game_logic()
        st.rerun()

    st.markdown("---")
    with st.expander("👁️ 開發者除錯後台 (謎底)"):
        if st.session_state.current_view_game == "✨ 進行中的當前遊戲":
            st.write(f"當前局答案：{st.session_state.secret_target}")
        else:
            st.write(f"正在檢視通關局：\n{st.session_state.current_view_game}")


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
    st.success(f"🎉 正在查看通關紀錄：{st.session_state.current_view_game}")

for message in display_messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if len(display_messages) == 0:
    with st.chat_message("assistant"):
        st.markdown("我已经想好了一個秘密的目標（水果、球類或生活用品）！\n\n請在下方輸入提問。我只能回答：**『是』、『不是』、『與故事/題目無關』、『不完全是』**。")


# ==========================================
# 6. 猜題輸入與【資安防禦檢查機制】
# ==========================================
placeholder_text = "請輸入你的問題 (限 50 字內，冷卻時間 1 秒)..." if not is_history_mode else "歷史回顧模式中，請點選左側切換回「進行中的當前遊戲」"

if user_question := st.chat_input(placeholder_text, disabled=is_history_mode):
    if not is_history_mode:
        
        current_time = time.time()
        
        # 🔒 【防禦檢查 1】：檢查提問時間間隔是否小於 1 秒 (防範 DDoS 連發)
        time_diff = current_time - st.session_state.last_submit_time
        if time_diff < 1.0:
            st.error(f"🛑 系統安全防禦中：請求過於頻繁！提問冷卻時間為 1 秒（您距離上次提問僅過了 {time_diff:.2f} 秒）。請稍候再試。")
            st.stop()
            
        # 🔒 【防禦檢查 2】：檢查輸入字串長度是否超過 50 個字 (防範緩衝區溢位/長文字惡意攻擊)
        if len(user_question) > 50:
            st.error(f"🛑 系統安全防禦中：提問字數不能超過 50 個字！(當前輸入字數：{len(user_question)} 字)。")
            st.stop()
            
        # 通過檢查，更新最後合法提問時間
        st.session_state.last_submit_time = current_time
        
        # 寫入當前局紀錄
        st.session_state.messages.append({"role": "user", "content": user_question})
        with st.chat_message("user"):
            st.markdown(user_question)
        
        history_key = f"👑 {st.session_state.game_time_label} ({st.session_state.secret_target})"
        
        # 準備 API 參數
        system_instruction = (
            "你是海龜湯的主持人。我（玩家）正在試圖猜出你心中秘密設定的目標物品。\n"
            f"你心中設定的秘密目標是：【{st.session_state.secret_target}】。\n\n"
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
        
        # 呼叫 Gemini API 並精準【記錄模型判定耗時】
        with st.chat_message("assistant"):
            response_placeholder = st.empty()
            with st.spinner("AI 判斷中..."):
                try:
                    start_api_time = time.time()  # ⏱️ 開始計時
                    
                    response = client.models.generate_content(
                        model='gemini-3.1-flash-lite',
                        contents=api_contents,
                        config=types.GenerateContentConfig(
                            system_instruction=system_instruction,
                            temperature=0.1,
                        )
                    )
                    
                    end_api_time = time.time()  # ⏱️ 結束計時
                    elapsed_time = end_api_time - start_api_time  # 計算總耗時
                    
                    ai_reply = response.text.strip()
                    
                    # ⚡ 【進攻組權益】：將精準耗時秒數渲染在回答下方，作為是否超過 1 秒的質疑依據
                    response_placeholder.markdown(f"{ai_reply}\n\n`⏱️ 系統判定耗時: {elapsed_time:.3f} 秒`")
                    
                    # 將結果存入紀錄
                    st.session_state.messages.append({"role": "assistant", "content": f"{ai_reply}\n\n`⏱️ 系統判定耗時: {elapsed_time:.3f} 秒`"})
                    
                    if "恭喜答對" in ai_reply:
                        st.session_state.game_history[history_key] = st.session_state.messages
                        st.session_state.current_view_game = history_key
                        st.session_state.current_game_finished = True
                        st.balloons()
                        
                except Exception as e:
                    st.error(f"呼叫 API 時發生錯誤: {e}")
        
        st.rerun()
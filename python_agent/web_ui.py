from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
import uvicorn
import asyncio
from core_logic import handle_chat, handle_task
from router import classify_intent

app = FastAPI(title="Ageis Agent UI")

# HTML/CSS/JS 프론트엔드 (단일 파일)
HTML_UI = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Ageis Agent</title>
    <style>
        :root {
            --bg-color: #1a1a2e;
            --chat-bg: #16213e;
            --user-msg-bg: #0f3460;
            --agent-msg-bg: #e94560;
            --text-color: #eee;
        }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: var(--bg-color);
            color: var(--text-color);
            margin: 0;
            display: flex;
            flex-direction: column;
            height: 100vh;
            justify-content: center;
            align-items: center;
        }
        .container {
            width: 90%;
            max-width: 800px;
            height: 90vh;
            background-color: var(--chat-bg);
            border-radius: 12px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.5);
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }
        header {
            padding: 20px;
            background-color: rgba(0,0,0,0.2);
            text-align: center;
            border-bottom: 1px solid #333;
        }
        h1 { margin: 0; font-size: 1.5rem; color: var(--agent-msg-bg); }
        .subtitle { font-size: 0.8rem; opacity: 0.7; }
        
        #chat-box {
            flex: 1;
            padding: 20px;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            gap: 15px;
        }
        
        .message {
            max-width: 80%;
            padding: 12px 16px;
            border-radius: 12px;
            line-height: 1.5;
            word-wrap: break-word;
            animation: fadeIn 0.3s ease;
        }
        
        .user {
            align-self: flex-end;
            background-color: var(--user-msg-bg);
            border-bottom-right-radius: 2px;
        }
        
        .agent {
            align-self: flex-start;
            background-color: rgba(255,255,255,0.1);
            border-bottom-left-radius: 2px;
        }

        .system {
            align-self: center;
            font-size: 0.8rem;
            color: #888;
            background: none;
        }
        
        .input-area {
            padding: 20px;
            background-color: rgba(0,0,0,0.2);
            display: flex;
            gap: 10px;
        }
        
        input {
            flex: 1;
            padding: 12px;
            border-radius: 6px;
            border: 1px solid #444;
            background-color: var(--bg-color);
            color: white;
            outline: none;
        }
        
        button {
            padding: 10px 20px;
            background-color: var(--agent-msg-bg);
            color: white;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-weight: bold;
            transition: background 0.2s;
        }
        button:hover { background-color: #c0354c; }
        button:disabled { background-color: #555; cursor: wait; }

        @keyframes fadeIn { from { opacity: 0; transform: translateY(5px); } to { opacity: 1; transform: translateY(0); } }
        
        /* 마크다운 스타일링 (간이) */
        .agent pre { background: #111; padding: 10px; border-radius: 4px; overflow-x: auto; }
        .agent code { font-family: monospace; background: rgba(0,0,0,0.3); padding: 2px 4px; border-radius: 3px; }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🤖 Ageis Agent</h1>
            <div class="subtitle">Phase 4: Expansion & UX (Web Interface)</div>
            <div id="status" style="font-size: 0.7rem; color: #4caf50; margin-top: 5px;">● Connected</div>
        </header>
        
        <div id="chat-box"></div>
        
        <div class="input-area">
            <input id="msg-input" type="text" placeholder="메시지를 입력하세요..." onkeypress="if(event.key==='Enter') sendMessage()">
            <button id="send-btn" onclick="sendMessage()">전송</button>
        </div>
    </div>

    <script>
        const ws = new WebSocket(`ws://${window.location.host}/ws`);
        const chatBox = document.getElementById("chat-box");
        const msgInput = document.getElementById("msg-input");
        const sendBtn = document.getElementById("send-btn");
        const statusDiv = document.getElementById("status");

        ws.onopen = () => {
            statusDiv.innerHTML = "● Connected";
            statusDiv.style.color = "#4caf50";
            addMessage("시스템에 연결되었습니다.", "system");
        };

        ws.onclose = () => {
            statusDiv.innerHTML = "● Disconnected";
            statusDiv.style.color = "#f44336";
            addMessage("연결이 끊어졌습니다. 새로고침 해주세요.", "system");
            msgInput.disabled = true;
            sendBtn.disabled = true;
        };

        ws.onmessage = (event) => {
            addMessage(event.data, "agent");
            sendBtn.disabled = false;
            msgInput.disabled = false;
            msgInput.focus();
        };

        function addMessage(text, sender) {
            const div = document.createElement("div");
            div.className = `message ${sender}`;
            
            // 간단한 줄바꿈 처리
            if (sender === 'agent') {
                // 에이전트 메시지는 HTML 태그를 일부 허용하거나 줄바꿈 처리
                div.innerHTML = text.replace(/\\n/g, '<br>');
            } else {
                div.textContent = text;
            }
            
            chatBox.appendChild(div);
            chatBox.scrollTop = chatBox.scrollHeight;
        }

        function sendMessage() {
            const text = msgInput.value.trim();
            if (!text) return;
            
            addMessage(text, "user");
            ws.send(text);
            msgInput.value = "";
            
            // 응답 대기 중 처리
            sendBtn.disabled = true;
            msgInput.disabled = true;
        }
    </script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def get_root():
    return HTML_UI

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    try:
        while True:
            # 1. 사용자 입력 수신
            user_input = await websocket.receive_text()
            
            # 2. 의도 분류 및 처리 (비동기로 실행하지 않으면 블로킹될 수 있음 - 여기선 간단히 동기 호출)
            # 실제 운영 환경에서는 `run_in_executor` 등을 사용해야 함
            intent = classify_intent(user_input)
            
            response = ""
            if intent == "CHAT":
                response = handle_chat(user_input)
            elif intent in ["FILE", "WEB", "TASK"]:
                response = handle_task(user_input)
            elif intent == "PERSONA":
                response = "persona.yaml 파일을 직접 수정한 후 재시작해 주세요."
            else:
                response = handle_chat(user_input)
            
            # 3. 결과 전송
            await websocket.send_text(response)
            
    except Exception as e:
        print(f"[WebSocket Error] {e}")

def web_main():
    """웹 서버 실행 진입점"""
    print("Starting Web UI on http://localhost:8000")
    print("Press Ctrl+C to stop.")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")

if __name__ == "__main__":
    web_main()

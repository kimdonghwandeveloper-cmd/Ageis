"""
web_ui.py — Ageis Agent Web UI (Phase 6: 멀티모달 확장)

엔드포인트:
  GET  /              — 채팅 UI
  GET  /api/health    — 헬스 체크
  POST /api/chat      — REST 채팅
  POST /api/task      — REST 태스크
  POST /api/vision    — 이미지 분석 (Phase 6-A)
  POST /api/voice     — 음성 녹음 → 텍스트 → 응답 (Phase 6-B)
  WS   /ws            — WebSocket 채팅 (텍스트)
"""
import asyncio
import base64

from fastapi import FastAPI, WebSocket, UploadFile, File, Form
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

from core_logic import handle_chat, handle_task, handle_vision, handle_voice
from router import classify_intent

app = FastAPI(title="Ageis Agent UI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8000",
        "tauri://localhost",
        "https://tauri.localhost",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Pydantic 모델 ──────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    response: str
    intent: str


class VisionRequest(BaseModel):
    base64_image: str
    prompt: str = "이 이미지에 무엇이 있나요? 자세히 설명해주세요."


class VoiceRequest(BaseModel):
    duration: float = 5.0
    language: str = "ko"
    tts_response: bool = True


# ─── HTML/CSS/JS 프론트엔드 ─────────────────────────────────────────────────

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
        * { box-sizing: border-box; }
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
            max-width: 820px;
            height: 90vh;
            background-color: var(--chat-bg);
            border-radius: 12px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.5);
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }
        header {
            padding: 16px 20px;
            background-color: rgba(0,0,0,0.2);
            text-align: center;
            border-bottom: 1px solid #333;
        }
        h1 { margin: 0; font-size: 1.4rem; color: var(--agent-msg-bg); }
        .subtitle { font-size: 0.75rem; opacity: 0.7; margin-top: 2px; }

        #chat-box {
            flex: 1;
            padding: 20px;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            gap: 12px;
        }

        .message {
            max-width: 80%;
            padding: 10px 14px;
            border-radius: 12px;
            line-height: 1.5;
            word-wrap: break-word;
            animation: fadeIn 0.25s ease;
        }
        .user  { align-self: flex-end;   background-color: var(--user-msg-bg); border-bottom-right-radius: 2px; }
        .agent { align-self: flex-start; background-color: rgba(255,255,255,0.1); border-bottom-left-radius: 2px; }
        .system { align-self: center; font-size: 0.78rem; color: #888; background: none; }

        /* 이미지 첨부 프리뷰 */
        .message img { max-width: 100%; border-radius: 6px; margin-top: 6px; display: block; }

        .input-area {
            padding: 14px 20px;
            background-color: rgba(0,0,0,0.2);
            border-top: 1px solid #333;
            display: flex;
            flex-direction: column;
            gap: 8px;
        }
        .input-row {
            display: flex;
            gap: 8px;
            align-items: center;
        }
        #msg-input {
            flex: 1;
            padding: 10px 12px;
            border-radius: 6px;
            border: 1px solid #444;
            background-color: var(--bg-color);
            color: white;
            outline: none;
            font-size: 0.95rem;
        }

        /* 버튼 공통 */
        .btn {
            padding: 9px 16px;
            color: white;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-weight: bold;
            transition: background 0.2s, opacity 0.2s;
            white-space: nowrap;
        }
        .btn:disabled { opacity: 0.45; cursor: wait; }
        .btn-send  { background-color: var(--agent-msg-bg); }
        .btn-send:hover:not(:disabled)  { background-color: #c0354c; }
        .btn-img   { background-color: #2a6496; }
        .btn-img:hover:not(:disabled)   { background-color: #1d4e75; }
        .btn-voice { background-color: #2e7d32; }
        .btn-voice:hover:not(:disabled) { background-color: #1b5e20; }
        .btn-voice.recording { background-color: #b71c1c; animation: pulse 1s infinite; }

        /* 이미지 업로드 힌트 바 */
        #img-preview-bar {
            display: none;
            align-items: center;
            gap: 8px;
            padding: 6px 10px;
            background: rgba(42,100,150,0.25);
            border-radius: 6px;
            font-size: 0.82rem;
        }
        #img-preview-bar img { width: 40px; height: 40px; object-fit: cover; border-radius: 4px; }
        #img-preview-bar span { flex: 1; opacity: 0.85; }
        #img-clear-btn { background: none; border: none; color: #f44336; cursor: pointer; font-size: 1rem; padding: 0 4px; }

        @keyframes fadeIn { from { opacity: 0; transform: translateY(4px); } to { opacity: 1; transform: translateY(0); } }
        @keyframes pulse  { 0%,100% { opacity: 1; } 50% { opacity: 0.6; } }

        /* 에이전트 응답 코드블록 */
        .agent pre { background: #111; padding: 10px; border-radius: 4px; overflow-x: auto; }
        .agent code { font-family: monospace; background: rgba(0,0,0,0.3); padding: 2px 4px; border-radius: 3px; }
    </style>
</head>
<body>
<div class="container">
    <header>
        <h1>🤖 Ageis Agent</h1>
        <div class="subtitle">Phase 6: The Senses — Vision &amp; Voice</div>
        <div id="status" style="font-size:0.7rem;color:#4caf50;margin-top:4px;">● Connected</div>
    </header>

    <div id="chat-box"></div>

    <div class="input-area">
        <!-- 이미지 첨부 프리뷰 바 -->
        <div id="img-preview-bar">
            <img id="img-thumb" src="" alt="preview">
            <span id="img-name">이미지 첨부됨</span>
            <button id="img-clear-btn" title="첨부 취소">✕</button>
        </div>

        <!-- 입력 행 -->
        <div class="input-row">
            <input id="msg-input" type="text"
                   placeholder="메시지를 입력하거나 이미지/마이크를 사용하세요..."
                   onkeypress="if(event.key==='Enter') sendMessage()">
            <button class="btn btn-img"    id="img-btn"   title="이미지 첨부"  onclick="triggerImageUpload()">🖼</button>
            <button class="btn btn-voice"  id="voice-btn" title="음성 입력"    onclick="toggleVoice()">🎤</button>
            <button class="btn btn-send"   id="send-btn"  onclick="sendMessage()">전송</button>
        </div>
    </div>
</div>

<!-- 숨겨진 파일 입력 -->
<input type="file" id="img-file-input" accept="image/*" style="display:none" onchange="onImageSelected(event)">

<script>
// ─── WebSocket ────────────────────────────────────────────────────────────
const ws = new WebSocket(`ws://${window.location.host}/ws`);
const chatBox    = document.getElementById("chat-box");
const msgInput   = document.getElementById("msg-input");
const sendBtn    = document.getElementById("send-btn");
const statusDiv  = document.getElementById("status");
const voiceBtn   = document.getElementById("voice-btn");
const imgBtn     = document.getElementById("img-btn");

ws.onopen  = () => { setStatus(true);  addMsg("시스템에 연결되었습니다.", "system"); };
ws.onclose = () => { setStatus(false); addMsg("연결이 끊어졌습니다. 새로고침 해주세요.", "system"); disableInput(); };
ws.onmessage = (e) => { addMsg(e.data, "agent"); enableInput(); };

function setStatus(ok) {
    statusDiv.innerHTML = ok ? "● Connected" : "● Disconnected";
    statusDiv.style.color = ok ? "#4caf50" : "#f44336";
}
function disableInput() { sendBtn.disabled = msgInput.disabled = true; }
function enableInput()  { sendBtn.disabled = msgInput.disabled = false; msgInput.focus(); }

// ─── 메시지 추가 ──────────────────────────────────────────────────────────
function addMsg(text, sender, imgSrc) {
    const div = document.createElement("div");
    div.className = `message ${sender}`;
    if (sender === "agent") {
        div.innerHTML = text.replace(/\\n/g, "<br>");
    } else {
        div.textContent = text;
    }
    if (imgSrc) {
        const img = document.createElement("img");
        img.src = imgSrc;
        div.appendChild(img);
    }
    chatBox.appendChild(div);
    chatBox.scrollTop = chatBox.scrollHeight;
}

// ─── 텍스트 전송 ──────────────────────────────────────────────────────────
let pendingImageB64 = "";   // 첨부된 이미지 base64

function sendMessage() {
    const text = msgInput.value.trim();

    if (pendingImageB64) {
        // 이미지가 첨부된 경우 → /api/vision REST 호출
        const prompt = text || "이 이미지에 무엇이 있나요? 자세히 설명해주세요.";
        addMsg(prompt, "user", "data:image/*;base64," + pendingImageB64);
        disableInput();
        sendVisionRequest(pendingImageB64, prompt);
        clearImageAttachment();
        msgInput.value = "";
        return;
    }

    if (!text) return;
    addMsg(text, "user");
    ws.send(text);
    msgInput.value = "";
    disableInput();
}

// ─── Vision (이미지 업로드) ───────────────────────────────────────────────
function triggerImageUpload() {
    document.getElementById("img-file-input").click();
}

function onImageSelected(event) {
    const file = event.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (e) => {
        const b64full = e.target.result;          // data:image/png;base64,XXXX
        pendingImageB64 = b64full.split(",")[1];  // base64 부분만 분리
        document.getElementById("img-thumb").src = b64full;
        document.getElementById("img-name").textContent = file.name;
        document.getElementById("img-preview-bar").style.display = "flex";
    };
    reader.readAsDataURL(file);
    event.target.value = "";  // 같은 파일 재선택 허용
}

document.getElementById("img-clear-btn").onclick = clearImageAttachment;
function clearImageAttachment() {
    pendingImageB64 = "";
    document.getElementById("img-preview-bar").style.display = "none";
}

async function sendVisionRequest(b64, prompt) {
    addMsg("이미지 분석 중...", "system");
    try {
        const res = await fetch("/api/vision", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ base64_image: b64, prompt: prompt }),
        });
        const data = await res.json();
        addMsg(data.response, "agent");
    } catch (e) {
        addMsg("이미지 분석 실패: " + e, "agent");
    }
    enableInput();
}

// ─── Voice (마이크 녹음 → STT → 응답) ────────────────────────────────────
let isRecording = false;
let mediaRecorder = null;
let audioChunks = [];

async function toggleVoice() {
    if (isRecording) {
        stopRecording();
    } else {
        await startRecording();
    }
}

async function startRecording() {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        audioChunks = [];
        mediaRecorder = new MediaRecorder(stream, { mimeType: "audio/webm" });
        mediaRecorder.ondataavailable = (e) => { if (e.data.size > 0) audioChunks.push(e.data); };
        mediaRecorder.onstop = sendAudioToSTT;
        mediaRecorder.start();
        isRecording = true;
        voiceBtn.classList.add("recording");
        voiceBtn.title = "녹음 중 (클릭하면 종료)";
        addMsg("🎤 녹음 중... (다시 클릭하면 종료)", "system");
    } catch (e) {
        addMsg("마이크 접근 실패: " + e, "system");
    }
}

function stopRecording() {
    if (mediaRecorder && mediaRecorder.state !== "inactive") {
        mediaRecorder.stop();
        mediaRecorder.stream.getTracks().forEach(t => t.stop());
    }
    isRecording = false;
    voiceBtn.classList.remove("recording");
    voiceBtn.title = "음성 입력";
}

async function sendAudioToSTT() {
    addMsg("음성 인식 중...", "system");
    disableInput();
    const blob = new Blob(audioChunks, { type: "audio/webm" });
    const formData = new FormData();
    formData.append("file", blob, "voice.webm");
    formData.append("language", "ko");
    try {
        const res = await fetch("/api/voice/upload", {
            method: "POST",
            body: formData,
        });
        const data = await res.json();
        if (data.transcribed) {
            addMsg("[음성] " + data.transcribed, "user");
        }
        addMsg(data.response, "agent");
    } catch (e) {
        addMsg("음성 처리 실패: " + e, "agent");
    }
    enableInput();
}

// ─── 클립보드 이미지 붙여넣기 (Ctrl+V) ──────────────────────────────────
document.addEventListener("paste", (e) => {
    const items = e.clipboardData && e.clipboardData.items;
    if (!items) return;
    for (const item of items) {
        if (item.type.startsWith("image/")) {
            const file = item.getAsFile();
            const reader = new FileReader();
            reader.onload = (ev) => {
                const b64full = ev.target.result;
                pendingImageB64 = b64full.split(",")[1];
                document.getElementById("img-thumb").src = b64full;
                document.getElementById("img-name").textContent = "클립보드 이미지";
                document.getElementById("img-preview-bar").style.display = "flex";
            };
            reader.readAsDataURL(file);
            break;
        }
    }
});
</script>
</body>
</html>
"""


# ─── REST 엔드포인트 ──────────────────────────────────────────────────────

@app.get("/api/health")
async def health_check():
    return {"status": "ok", "version": "0.2.0", "phase": "6"}


@app.post("/api/chat", response_model=ChatResponse)
async def api_chat(req: ChatRequest):
    intent = classify_intent(req.message)
    response = handle_chat(req.message)
    return ChatResponse(response=response, intent=intent)


@app.post("/api/task", response_model=ChatResponse)
async def api_task(req: ChatRequest):
    intent = classify_intent(req.message)
    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(None, handle_task, req.message)
    return ChatResponse(response=response, intent=intent)


@app.post("/api/vision")
async def api_vision(req: VisionRequest):
    """
    Phase 6-A: base64 이미지 분석 엔드포인트.
    요청: { "base64_image": "...", "prompt": "..." }
    응답: { "response": "..." }
    """
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None,
        handle_vision,
        "",               # image_path (없음)
        req.base64_image,
        req.prompt,
    )
    return {"response": result}


@app.post("/api/vision/file")
async def api_vision_file(
    file: UploadFile = File(...),
    prompt: str = Form(default="이 이미지에 무엇이 있나요? 자세히 설명해주세요."),
):
    """
    Phase 6-A: 파일 업로드 방식 이미지 분석 엔드포인트.
    """
    raw = await file.read()
    b64 = base64.b64encode(raw).decode("utf-8")
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, handle_vision, "", b64, prompt)
    return {"response": result, "filename": file.filename}


@app.post("/api/voice")
async def api_voice(req: VoiceRequest):
    """
    Phase 6-B: 서버 사이드 마이크 녹음 → STT → LLM 응답 → TTS.
    (서버 머신에 마이크가 연결된 경우 사용 가능)
    """
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None,
        handle_voice,
        req.duration,
        req.language,
        req.tts_response,
    )
    return {"response": result}


@app.post("/api/voice/upload")
async def api_voice_upload(
    file: UploadFile = File(...),
    language: str = Form(default="ko"),
):
    """
    Phase 6-B: 클라이언트(브라우저 MediaRecorder)에서 녹음한 오디오 파일을
    업로드받아 STT → LLM 응답 반환.
    """
    import tempfile, os
    raw = await file.read()

    # 임시 파일로 저장 (faster-whisper는 파일 경로를 받음)
    suffix = os.path.splitext(file.filename or ".webm")[1] or ".webm"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(raw)
        tmp_path = tmp.name

    try:
        from tools.stt_tool import transcribe_file_tool
        transcribed = transcribe_file_tool({"path": tmp_path, "language": language})

        if transcribed.startswith("ERROR:"):
            return {"response": transcribed, "transcribed": ""}

        # STT 결과로 LLM 대화 처리
        loop = asyncio.get_event_loop()
        answer = await loop.run_in_executor(None, handle_chat, transcribed)
        return {"response": answer, "transcribed": transcribed}
    finally:
        os.unlink(tmp_path)


# ─── WebSocket ────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def get_root():
    return HTML_UI


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            user_input = await websocket.receive_text()
            intent = classify_intent(user_input)

            if intent == "CHAT":
                response = handle_chat(user_input)
            elif intent in ("FILE", "WEB", "TASK"):
                response = handle_task(user_input)
            elif intent == "PERSONA":
                response = "persona.yaml 파일을 직접 수정한 후 재시작해 주세요."
            elif intent == "VISION":
                response = "이미지를 분석하려면 🖼 버튼으로 이미지를 첨부해 주세요."
            elif intent == "VOICE":
                response = "음성 입력을 사용하려면 🎤 버튼을 눌러 주세요."
            else:
                response = handle_chat(user_input)

            await websocket.send_text(response)
    except Exception as e:
        print(f"[WebSocket Error] {e}")


# ─── 진입점 ──────────────────────────────────────────────────────────────

def web_main():
    """웹 서버 실행 진입점"""
    print("Starting Web UI on http://localhost:8000")
    print("Phase 6: Vision & Voice enabled")
    print("Press Ctrl+C to stop.")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")


if __name__ == "__main__":
    web_main()

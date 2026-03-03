"""
web_ui.py — Ageis Agent Web UI (Phase 7: 자율성 & 스케줄링)

엔드포인트:
  GET  /                       — 채팅 UI
  GET  /api/health             — 헬스 체크
  POST /api/chat               — REST 채팅
  POST /api/task               — REST 태스크
  POST /api/vision             — 이미지 분석 (Phase 6-A)
  POST /api/vision/file        — 파일 업로드 이미지 분석 (Phase 6-A)
  POST /api/voice              — 서버 마이크 녹음 → STT → 응답 (Phase 6-B)
  POST /api/voice/upload       — 브라우저 녹음 업로드 → STT → 응답 (Phase 6-B)
  POST /api/schedule           — 스케줄 등록 (Phase 7-A)
  GET  /api/schedules          — 스케줄 목록 (Phase 7-A)
  DELETE /api/schedule/{id}    — 스케줄 삭제 (Phase 7-A)
  POST /api/watch              — 감시 규칙 등록 (Phase 7-B)
  GET  /api/watches            — 감시 규칙 목록 (Phase 7-B)
  DELETE /api/watch/{id}       — 감시 규칙 삭제 (Phase 7-B)
  WS   /ws                     — WebSocket 채팅 (텍스트)
"""
import os
import sys
import asyncio
import json
import base64
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, Form
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

from core_logic import handle_chat, handle_task, handle_vision, handle_voice, handle_society
from router import classify_intent
from scheduler import AgentScheduler
from event_monitor import EventMonitor

# ─── Phase 7: 자율 실행 인스턴스 ─────────────────────────────────────────────

_scheduler = AgentScheduler(task_runner=handle_task)
_monitor = EventMonitor(task_runner=handle_task)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan — 스케줄러 & 이벤트 모니터 시작/종료 관리."""
    # startup
    _scheduler.start()
    _monitor.start(asyncio.get_event_loop())
    yield
    # shutdown
    _scheduler.stop()
    _monitor.stop()


app = FastAPI(title="Ageis Agent UI", lifespan=lifespan)

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


class ScheduleRequest(BaseModel):
    cron: str        # e.g. "0 9 * * 1-5"
    task: str        # e.g. "주식 시장 요약해줘"


class WatchRequest(BaseModel):
    path: str        # e.g. "Agent_Workspace/downloads"
    pattern: str     # e.g. "*.pdf"
    event: str       # "created" | "modified" | "deleted"
    task: str        # e.g. "{file} 파일을 요약해서 저장해줘"


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
            --accent: #e94560;
            --accent2: #4fc3f7;
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
            width: 95%;
            max-width: 960px;
            height: 94vh;
            background-color: var(--chat-bg);
            border-radius: 12px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.6);
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }
        header {
            padding: 12px 20px;
            background-color: rgba(0,0,0,0.25);
            text-align: center;
            border-bottom: 1px solid #333;
            flex-shrink: 0;
        }
        h1 { margin: 0; font-size: 1.3rem; color: var(--accent); }
        .subtitle { font-size: 0.72rem; opacity: 0.7; margin-top: 2px; }

        /* ── 탭 ── */
        .tabs {
            display: flex;
            background: rgba(0,0,0,0.15);
            border-bottom: 1px solid #333;
            flex-shrink: 0;
        }
        .tab-btn {
            flex: 1;
            padding: 10px;
            background: none;
            border: none;
            color: #aaa;
            cursor: pointer;
            font-size: 0.85rem;
            font-weight: bold;
            border-bottom: 2px solid transparent;
            transition: color 0.2s, border-color 0.2s;
        }
        .tab-btn.active { color: var(--accent2); border-bottom-color: var(--accent2); }
        .tab-btn:hover:not(.active) { color: #ddd; }

        .tab-panel { display: none; flex: 1; flex-direction: column; overflow: hidden; }
        .tab-panel.active { display: flex; }

        /* ── 채팅 탭 ── */
        #chat-box {
            flex: 1;
            padding: 16px 20px;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            gap: 10px;
        }
        .message {
            max-width: 82%;
            padding: 9px 13px;
            border-radius: 12px;
            line-height: 1.5;
            word-wrap: break-word;
            animation: fadeIn 0.2s ease;
            font-size: 0.92rem;
        }
        .user  { align-self: flex-end;   background-color: var(--user-msg-bg); border-bottom-right-radius: 2px; }
        .agent { align-self: flex-start; background-color: rgba(255,255,255,0.09); border-bottom-left-radius: 2px; }
        .system { align-self: center; font-size: 0.74rem; color: #888; background: none; }
        .message img { max-width: 100%; border-radius: 6px; margin-top: 6px; display: block; }

        .input-area {
            padding: 12px 18px;
            background-color: rgba(0,0,0,0.2);
            border-top: 1px solid #333;
            display: flex;
            flex-direction: column;
            gap: 8px;
            flex-shrink: 0;
        }
        .input-row { display: flex; gap: 7px; align-items: center; }
        #msg-input {
            flex: 1;
            padding: 9px 12px;
            border-radius: 6px;
            border: 1px solid #444;
            background-color: var(--bg-color);
            color: white;
            outline: none;
            font-size: 0.92rem;
        }

        /* ── 버튼 공통 ── */
        .btn {
            padding: 8px 14px;
            color: white;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-weight: bold;
            transition: background 0.2s, opacity 0.2s;
            white-space: nowrap;
            font-size: 0.87rem;
        }
        .btn:disabled { opacity: 0.4; cursor: wait; }
        .btn-send   { background-color: var(--accent); }
        .btn-send:hover:not(:disabled)  { background-color: #c0354c; }
        .btn-img    { background-color: #2a6496; }
        .btn-img:hover:not(:disabled)   { background-color: #1d4e75; }
        .btn-voice  { background-color: #2e7d32; }
        .btn-voice:hover:not(:disabled) { background-color: #1b5e20; }
        .btn-voice.recording { background-color: #b71c1c; animation: pulse 1s infinite; }
        .btn-danger { background-color: #c62828; }
        .btn-danger:hover { background-color: #b71c1c; }
        .btn-primary { background-color: #1565c0; }
        .btn-primary:hover { background-color: #0d47a1; }

        /* ── 이미지 프리뷰 바 ── */
        #img-preview-bar {
            display: none;
            align-items: center;
            gap: 8px;
            padding: 5px 8px;
            background: rgba(42,100,150,0.22);
            border-radius: 6px;
            font-size: 0.8rem;
        }
        #img-preview-bar img { width: 36px; height: 36px; object-fit: cover; border-radius: 4px; }
        #img-preview-bar span { flex: 1; opacity: 0.85; }
        #img-clear-btn { background: none; border: none; color: #f44336; cursor: pointer; font-size: 0.95rem; padding: 0 4px; }

        /* ── 자동화 탭 ── */
        .auto-panel {
            flex: 1;
            overflow-y: auto;
            padding: 18px 22px;
            display: flex;
            flex-direction: column;
            gap: 24px;
        }
        .auto-section { background: rgba(0,0,0,0.18); border-radius: 10px; padding: 16px 18px; }
        .auto-section h3 { margin: 0 0 12px; font-size: 1rem; color: var(--accent2); }
        .form-row { display: flex; gap: 8px; flex-wrap: wrap; align-items: flex-start; margin-bottom: 8px; }
        .form-row label { font-size: 0.78rem; opacity: 0.75; display: block; margin-bottom: 3px; }
        .form-input {
            padding: 7px 10px;
            border-radius: 5px;
            border: 1px solid #444;
            background: var(--bg-color);
            color: white;
            font-size: 0.85rem;
            min-width: 140px;
        }
        .form-input.wide { flex: 1; min-width: 220px; }
        .rule-list { display: flex; flex-direction: column; gap: 6px; margin-top: 10px; }
        .rule-item {
            display: flex;
            align-items: center;
            gap: 10px;
            background: rgba(255,255,255,0.05);
            border-radius: 6px;
            padding: 8px 10px;
            font-size: 0.82rem;
        }
        .rule-item .rule-info { flex: 1; }
        .rule-item .rule-cron { color: var(--accent2); font-family: monospace; }
        .rule-item .rule-task { opacity: 0.85; margin-top: 2px; }
        .rule-item .rule-meta { font-size: 0.72rem; opacity: 0.5; }
        .empty-state { color: #666; font-size: 0.83rem; text-align: center; padding: 12px 0; }

        /* ── 애니메이션 ── */
        @keyframes fadeIn { from { opacity: 0; transform: translateY(3px); } to { opacity: 1; transform: translateY(0); } }
        @keyframes pulse  { 0%,100% { opacity: 1; } 50% { opacity: 0.55; } }

        .agent pre { background: #111; padding: 10px; border-radius: 4px; overflow-x: auto; }
        .agent code { font-family: monospace; background: rgba(0,0,0,0.3); padding: 2px 4px; border-radius: 3px; }

        /* ── 상태 표시 ── */
        #status { font-size: 0.68rem; color: #4caf50; margin-top: 3px; }
    </style>
</head>
<body>
<div class="container">
    <header>
        <h1>🤖 Ageis Agent</h1>
        <div class="subtitle">Phase 7: The Legs — Scheduler &amp; Event Monitor</div>
        <div id="status">● Connected</div>
    </header>

    <!-- 탭 버튼 -->
    <div class="tabs">
        <button class="tab-btn active" onclick="switchTab('chat')">💬 채팅</button>
        <button class="tab-btn" onclick="switchTab('auto')">⚙️ 자동화</button>
    </div>

    <!-- ── 채팅 탭 ─────────────────────────────────────────── -->
    <div id="tab-chat" class="tab-panel active">
        <div id="chat-box"></div>
        <div class="input-area">
            <div id="img-preview-bar">
                <img id="img-thumb" src="" alt="preview">
                <span id="img-name">이미지 첨부됨</span>
                <button id="img-clear-btn" title="첨부 취소">✕</button>
            </div>
            <div class="input-row">
                <input id="msg-input" type="text"
                       placeholder="메시지 입력 / 이미지·마이크 버튼 사용..."
                       onkeypress="if(event.key==='Enter') sendMessage()">
                <button class="btn btn-img"   id="img-btn"   title="이미지 첨부" onclick="triggerImageUpload()">🖼</button>
                <button class="btn btn-voice" id="voice-btn" title="음성 입력"   onclick="toggleVoice()">🎤</button>
                <button class="btn btn-send"  id="send-btn"  onclick="sendMessage()">전송</button>
            </div>
        </div>
    </div>

    <!-- ── 자동화 탭 ──────────────────────────────────────── -->
    <div id="tab-auto" class="tab-panel">
        <div class="auto-panel">

            <!-- 7-A: 스케줄러 -->
            <div class="auto-section">
                <h3>⏰ 스케줄러 (시간 기반 자동 실행)</h3>
                <div class="form-row">
                    <div>
                        <label>Cron 표현식</label>
                        <input class="form-input" id="sch-cron" placeholder="0 9 * * 1-5" style="width:160px">
                    </div>
                    <div style="flex:1">
                        <label>실행할 태스크</label>
                        <input class="form-input wide" id="sch-task" placeholder="뉴스 요약해서 Agent_Workspace/news.txt에 저장해줘">
                    </div>
                    <div style="align-self:flex-end">
                        <button class="btn btn-primary" onclick="addSchedule()">+ 추가</button>
                    </div>
                </div>
                <div style="font-size:0.74rem;opacity:0.55;margin-bottom:8px;">
                    예시: <code>0 9 * * 1-5</code> 평일 09:00 &nbsp;|&nbsp; <code>*/30 * * * *</code> 30분마다 &nbsp;|&nbsp; <code>0 0 * * *</code> 매일 자정
                </div>
                <div id="schedule-list" class="rule-list">
                    <div class="empty-state">등록된 스케줄이 없습니다.</div>
                </div>
            </div>

            <!-- 7-B: 파일 감시 -->
            <div class="auto-section">
                <h3>👁️ 파일 감시 (이벤트 기반 자동 실행)</h3>
                <div class="form-row">
                    <div>
                        <label>감시 경로</label>
                        <input class="form-input" id="wt-path" placeholder="Agent_Workspace/downloads" style="width:200px">
                    </div>
                    <div>
                        <label>파일 패턴</label>
                        <input class="form-input" id="wt-pattern" placeholder="*.pdf" style="width:100px">
                    </div>
                    <div>
                        <label>이벤트</label>
                        <select class="form-input" id="wt-event" style="width:110px">
                            <option value="created">생성 (created)</option>
                            <option value="modified">수정 (modified)</option>
                            <option value="deleted">삭제 (deleted)</option>
                        </select>
                    </div>
                </div>
                <div class="form-row">
                    <div style="flex:1">
                        <label>실행할 태스크 (<code>{file}</code> = 파일 경로 자동 치환)</label>
                        <input class="form-input wide" id="wt-task" placeholder="{file} 파일을 요약해서 Agent_Workspace/summaries/ 에 저장해줘">
                    </div>
                    <div style="align-self:flex-end">
                        <button class="btn btn-primary" onclick="addWatch()">+ 추가</button>
                    </div>
                </div>
                <div id="watch-list" class="rule-list">
                    <div class="empty-state">등록된 감시 규칙이 없습니다.</div>
                </div>
            </div>

        </div>
    </div>
</div>

<!-- 숨겨진 파일 입력 -->
<input type="file" id="img-file-input" accept="image/*" style="display:none" onchange="onImageSelected(event)">

<script>
// ─── 탭 전환 ─────────────────────────────────────────────────────────────
function switchTab(name) {
    document.querySelectorAll(".tab-panel").forEach(p => p.classList.remove("active"));
    document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
    document.getElementById("tab-" + name).classList.add("active");
    event.currentTarget.classList.add("active");
    if (name === "auto") loadAutomation();
}

// ─── WebSocket ────────────────────────────────────────────────────────────
const ws = new WebSocket(`ws://${window.location.host}/ws`);
const chatBox   = document.getElementById("chat-box");
const msgInput  = document.getElementById("msg-input");
const sendBtn   = document.getElementById("send-btn");
const statusDiv = document.getElementById("status");
const voiceBtn  = document.getElementById("voice-btn");

let wsPingInterval = null;

ws.onopen  = () => {
    setStatus(true);
    addMsg("시스템에 연결되었습니다.", "system");
    // 25초마다 ping — AI 생성 중 브라우저 idle timeout 방지
    if (wsPingInterval) clearInterval(wsPingInterval);
    wsPingInterval = setInterval(() => {
        if (ws && ws.readyState === WebSocket.OPEN) ws.send("__ping__");
    }, 25000);
};
ws.onclose = () => {
    setStatus(false);
    addMsg("연결이 끊어졌습니다. 새로고침 해주세요.", "system");
    disableInput();
    if (wsPingInterval) { clearInterval(wsPingInterval); wsPingInterval = null; }
};
ws.onmessage = (e) => {
    if (e.data === "__pong__") return; // 킵얼라이브 응답 무시
    addMsg(e.data, "agent");
    enableInput();
};

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
let pendingImageB64 = "";

function sendMessage() {
    const text = msgInput.value.trim();
    if (pendingImageB64) {
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

// ─── Vision ───────────────────────────────────────────────────────────────
function triggerImageUpload() { document.getElementById("img-file-input").click(); }

function onImageSelected(event) {
    const file = event.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (e) => {
        const b64full = e.target.result;
        pendingImageB64 = b64full.split(",")[1];
        document.getElementById("img-thumb").src = b64full;
        document.getElementById("img-name").textContent = file.name;
        document.getElementById("img-preview-bar").style.display = "flex";
    };
    reader.readAsDataURL(file);
    event.target.value = "";
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
            body: JSON.stringify({ base64_image: b64, prompt }),
        });
        const data = await res.json();
        addMsg(data.response, "agent");
    } catch (e) {
        addMsg("이미지 분석 실패: " + e, "agent");
    }
    enableInput();
}

// ─── Voice ────────────────────────────────────────────────────────────────
let isRecording = false, mediaRecorder = null, audioChunks = [];

async function toggleVoice() {
    isRecording ? stopRecording() : await startRecording();
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
}

async function sendAudioToSTT() {
    addMsg("음성 인식 중...", "system");
    disableInput();
    const blob = new Blob(audioChunks, { type: "audio/webm" });
    const formData = new FormData();
    formData.append("file", blob, "voice.webm");
    formData.append("language", "ko");
    try {
        const res = await fetch("/api/voice/upload", { method: "POST", body: formData });
        const data = await res.json();
        if (data.transcribed) addMsg("[음성] " + data.transcribed, "user");
        addMsg(data.response, "agent");
    } catch (e) {
        addMsg("음성 처리 실패: " + e, "agent");
    }
    enableInput();
}

// ─── 클립보드 이미지 붙여넣기 ────────────────────────────────────────────
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

// ─── 자동화 탭: Scheduler & EventMonitor ─────────────────────────────────

async function loadAutomation() {
    await Promise.all([loadSchedules(), loadWatches()]);
}

// ── 스케줄러 ──

async function loadSchedules() {
    const res = await fetch("/api/schedules");
    const data = await res.json();
    renderSchedules(data.schedules || []);
}

function renderSchedules(list) {
    const el = document.getElementById("schedule-list");
    if (!list.length) {
        el.innerHTML = '<div class="empty-state">등록된 스케줄이 없습니다.</div>';
        return;
    }
    el.innerHTML = list.map(r => `
        <div class="rule-item">
            <div class="rule-info">
                <div class="rule-cron">🕐 ${r.cron}</div>
                <div class="rule-task">${escHtml(r.task)}</div>
                <div class="rule-meta">ID: ${r.id.slice(0,8)}… | 등록: ${r.created_at}</div>
            </div>
            <button class="btn btn-danger" onclick="deleteSchedule('${r.id}')">삭제</button>
        </div>`).join("");
}

async function addSchedule() {
    const cron = document.getElementById("sch-cron").value.trim();
    const task = document.getElementById("sch-task").value.trim();
    if (!cron || !task) { alert("Cron 표현식과 태스크를 모두 입력해주세요."); return; }
    const res = await fetch("/api/schedule", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ cron, task }),
    });
    if (res.ok) {
        document.getElementById("sch-cron").value = "";
        document.getElementById("sch-task").value = "";
        await loadSchedules();
    } else {
        const err = await res.json();
        alert("등록 실패: " + (err.detail || JSON.stringify(err)));
    }
}

async function deleteSchedule(id) {
    if (!confirm("이 스케줄을 삭제할까요?")) return;
    await fetch(`/api/schedule/${id}`, { method: "DELETE" });
    await loadSchedules();
}

// ── 파일 감시 ──

async function loadWatches() {
    const res = await fetch("/api/watches");
    const data = await res.json();
    renderWatches(data.watches || []);
}

function renderWatches(list) {
    const el = document.getElementById("watch-list");
    if (!list.length) {
        el.innerHTML = '<div class="empty-state">등록된 감시 규칙이 없습니다.</div>';
        return;
    }
    const evtIcon = { created: "🟢", modified: "🟡", deleted: "🔴" };
    el.innerHTML = list.map(r => `
        <div class="rule-item">
            <div class="rule-info">
                <div class="rule-cron">${evtIcon[r.event] || "●"} ${escHtml(r.path)} &nbsp;<code>${escHtml(r.pattern)}</code> &nbsp;on <b>${r.event}</b></div>
                <div class="rule-task">${escHtml(r.task)}</div>
                <div class="rule-meta">ID: ${r.id.slice(0,8)}… | 등록: ${r.created_at}</div>
            </div>
            <button class="btn btn-danger" onclick="deleteWatch('${r.id}')">삭제</button>
        </div>`).join("");
}

async function addWatch() {
    const path    = document.getElementById("wt-path").value.trim();
    const pattern = document.getElementById("wt-pattern").value.trim() || "*";
    const event   = document.getElementById("wt-event").value;
    const task    = document.getElementById("wt-task").value.trim();
    if (!path || !task) { alert("감시 경로와 태스크를 입력해주세요."); return; }
    const res = await fetch("/api/watch", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ path, pattern, event, task }),
    });
    if (res.ok) {
        document.getElementById("wt-path").value = "";
        document.getElementById("wt-pattern").value = "";
        document.getElementById("wt-task").value = "";
        await loadWatches();
    } else {
        const err = await res.json();
        alert("등록 실패: " + (err.detail || JSON.stringify(err)));
    }
}

async function deleteWatch(id) {
    if (!confirm("이 감시 규칙을 삭제할까요?")) return;
    await fetch(`/api/watch/${id}`, { method: "DELETE" });
    await loadWatches();
}

function escHtml(s) {
    return String(s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
}
</script>
</body>
</html>
"""


# ─── REST 엔드포인트 ──────────────────────────────────────────────────────

@app.get("/api/health")
async def health_check():
    return {
        "status": "ok",
        "version": "0.4.0",
        "phase": "8",
        "schedules": len(_scheduler.list_schedules()),
        "watches": len(_monitor.list_watches()),
    }


@app.post("/api/chat", response_model=ChatResponse)
async def api_chat(req: ChatRequest):
    intent = classify_intent(req.message)

    # Intent-based Routing
    loop = asyncio.get_running_loop()
    
    if intent == "SOCIETY":
        # Multi-Agent
        response = await loop.run_in_executor(None, handle_society, req.message)
    elif intent in ["FILE", "WEB", "TASK"]:
        # ReAct Single Agent
        response = await loop.run_in_executor(None, handle_task, req.message)
    else:
        # Simple Chat
        response = handle_chat(req.message)
        
    return ChatResponse(response=response, intent=intent)


@app.post("/api/task", response_model=ChatResponse)
async def api_task(req: ChatRequest):
    intent = classify_intent(req.message)
    loop = asyncio.get_running_loop()
    response = await loop.run_in_executor(None, handle_task, req.message)
    return ChatResponse(response=response, intent=intent)


# ── Phase 6-A: Vision ────────────────────────────────────────────────────

@app.post("/api/vision")
async def api_vision(req: VisionRequest):
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(None, handle_vision, "", req.base64_image, req.prompt)
    return {"response": result}


@app.post("/api/vision/file")
async def api_vision_file(
    file: UploadFile = File(...),
    prompt: str = Form(default="이 이미지에 무엇이 있나요? 자세히 설명해주세요."),
):
    raw = await file.read()
    b64 = base64.b64encode(raw).decode("utf-8")
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(None, handle_vision, "", b64, prompt)
    return {"response": result, "filename": file.filename}


# ── Phase 6-B: Voice ─────────────────────────────────────────────────────

@app.post("/api/voice")
async def api_voice(req: VoiceRequest):
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(None, handle_voice, req.duration, req.language, req.tts_response)
    return {"response": result}


@app.post("/api/voice/upload")
async def api_voice_upload(
    file: UploadFile = File(...),
    language: str = Form(default="ko"),
):
    import tempfile, os
    raw = await file.read()
    suffix = os.path.splitext(file.filename or ".webm")[1] or ".webm"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(raw)
        tmp_path = tmp.name
    try:
        from tools.stt_tool import transcribe_file_tool
        transcribed = transcribe_file_tool({"path": tmp_path, "language": language})
        if transcribed.startswith("ERROR:"):
            return {"response": transcribed, "transcribed": ""}
        loop = asyncio.get_running_loop()
        answer = await loop.run_in_executor(None, handle_chat, transcribed)
        return {"response": answer, "transcribed": transcribed}
    finally:
        os.unlink(tmp_path)


# ── Phase 7-A: Scheduler ─────────────────────────────────────────────────

@app.post("/api/schedule", status_code=201)
async def api_add_schedule(req: ScheduleRequest):
    """새 cron 스케줄을 등록합니다."""
    try:
        rule = _scheduler.add_schedule(cron=req.cron, task=req.task)
        return rule
    except Exception as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/schedules")
async def api_list_schedules():
    return {"schedules": _scheduler.list_schedules()}


@app.delete("/api/schedule/{schedule_id}")
async def api_delete_schedule(schedule_id: str):
    deleted = _scheduler.delete_schedule(schedule_id)
    if not deleted:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Schedule not found")
    return {"deleted": schedule_id}


# ── Phase 7-B: Event Monitor ─────────────────────────────────────────────

@app.post("/api/watch", status_code=201)
async def api_add_watch(req: WatchRequest):
    """새 파일시스템 감시 규칙을 등록합니다."""
    rule = _monitor.add_watch(
        path=req.path,
        pattern=req.pattern,
        event=req.event,
        task=req.task,
    )
    return rule


@app.get("/api/watches")
async def api_list_watches():
    return {"watches": _monitor.list_watches()}


@app.delete("/api/watch/{watch_id}")
async def api_delete_watch(watch_id: str):
    deleted = _monitor.delete_watch(watch_id)
    if not deleted:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Watch rule not found")
    return {"deleted": watch_id}


# ── Phase 8: Multi-Agent Society ─────────────────────────────────────────

@app.post("/api/society")
async def api_society(req: ChatRequest):
    """
    Phase 8: 멀티에이전트(Manager → Researcher/Writer) 파이프라인.
    복잡한 조사·작성 태스크를 여러 전문 에이전트가 협력하여 처리합니다.
    """
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(None, handle_society, req.message)
    return {"response": result, "intent": "SOCIETY"}


# ─── WebSocket ────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def get_root():
    return HTML_UI



# 디버그 로깅 헬퍼
def log_error(msg):
    import time
    try:
        with open("sidecar_debug.log", "a", encoding="utf-8") as f:
            f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] ERROR: {msg}\n")
    except:
        pass

def log_info(msg):
    import time
    try:
        with open("sidecar_debug.log", "a", encoding="utf-8") as f:
            f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] INFO: {msg}\n")
    except:
        pass

# 백그라운드 태스크가 가비지 컬렉터(GC)에 의해 강제 종료되는 것을 방지하기 위한 참조 Set
active_ws_tasks = set()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    log_info(f"{websocket.client.host}:{websocket.client.port} - \"WebSocket /ws\" [accepted]")
    log_info("connection open")
    
    try:
        while True:
            data = await websocket.receive_text()

            # 킵얼라이브 ping 처리 (클라이언트 타임아웃 방지)
            if data == "__ping__":
                await websocket.send_text("__pong__")
                continue

            # 1. 메시지 처리 함수 분리 (Background Task용)
            async def process_message(user_text: str):
                loop = asyncio.get_running_loop()
                try:
                    # A. 분류
                    intent = await loop.run_in_executor(None, classify_intent, user_text)
                    log_info(f"Received: {user_text[:50]}... -> Intent: {intent}")
                    
                    # B. 처리 (Intent에 따라 분기)
                    if intent == "SOCIETY":
                        response = await loop.run_in_executor(None, handle_society, user_text)
                    elif intent in ["FILE", "WEB", "TASK"]:
                        response = await loop.run_in_executor(None, handle_task, user_text)
                    else:
                        response = await loop.run_in_executor(None, handle_chat, user_text)
                        
                    await websocket.send_text(response)
                    
                except Exception as e:
                    err_msg = f"Processing Error: {str(e)}"
                    log_error(err_msg)
                    import traceback
                    log_error(traceback.format_exc())
                    try:
                        await websocket.send_text(f"Error: {str(e)}")
                    except Exception:
                        pass  # 웹소켓이 이미 닫혔으면 무시

            # Blocking I/O를 별도 태스크로 던져서 receive_text() 루프가 막히지 않게 함
            # 파이썬 GC 이슈 방지: 백그라운드 태스크를 셋에 저장하고 완료시 버림
            task = asyncio.create_task(process_message(data))
            active_ws_tasks.add(task)
            task.add_done_callback(active_ws_tasks.discard)

    except WebSocketDisconnect:
        log_info("connection closed")
    except Exception as e:
        log_error(f"WebSocket Critical Error: {str(e)}")
        import traceback
        log_error(traceback.format_exc())
def free_port(port: int):
    """PowerShell Get-NetTCPConnection으로 정확한 포트 매칭 후 좀비 프로세스 종료."""
    import platform, subprocess, time
    if platform.system() != "Windows":
        return
    try:
        ps_cmd = (
            f"Get-NetTCPConnection -LocalPort {port} -State Listen "
            f"-ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess"
        )
        result = subprocess.check_output(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_cmd],
            stderr=subprocess.DEVNULL,
            timeout=10,
        ).decode().strip()

        my_pid = str(os.getpid())
        killed = False
        for pid_str in result.splitlines():
            pid_str = pid_str.strip()
            if pid_str and pid_str != "0" and pid_str != my_pid:
                print(f"[포트 {port} 해제] 좀비 프로세스(PID: {pid_str}) 종료 중...", flush=True)
                subprocess.call(
                    ["taskkill", "/F", "/PID", pid_str],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                killed = True
        if killed:
            time.sleep(1.0)  # OS가 포트를 실제로 반납할 때까지 대기
    except Exception as e:
        print(f"[free_port] 경고: {e}", flush=True)

def web_main():
    # Unbuffered Output for PyInstaller/Tauri
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

    print("Starting Web UI on http://127.0.0.1:8000", flush=True)
    print("Phase 7: Scheduler & Event Monitor enabled", flush=True)
    print("Press Ctrl+C to stop.", flush=True)

    # 포트 8000 확보 — 최대 3번 시도 (좀비 프로세스 제거 후 재시도)
    import socket, time
    port_secured = False
    for attempt in range(1, 4):
        free_port(8000)
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind(("127.0.0.1", 8000))
            port_secured = True
            break
        except OSError:
            print(f"[포트 확보 재시도] {attempt}/3 실패 — 2초 후 재시도...", flush=True)
            time.sleep(2)

    if not port_secured:
        print("[FATAL] 포트 8000을 확보할 수 없습니다. 다른 앱이 점유 중인지 확인하세요.", flush=True)
        return

    try:
        # reload=False is safer for frozen apps
        uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info", reload=False)
    except Exception as e:
        print(f"[FATAL ERROR] Web UI crashed: {e}", flush=True)
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    try:
        web_main()
    except Exception as e:
        print(f"[FATAL STARTUP ERROR] {e}", flush=True)
        import traceback
        traceback.print_exc()
        input("Press Enter to exit...") # Console mode debugging

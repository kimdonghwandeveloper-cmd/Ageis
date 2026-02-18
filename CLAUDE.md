# Claude.md — 로컬 AI 에이전트 시스템 개발 마스터 플랜

> **프로젝트 코드명:** Ageis Agent  
> **작성일:** 2026-02-17  
> **패키지 매니저:** `uv`  
> **LLM 백엔드:** 로컬 모델 (Ollama)  
> **IPC 통신:** gRPC (강타입, 스키마 우선)  
> **타겟 OS:** 크로스플랫폼 (Linux / macOS / Windows)

---

## 아키텍처 개요

```
┌─────────────────────────────────────────────────────────┐
│                      사용자 인터페이스                        │
│              CLI Dashboard  /  Web UI (localhost)         │
└───────────────────────────┬─────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────┐
│               Python 마이크로서비스 레이어                    │
│   Router → ReAct Loop → Tools → Persona → Memory (RAG)  │
└───────────────────────────┬─────────────────────────────┘
                            │  gRPC (Proto 스키마)
┌───────────────────────────▼─────────────────────────────┐
│                 Rust 코어 데몬 (보안 게이트웨이)               │
│         Permission System │ Sandbox │ IPC 브로커           │
└───────────────────────────┬─────────────────────────────┘
                            │
              ┌─────────────┴──────────────┐
              │                            │
     Agent_Workspace /               Ollama API
     파일 시스템 (샌드박스)            (로컬 LLM)
```

---

## Phase 1. 뼈대 세우기: 통신 기반 및 보안 샌드박스 (The Body)

> **핵심 목표:** Rust와 Python이 안전하고 빠르게 데이터를 주고받는 고속도로를 깔고, 방어벽을 세운다.

### 목표 1: 로컬 프로세스 간 통신 (IPC) 구축

#### 기술 스택
- **Rust 코어 데몬:** `tonic` 크레이트 (gRPC 서버)
- **Python 마이크로서비스:** `grpcio` + `grpcio-tools` (gRPC 클라이언트)
- **Proto 스키마:** `.proto` 파일로 메시지 및 서비스 인터페이스 정의

#### 구현 세부사항

**디렉토리 구조:**
```
ageis/
├── proto/
│   └── agent.proto          # gRPC 서비스 스키마 정의
├── rust_core/               # Rust 코어 데몬
│   ├── Cargo.toml
│   └── src/
│       ├── main.rs
│       ├── server.rs        # gRPC 서버 구현
│       └── sandbox.rs       # 샌드박스 로직
├── python_agent/            # Python 마이크로서비스
│   ├── pyproject.toml       # uv 프로젝트 파일
│   ├── main.py
│   ├── router.py
│   ├── react_loop.py
│   └── tools/
│       ├── file_reader.py
│       └── web_scraper.py
├── Agent_Workspace/         # 샌드박스 허용 디렉토리
└── claude.md                # 이 파일
```

**`proto/agent.proto` 핵심 인터페이스:**
```protobuf
syntax = "proto3";
package agent;

service AgentBroker {
  // Python → Rust: 파일 I/O 요청 (권한 게이트)
  rpc RequestFileRead (FileRequest) returns (FileResponse);
  rpc RequestFileWrite (FileWriteRequest) returns (StatusResponse);

  // Python → Rust: 명령 실행 위임
  rpc ExecuteCommand (CommandRequest) returns (CommandResponse);

  // 양방향: 텍스트 스트리밍 (대화용)
  rpc StreamChat (stream ChatMessage) returns (stream ChatMessage);
}

message FileRequest   { string path = 1; }
message FileResponse  { bytes content = 1; bool allowed = 2; string error = 3; }
message FileWriteRequest { string path = 1; bytes content = 2; }
message StatusResponse { bool success = 1; string message = 2; }
message CommandRequest { string command = 1; repeated string args = 2; }
message CommandResponse { int32 exit_code = 1; string stdout = 2; string stderr = 3; }
message ChatMessage   { string role = 1; string content = 2; string session_id = 3; }
```

**Rust 코어 데몬 실행:**
```bash
# 크로스플랫폼 빌드
cargo build --release
./target/release/ageis-core --port 50051
```

**Python 마이크로서비스 실행 (uv 사용):**
```bash
cd python_agent
uv run python main.py
```

---

### 목표 2: 기본 권한 제어 (Permission) 시스템 설계

#### 아키텍처 강제 원칙
- Python 엔진은 **절대로** 직접 파일시스템에 접근하지 않는다.
- 모든 파일 I/O는 반드시 **Rust 코어 데몬의 gRPC 엔드포인트**를 경유한다.
- Rust가 유일한 시스템 접근 게이트웨이 역할을 수행한다.

#### Rust 샌드박스 로직 (`rust_core/src/sandbox.rs`)
```rust
use std::path::{Path, PathBuf};

pub struct Sandbox {
    allowed_root: PathBuf,
}

impl Sandbox {
    pub fn new(workspace: &str) -> Self {
        Sandbox {
            allowed_root: PathBuf::from(workspace).canonicalize().unwrap(),
        }
    }

    /// 경로가 Agent_Workspace 내부인지 검증 (Path Traversal 방어)
    pub fn is_path_allowed(&self, requested: &str) -> bool {
        let path = match PathBuf::from(requested).canonicalize() {
            Ok(p) => p,
            Err(_) => return false,
        };
        path.starts_with(&self.allowed_root)
    }

    pub fn safe_read(&self, path: &str) -> Result<Vec<u8>, String> {
        if !self.is_path_allowed(path) {
            return Err(format!("DENIED: '{}' is outside Agent_Workspace", path));
        }
        std::fs::read(path).map_err(|e| e.to_string())
    }

    pub fn safe_write(&self, path: &str, content: &[u8]) -> Result<(), String> {
        if !self.is_path_allowed(path) {
            return Err(format!("DENIED: '{}' is outside Agent_Workspace", path));
        }
        std::fs::write(path, content).map_err(|e| e.to_string())
    }
}
```

#### 크로스플랫폼 고려사항
| OS | 경로 구분자 | canonicalize() 주의점 |
|----|------------|----------------------|
| Linux / macOS | `/` | 심볼릭 링크 해소됨 |
| Windows | `\` | UNC 경로 처리 필요, `dunce` 크레이트 활용 권장 |

**Windows 대응:** `Cargo.toml`에 `dunce = "1"` 추가 후 `dunce::canonicalize()` 사용.

#### Rust 핵심 의존성 (`Cargo.toml`)
```toml
[dependencies]
tonic       = "0.12"
prost       = "0.13"
tokio       = { version = "1", features = ["full"] }
dunce       = "1"          # Windows 경로 정규화
tracing     = "0.1"        # 구조화 로깅
tracing-subscriber = "0.3"

[build-dependencies]
tonic-build = "0.12"
```

#### Python 핵심 의존성 (`python_agent/pyproject.toml`)
```toml
[project]
name = "ageis-agent"
requires-python = ">=3.11"
dependencies = [
    "grpcio>=1.65",
    "grpcio-tools>=1.65",
    "ollama>=0.3",
]
```

---

## Phase 2. 뇌 이식: LLM 인지 루프와 기초 도구 (The Brain)

> **핵심 목표:** LLM이 상황을 판단하고 행동할 수 있는 지능을 부여한다.

### 목표 1: 라우터 (Router) 패턴 도입

#### 의도 분류기 (Classifier) 프롬프트
```python
# python_agent/router.py

CLASSIFIER_PROMPT = """
당신은 사용자 입력을 분석하여 적절한 파이프라인으로 라우팅하는 분류기입니다.
아래 카테고리 중 하나만 반환하세요:

- CHAT: 일반 대화, 질문, 설명 요청
- FILE: 파일 읽기, 쓰기, 수정 관련 작업
- WEB: 웹 검색, URL 크롤링, 최신 정보 수집
- TASK: 여러 도구를 조합한 복합 작업 (ReAct 루프 필요)
- PERSONA: 에이전트 설정 변경 (이름, 말투, 규칙 수정)

사용자 입력: {user_input}
카테고리:"""

PIPELINE_MAP = {
    "CHAT":    "handle_chat",
    "FILE":    "handle_file_via_grpc",
    "WEB":     "handle_web_scrape",
    "TASK":    "handle_react_loop",
    "PERSONA": "handle_persona_update",
}
```

---

### 목표 2: ReAct (Reasoning + Acting) 루프 구현

```python
# python_agent/react_loop.py

MAX_ITERATIONS = 10

REACT_SYSTEM_PROMPT = """
당신은 도구를 사용해 임무를 수행하는 에이전트입니다.
다음 형식을 엄격히 따르세요:

Thought: [현재 상황 분석 및 다음 행동 계획]
Action: [사용할 도구 이름]
Action Input: [도구에 전달할 입력값 (JSON)]
Observation: [도구 실행 결과 — 시스템이 채워넣음]
... (필요한 만큼 반복)
Final Answer: [최종 답변]

사용 가능한 도구: {tool_descriptions}
"""

class ReActAgent:
    def __init__(self, tools: dict, llm_client):
        self.tools = tools          # {"tool_name": callable}
        self.llm = llm_client
        self.history = []

    def run(self, task: str) -> str:
        self.history = [{"role": "user", "content": task}]

        for iteration in range(MAX_ITERATIONS):
            response = self.llm.chat(
                model="llama3.2",   # Ollama 모델명 (설정으로 교체 가능)
                messages=self.history
            )
            output = response["message"]["content"]
            self.history.append({"role": "assistant", "content": output})

            # Final Answer 도달 시 종료
            if "Final Answer:" in output:
                return output.split("Final Answer:")[-1].strip()

            # Action 파싱 및 실행
            action, action_input = self._parse_action(output)
            if action and action in self.tools:
                observation = self.tools[action](action_input)
                obs_message = f"Observation: {observation}"
                self.history.append({"role": "user", "content": obs_message})
            else:
                self.history.append({
                    "role": "user",
                    "content": f"Observation: Error - Tool '{action}' not found."
                })

        return "Max iterations reached. Could not complete the task."

    def _parse_action(self, text: str) -> tuple:
        import re, json
        action_match = re.search(r"Action:\s*(.+)", text)
        input_match  = re.search(r"Action Input:\s*(\{.*?\})", text, re.DOTALL)
        action = action_match.group(1).strip() if action_match else None
        try:
            action_input = json.loads(input_match.group(1)) if input_match else {}
        except json.JSONDecodeError:
            action_input = {}
        return action, action_input
```

---

### 목표 3: 기초 도구 (Tools) 파이프라인 연동

**도구 1: 샌드박스 파일 리더 (gRPC 경유)**
```python
# python_agent/tools/file_reader.py
import grpc
# (자동 생성된 proto 파일 임포트)

def read_file_tool(args: dict) -> str:
    """Agent_Workspace 내 파일 읽기 (Rust 샌드박스 통과)"""
    path = args.get("path", "")
    with grpc.insecure_channel("localhost:50051") as channel:
        stub = AgentBrokerStub(channel)
        response = stub.RequestFileRead(FileRequest(path=path))
    if response.allowed:
        return response.content.decode("utf-8")
    return f"ERROR: {response.error}"
```

**도구 2: 경량 웹 크롤러**
```python
# python_agent/tools/web_scraper.py
# uv add: httpx beautifulsoup4

import httpx
from bs4 import BeautifulSoup

def web_scrape_tool(args: dict) -> str:
    """URL에서 본문 텍스트만 추출 (최대 2000자)"""
    url = args.get("url", "")
    try:
        resp = httpx.get(url, timeout=10, follow_redirects=True)
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer"]):
            tag.decompose()
        text = soup.get_text(separator="\n", strip=True)
        return text[:2000]
    except Exception as e:
        return f"ERROR: {e}"
```

**도구 등록 및 ReAct 루프 연결:**
```python
# python_agent/main.py
from tools.file_reader import read_file_tool
from tools.web_scraper import web_scrape_tool
from react_loop import ReActAgent
import ollama

TOOLS = {
    "read_file": read_file_tool,
    "web_scrape": web_scrape_tool,
}

agent = ReActAgent(tools=TOOLS, llm_client=ollama)
```

---

## Phase 3. 자아 형성: 장기 기억과 페르소나 주입 (The Soul)

> **핵심 목표:** 에이전트가 과거를 기억하고 성격을 갖춘 인격체로 거듭난다.

### 목표 1: 로컬 Vector DB 연동 및 RAG 파이프라인 구축

#### 기술 스택 선택
- **Vector DB:** ChromaDB (로컬 파일 기반, 서버 불필요)
- **임베딩 모델:** Ollama 임베딩 엔드포인트 (`nomic-embed-text`)
- **패키지:** `uv add chromadb ollama`

#### RAG 파이프라인 구조
```python
# python_agent/memory.py
import chromadb
import ollama

class AgentMemory:
    def __init__(self, persist_dir: str = "Agent_Workspace/.chroma"):
        self.client = chromadb.PersistentClient(path=persist_dir)
        self.collection = self.client.get_or_create_collection(
            name="agent_memory",
            metadata={"hnsw:space": "cosine"}
        )

    def _embed(self, text: str) -> list[float]:
        response = ollama.embeddings(model="nomic-embed-text", prompt=text)
        return response["embedding"]

    def save(self, text: str, metadata: dict = {}):
        """대화 또는 설정을 임베딩하여 저장"""
        import uuid
        self.collection.add(
            ids=[str(uuid.uuid4())],
            embeddings=[self._embed(text)],
            documents=[text],
            metadatas=[metadata]
        )

    def recall(self, query: str, n_results: int = 5) -> list[str]:
        """관련 기억 검색 (RAG)"""
        results = self.collection.query(
            query_embeddings=[self._embed(query)],
            n_results=n_results
        )
        return results["documents"][0] if results["documents"] else []
```

#### 대화 기록 자동 저장 흐름
```
사용자 입력 → ReAct 루프 실행 → 결과 생성
    → AgentMemory.save(대화 전문, metadata={timestamp, session_id})
    → 다음 요청 시 AgentMemory.recall(새 쿼리) → 관련 기억 → 프롬프트 주입
```

---

### 목표 2: 동적 시스템 프롬프트 (Persona) 설계

#### 페르소나 정의 파일 포맷 (`Agent_Workspace/persona.yaml`)
```yaml
# 에이전트 페르소나 설정 파일
# 이 파일을 수정하면 다음 세션부터 자동 적용됩니다.

name: "Aria"
version: "1.0.0"

personality:
  description: "논리적이고 간결하며, 필요할 때만 유머를 사용하는 전문가형 어시스턴트"
  tone: "professional"           # professional / casual / friendly / formal
  language: "ko"                 # ko / en / auto
  verbosity: "concise"           # verbose / concise / minimal

capabilities:
  - "파일 시스템 제어 (샌드박스 내)"
  - "웹 정보 수집"
  - "복합 태스크 자동화"

restrictions:
  absolute_forbidden:
    - "Agent_Workspace 외부 파일 접근 시도"
    - "사용자 개인정보 외부 전송"
    - "시스템 명령어 직접 실행 (Rust 게이트 미경유)"
  content_policy:
    - "불법적이거나 유해한 콘텐츠 생성 거부"

memory:
  enabled: true
  max_recall_items: 5
  session_persistence: true
```

#### 페르소나 로더 및 최종 프롬프트 조립
```python
# python_agent/persona.py
import yaml
from memory import AgentMemory

def load_persona(path: str = "Agent_Workspace/persona.yaml") -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def build_system_prompt(user_query: str, memory: AgentMemory) -> str:
    persona = load_persona()
    recalled_memories = memory.recall(user_query)
    memories_text = "\n".join(f"- {m}" for m in recalled_memories)

    system_prompt = f"""
당신의 이름은 {persona['name']}입니다.
성격: {persona['personality']['description']}
말투: {persona['personality']['tone']} / 언어: {persona['personality']['language']}

[절대 금지 행동]
{chr(10).join(f"- {r}" for r in persona['restrictions']['absolute_forbidden'])}

[관련 기억 (RAG 검색 결과)]
{memories_text if memories_text else "관련 기억 없음"}

위 페르소나와 기억을 바탕으로 사용자 요청에 응답하세요.
""".strip()

    return system_prompt
```

---

## Phase 4. 확장 및 사용자 경험 (Expansion & UX)

> **핵심 목표:** 일반 대중과 개발자가 쉽게 사용하고 개조할 수 있도록 포장한다.

### 목표 1: 커스텀 플러그인 생태계 기반 마련

#### 플러그인 규격 (인터페이스 계약)
```python
# 플러그인 파일 예시: Agent_Workspace/plugins/my_tool.py

TOOL_NAME = "my_custom_tool"           # 필수: 도구 이름
TOOL_DESCRIPTION = "사용자가 정의한 도구"  # 필수: ReAct 루프에서 LLM이 참고

def run(args: dict) -> str:            # 필수: 실행 함수 시그니처
    """args를 받아 문자열 결과를 반환"""
    return f"플러그인 실행 결과: {args}"
```

#### 동적 플러그인 로더
```python
# python_agent/plugin_loader.py
import importlib.util
import os

PLUGIN_DIR = "Agent_Workspace/plugins"

def load_plugins() -> dict:
    """plugins/ 폴더의 .py 파일을 자동으로 도구로 등록"""
    tools = {}
    if not os.path.isdir(PLUGIN_DIR):
        return tools

    for filename in os.listdir(PLUGIN_DIR):
        if not filename.endswith(".py") or filename.startswith("_"):
            continue
        filepath = os.path.join(PLUGIN_DIR, filename)
        spec = importlib.util.spec_from_file_location(filename[:-3], filepath)
        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)
            if hasattr(module, "TOOL_NAME") and hasattr(module, "run"):
                tools[module.TOOL_NAME] = module.run
                print(f"[Plugin] Loaded: {module.TOOL_NAME}")
        except Exception as e:
            print(f"[Plugin] Failed to load {filename}: {e}")
    return tools
```

---

### 목표 2: 로컬 웹 UI 또는 CLI 대시보드 구축

#### CLI 대시보드 (`python_agent/cli.py`)
```python
# uv add: rich prompt-toolkit

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

console = Console()

def cli_main(agent):
    console.print(Panel.fit(
        "[bold cyan]Ageis Agent[/bold cyan]\n"
        "Type your command. Use [bold]/quit[/bold] to exit.",
        border_style="cyan"
    ))

    while True:
        try:
            user_input = Prompt.ask("[bold green]You[/bold green]")
            if user_input.strip().lower() in ("/quit", "/exit"):
                console.print("[yellow]Goodbye.[/yellow]")
                break
            with console.status("[bold]Thinking...[/bold]"):
                result = agent.run(user_input)
            console.print(Panel(result, title="[bold magenta]Agent[/bold magenta]",
                                border_style="magenta"))
        except KeyboardInterrupt:
            break
```

#### 로컬 웹 UI (`python_agent/web_ui.py`)
```python
# uv add: fastapi uvicorn[standard] websockets

from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
import uvicorn

app = FastAPI(title="Ageis Agent UI")

HTML_UI = """
<!DOCTYPE html>
<html>
<head>
  <title>Ageis Agent</title>
  <style>
    body { font-family: monospace; max-width: 800px; margin: 40px auto; background: #1a1a2e; color: #eee; }
    #chat { height: 500px; overflow-y: auto; border: 1px solid #444; padding: 16px; border-radius: 8px; }
    input { width: 80%; padding: 8px; background: #16213e; color: #eee; border: 1px solid #444; border-radius: 4px; }
    button { padding: 8px 16px; background: #0f3460; color: white; border: none; border-radius: 4px; cursor: pointer; }
    .user { color: #4fc3f7; } .agent { color: #a5d6a7; }
  </style>
</head>
<body>
  <h1>🤖 Ageis Agent</h1>
  <div id="chat"></div>
  <br>
  <input id="msg" type="text" placeholder="메시지를 입력하세요..." onkeypress="if(event.key==='Enter')send()">
  <button onclick="send()">전송</button>
  <script>
    const ws = new WebSocket("ws://localhost:8000/ws");
    const chat = document.getElementById("chat");
    ws.onmessage = e => {
      chat.innerHTML += `<p class="agent"><b>Agent:</b> ${e.data}</p>`;
      chat.scrollTop = chat.scrollHeight;
    };
    function send() {
      const msg = document.getElementById("msg").value.trim();
      if (!msg) return;
      chat.innerHTML += `<p class="user"><b>You:</b> ${msg}</p>`;
      ws.send(msg);
      document.getElementById("msg").value = "";
    }
  </script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def root():
    return HTML_UI

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, agent=None):
    await websocket.accept()
    while True:
        data = await websocket.receive_text()
        result = agent.run(data)   # 실제 agent 인스턴스 주입 필요
        await websocket.send_text(result)

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
```

---

## 전체 의존성 요약

### Python (`uv add` 명령어 목록)

```bash
# Phase 1
uv add grpcio grpcio-tools

# Phase 2
uv add ollama httpx beautifulsoup4

# Phase 3
uv add chromadb pyyaml

# Phase 4
uv add rich prompt-toolkit fastapi "uvicorn[standard]" websockets
```

### Rust (`Cargo.toml`)

```toml
[dependencies]
tonic               = "0.12"
prost               = "0.13"
tokio               = { version = "1", features = ["full"] }
dunce               = "1"
tracing             = "0.1"
tracing-subscriber  = { version = "0.3", features = ["env-filter"] }

[build-dependencies]
tonic-build = "0.12"
```

---

## 크로스플랫폼 체크리스트

| 항목 | Linux | macOS | Windows |
|------|:-----:|:-----:|:-------:|
| gRPC Unix Socket 사용 | ✅ | ✅ | ❌ (TCP 대체) |
| `dunce::canonicalize()` | 불필요 | 불필요 | ✅ 필수 |
| ChromaDB 로컬 파일 | ✅ | ✅ | ✅ |
| Ollama 설치 | ✅ | ✅ | ✅ |
| `Agent_Workspace` 경로 | `/` 사용 | `/` 사용 | `\` 주의 |

**Windows gRPC 대안:** Unix Domain Socket 대신 `localhost:50051` TCP 연결 사용.  
Rust 서버에서 `#[cfg(target_os = "windows")]` 분기로 자동 처리 구현 권장.

---

## 개발 순서 요약

```
Phase 1 ──► Rust gRPC 서버 + Proto 정의 + Python 클라이언트 연결
    │         └─► Sandbox 경로 검증 로직 검증 (단위 테스트)
    ▼
Phase 2 ──► Classifier 프롬프트 + ReAct 루프 + 기초 도구 2종
    │         └─► Ollama 연동 후 end-to-end 테스트
    ▼
Phase 3 ──► ChromaDB RAG 파이프라인 + persona.yaml 로더 + 프롬프트 조립
    │         └─► 기억 저장/검색 정확도 검증
    ▼
Phase 4 ──► 플러그인 동적 로더 + CLI 대시보드 + Web UI
              └─► 통합 테스트 및 문서화
```

---

*이 문서는 개발 진행에 따라 각 Phase 완료 시 업데이트한다.*
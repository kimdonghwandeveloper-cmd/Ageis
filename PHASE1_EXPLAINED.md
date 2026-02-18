# Phase 1 코드 쉽게 이해하기

> 이 문서는 Phase 1에서 만든 코드가 **무슨 일을 하는지** 비유와 함께 설명합니다.

---

## 전체 그림: 은행 창구 비유

```
[Python 에이전트]          [Rust 코어 데몬]           [Agent_Workspace]
    고객                      은행 창구                    금고

 "이 파일 좀 읽어줘"  ──►  "신분 확인... 통과!"  ──►  파일 꺼내서 전달
 "저 파일에 써줘"     ──►  "경로 확인... 통과!"  ──►  파일에 기록
 "rm -rf / 실행해줘"  ──►  "거부! 허용 목록에 없음" ✘
 "../../../etc/passwd" ──►  "거부! 금고 밖임"       ✘
```

- **Python** = 고객. 하고 싶은 일을 요청만 한다. 직접 금고에 손대지 못한다.
- **Rust** = 은행 창구. 모든 요청을 검사하고, 안전한 것만 처리한다.
- **Agent_Workspace** = 금고. 이 안에 있는 파일만 읽고 쓸 수 있다.
- **gRPC** = 고객과 창구 사이의 전화선. 정해진 양식(proto)으로만 대화한다.

---

## 파일 하나씩 뜯어보기

### 1. `proto/agent.proto` — 대화 양식지

은행에 가면 "입금 신청서", "출금 신청서" 같은 양식이 있다.
이 파일이 바로 그 **양식 모음집**이다.

```
"파일 읽어줘" 양식 (FileRequest)     → 칸: 경로
"파일 써줘" 양식 (FileWriteRequest)  → 칸: 경로, 내용
"명령어 실행해줘" 양식 (CommandRequest) → 칸: 명령어, 인자들
"채팅하자" 양식 (ChatMessage)        → 칸: 역할, 내용, 세션ID
```

이 양식을 기반으로:
- Rust 쪽에는 "양식을 받아 처리하는 코드"가 자동 생성되고
- Python 쪽에는 "양식을 작성해서 보내는 코드"가 자동 생성된다

---

### 2. `rust_core/src/sandbox.rs` — 경비원

이 파일의 역할은 딱 하나: **"이 경로, 들여보내도 되나?"**

```
요청: "Agent_Workspace/memo.txt"
  → 경로를 절대 경로로 변환 (심볼릭 링크, .. 등 트릭 제거)
  → "C:\Users\karl3\Ageis\Agent_Workspace\memo.txt"
  → Agent_Workspace 안에 있나? ✅ 통과!

요청: "../../Windows/System32/config/sam"
  → 절대 경로로 변환
  → "C:\Windows\System32\config\sam"
  → Agent_Workspace 안에 있나? ❌ 거부!
```

**왜 `dunce`라는 라이브러리를 쓰나?**
Windows에서 경로를 정규화하면 `\\?\C:\Users\...` 같은 이상한 접두사가 붙는다.
`dunce`는 이걸 깔끔하게 `C:\Users\...`로 만들어준다.

---

### 3. `rust_core/src/server.rs` — 은행 창구 직원

4가지 업무를 처리한다:

| 업무 | 하는 일 | 보안 |
|------|---------|------|
| `request_file_read` | 파일 읽기 | sandbox.rs에게 경로 확인 요청 |
| `request_file_write` | 파일 쓰기 | sandbox.rs에게 경로 확인 요청 |
| `execute_command` | 명령어 실행 | 화이트리스트(echo, ls, dir, cat, type, date)만 허용 |
| `stream_chat` | 채팅 | 현재는 받은 말을 그대로 돌려주는 에코 모드 |

**`Arc<Sandbox>`가 뭔가?**
여러 고객(요청)이 동시에 오면 경비원(Sandbox)을 공유해야 한다.
`Arc`는 "여러 명이 같이 쓸 수 있는 공유 열쇠"라고 생각하면 된다.

---

### 4. `rust_core/src/main.rs` — 은행 문 여는 사람

프로그램을 시작하면 이 파일이 실행된다. 하는 일:

1. 로깅 시스템 켜기 (뭐가 일어나는지 터미널에 출력)
2. 커맨드라인 인자 읽기 (`--port 50051 --workspace ../Agent_Workspace`)
3. 경비원(Sandbox) 고용
4. 창구 직원(AgentBrokerService) 배치
5. 은행 문 열기 (gRPC 서버 시작, 0.0.0.0:50051에서 대기)

---

### 5. `rust_core/build.rs` — 양식 인쇄기

`cargo build` 할 때 **컴파일 전에** 자동 실행된다.
`proto/agent.proto` 파일을 읽어서 Rust가 이해할 수 있는 코드로 변환한다.
직접 건드릴 일은 거의 없다.

---

### 6. `python_agent/generate_proto.py` — Python용 양식 인쇄기

`build.rs`의 Python 버전이다.
`proto/agent.proto`를 읽어서 2개의 Python 파일을 만든다:

- `agent_pb2.py` → 양식 클래스들 (FileRequest, ChatMessage 등)
- `agent_pb2_grpc.py` → 전화 거는 코드 (AgentBrokerStub)

**주의:** `agent.proto`를 수정하면 이 스크립트를 다시 실행해야 한다.

---

### 7. `python_agent/grpc_client.py` — 전화기

Rust 서버에 전화 거는 코드를 깔끔하게 감싼 클래스다.

```python
# 이렇게 쓸 수 있다:
with AgentGrpcClient("localhost:50051") as client:
    내용 = client.read_file("Agent_Workspace/memo.txt")
    client.write_file("Agent_Workspace/결과.txt", "완료!")
    결과 = client.execute_command("echo", ["안녕하세요"])
```

내부적으로는:
1. Python 객체 → protobuf 바이트로 직렬화
2. 네트워크로 Rust 서버에 전송
3. Rust가 처리 후 응답 바이트 반환
4. protobuf 바이트 → Python 객체로 역직렬화

이 과정을 `read_file()`, `write_file()` 같은 간단한 메서드로 감춰준다.

---

### 8. `python_agent/main.py` — 테스트 스크립트

5가지 시나리오를 순서대로 테스트한다:

1. `echo` 명령어 실행 → 정상 동작 확인
2. 파일 쓰기 → Agent_Workspace에 파일 생성
3. 파일 읽기 → 방금 쓴 파일 읽기
4. 샌드박스 밖 접근 → "DENIED" 응답 확인
5. 금지 명령어(`rm`) → "DENIED" 응답 확인

---

## 데이터 흐름 한눈에 보기

```
사용자가 "memo.txt 읽어줘"라고 요청하면:

[Python main.py]
    │
    ▼
[grpc_client.py]  →  FileRequest(path="memo.txt") 생성
    │
    ▼  (gRPC 네트워크 전송, localhost:50051)
    │
[Rust server.rs]  →  request_file_read() 호출
    │
    ▼
[Rust sandbox.rs] →  is_path_allowed("memo.txt") 검증
    │                   경로 정규화 → Agent_Workspace 안인지 확인
    ▼
  ✅ 허용 → std::fs::read()로 파일 읽기
    │
    ▼  (gRPC 응답 반환)
    │
[Python grpc_client.py]  →  bytes를 문자열로 변환
    │
    ▼
[Python main.py]  →  화면에 출력
```

---

## 자주 쓸 명령어 모음

```bash
# Rust 서버 빌드 + 실행
cd rust_core && cargo run --release -- --workspace ../Agent_Workspace

# Python 테스트 실행 (다른 터미널에서, 서버 켜둔 상태로)
cd python_agent && uv run python main.py

# proto 파일 수정 후 Python 코드 재생성
cd python_agent && uv run python generate_proto.py

# Rust 단위 테스트 실행
cd rust_core && cargo test
```

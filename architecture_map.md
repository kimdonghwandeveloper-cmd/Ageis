# Ageis Agent Architecture Map (Phase 1 & 2)

이 문서는 **Phase 1 (The Body)** 와 **Phase 2 (The Brain)** 의 전체 구조와 데이터 흐름을 시각화합니다.

## 1. 전체 시스템 개요 (The Big Picture)

Rust 코어(보안/시스템)와 Python 에이전트(지능/로직)가 **gRPC**로 연결된 구조입니다.

```mermaid
graph TD
    subgraph "External World"
        User((User))
        Web[Web Sites]
    end

    subgraph "Ageis System"
        subgraph "Python Agent (The Brain)"
            Router[Router<br/>(의도 분류)]
            ReAct[ReAct Loop<br/>(추론/행동)]
            Tools[Tools Wrapper]
        end

        subgraph "Rust Core (The Body)"
            gRPC_Server[gRPC Server<br/>(AgentBroker)]
            Sandbox[Sandbox<br/>(Path Verification)]
        end
        
        LLM[Ollama Local LLM<br/>(Llama 3.2)]
    end

    subgraph "File System"
        Workspace[Agent_Workspace]
        Forbidden[System Files<br/>(Access Denied)]
    end

    %% Connections
    User -->|Command/Chat| Router
    Router -->|Simple Chat| LLM
    Router -->|Complex Task| ReAct
    
    ReAct <-->|Prompt/Response| LLM
    ReAct -->|Call Tool| Tools
    
    Tools -->|Scrape| Web
    Tools <-->|gRPC Request| gRPC_Server
    
    gRPC_Server -->|Check Path| Sandbox
    Sandbox -- Allowed --> Workspace
    Sandbox -- Denied --> Forbidden
```

---

## 2. Phase 1: 튼튼한 뼈대 (Communication & Security)

**Rust Core**가 Python의 요청을 받아 **보안 검사(Sandbox)** 후 파일 시스템에 접근하는 흐름입니다.

```mermaid
sequenceDiagram
    participant Py as Python Agent (gRPC Client)
    participant Rust as Rust Core (gRPC Server)
    participant SB as Sandbox Logic
    participant FS as File System

    Note over Py, Rust: gRPC (Protobuf Contract)

    Py->>Rust: RequestFileRead(path="README.md")
    Rust->>SB: is_path_allowed("README.md")
    
    alt Path is Safe (Inside Workspace)
        SB-->>Rust: True
        Rust->>FS: Read File
        FS-->>Rust: File Content (bytes)
        Rust-->>Py: FileResponse(content, allowed=true)
    else Path is Unsafe (../tokens.txt)
        SB-->>Rust: False
        Rust-->>Py: FileResponse(error, allowed=false)
    end
```

---

## 3. Phase 2: 깨어난 지능 (Reasoning Loop)

**Python Agent**가 사용자의 복잡한 명령을 **생각(Thought)하고 행동(Action)** 하는 과정입니다.

```mermaid
stateDiagram-v2
    [*] --> Idle
    
    state "User Input" as Input
    Idle --> Input
    
    state "Router (Classifier)" as Router
    Input --> Router
    
    state "Chat Mode" as Chat
    Router --> Chat: Intent = CHAT
    Chat --> [*]: Reply
    
    state "ReAct Loop (Task Mode)" as ReAct {
        [*] --> Thought
        Thought --> LLM_Generate
        LLM_Generate --> Action_Parser
        
        state "Thinking..." as Thought
        state "Call Ollama" as LLM_Generate
        state "Decision" as Decision
        
        Action_Parser --> Decision
        
        state "Execute Tool" as Tool
        Decision --> Tool: Tool Call Found
        
        state "Observe Result" as Obs
        Tool --> Obs: Return Output
        Obs --> Thought: Feed observation back to LLM
        
        Decision --> Final_Answer: "Final Answer:" Found
    }
    
    Router --> ReAct: Intent = TASK / FILE / WEB
    
    state "Final Answer" as Final
    Final --> [*]: Task Complete
```

---

## 4. 컴포넌트 상세 (Class/Module View)

주요 클래스와 모듈의 역할입니다.

```mermaid
classDiagram
    %% Rust Core
    class Rust_Main {
        +main()
        +Args: port, workspace
    }
    class AgentBrokerService {
        +request_file_read()
        +execute_command()
        +stream_chat()
    }
    class Sandbox {
        -allowed_root: PathBuf
        +new(workspace)
        +is_path_allowed(path)
    }

    Rust_Main --> AgentBrokerService : Spawns
    AgentBrokerService --> Sandbox : Uses

    %% Python Agent
    class Main {
        +main()
        +handle_chat()
        +handle_task()
    }
    class Router {
        +classify_intent(input)
    }
    class ReActAgent {
        -tools: dict
        -history: list
        +run(task)
        -_parse_action()
    }
    class Tools {
        +read_file_tool()
        +web_scrape_tool()
    }
    class GrpcClient {
        +read_file()
        +execute_command()
    }

    Main --> Router : Calls
    Main --> ReActAgent : Uses for Tasks
    ReActAgent --> Tools : Executes
    Tools --> GrpcClient : Uses (File I/O)
```

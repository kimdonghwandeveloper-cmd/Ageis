// ============================================================
// server.rs — gRPC 서비스 구현체
//
// 역할: proto/agent.proto에 정의된 AgentBroker 서비스의 실제 로직을 구현한다.
// Python 클라이언트로부터 gRPC 요청을 받아 처리하고 응답을 반환한다.
// 모든 파일 I/O는 Sandbox를 통해 보안 검증을 거친다.
// ============================================================

use std::pin::Pin;   // 비동기 스트림을 메모리에 고정하기 위한 타입 (Rust 비동기의 필수 요소)
use std::sync::Arc;  // 원자적 참조 카운팅 스마트 포인터 (멀티 스레드에서 Sandbox를 안전하게 공유)

use tokio::sync::mpsc;  // 비동기 다중-생산자 단일-소비자 채널 (스트리밍 응답 전송용)
use tokio_stream::{wrappers::ReceiverStream, Stream, StreamExt}; // 비동기 스트림 유틸리티
use tonic::{Request, Response, Status, Streaming}; // gRPC 요청/응답/에러/스트리밍 타입

// proto에서 자동 생성된 Rust 코드를 가져옴
use crate::agent_proto::agent_broker_server::AgentBroker; // AgentBroker 트레이트 (우리가 구현해야 할 인터페이스)
use crate::agent_proto::*;  // 모든 메시지 타입 (FileRequest, FileResponse 등)
use crate::sandbox::Sandbox; // 파일시스템 샌드박스 모듈

/// gRPC 서비스의 상태를 보관하는 구조체
/// Arc<Sandbox>: 여러 비동기 태스크에서 동시에 접근할 수 있도록 Arc로 감싸둠
pub struct AgentBrokerService {
    sandbox: Arc<Sandbox>, // 공유 샌드박스 인스턴스 (스레드 안전)
}

impl AgentBrokerService {
    /// 새로운 서비스 인스턴스를 생성한다.
    /// sandbox: Sandbox 인스턴스의 소유권을 받아 Arc로 감싼다.
    pub fn new(sandbox: Sandbox) -> Self {
        Self {
            sandbox: Arc::new(sandbox), // 소유권 이전 후 Arc로 래핑
        }
    }
}

// tonic::async_trait 매크로: 트레이트에서 async fn을 사용할 수 있게 해줌
// (Rust 표준 트레이트는 아직 async fn을 직접 지원하지 않으므로 매크로 필요)
#[tonic::async_trait]
impl AgentBroker for AgentBrokerService {

    // ========================================
    // [RPC 1] 파일 읽기 요청 처리
    // ========================================
    async fn request_file_read(
        &self,
        request: Request<FileRequest>,    // 클라이언트가 보낸 파일 읽기 요청
    ) -> Result<Response<FileResponse>, Status> {  // 성공 시 FileResponse, 실패 시 gRPC Status 에러
        // into_inner(): gRPC 메타데이터를 제거하고 순수 메시지 본문만 추출
        let path = &request.into_inner().path;
        // 요청된 경로를 로그에 기록 (디버깅 및 감사 추적용)
        tracing::info!("FileRead request: {}", path);

        // 샌드박스를 통해 파일 읽기 시도
        match self.sandbox.safe_read(path) {
            // 읽기 성공: 파일 내용과 허용 플래그를 응답으로 반환
            Ok(content) => Ok(Response::new(FileResponse {
                content,                   // 파일 바이트 데이터
                allowed: true,             // 샌드박스 통과 표시
                error: String::new(),      // 에러 없음 (빈 문자열)
            })),
            // 읽기 거부/실패: 빈 내용과 에러 메시지를 응답으로 반환
            Err(err) => Ok(Response::new(FileResponse {
                content: Vec::new(),       // 빈 바이트 벡터
                allowed: false,            // 거부됨 표시
                error: err,                // 거부 사유 메시지
            })),
        }
    }

    // ========================================
    // [RPC 2] 파일 쓰기 요청 처리
    // ========================================
    async fn request_file_write(
        &self,
        request: Request<FileWriteRequest>,
    ) -> Result<Response<StatusResponse>, Status> {
        let req = request.into_inner(); // 요청 본문 추출
        tracing::info!("FileWrite request: {}", req.path);

        // 샌드박스를 통해 파일 쓰기 시도
        match self.sandbox.safe_write(&req.path, &req.content) {
            // 쓰기 성공
            Ok(()) => Ok(Response::new(StatusResponse {
                success: true,
                message: "File written successfully".to_string(),
            })),
            // 쓰기 거부/실패
            Err(err) => Ok(Response::new(StatusResponse {
                success: false,
                message: err, // 거부 사유 또는 I/O 에러 메시지
            })),
        }
    }

    // ========================================
    // [RPC 3] 명령어 실행 요청 처리
    // ========================================
    async fn execute_command(
        &self,
        request: Request<CommandRequest>,
    ) -> Result<Response<CommandResponse>, Status> {
        let req = request.into_inner();
        tracing::info!("ExecuteCommand request: {} {:?}", req.command, req.args);

        // 보안: 실행 가능한 명령어를 화이트리스트로 제한
        // 이 목록에 없는 명령어는 무조건 거부된다 (rm, del, powershell 등 차단)
        let allowed_commands = ["echo", "ls", "dir", "cat", "type", "date"];
        if !allowed_commands.contains(&req.command.as_str()) {
            // 화이트리스트에 없는 명령어 → 즉시 거부 응답
            return Ok(Response::new(CommandResponse {
                exit_code: -1,             // -1 = 실행되지 않았음을 표시
                stdout: String::new(),
                stderr: format!("DENIED: command '{}' is not in the allowed list", req.command),
            }));
        }

        // tokio::process::Command: 비동기 프로세스 실행 (블로킹 없이 자식 프로세스 생성)
        let output = tokio::process::Command::new(&req.command)
            .args(&req.args)       // 명령어 인자 전달
            .output()              // 프로세스 실행 후 stdout/stderr/exit_code 수집
            .await                 // 비동기 대기
            .map_err(|e| Status::internal(e.to_string()))?; // 프로세스 생성 실패 시 gRPC INTERNAL 에러

        // 프로세스 실행 결과를 응답으로 반환
        Ok(Response::new(CommandResponse {
            exit_code: output.status.code().unwrap_or(-1), // 종료 코드 (시그널로 죽은 경우 -1)
            stdout: String::from_utf8_lossy(&output.stdout).to_string(), // 바이트 → 문자열 변환 (깨진 UTF-8 안전 처리)
            stderr: String::from_utf8_lossy(&output.stderr).to_string(),
        }))
    }

    // ========================================
    // [RPC 4] 양방향 채팅 스트리밍
    // ========================================

    // 스트림 응답 타입 정의: Pin<Box<dyn Stream<...>>> 형태가 tonic의 규격
    // Pin: 비동기 스트림이 메모리에서 움직이지 않도록 고정
    // Box<dyn ...>: 동적 디스패치 (구체 타입을 컴파일 타임에 몰라도 됨)
    // Send + 'static: 스레드 간 전송 가능 + 참조 없는 독립 수명
    type StreamChatStream =
        Pin<Box<dyn Stream<Item = Result<ChatMessage, Status>> + Send + 'static>>;

    async fn stream_chat(
        &self,
        request: Request<Streaming<ChatMessage>>, // Streaming<T>: 클라이언트에서 연속으로 들어오는 메시지 스트림
    ) -> Result<Response<Self::StreamChatStream>, Status> {
        let mut stream = request.into_inner(); // 입력 스트림 추출
        // mpsc 채널 생성: tx(송신)로 응답을 보내면 rx(수신)에서 스트림으로 나간다
        // 버퍼 크기 128: 최대 128개 메시지까지 대기열에 쌓을 수 있음
        let (tx, rx) = mpsc::channel(128);

        // 별도의 비동기 태스크를 생성하여 입력 스트림을 처리
        // tokio::spawn: 현재 함수와 독립적으로 백그라운드에서 실행
        tokio::spawn(async move {
            // 스트림에서 메시지를 하나씩 꺼내어 처리
            while let Some(Ok(msg)) = stream.next().await {
                // 수신된 메시지 로깅
                tracing::info!(
                    "[Chat] session={} role={}: {}",
                    msg.session_id,
                    msg.role,
                    msg.content
                );
                // 현재는 에코 응답 — Phase 2에서 Ollama LLM 연동으로 대체 예정
                let reply = ChatMessage {
                    role: "assistant".to_string(),      // 응답자 역할
                    content: format!("[echo] {}", msg.content), // 원본 메시지에 [echo] 접두사
                    session_id: msg.session_id,         // 같은 세션 ID 유지
                };
                // 채널을 통해 응답 전송 (수신 측이 닫혔으면 루프 종료)
                if tx.send(Ok(reply)).await.is_err() {
                    break;
                }
            }
        });

        // ReceiverStream: mpsc::Receiver를 tonic이 요구하는 Stream 트레이트로 변환
        // Box::pin: 힙에 할당하고 Pin으로 감싸서 반환
        Ok(Response::new(Box::pin(ReceiverStream::new(rx))))
    }
}

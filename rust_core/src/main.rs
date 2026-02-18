// ============================================================
// main.rs — Ageis Core 데몬 진입점
//
// 역할: 프로그램의 시작점. CLI 인자를 파싱하고,
// 로깅을 초기화하고, 샌드박스와 gRPC 서버를 구동한다.
// 실행 예: ./ageis-core --port 50051 --workspace ../Agent_Workspace
// ============================================================

mod sandbox; // sandbox.rs 모듈을 이 크레이트에 포함
mod server;  // server.rs 모듈을 이 크레이트에 포함

// proto/agent.proto에서 자동 생성된 Rust 코드를 agent_proto 모듈로 노출
pub mod agent_proto {
    // tonic::include_proto! 매크로:
    // build.rs에서 tonic_build가 생성한 코드를 여기에 인라인으로 삽입한다.
    // "agent"는 proto 파일의 package agent; 에 대응한다.
    tonic::include_proto!("agent");
}

// 자동 생성된 gRPC 서버 트레이트 임포트
use agent_proto::agent_broker_server::AgentBrokerServer;
use clap::Parser;              // CLI 인자 파싱 derive 매크로
use sandbox::Sandbox;          // 파일시스템 샌드박스
use server::AgentBrokerService; // gRPC 서비스 구현체
use tonic::transport::Server;  // tonic gRPC 서버 빌더

/// CLI 인자 구조체
/// clap의 derive 매크로가 이 구조체에서 자동으로 인자 파서를 생성한다.
/// 사용법: ageis-core --port 50051 --workspace ./Agent_Workspace
#[derive(Parser)]
#[command(name = "ageis-core", about = "Ageis Agent Core Daemon")]
struct Args {
    /// gRPC 서버가 수신할 포트 번호 (기본값: 50051)
    #[arg(long, default_value = "50051")]
    port: u16,

    /// Agent_Workspace 디렉토리 경로 (샌드박스 루트)
    /// 이 디렉토리 안에서만 파일 읽기/쓰기가 허용된다.
    #[arg(long, default_value = "../Agent_Workspace")]
    workspace: String,
}

// #[tokio::main]: main 함수를 비동기 함수로 변환
// tokio 런타임을 자동 생성하고 그 위에서 async main을 실행한다.
#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    // 로깅 시스템 초기화
    // RUST_LOG 환경변수로 로그 레벨 제어 가능 (예: RUST_LOG=debug)
    // 환경변수가 없으면 기본적으로 ageis_core 모듈의 info 레벨만 출력
    tracing_subscriber::fmt()
        .with_env_filter(
            tracing_subscriber::EnvFilter::try_from_default_env()
                .unwrap_or_else(|_| "ageis_core=info".into()),
        )
        .init();

    // 커맨드라인 인자를 파싱하여 Args 구조체로 변환
    let args = Args::parse();
    // 수신 주소 생성: 0.0.0.0 = 모든 네트워크 인터페이스에서 수신
    let addr = format!("0.0.0.0:{}", args.port).parse()?;

    // 샌드박스 생성: workspace 경로를 정규화하고 존재 여부 확인
    let sandbox = Sandbox::new(&args.workspace);
    // gRPC 서비스 인스턴스 생성 (샌드박스를 Arc로 감싸서 보관)
    let service = AgentBrokerService::new(sandbox);

    // 서버 시작 로그 출력
    println!("Starting Ageis Core Daemon on port {}...", args.port);
    tracing::info!("Workspace: {}", args.workspace);

    // tonic gRPC 서버 구동
    // Server::builder(): 서버 빌더 패턴 시작
    // add_service(): AgentBroker 서비스를 서버에 등록
    // serve(): 지정된 주소에서 요청 수신 시작 (프로그램이 종료될 때까지 블로킹)
    Server::builder()
        .add_service(AgentBrokerServer::new(service))
        .serve(addr)
        .await?;

    Ok(())
}

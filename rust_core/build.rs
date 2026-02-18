// ============================================================
// build.rs — 빌드 스크립트
// cargo build 실행 시 컴파일 전에 자동으로 실행된다.
// proto/agent.proto 파일을 읽어서 Rust 소스코드를 자동 생성한다.
// 생성된 코드는 target/ 디렉토리 안에 저장되고,
// main.rs에서 tonic::include_proto!("agent") 매크로로 가져온다.
// ============================================================

fn main() -> Result<(), Box<dyn std::error::Error>> {
    // "../proto/agent.proto" 파일을 파싱하여 Rust gRPC 서버/클라이언트 코드 생성
    // 생성되는 항목: AgentBrokerServer 트레이트, 각 Message 구조체, 직렬화/역직렬화 구현
    tonic_build::compile_protos("../proto/agent.proto")?;
    Ok(())
}

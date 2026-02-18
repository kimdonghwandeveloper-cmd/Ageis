// ============================================================
// sandbox.rs — 파일시스템 샌드박스 (보안 핵심 모듈)
//
// 역할: Agent_Workspace 디렉토리 바깥으로의 파일 접근을 차단한다.
// 모든 파일 읽기/쓰기는 반드시 이 모듈을 거쳐야 하며,
// Path Traversal 공격 (예: ../../etc/passwd)을 방어한다.
// ============================================================

use std::path::PathBuf; // 파일 경로를 다루는 표준 라이브러리 타입

/// 샌드박스 구조체: 허용된 루트 디렉토리 경로를 보관
pub struct Sandbox {
    allowed_root: PathBuf, // 접근이 허용된 최상위 디렉토리 (정규화된 절대 경로)
}

impl Sandbox {
    /// 새로운 샌드박스 인스턴스를 생성한다.
    /// workspace: Agent_Workspace 디렉토리 경로 (상대/절대 모두 가능)
    /// dunce::canonicalize()를 사용하여 Windows에서도 UNC 접두사 없는 깔끔한 경로를 얻는다.
    pub fn new(workspace: &str) -> Self {
        Sandbox {
            // dunce::canonicalize: 심볼릭 링크 해소 + 절대 경로 변환
            // Windows에서 std::fs::canonicalize()는 \\?\ 접두사를 붙이지만,
            // dunce는 이를 제거하여 일반 경로 형태로 반환한다.
            allowed_root: dunce::canonicalize(workspace)
                .expect("Agent_Workspace path must exist"), // 경로가 없으면 패닉 (서버 시작 시 필수 검증)
        }
    }

    /// 요청된 경로가 Agent_Workspace 내부인지 검증한다.
    /// Path Traversal 공격 방어의 핵심 로직이다.
    /// requested: 클라이언트가 요청한 파일 경로
    /// 반환값: true=허용, false=거부
    pub fn is_path_allowed(&self, requested: &str) -> bool {
        // 요청 경로를 정규화 (심볼릭 링크, .., . 등을 모두 해소)
        match dunce::canonicalize(requested) {
            // 정규화된 경로가 allowed_root로 시작하면 내부 경로 → 허용
            Ok(path) => path.starts_with(&self.allowed_root),
            // 존재하지 않는 경로 등 정규화 실패 → 거부
            Err(_) => false,
        }
    }

    /// 샌드박스 내부의 파일을 안전하게 읽는다.
    /// path: 읽을 파일 경로
    /// 반환값: Ok(바이트 벡터) 또는 Err(에러 메시지)
    pub fn safe_read(&self, path: &str) -> Result<Vec<u8>, String> {
        // 1단계: 경로가 샌드박스 내부인지 확인
        if !self.is_path_allowed(path) {
            return Err(format!("DENIED: '{}' is outside Agent_Workspace", path));
        }
        // 2단계: 검증 통과 시 실제 파일 읽기 수행
        std::fs::read(path).map_err(|e| e.to_string()) // I/O 에러를 문자열로 변환
    }

    /// 샌드박스 내부에 파일을 안전하게 쓴다.
    /// path: 쓸 파일 경로, content: 기록할 바이트 데이터
    /// 반환값: Ok(()) 또는 Err(에러 메시지)
    pub fn safe_write(&self, path: &str, content: &[u8]) -> Result<(), String> {
        // 1단계: 경로가 샌드박스 내부인지 확인
        if !self.is_path_allowed(path) {
            return Err(format!("DENIED: '{}' is outside Agent_Workspace", path));
        }
        // 2단계: 검증 통과 시 실제 파일 쓰기 수행
        std::fs::write(path, content).map_err(|e| e.to_string())
    }
}

// ============================================================
// 단위 테스트: cargo test 로 실행
// ============================================================
#[cfg(test)] // 테스트 빌드에서만 컴파일
mod tests {
    use super::*;  // 부모 모듈(Sandbox)의 모든 항목을 가져옴
    use std::fs;   // 파일 생성용

    /// 테스트: Agent_Workspace 내부 파일은 접근이 허용되는지 확인
    #[test]
    fn test_allowed_path() {
        // tempfile::tempdir()로 임시 디렉토리 생성 (테스트 종료 시 자동 삭제)
        let dir = tempfile::tempdir().unwrap();
        let workspace = dir.path().to_str().unwrap();
        let sandbox = Sandbox::new(workspace); // 임시 디렉토리를 워크스페이스로 설정

        // 임시 디렉토리 안에 테스트 파일 생성
        let test_file = dir.path().join("test.txt");
        fs::write(&test_file, b"hello").unwrap();

        // 워크스페이스 내부 파일 → is_path_allowed()가 true 반환해야 함
        assert!(sandbox.is_path_allowed(test_file.to_str().unwrap()));
    }

    /// 테스트: Agent_Workspace 외부 파일은 접근이 거부되는지 확인
    #[test]
    fn test_denied_path() {
        let dir = tempfile::tempdir().unwrap();
        let workspace = dir.path().to_str().unwrap();
        let sandbox = Sandbox::new(workspace);

        // 워크스페이스 바깥 경로 → is_path_allowed()가 false 반환해야 함
        assert!(!sandbox.is_path_allowed("/etc/passwd"));
    }
}

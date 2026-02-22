use std::process::Command;

fn main() {
    // 빌드 시작 전에 백그라운드에 남아있는 좀비 사이드카 프로세스를 강제로 죽여서 
    // PermissionDenied (os error 5) 빌드 락 에러를 방지합니다.
    #[cfg(windows)]
    let _ = Command::new("taskkill")
        .args(&["/F", "/IM", "ageis-agent.exe"])
        .output();

    tauri_build::build()
}

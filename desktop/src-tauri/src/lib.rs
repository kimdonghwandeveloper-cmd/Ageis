use std::sync::Mutex;
use tauri::Manager;
use tauri_plugin_shell::process::CommandChild;
use tauri_plugin_shell::ShellExt;

/// 앱 종료 시 사이드카를 kill하기 위해 프로세스 핸들을 관리 상태로 보관
struct SidecarState(Mutex<Option<CommandChild>>);

/// 사이드카 종료 헬퍼 — 중복 호출 시 두 번째부터는 아무것도 하지 않음 (take() 활용)
fn kill_sidecar(app_handle: &tauri::AppHandle) {
    let state = app_handle.state::<SidecarState>();
    let mut guard = state.0.lock().unwrap();
    if let Some(child) = guard.take() {
        let _ = child.kill();
        println!("[Tauri] Sidecar terminated.");
    }
}

#[tauri::command]
fn log_from_frontend(level: String, message: String) {
    if level == "error" {
        eprintln!("[Frontend Error] {}", message);
    } else {
        println!("[Frontend Info] {}", message);
    }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .setup(|app| {
            // 릴리즈 빌드에서만 사이드카 자동 시작
            // 개발 시(`cargo tauri dev`)에는 서버를 별도 터미널에서 직접 실행:
            //   cd python_agent && uv run python main.py
            #[cfg(not(debug_assertions))]
            {
                let (mut rx, child) = app
                    .shell()
                    .sidecar("ageis-agent")
                    .expect("Failed to create sidecar command")
                    .spawn()
                    .expect("Failed to spawn sidecar");

                app.handle().manage(SidecarState(Mutex::new(Some(child))));

                tauri::async_runtime::spawn(async move {
                    while let Some(event) = rx.recv().await {
                        match event {
                            tauri_plugin_shell::process::CommandEvent::Stdout(line) => {
                                let text = String::from_utf8_lossy(&line);
                                println!("[Python Agent] {}", text);
                            }
                            tauri_plugin_shell::process::CommandEvent::Stderr(line) => {
                                let text = String::from_utf8_lossy(&line);
                                eprintln!("[Python Agent ERR] {}", text);
                            }
                            _ => {}
                        }
                    }
                });
            }

            // 개발 모드: 사이드카 없음, None으로 상태 등록 (종료 시 kill 생략)
            #[cfg(debug_assertions)]
            app.handle().manage(SidecarState(Mutex::new(None)));

            Ok(())
        })
        .invoke_handler(tauri::generate_handler![log_from_frontend])
        .build(tauri::generate_context!())
        .expect("Ageis Desktop app build failed")
        .run(|app_handle, event| {
            match event {
                // 정상 종료 경로
                tauri::RunEvent::Exit => {
                    kill_sidecar(app_handle);
                }
                // 창이 파괴될 때 (X 버튼, 작업관리자 종료 등 다양한 경로 대응)
                // kill_sidecar 내부에서 take()로 중복 실행 방지
                tauri::RunEvent::WindowEvent {
                    event: tauri::WindowEvent::Destroyed,
                    ..
                } => {
                    kill_sidecar(app_handle);
                }
                _ => {}
            }
        });
}

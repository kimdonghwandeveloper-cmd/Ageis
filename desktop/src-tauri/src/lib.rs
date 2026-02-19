use std::sync::Mutex;
use tauri_plugin_shell::process::CommandChild;

/// 앱 종료 시 사이드카를 kill하기 위해 프로세스 핸들을 관리 상태로 보관
struct SidecarState(Mutex<Option<CommandChild>>);

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .setup(|app| {
            use tauri_plugin_shell::ShellExt;

            let (mut rx, child) = app
                .shell()
                .sidecar("ageis-agent")
                .unwrap()
                .spawn()
                .expect("Failed to spawn sidecar");

            // 핸들을 앱 상태로 등록 (종료 이벤트에서 참조)
            app.manage(SidecarState(Mutex::new(Some(child))));

            // 사이드카 stdout / stderr 로깅
            tauri::async_runtime::spawn(async move {
                while let Some(event) = rx.recv().await {
                    match event {
                        tauri_plugin_shell::process::CommandEvent::Stdout(line) => {
                            println!(
                                "[Python Agent] {}",
                                String::from_utf8_lossy(&line)
                            );
                        }
                        tauri_plugin_shell::process::CommandEvent::Stderr(line) => {
                            eprintln!(
                                "[Python Agent ERR] {}",
                                String::from_utf8_lossy(&line)
                            );
                        }
                        _ => {}
                    }
                }
            });

            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("Ageis Desktop 앱 빌드 중 오류 발생")
        .run(|app_handle, event| {
            // 앱이 완전히 종료될 때 사이드카 프로세스도 함께 종료
            if let tauri::RunEvent::Exit = event {
                let state = app_handle.state::<SidecarState>();
                if let Ok(mut guard) = state.0.lock() {
                    if let Some(mut child) = guard.take() {
                        let _ = child.kill();
                        println!("[Tauri] Sidecar terminated.");
                    }
                }
            }
        });
}

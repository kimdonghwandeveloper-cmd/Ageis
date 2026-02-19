use std::sync::Mutex;
use tauri::Manager;
use tauri_plugin_shell::process::CommandChild;
use tauri_plugin_shell::ShellExt;

/// 앱 종료 시 사이드카를 kill하기 위해 프로세스 핸들을 관리 상태로 보관
struct SidecarState(Mutex<Option<CommandChild>>);

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .setup(|app| {
            // 사이드카 실행
            let (mut rx, child) = app
                .shell()
                .sidecar("ageis-agent")
                .expect("Failed to create sidecar command")
                .spawn()
                .expect("Failed to spawn sidecar");

            // AppHandle을 통해 상태 등록
            app.handle().manage(SidecarState(Mutex::new(Some(child))));

            // 사이드카 로그 출력 스레드
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

            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("Ageis Desktop app build failed")
        .run(|app_handle, event| {
            // 앱 종료 이벤트 감지 -> 사이드카 종료
            if let tauri::RunEvent::Exit = event {
                let state = app_handle.state::<SidecarState>();
                
                // if let Ok(...) 대신 .lock().unwrap() 사용
                // 종료 시점이라 패닉해도 무방하며, PoisonError가 발생해도 사실상 종료해야 함
                let mut guard = state.0.lock().unwrap();
                if let Some(child) = guard.take() {
                    let _ = child.kill();
                    println!("[Tauri] Sidecar terminated.");
                }
            }
        });
}

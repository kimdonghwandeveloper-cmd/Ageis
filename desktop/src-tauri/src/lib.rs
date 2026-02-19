#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .setup(|app| {
            use tauri_plugin_shell::ShellExt;
            
            let sidecar_command = app.shell().sidecar("ageis-agent").unwrap();
            let (mut rx, mut _child) = sidecar_command.spawn().expect("Failed to spawn sidecar");

            tauri::async_runtime::spawn(async move {
                // Sidecar의 출력을 로그로 남김 (디버깅용)
                while let Some(event) = rx.recv().await {
                    match event {
                        tauri_plugin_shell::process::CommandEvent::Stdout(line) => {
                             println!("[Python Agent] {}", String::from_utf8(line).unwrap());
                        }
                        tauri_plugin_shell::process::CommandEvent::Stderr(line) => {
                            eprintln!("[Python Agent ERR] {}", String::from_utf8(line).unwrap());
                        }
                        _ => {}
                    }
                }
            });

            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("Ageis Desktop 앱 실행 중 오류 발생");
}

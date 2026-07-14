use std::sync::Mutex;

use tauri::{
    menu::{MenuBuilder, MenuItemBuilder},
    tray::TrayIconBuilder,
    Manager, RunEvent,
};
use tauri_plugin_shell::ShellExt;
use tauri_plugin_shell::process::CommandChild;

// ── 应用状态 ──────────────────────────────────────────────────

/// 后端副进程句柄，用于退出时清理
struct BackendProcess(Mutex<Option<CommandChild>>);

// ── Tauri 命令 ────────────────────────────────────────────────

/// 简单问候命令，供前端测试 IPC 通信
#[tauri::command]
fn greet(name: &str) -> String {
    format!("你好，{}！欢迎使用 Multica AI", name)
}

/// 获取后端服务状态（通过 TCP 连接检测端口是否开放）
#[tauri::command]
fn get_backend_status() -> Result<String, String> {
    match std::net::TcpStream::connect_timeout(
        &"127.0.0.1:8765".parse().unwrap(),
        std::time::Duration::from_secs(3),
    ) {
        Ok(_) => Ok("running".to_string()),
        Err(_) => Ok("stopped".to_string()),
    }
}

// ── 应用入口 ──────────────────────────────────────────────────

pub fn run() {
    tauri::Builder::default()
        // ── 插件注册 ──
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_notification::init())
        .plugin(tauri_plugin_autostart::init(
            tauri_plugin_autostart::MacosLauncher::LaunchAgent,
            Some(vec![]),
        ))
        .plugin(tauri_plugin_updater::Builder::new().build())
        .plugin(tauri_plugin_process::init())
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_window_state::Builder::new().build())

        // ── 应用初始化 ──
        .setup(|app| {
            // 创建系统托盘菜单项
            let show_item = MenuItemBuilder::with_id("show", "显示窗口").build(app)?;
            let hide_item = MenuItemBuilder::with_id("hide", "隐藏窗口").build(app)?;
            let separator = tauri::menu::PredefinedMenuItem::separator(app)?;
            let restart_item = MenuItemBuilder::with_id("restart", "重启后端").build(app)?;
            let quit_item = MenuItemBuilder::with_id("quit", "退出").build(app)?;

            let menu = MenuBuilder::new(app)
                .item(&show_item)
                .item(&hide_item)
                .item(&separator)
                .item(&restart_item)
                .item(&quit_item)
                .build()?;

            // 构建系统托盘图标
            TrayIconBuilder::new()
                .icon(app.default_window_icon().unwrap().clone())
                .tooltip("Multica AI")
                .menu(&menu)
                .on_menu_event(|app, event| match event.id().as_ref() {
                    "show" => {
                        if let Some(window) = app.get_webview_window("main") {
                            let _ = window.show();
                            let _ = window.set_focus();
                        }
                    }
                    "hide" => {
                        if let Some(window) = app.get_webview_window("main") {
                            let _ = window.hide();
                        }
                    }
                    "restart" => {
                        // 终止旧进程并重新启动后端
                        if let Some(state) = app.try_state::<BackendProcess>() {
                            if let Ok(mut guard) = state.0.lock() {
                                // 杀死当前后端进程
                                if let Some(child) = guard.take() {
                                    let _ = child.kill();
                                }
                                // 重新启动
                                match app
                                    .shell()
                                    .sidecar("backend")
                                    .map_err(|e| e.to_string())
                                    .and_then(|cmd| cmd.spawn().map_err(|e| e.to_string()))
                                {
                                    Ok((_rx, child)) => {
                                        *guard = Some(child);
                                    }
                                    Err(e) => {
                                        eprintln!("重启后端失败: {}", e);
                                    }
                                }
                            }
                        }
                    }
                    "quit" => {
                        // 退出前清理后端进程
                        if let Some(state) = app.try_state::<BackendProcess>() {
                            if let Ok(mut guard) = state.0.lock() {
                                if let Some(child) = guard.take() {
                                    let _ = child.kill();
                                }
                            }
                        }
                        app.exit(0);
                    }
                    _ => {}
                })
                .build(app)?;

            // ── 启动后端子进程（sidecar） ──
            let sidecar_result = app
                .shell()
                .sidecar("backend")
                .map_err(|e| e.to_string())
                .and_then(|cmd| cmd.spawn().map_err(|e| e.to_string()));

            match sidecar_result {
                Ok((_rx, child)) => {
                    app.manage(BackendProcess(Mutex::new(Some(child))));
                    println!("后端 sidecar 启动成功");
                }
                Err(e) => {
                    eprintln!("后端 sidecar 启动失败: {}", e);
                    // 不阻塞应用启动，后端可能手动启动
                }
            }

            // 窗口状态恢复由 tauri-plugin-window-state 自动处理
            Ok(())
        })

        // ── 窗口关闭事件：隐藏到托盘而非退出 ──
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::CloseRequested { api, .. } = event {
                // 隐藏窗口到系统托盘
                let _ = window.hide();
                api.prevent_close();
            }
        })

        // ── 命令注册 ──
        .invoke_handler(tauri::generate_handler![greet, get_backend_status])

        // ── 构建并运行 ──
        .build(tauri::generate_context!())
        .expect("构建 Tauri 应用失败")
        .run(|app_handle, event| {
            // ── 应用退出事件：清理后端进程 ──
            if let RunEvent::Exit = event {
                if let Some(state) = app_handle.try_state::<BackendProcess>() {
                    if let Ok(mut guard) = state.0.lock() {
                        if let Some(child) = guard.take() {
                            let _ = child.kill();
                            println!("后端 sidecar 已终止");
                        }
                    }
                }
            }
        });
}

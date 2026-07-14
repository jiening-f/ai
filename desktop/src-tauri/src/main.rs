// 隐藏控制台窗口（仅 release 模式生效）
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

// 委托给 lib.rs 中的 run 函数
fn main() {
    multica_ai_desktop_lib::run()
}

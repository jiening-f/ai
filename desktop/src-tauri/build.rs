use std::path::PathBuf;
use std::{env, fs};

fn main() {
    copy_webview2_loader();
    tauri_build::build()
}

/// 从 cargo registry 找到 WebView2Loader.dll 并复制到 src-tauri/resources/
/// 解决 MinGW 工具链下 EXE 进程初始化时依赖该 DLL 的问题
fn copy_webview2_loader() {
    // 确定 cargo home 目录
    let cargo_home = env::var("CARGO_HOME").unwrap_or_else(|_| {
        let home = env::var("USERPROFILE")
            .or_else(|_| env::var("HOME"))
            .unwrap_or_default();
        format!("{}/.cargo", home)
    });

    // 搜索 webview2-com-sys crate 中的 x64 DLL
    let registry_src = PathBuf::from(&cargo_home).join("registry/src");
    let dll_path = find_dll(&registry_src);

    match dll_path {
        Some(dll) => {
            // 确定 resources 目录（相对于 Cargo.toml 所在目录，即 src-tauri/）
            let manifest_dir = PathBuf::from(env::var("CARGO_MANIFEST_DIR").unwrap());
            let resources_dir = manifest_dir.join("resources");
            fs::create_dir_all(&resources_dir).ok();

            let dest = resources_dir.join("WebView2Loader.dll");
            match fs::copy(&dll, &dest) {
                Ok(_) => println!("cargo:warning=已复制 WebView2Loader.dll → resources/"),
                Err(e) => println!("cargo:warning=复制 WebView2Loader.dll 失败: {}", e),
            }
        }
        None => {
            println!(
                "cargo:warning=未在 cargo registry 中找到 WebView2Loader.dll，\
                 请手动将 x64/WebView2Loader.dll 放入 src-tauri/resources/ 目录"
            );
        }
    }
}

/// 在 cargo registry 中搜索 webview2-com-sys 的 x64 WebView2Loader.dll
fn find_dll(registry_src: &PathBuf) -> Option<PathBuf> {
    if !registry_src.is_dir() {
        return None;
    }

    // 遍历 registry/src 下的所有源目录
    let entries = fs::read_dir(registry_src).ok()?;
    for entry in entries.flatten() {
        let path = entry.path();
        if !path.is_dir() {
            continue;
        }
        // 检查是否是 webview2-com-sys 目录
        let dir_name = path.file_name()?.to_str()?;
        if dir_name.starts_with("webview2-com-sys-") {
            let dll = path.join("x64").join("WebView2Loader.dll");
            if dll.is_file() {
                return Some(dll);
            }
            // 也检查不带 x64 子目录的情况
            let dll_flat = path.join("WebView2Loader.dll");
            if dll_flat.is_file() {
                return Some(dll_flat);
            }
        }
    }
    None
}

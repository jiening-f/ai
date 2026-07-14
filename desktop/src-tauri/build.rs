use std::path::PathBuf;
use std::{env, fs};

fn main() {
    println!("cargo:rerun-if-env-changed=CARGO_HOME");
    println!("cargo:rerun-if-env-changed=CARGO_MANIFEST_DIR");
    println!("cargo:rerun-if-changed=../Cargo.lock");
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
    let dll_path = find_best_dll(&registry_src);

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

/// 在 cargo registry 中搜索 webview2-com-sys，按 semver 取最高版本的 x64 WebView2Loader.dll
fn find_best_dll(registry_src: &PathBuf) -> Option<PathBuf> {
    if !registry_src.is_dir() {
        return None;
    }

    // 收集所有 webview2-com-sys-{version} 目录及其版本号
    let mut candidates: Vec<(String, PathBuf)> = Vec::new();
    let entries = fs::read_dir(registry_src).ok()?;
    for entry in entries.flatten() {
        let path = entry.path();
        if !path.is_dir() {
            continue;
        }
        let dir_name = path.file_name()?.to_str()?;
        if let Some(version) = dir_name.strip_prefix("webview2-com-sys-") {
            let dll = path.join("x64").join("WebView2Loader.dll");
            if dll.is_file() {
                candidates.push((version.to_string(), dll));
            }
        }
    }

    if candidates.is_empty() {
        return None;
    }

    // 按 semver 降序排序，取最高版本
    candidates.sort_by(|(v1, _), (v2, _)| compare_semver(v2, v1));

    let (version, dll) = &candidates[0];
    println!("cargo:warning=使用 WebView2Loader.dll (webview2-com-sys v{}): {}", version, dll.display());
    Some(dll.clone())
}

/// 简易 semver 比较：按 major.minor.patch 逐个比较
fn compare_semver(a: &str, b: &str) -> std::cmp::Ordering {
    let parse = |v: &str| -> Vec<u32> {
        v.split('.')
            .filter_map(|s| s.parse::<u32>().ok())
            .collect()
    };
    let va = parse(a);
    let vb = parse(b);
    // 补齐到相同长度（短的尾部补 0）
    let len = va.len().max(vb.len());
    for i in 0..len {
        let na = va.get(i).copied().unwrap_or(0);
        let nb = vb.get(i).copied().unwrap_or(0);
        match na.cmp(&nb) {
            std::cmp::Ordering::Equal => continue,
            other => return other,
        }
    }
    std::cmp::Ordering::Equal
}

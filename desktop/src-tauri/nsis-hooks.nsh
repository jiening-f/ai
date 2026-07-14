; Tauri v2 NSIS 安装钩子 — WebView2Loader.dll 路径修复
;
; 根因：MinGW 生成的 EXE 在进程初始化时依赖 WebView2Loader.dll（load-time dependency），
; 而 Tauri NSIS 打包器将 resources 放在 $INSTDIR\resources\ 子目录中。
; Windows DLL 加载器只在 EXE 同目录和系统 PATH 搜索，不会进入子目录。
;
; 解决方案：安装完成后将 DLL 从 resources\ 复制到 $INSTDIR 根目录，卸载时清理。

!macro NSIS_HOOK_POSTINSTALL
  ; 安装完成后，将 WebView2Loader.dll 从 resources 子目录复制到安装根目录
  CopyFiles /SILENT "$INSTDIR\resources\WebView2Loader.dll" "$INSTDIR\WebView2Loader.dll"
  ${IfNot} ${FileExists} "$INSTDIR\WebView2Loader.dll"
    MessageBox MB_ICONEXCLAMATION "WebView2Loader.dll 复制失败，程序可能无法启动。请重新安装。"
  ${EndIf}
!macroend

!macro NSIS_HOOK_PREUNINSTALL
  ; 卸载前，清理安装根目录下的 WebView2Loader.dll
  Delete "$INSTDIR\WebView2Loader.dll"
!macroend

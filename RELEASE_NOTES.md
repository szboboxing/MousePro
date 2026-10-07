# MousePro v1.0.0 — 鼠标 Pro 首个独立版本 / First independent release

## 中文

鼠标 Pro（MousePro）基于开源项目 PourInput v1.4.3（MIT）独立演进，在其完整的鼠标按键映射、应用配置、罗技 MX 增强、阅读模式之上，新增一组 Windows 鼠标增强能力，并将界面默认语言设为简体中文。

**新增功能（Windows）**

- **右键组合手势**：按住鼠标右键不放，滚轮上滑立即复制，滚轮下滑执行增强粘贴，按下已确认的侧键调用系统截图（Win+Shift+S）。每次按住右键最多执行一个动作；未触发任何动作时松开右键，原样弹出系统右键菜单。
- **增强粘贴**：在当前激活的文件资源管理器窗口或桌面新建文件夹，并以剪贴板内容命名。
- **系统工具页**：一键启动计算器、默认浏览器、媒体播放器；一键打开鼠标指针大小设置（Windows 11 打开「设置 → 辅助功能 → 鼠标指针与触控」，Windows 10 打开「调整鼠标和光标大小」）；亮度与对比度降低/提高（内置屏幕走 WMI，外接显示器走 DDC/CI，硬件不支持时提示原因）。
- **鼠标按键测试页**：左键、右键、中键、滚轮上/下、X1/X2 侧键共 7 类输入实时高亮与计数，测试期间只读透传、不触发任何动作；支持侧键重新确认并保存为截图手势侧键。
- **使用统计页**：统计本次运行的各按键次数、滚轮次数、鼠标移动像素距离，以及复制、增强粘贴、系统截图的成功次数，可随时清零。
- 动作选择面板中的「MousePro 增强」分类采用高亮样式，便于快速找到新动作；这些动作也可单独绑定到任意鼠标按键的单击或长按。

**其他**

- 首次启动默认简体中文；通用设置中仍可切换 English。
- 增强功能仅在 Windows 显示与启用，macOS/Linux 构建保留原有功能。
- 953 项自动化测试，Windows 包由 GitHub Actions 在 windows-latest 上构建并通过启动冒烟测试。
- 程序尚未签名。请从系统托盘退出旧版本，将 ZIP 完整解压到较短路径后运行 MousePro/MousePro.exe。

## English

MousePro is an independent evolution of the open-source PourInput v1.4.3 (MIT). It keeps everything from the upstream — per-button click/long-press mappings, per-app profiles, Logitech MX enhancements, and reading mode — and adds a set of Windows mouse enhancements, with Simplified Chinese as the default UI language.

**New (Windows)**

- **Right-button combo gestures**: hold the right mouse button, then scroll up to copy, scroll down for enhanced paste, or press a confirmed side button for the system screenshot (Win+Shift+S). At most one action fires per right-button hold; releasing without a gesture shows the native context menu as usual.
- **Enhanced paste**: creates a new folder in the active File Explorer window (or on the desktop) and names it with the current clipboard content.
- **System Tools page**: launch Calculator, the default browser, or the media player; open mouse pointer size settings directly (Windows 11: Settings → Accessibility → Mouse pointer and touch; Windows 10: Change mouse pointer and cursor size); decrease/increase brightness and contrast (WMI for built-in screens, DDC/CI for external monitors, with a clear message when unsupported).
- **Button test page**: live highlight and counters for seven inputs (left, right, middle, wheel up/down, X1/X2). Inputs are passed through read-only — no actions fire — and side buttons can be reconfirmed and saved as screenshot gesture buttons.
- **Usage stats page**: per-button clicks, wheel notches, pointer travel distance, and successful copy / enhanced paste / screenshot counts for the current session, with one-click reset.
- The "MousePro" action group in the action picker is highlighted so the new actions are easy to spot; each can also be bound to any button's click or long press.

**Other**

- First launch defaults to Simplified Chinese; English remains available in general settings.
- The enhancements are shown and enabled on Windows only; macOS/Linux builds keep the existing feature set.
- 953 automated tests; the Windows archive is built on GitHub Actions windows-latest and passes a packaged-app startup smoke test.
- The executable is unsigned. Quit any previous tray instance, fully extract the ZIP to a short path, then run MousePro/MousePro.exe.

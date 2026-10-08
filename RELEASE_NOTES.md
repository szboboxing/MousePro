# MousePro v1.0.1 — 单文件便携版 / Single-file portable build

## 中文

v1.0.1 在 v1.0.0 基础上新增**单文件便携版**，功能与 v1.0.0 完全一致。

- **单文件版**（Windows）：`MousePro-v1.0.1-Windows-OneFile.exe`。单 exe 免安装，没有 `_internal` 依赖文件夹，拷到哪都能跑，适合内网电脑、U 盘分发。首次启动需要解压到临时目录，比目录版慢几秒属正常。
- **目录版 zip**：与 v1.0.0 相同的 `MousePro/` 文件夹结构（`MousePro.exe` + `_internal/`）。注意：`MousePro.exe` 必须与 `_internal` 文件夹**一起**拷贝，单独移动 exe 会报 "Failed to load Python DLL" 错误。
- **内网使用提示**：程序未签名，若杀毒软件拦截请将 MousePro 加入信任/白名单；系统要求 Windows 10 及以上。

## English

v1.0.1 adds a **single-file portable build** on top of v1.0.0; features are identical to v1.0.0.

- **Single-file build** (Windows): `MousePro-v1.0.1-Windows-OneFile.exe`. One standalone exe with no `_internal` folder — copy it anywhere and run. Ideal for intranet PCs and USB distribution. The first launch unpacks to a temp directory and takes a few extra seconds.
- **Folder zip**: same `MousePro/` layout as v1.0.0 (`MousePro.exe` + `_internal/`). Note: `MousePro.exe` must be moved **together** with its `_internal` folder; moving the exe alone causes a "Failed to load Python DLL" error.
- **Intranet note**: the executable is unsigned — whitelist it if your antivirus complains. Windows 10 or later is required.

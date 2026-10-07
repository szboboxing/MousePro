<p align="center">
  <img src="images/logo.png" alt="鼠标Pro" width="140">
</p>

# 鼠标Pro

### 你的鼠标，由你掌控。

[English](README.md) · **简体中文**

**鼠标Pro 是一款鼠标自定义软件。** 把复制、粘贴、切换标签页、截图、自定义快捷键等常用操作放到鼠标上。为支持的按键分别设置单击和长按动作，再按应用创建配置，让鼠标随着你正在使用的软件切换操作。

[**下载 Windows 正式版 · v1.0.0**](https://github.com/szboboxing/MousePro/releases/download/v1.0.0/MousePro-v1.0.0-Windows.zip) · [更新说明](https://github.com/szboboxing/MousePro/releases/tag/v1.0.0) · [完整功能图集](docs/FEATURES_CN.md)

![鼠标Pro v1.0.0 鼠标按钮与应用配置](images/screenshots-v1.4.3/mouse-zh-CN.png)

*截图使用 v1.0.0 实际界面渲染，搭配示例配置与设备能力数据。截图用于说明界面；具体硬件功能取决于鼠标型号和固件。*

## 把常用操作放到鼠标上

在鼠标示意图上选择支持的按键，就能配置浏览器导航、文字编辑、媒体控制、桌面操作或自定义快捷键。截图操作支持全屏和区域截图，可保存到剪贴板或文件。

**一个按键，可以承担两种操作。** 例如，单击中键截取区域，长按中键复制。支持的按键可以分别设置单击和长按动作。

![动作选择、截图、自定义快捷键与长按设置](images/screenshots-v1.4.3/actions-zh-CN.png)

[查看完整动作分类和快捷键编辑器 →](docs/FEATURES_CN.md#buttons-and-shortcuts)

## 不同软件，使用不同配置

保留一套默认配置，再为浏览器、编辑器等软件添加应用配置。鼠标Pro 会根据当前获得焦点的应用切换映射。同一个侧键，在浏览器里可以后退，在其他软件里也可以执行另一组快捷键。

![应用配置选择](images/screenshots-v1.4.3/profiles-zh-CN.png)

## 普通鼠标与 MX 高级功能，都能发挥作用

**通用鼠标模式**支持 Windows 标准中键和两个侧键，也适用于 ZOWIE 等普通鼠标。开启后，这些输入由通用模式独占处理；设置为“无操作”就不执行动作，不会调用原来的 MX 映射。关闭通用模式后会恢复设备专用路径，已保存的映射不会被删除。

![开启通用鼠标模式](images/screenshots-v1.4.3/generic-zh-CN.png)

对于支持的 **MX Master 设备增强功能**，手势、水平滚动、模式切换、智能切换和 DPI 等不冲突的控制仍然可用。可以分别配置方向手势、调整触发阈值、设置水平滚动动作，并选择设备支持的滚轮行为。可用功能因设备和固件而异。

![DPI、智能切换灵敏度、外观及语言设置](images/screenshots-v1.4.3/settings-1-zh-CN.png)

[查看手势、水平滚动、滚轮模式和完整设置 →](docs/FEATURES_CN.md#mx-controls)

## 按自己的习惯使用

选择浅色、深色或跟随系统的外观，切换简体中文或英文。按需设置开机启动、启动时最小化、更新检查、截图保存目录，以及纵向和横向滚动方向。鼠标映射与阅读数据分开保存在本地。

## 阅读模式：让鼠标适应具体场景

鼠标自定义始终是 鼠标Pro 的核心。阅读模式沿着这个方向迈出了一步：除了决定“按键执行什么”，也让鼠标适应“此刻正在做什么”。它展示了鼠标控制如何融入一段完整的使用过程，同时保留原有的日常映射。

### 把本地书籍放进阅读浮窗

导入 **TXT 或 EPUB**，用滚轮手动浏览，或开启可调速、可暂停的**自动连续滚动**。字号和浮窗大小保持稳定，放不下的文字接着往后显示。浮窗保持置顶，不抢走键盘焦点。

![阅读控制、自动滚动与章节目录](images/screenshots-v1.4.3/reading-zh-CN.png)

### 通过章节找到想读的位置

章节目录支持 EPUB 内置目录和 TXT 章节标题。没有明确标题时，还会根据独立短行、空行等格式推测标题。推测结果会明确标注，确认后才跳转，也可能存在遗漏或误判。跳转从章节标题开始，标题单独一行。旧版导入的书籍可能需要重新导入，才能获得准确目录。

### 随手移动、调整和隐藏

拖动书页与树叶图标即可移动浮窗，拖动右下角调整大小。可自定义字号、文字颜色、不透明度和完全透明的背景，并选择**标准、简洁、隐约**三种显示方式。简洁与隐约模式允许鼠标点击穿过正文区域。

![标题单独成行的标准阅读浮窗](images/screenshots-v1.4.3/overlay-zh-CN.png)

**按一下隐藏，再按一下显示。** 松开按键后仍然隐藏；隐藏期间自动阅读暂停，显示后继续。阅读模式、阅读位置和滚轮接管保持不变。阅读开启时，选中的鼠标隐藏键只控制浮窗；键盘按键仍保留其原有作用。

关闭阅读模式，滚轮恢复普通页面滚动；开启后，阅读功能优先接管竖向滚轮。切换鼠标配置或通用模式不会重置书籍。重新打开软件会恢复位置，自动阅读默认暂停。

[查看完整阅读设置与三种浮窗样式 →](docs/FEATURES_CN.md#reading) · [阅读功能技术说明（英文）](docs/READING_MODE.md)

## 在 Windows 上开始使用

[**下载 鼠标Pro v1.0.0 Windows 正式版**](https://github.com/szboboxing/MousePro/releases/download/v1.0.0/MousePro-v1.0.0-Windows.zip)

1. 将 ZIP **完整解压**到较短的路径，例如 `F:\Apps`。不要直接在压缩包内运行，也不要在解压报错时跳过文件。
2. 从**系统托盘菜单**退出旧版 鼠标Pro。只关闭设置窗口，并不代表软件已经退出。
3. 打开 `MousePro/MousePro.exe`，无需另外安装 Python。
4. 要设置按键，进入鼠标页面，点击对应按钮。
5. 按需添加应用配置；要自定义标准中键和侧键时，开启通用鼠标模式。

Windows 程序尚未签名。[发布页](https://github.com/szboboxing/MousePro/releases/tag/v1.0.0)同时提供 SHA-256 校验文件和更新清单。

## 设备与平台说明

**Windows 实机验证：** 已使用 MX Master 4 和一只 ZOWIE 鼠标验证阅读、滚轮接管及浮窗隐藏等流程。此前也测试过 MX Master 3 控件。这不代表每个型号、每种固件都能提供全部功能。

通用鼠标模式目前支持中键和两个侧键，暂不能按物理来源区分多只普通鼠标，也不提供通用的左／右键或竖向滚轮重映射。阅读模式对滚轮的接管是独立功能。

其他罗技型号在提供所需 HID++ 控件时可能兼容。如果软件检测到了鼠标，却没有显示某个控件，可以在鼠标页面导出设备信息，并附在[设备支持反馈](https://github.com/szboboxing/MousePro/issues)中。

### macOS 版本

macOS 版本随 **v1.0.0** 一同发布。上面介绍的 Windows 阅读和自动滚动功能，不包含在这个 macOS 版本中。

[Apple Silicon 下载](https://github.com/szboboxing/MousePro/releases/download/v1.0.0/MousePro-macOS.zip) · [Intel 下载](https://github.com/szboboxing/MousePro/releases/download/v1.0.0/MousePro-macOS-intel.zip) · [macOS 版本说明](https://github.com/szboboxing/MousePro/releases/tag/v1.0.0)

解压对应版本，打开 `MousePro.app`，按提示授予辅助功能权限。此版本尚未签名和公证。Intel 版曾使用 MacBook Air 和 MX Master 3 实测；Apple Silicon 目前仅通过构建验证。通用鼠标模式仅支持 Windows，Linux 仍处于验证阶段。

## 常见问题

**按钮执行了预想之外的动作？** 检查当前应用配置、通用鼠标模式，以及这个按钮是否被选作阅读隐藏键。

**解压提示“路径太长”？** 取消解压，换一个更短的目标路径重新完整解压，不要跳过失败的文件。

**打开软件好像没有反应？** 先看看系统托盘中是否已有 鼠标Pro 运行。打开另一个版本前，先退出旧进程。

## 开发与参与贡献

开发请参阅[开发指南](DEVELOPMENT.md)、[架构概览](docs/ARCHITECTURE.md)和[阅读模式说明](docs/READING_MODE.md)。提交改进前，请阅读[贡献指南](CONTRIBUTING.md)与[设备支持指南](CONTRIBUTING_DEVICES.md)。

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main_qml.py
.\.venv\Scripts\python.exe -m unittest discover -s tests
```

由 **szboboxing** 维护。鼠标Pro Fork 自 [pour-soi/PourInput](https://github.com/pour-soi/PourInput)（MIT 许可证）；上游早期开发使用了 [Mouser](https://github.com/TomBadash/Mouser) 的部分工作。鼠标Pro 现独立维护，运行时不需要 Mouser。

[MIT 许可证](LICENSE) · [更新记录](CHANGELOG.md) · [问题反馈](https://github.com/szboboxing/MousePro/issues)

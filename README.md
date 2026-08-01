# PDF Blade

一款快速、完全本地运行的 Windows PDF 拆分工具。

PDF Blade 使用 PyMuPDF 处理 PDF，通过 pywebview 提供桌面界面。文件不会上传到服务器；导出时会清理未使用的 PDF 对象并进行压缩，尽量避免拆分后的文件体积膨胀。

## 功能

- 挑选任意页面，合成为新的 PDF
- 按页码范围批量拆分，例如 `1-3, 5, 8-10`
- 按 PDF 内嵌目录（书签）导出章节及其子章节
- 页面缩略图懒加载
- 简体中文、English、Español、Português、Français、Deutsch、Русский、日本語、한국어、العربية
- 多主题与可关闭的动态效果
- 100% 本地处理，无需上传文件

## 下载和使用

前往仓库的 **Releases** 页面，下载 `PDF-Blade-windows-x64.exe`，然后直接运行。

当前 Windows 构建未进行代码签名。首次运行时，Windows SmartScreen 可能显示安全提示。请只从本仓库的 Releases 页面下载。

## 从源码运行

需要 Python 3.11。

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python app.py
```

## 构建 Windows 可执行文件

```powershell
python -m pip install -r requirements-dev.txt
pyinstaller --noconfirm "PDF Blade.spec"
```

构建结果位于 `dist\PDF Blade.exe`。

## 技术结构

- `app.py`：桌面入口、pywebview API 和 PyMuPDF 处理逻辑
- `ui.html`：正式桌面界面
- `PDF Blade.spec`：PyInstaller 单文件构建配置
- `index.html`：早期纯浏览器原型，不参与桌面版构建

核心导出流程会创建新的 PDF，插入所需页面，并使用 `garbage=4`、`deflate=True` 和 `clean=True` 保存。

## 发布新版本

推送形如 `v1.0.0` 的 Git 标签后，GitHub Actions 会在 Windows 构建机上生成可执行文件，并自动创建对应的 GitHub Release。

```powershell
git tag v1.0.0
git push origin v1.0.0
```

## 隐私

桌面版没有上传接口，也不需要网络连接。PDF 内容只在本机由 PyMuPDF 读取和处理。

## 许可证

本项目采用 [MIT License](LICENSE)。

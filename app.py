# -*- coding: utf-8 -*-
"""PDF Blade — 极速 PDF 拆分桌面版
界面: webview (HTML/CSS/JS)  ·  引擎: PyMuPDF (mupdf)  ·  真正垃圾回收，体积不膨胀
"""
import os
import sys
import base64
import re
import webview
import fitz  # PyMuPDF


def resource_path(rel):
    """兼容 PyInstaller 打包后的资源路径"""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, rel)


# 后端少量用户可见消息的多语言映射
MSG = {
    "encrypted": {"zh": "该 PDF 已加密，暂不支持", "en": "This PDF is encrypted and not supported",
        "es": "Este PDF está cifrado y no es compatible", "pt": "Este PDF está cifrado e não é suportado",
        "fr": "Ce PDF est chiffré et non pris en charge", "de": "Diese PDF ist verschlüsselt und wird nicht unterstützt",
        "ru": "PDF зашифрован и не поддерживается", "ja": "このPDFは暗号化されており未対応です",
        "ko": "이 PDF는 암호화되어 지원되지 않습니다", "ar": "هذا الملف مشفّر وغير مدعوم"},
    "no_title": {"zh": "(无标题)", "en": "(untitled)", "es": "(sin título)", "pt": "(sem título)",
        "fr": "(sans titre)", "de": "(ohne Titel)", "ru": "(без названия)", "ja": "(無題)",
        "ko": "(제목 없음)", "ar": "(بدون عنوان)"},
    "no_sel": {"zh": "未选择任何页面", "en": "No pages selected", "es": "No hay páginas seleccionadas",
        "pt": "Nenhuma página selecionada", "fr": "Aucune page sélectionnée", "de": "Keine Seiten ausgewählt",
        "ru": "Страницы не выбраны", "ja": "ページが選択されていません", "ko": "선택된 페이지가 없습니다",
        "ar": "لم يتم تحديد أي صفحة"},
    "no_range": {"zh": "未提供范围", "en": "No range provided", "es": "No se indicó rango",
        "pt": "Nenhum intervalo fornecido", "fr": "Aucune plage fournie", "de": "Kein Bereich angegeben",
        "ru": "Диапазон не указан", "ja": "範囲が指定されていません", "ko": "범위가 지정되지 않았습니다",
        "ar": "لم يتم تحديد نطاق"},
    "bad_range": {"zh": "页码范围无效", "en": "Invalid page range", "es": "Rango de páginas no válido",
        "pt": "Intervalo de páginas inválido", "fr": "Plage de pages invalide", "de": "Ungültiger Seitenbereich",
        "ru": "Неверный диапазон страниц", "ja": "ページ範囲が無効です", "ko": "잘못된 페이지 범위",
        "ar": "نطاق صفحات غير صالح"},
}


class Api:
    def __init__(self):
        self.path = None          # 当前 PDF 路径
        self.doc = None           # fitz.Document
        self.base = "document"    # 不含扩展名的文件名
        self.lang = "zh"          # 界面语言（前端 set_lang 同步）

    def set_lang(self, code):
        self.lang = code if code in ("zh", "en", "es", "pt", "fr", "de", "ru", "ja", "ko", "ar") else "en"
        return True

    def _m(self, key):
        return MSG.get(key, {}).get(self.lang) or MSG.get(key, {}).get("en", key)

    # ---------- 打开文件 ----------
    def open_file(self):
        res = window.create_file_dialog(
            webview.OPEN_DIALOG, allow_multiple=False,
            file_types=("PDF 文件 (*.pdf)",))
        if not res:
            return None
        return self._load(res[0])

    def _load(self, path):
        try:
            if self.doc:
                self.doc.close()
            self.doc = fitz.open(path)
            if self.doc.needs_pass:
                return {"error": self._m("encrypted")}
            self.path = path
            self.base = os.path.splitext(os.path.basename(path))[0] or "document"
            size = os.path.getsize(path)
            return {
                "name": os.path.basename(path),
                "pages": self.doc.page_count,
                "size": size,
            }
        except Exception as e:
            return {"error": str(e)}

    # ---------- 缩略图（按需，懒加载）----------
    def thumb(self, index):
        try:
            page = self.doc.load_page(index)
            # 缩到约 200px 宽
            r = page.rect
            scale = 200.0 / r.width if r.width else 1.0
            pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
            data = pix.tobytes("png")
            return "data:image/png;base64," + base64.b64encode(data).decode()
        except Exception:
            return None

    # 不同平台/版本的 pywebview 对话框可能返回 str 或 (str,) / [str]，统一成 str
    @staticmethod
    def _pick(res):
        if not res:
            return None
        if isinstance(res, (list, tuple)):
            return res[0] if res else None
        return res

    # ---------- 核心：按页码集合保存为新 PDF（带垃圾回收）----------
    def _save_subset(self, indices, out_path):
        """从原文档抽取指定页 -> 新文档 -> 保存时 garbage=4 去重压缩"""
        out = fitz.open()
        # insert_pdf 保持顺序；需要 0 基页码且按指定顺序
        for i in indices:
            out.insert_pdf(self.doc, from_page=i, to_page=i)
        out.save(out_path, garbage=4, deflate=True, clean=True)
        out.close()

    # ---------- 模式一：导出所选页面 ----------
    def export_selected(self, indices):
        indices = sorted(set(int(i) for i in indices))
        if not indices:
            return {"error": self._m("no_sel")}
        default = f"{self.base}_selected_{len(indices)}p.pdf"
        dst = self._pick(window.create_file_dialog(
            webview.SAVE_DIALOG, save_filename=default,
            file_types=("PDF 文件 (*.pdf)",)))
        if not dst:
            return {"cancelled": True}
        try:
            self._save_subset(indices, dst)
            return {"ok": True, "size": os.path.getsize(dst), "path": dst}
        except Exception as e:
            return {"error": str(e)}

    # ---------- 模式二：按范围拆分 ----------
    def export_ranges(self, groups):
        """groups: [{label, pages:[0基页码...]}]"""
        if not groups:
            return {"error": self._m("no_range")}
        try:
            if len(groups) == 1:
                g = groups[0]
                default = f"{self.base}_{g['label']}.pdf"
                dst = self._pick(window.create_file_dialog(
                    webview.SAVE_DIALOG, save_filename=default,
                    file_types=("PDF 文件 (*.pdf)",)))
                if not dst:
                    return {"cancelled": True}
                self._save_subset([int(p) for p in g["pages"]], dst)
                return {"ok": True, "count": 1, "path": dst}
            # 多个范围 -> 选输出文件夹
            folder = self._pick(window.create_file_dialog(webview.FOLDER_DIALOG))
            if not folder:
                return {"cancelled": True}
            for g in groups:
                out = os.path.join(folder, f"{self.base}_{g['label']}.pdf")
                self._save_subset([int(p) for p in g["pages"]], out)
            return {"ok": True, "count": len(groups), "path": folder}
        except Exception as e:
            return {"error": str(e)}

    # ---------- 模式三：每 N 页拆一份 ----------
    def export_every(self, n):
        n = max(1, int(n))
        total = self.doc.page_count
        chunks = [list(range(i, min(i + n, total))) for i in range(0, total, n)]
        try:
            if len(chunks) == 1:
                default = f"{self.base}.pdf"
                dst = self._pick(window.create_file_dialog(
                    webview.SAVE_DIALOG, save_filename=default,
                    file_types=("PDF 文件 (*.pdf)",)))
                if not dst:
                    return {"cancelled": True}
                self._save_subset(chunks[0], dst)
                return {"ok": True, "count": 1, "path": dst}
            folder = self._pick(window.create_file_dialog(webview.FOLDER_DIALOG))
            if not folder:
                return {"cancelled": True}
            pad = len(str(len(chunks)))
            for i, ch in enumerate(chunks, 1):
                out = os.path.join(folder, f"{self.base}_part{str(i).zfill(pad)}.pdf")
                self._save_subset(ch, out)
            return {"ok": True, "count": len(chunks), "path": folder}
        except Exception as e:
            return {"error": str(e)}

    # ---------- 目录大纲（书签树）----------
    def get_toc(self):
        """返回大纲项：每项含层级、标题、起止页（0 基，含子节点全部范围）"""
        try:
            toc = self.doc.get_toc(simple=True)  # [[level, title, page1based], ...]
        except Exception:
            toc = []
        total = self.doc.page_count
        n = len(toc)
        items = []
        for i, (lvl, title, page) in enumerate(toc):
            start = max(0, page - 1)
            # 本节范围 = 直到下一个层级 <= 当前层级的条目之前（即包含所有子孙）
            end = total - 1
            for j in range(i + 1, n):
                if toc[j][0] <= lvl:
                    end = max(start, toc[j][2] - 2)
                    break
            items.append({
                "level": lvl, "title": title or self._m("no_title"),
                "start": start, "end": end,
            })
        return {"items": items, "total": total}

    # ---------- 模式四：导出某个目录节点（含其下全部内容）----------
    def export_outline(self, start, end, label):
        start, end = int(start), int(end)
        if start < 0 or end >= self.doc.page_count or end < start:
            return {"error": self._m("bad_range")}
        safe = re.sub(r'[\\/:*?"<>|]+', "_", str(label)).strip()[:80] or "section"
        default = f"{self.base}_{safe}.pdf"
        dst = self._pick(window.create_file_dialog(
            webview.SAVE_DIALOG, save_filename=default,
            file_types=("PDF 文件 (*.pdf)",)))
        if not dst:
            return {"cancelled": True}
        try:
            out = fitz.open()
            out.insert_pdf(self.doc, from_page=start, to_page=end)
            # 保留该节的子目录结构：截取范围内的书签，页码与层级重新基准化
            try:
                full = self.doc.get_toc(simple=True)
            except Exception:
                full = []
            sub = [(lvl, t, p - 1) for (lvl, t, p) in full
                   if p >= 1 and start <= (p - 1) <= end]
            if sub:
                base = min(lvl for lvl, _, _ in sub)
                new_toc = [[max(1, lvl - base + 1), t, (p0 - start) + 1]
                           for (lvl, t, p0) in sub]
                out.set_toc(new_toc)
            out.save(dst, garbage=4, deflate=True, clean=True)
            out.close()
            return {"ok": True, "size": os.path.getsize(dst), "path": dst,
                    "pages": end - start + 1}
        except Exception as e:
            return {"error": str(e)}


api = Api()
window = None


def main():
    global window
    window = webview.create_window(
        "PDF Blade — 极速 PDF 拆分",
        url=resource_path("ui.html"),
        js_api=api,
        width=1080, height=820, min_size=(720, 620),
        background_color="#0a0a0f",
    )
    webview.start()


if __name__ == "__main__":
    main()

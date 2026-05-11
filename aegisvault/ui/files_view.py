"""Files view: list, drag-drop, add/export/verify/delete."""
from __future__ import annotations
import os
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk

from . import widgets as w

try:
    from tkinterdnd2 import DND_FILES  # noqa: F401
    HAS_DND = True
except Exception:
    HAS_DND = False


class FilesView(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color=w.BG)
        self.app = app
        self.search_var = tk.StringVar()
        self.fav_only = tk.BooleanVar(value=False)
        self._build()
        self.refresh()

    def _build(self):
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=24, pady=(20, 8))
        ctk.CTkLabel(top, text="Encrypted Files", text_color=w.TEXT,
                     font=w.FONT_TITLE).pack(side="left")
        w.neon_button(top, "+ Add file", command=self._add_dialog).pack(side="right")
        w.ghost_button(top, "Export vault", command=self._export_vault, width=130).pack(side="right", padx=8)

        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.pack(fill="x", padx=24)
        e = ctk.CTkEntry(bar, textvariable=self.search_var, placeholder_text="Search files & tags…",
                         fg_color=w.PANEL_2, border_color=w.BORDER, height=34)
        e.pack(side="left", fill="x", expand=True)
        e.bind("<KeyRelease>", lambda *_: self.refresh())
        ctk.CTkCheckBox(bar, text="Favorites", variable=self.fav_only, command=self.refresh,
                        text_color=w.TEXT, fg_color=w.ACCENT).pack(side="left", padx=12)

        # Drop zone
        self.drop = ctk.CTkFrame(self, fg_color=w.PANEL, border_color=w.BORDER,
                                 border_width=1, corner_radius=12, height=72)
        self.drop.pack(fill="x", padx=24, pady=12)
        msg = "Drag & drop files here to encrypt" if HAS_DND else \
              "Use “+ Add file” (drag-drop requires tkinterdnd2)"
        ctk.CTkLabel(self.drop, text=msg, text_color=w.TEXT_DIM,
                     font=w.FONT_BODY).pack(expand=True)
        if HAS_DND:
            try:
                self.drop.drop_target_register(DND_FILES)
                self.drop.dnd_bind("<<Drop>>", self._on_drop)
            except Exception:
                pass

        # List
        self.list_frame = ctk.CTkScrollableFrame(self, fg_color=w.BG)
        self.list_frame.pack(fill="both", expand=True, padx=20, pady=(0, 16))

    def refresh(self):
        for child in self.list_frame.winfo_children():
            child.destroy()
        rows = self.app.db.list_files(self.app.session.user_id,
                                      self.search_var.get(),
                                      favorites_only=self.fav_only.get())
        if not rows:
            ctk.CTkLabel(self.list_frame, text="No files yet.",
                         text_color=w.TEXT_DIM).pack(pady=24)
            return
        for r in rows:
            self._row(r)

    def _row(self, r):
        card = ctk.CTkFrame(self.list_frame, fg_color=w.PANEL, corner_radius=10,
                            border_color=w.BORDER, border_width=1)
        card.pack(fill="x", padx=4, pady=4)

        left = ctk.CTkFrame(card, fg_color="transparent")
        left.pack(side="left", fill="both", expand=True, padx=14, pady=10)
        star = "★" if r["favorite"] else "☆"
        ctk.CTkLabel(left, text=f"{star}  {r['name']}",
                     text_color=w.TEXT, font=w.FONT_H2, anchor="w").pack(anchor="w")
        meta = f"{w.human_size(r['size_bytes'])}  •  {r['folder']}  •  AES-256-GCM  •  SHA-256: {r['sha256'][:16]}…"
        ctk.CTkLabel(left, text=meta, text_color=w.TEXT_DIM,
                     font=("Consolas", 10), anchor="w").pack(anchor="w")
        if r["tags"]:
            ctk.CTkLabel(left, text=f"#{r['tags']}", text_color=w.ACCENT_2,
                         font=("Segoe UI", 10), anchor="w").pack(anchor="w")

        right = ctk.CTkFrame(card, fg_color="transparent")
        right.pack(side="right", padx=10)
        w.ghost_button(right, "★ Fav", width=70,
                       command=lambda i=r["id"]: self._toggle_fav(i)).pack(side="left", padx=2)
        w.ghost_button(right, "Verify", width=70,
                       command=lambda i=r["id"]: self._verify(i)).pack(side="left", padx=2)
        w.ghost_button(right, "Export", width=70,
                       command=lambda i=r["id"]: self._export(i)).pack(side="left", padx=2)
        w.neon_button(right, "Delete", danger=True, width=70,
                      command=lambda i=r["id"]: self._delete(i)).pack(side="left", padx=2)

    # actions
    def _add_dialog(self):
        paths = filedialog.askopenfilenames(title="Add files to vault")
        for p in paths:
            self._add(p)
        if paths:
            self.refresh()

    def _on_drop(self, event):
        paths = self._parse_drop(event.data)
        for p in paths:
            self._add(p)
        self.refresh()

    def _parse_drop(self, data: str) -> list[str]:
        out, buf, in_brace = [], "", False
        for ch in data:
            if ch == "{": in_brace = True; continue
            if ch == "}": in_brace = False; out.append(buf); buf = ""; continue
            if ch == " " and not in_brace:
                if buf: out.append(buf); buf = ""
                continue
            buf += ch
        if buf: out.append(buf)
        return [p for p in out if os.path.isfile(p)]

    def _add(self, path: str):
        try:
            self.app.vault.add_file(path)
        except Exception as e:
            messagebox.showerror("AegisVault", f"Failed to add {path}\n{e}")

    def _toggle_fav(self, fid: int):
        self.app.db.toggle_favorite_file(fid); self.refresh()

    def _verify(self, fid: int):
        try:
            ok = self.app.vault.verify_file(fid)
            messagebox.showinfo("Integrity", "✔ File integrity OK" if ok else "✘ Integrity MISMATCH")
        except Exception as e:
            messagebox.showerror("Integrity", str(e))

    def _export(self, fid: int):
        row = self.app.db.get_file(fid)
        if not row: return
        dest = filedialog.asksaveasfilename(initialfile=row["name"])
        if not dest: return
        try:
            self.app.vault.export_file(fid, dest)
            messagebox.showinfo("AegisVault", "Decrypted file written.")
        except Exception as e:
            messagebox.showerror("Export", str(e))

    def _delete(self, fid: int):
        if not messagebox.askyesno("Securely delete", "Securely wipe this file from the vault?"):
            return
        self.app.vault.delete_file(fid); self.refresh()

    def _export_vault(self):
        dest = filedialog.asksaveasfilename(defaultextension=".zip",
                                            initialfile="aegisvault_backup.zip")
        if not dest: return
        try:
            self.app.vault.export_vault(dest)
            messagebox.showinfo("Backup", "Encrypted backup created.")
        except Exception as e:
            messagebox.showerror("Backup", str(e))

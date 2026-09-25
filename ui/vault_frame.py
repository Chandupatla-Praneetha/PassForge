import customtkinter as ctk

from core import crypto_utils as cu
from ui import style
from ui.add_entry_dialog import AddEntryDialog
from ui.change_master_dialog import ChangeMasterPasswordDialog


class VaultFrame(ctk.CTkFrame):
    def __init__(self, master, controller):
        super().__init__(master, fg_color=style.BG)
        self.controller = controller
        self._revealed = set()   # entry ids currently shown in plaintext
        self._row_widgets = {}   # entry id -> {"value_label": ..., "toggle_btn": ...}

        # ---------------- header ----------------
        header = ctk.CTkFrame(self, fg_color=style.SURFACE, height=84,
                               corner_radius=0, border_width=0)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)

        left = ctk.CTkFrame(header, fg_color="transparent")
        left.pack(side="left", padx=24, pady=12)
        controller.render_logo(left, size=44).pack(side="left", padx=(0, 10))
        title_box = ctk.CTkFrame(left, fg_color="transparent")
        title_box.pack(side="left")
        ctk.CTkLabel(title_box, text="PassForge", font=style.font(18, "bold"),
                     text_color=style.PRIMARY).pack(anchor="w")
        ctk.CTkLabel(title_box, text="Generate. Analyze. Protect.", font=style.font(11),
                     text_color=style.INK_DIM).pack(anchor="w")

        right = ctk.CTkFrame(header, fg_color="transparent")
        right.pack(side="right", padx=24)
        ctk.CTkButton(right, text="Lock", width=84, height=34,
                      fg_color=style.SURFACE, text_color=style.INK,
                      border_width=1, border_color=style.BORDER,
                      hover_color=style.ACCENT_LIGHT,
                      command=controller.lock).pack(side="right")
        ctk.CTkButton(right, text="Change master password", width=180, height=34,
                      fg_color=style.SURFACE, text_color=style.INK,
                      border_width=1, border_color=style.BORDER,
                      hover_color=style.ACCENT_LIGHT,
                      command=self._open_change_master_dialog).pack(side="right", padx=(0, 10))

        divider = ctk.CTkFrame(self, height=1, fg_color=style.BORDER)
        divider.pack(fill="x")

        # ---------------- toolbar ----------------
        toolbar = ctk.CTkFrame(self, fg_color="transparent")
        toolbar.pack(fill="x", padx=24, pady=16)
        self.search_entry = ctk.CTkEntry(toolbar, height=38, width=320,
                                          placeholder_text="Search by reason…")
        self.search_entry.pack(side="left")
        self.search_entry.bind("<KeyRelease>", lambda _e: self.refresh())

        ctk.CTkButton(toolbar, text="+  New password", height=38, font=style.font(13, "bold"),
                      fg_color=style.PRIMARY, hover_color=style.PRIMARY_HOVER,
                      command=self._open_add_dialog).pack(side="right")

        # ---------------- list ----------------
        self.list_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.list_frame.pack(fill="both", expand=True, padx=24, pady=(0, 20))

        self.empty_label = ctk.CTkLabel(
            self.list_frame,
            text="No passwords saved yet.\nClick \u201c+ New password\u201d to create your first one.",
            font=style.font(13), text_color=style.INK_DIM, justify="center")

        self.refresh()

    # ---------------------------------------------------------------- data --
    def refresh(self):
        for child in self.list_frame.winfo_children():
            child.destroy()
        self._row_widgets.clear()
        # Rows are always rebuilt masked, so any previously "revealed" state
        # must be cleared too — otherwise the first click after a refresh
        # looks like it does nothing (internal state says shown, display
        # says hidden, so the click just re-hides what already looks hidden).
        self._revealed.clear()

        entries = self.controller.db.list_entries(search=self.search_entry.get().strip())
        if not entries:
            self.empty_label = ctk.CTkLabel(
                self.list_frame,
                text="No passwords saved yet.\nClick \u201c+ New password\u201d to create your first one.",
                font=style.font(13), text_color=style.INK_DIM, justify="center")
            self.empty_label.pack(pady=60)
            return

        for entry in entries:
            self._build_row(entry)

    def _build_row(self, entry):
        row = ctk.CTkFrame(self.list_frame, fg_color=style.SURFACE, corner_radius=10,
                            border_width=1, border_color=style.BORDER)
        row.pack(fill="x", pady=6)

        info = ctk.CTkFrame(row, fg_color="transparent")
        info.pack(side="left", fill="x", expand=True, padx=16, pady=12)

        top_line = ctk.CTkFrame(info, fg_color="transparent")
        top_line.pack(fill="x", anchor="w")
        ctk.CTkLabel(top_line, text=entry.reason, font=style.font(14, "bold"),
                     text_color=style.INK).pack(side="left")

        badge_color = style.STRENGTH_COLORS.get(entry.strength_label, style.BORDER)
        badge = ctk.CTkLabel(top_line, text=entry.strength_label, font=style.font(10, "bold"),
                              text_color="white", fg_color=badge_color, corner_radius=8,
                              width=64, height=20)
        badge.pack(side="left", padx=(10, 0))

        value_label = ctk.CTkLabel(info, text="•" * 14, font=style.font(13),
                                    text_color=style.INK_DIM, anchor="w")
        value_label.pack(fill="x", anchor="w", pady=(4, 0))

        meta_label = ctk.CTkLabel(info, text=entry.created_at.split("T")[0],
                                   font=style.font(10), text_color=style.INK_DIM)
        meta_label.pack(anchor="w", pady=(2, 0))

        actions = ctk.CTkFrame(row, fg_color="transparent")
        actions.pack(side="right", padx=12, pady=12)

        toggle_btn = ctk.CTkButton(actions, text="Show", width=64, height=30,
                                    font=style.font(11), fg_color=style.SURFACE,
                                    text_color=style.PRIMARY, border_width=1,
                                    border_color=style.BORDER, hover_color=style.ACCENT_LIGHT,
                                    command=lambda e=entry: self._toggle_reveal(e))
        toggle_btn.pack(side="left", padx=(0, 6))

        copy_btn = ctk.CTkButton(actions, text="Copy", width=56, height=30,
                                  font=style.font(11), fg_color=style.ACCENT,
                                  hover_color="#0B72C4",
                                  command=lambda e=entry: self._copy(e))
        copy_btn.pack(side="left", padx=(0, 6))

        edit_btn = ctk.CTkButton(actions, text="Edit", width=52, height=30,
                                  font=style.font(11), fg_color=style.SURFACE,
                                  text_color=style.INK, border_width=1,
                                  border_color=style.BORDER, hover_color=style.ACCENT_LIGHT,
                                  command=lambda e=entry: self._open_edit_dialog(e))
        edit_btn.pack(side="left", padx=(0, 6))

        delete_btn = ctk.CTkButton(actions, text="Delete", width=60, height=30,
                                    font=style.font(11), fg_color=style.SURFACE,
                                    text_color=style.DANGER, border_width=1,
                                    border_color=style.BORDER, hover_color="#FBEAE9",
                                    command=lambda e=entry: self._delete(e))
        delete_btn.pack(side="left")

        self._row_widgets[entry.id] = {"value_label": value_label, "toggle_btn": toggle_btn}

    # -------------------------------------------------------------- actions --
    def _decrypt(self, entry):
        return cu.decrypt_value(self.controller.session.vault_key, entry.ciphertext)

    def _toggle_reveal(self, entry):
        widgets = self._row_widgets.get(entry.id)
        if not widgets:
            return
        if entry.id in self._revealed:
            self._revealed.discard(entry.id)
            widgets["value_label"].configure(text="•" * 14)
            widgets["toggle_btn"].configure(text="Show")
        else:
            try:
                plaintext = self._decrypt(entry)
            except ValueError:
                widgets["value_label"].configure(text="Could not decrypt this entry.")
                return
            self._revealed.add(entry.id)
            widgets["value_label"].configure(text=plaintext, text_color=style.INK)
            widgets["toggle_btn"].configure(text="Hide")

    def _copy(self, entry):
        try:
            plaintext = self._decrypt(entry)
        except ValueError:
            return
        self.clipboard_clear()
        self.clipboard_append(plaintext)
        # Best-effort auto-clear after 20s if the clipboard still holds it.
        self.after(20000, lambda: self._maybe_clear_clipboard(plaintext))

    def _maybe_clear_clipboard(self, expected_value):
        # The vault frame may already be gone (e.g. the user hit Lock before
        # the 20s elapsed) — guard against acting on a destroyed widget.
        if not self.winfo_exists():
            return
        try:
            if self.clipboard_get() == expected_value:
                self.clipboard_clear()
        except Exception:
            pass

    def _delete(self, entry):
        self.controller.db.delete_entry(entry.id)
        self.refresh()

    def _open_add_dialog(self):
        self._last_dialog = AddEntryDialog(self, self.controller, on_saved=self.refresh)

    def _open_edit_dialog(self, entry):
        self._last_dialog = AddEntryDialog(self, self.controller, on_saved=self.refresh, entry=entry)

    def _open_change_master_dialog(self):
        self._last_change_dialog = ChangeMasterPasswordDialog(self, self.controller)

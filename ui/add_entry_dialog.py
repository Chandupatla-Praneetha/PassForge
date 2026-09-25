import customtkinter as ctk

from core import crypto_utils as cu
from core.password_tools import analyze_strength, generate_password, generate_passphrase
from ui import style


class AddEntryDialog(ctk.CTkToplevel):
    METER_WIDTH = 400  # fixed, since the dialog window itself has a fixed size

    def __init__(self, master, controller, on_saved, entry=None):
        """If `entry` (a core.db.VaultEntry) is given, the dialog opens in
        edit mode: fields are prefilled and saving updates that entry
        instead of creating a new one."""
        super().__init__(master)
        self.controller = controller
        self.on_saved = on_saved
        self.editing_entry = entry
        self.mode = ctk.StringVar(value="manual")

        self.title(("Edit password" if entry else "New password") + " — PassForge")
        self.configure(fg_color=style.BG)
        self.geometry("460x620")
        self.resizable(False, False)
        self.grab_set()  # modal

        pad = ctk.CTkFrame(self, fg_color="transparent")
        pad.pack(fill="both", expand=True, padx=28, pady=24)

        ctk.CTkLabel(pad, text="Edit password" if entry else "Add a new password",
                     font=style.font(18, "bold"), text_color=style.INK).pack(anchor="w")
        ctk.CTkLabel(pad, text="Update the reason or the password itself below."
                               if entry else
                               "Tell PassForge what this password is for, and how you\n"
                               "want to create it.",
                     font=style.font(12), text_color=style.INK_DIM,
                     justify="left").pack(anchor="w", pady=(2, 18))

        ctk.CTkLabel(pad, text="Why are you creating this password?", font=style.font(12, "bold"),
                     text_color=style.INK, anchor="w").pack(fill="x")
        self.reason_entry = ctk.CTkEntry(pad, height=38,
                                          placeholder_text="e.g. Personal Gmail, Work VPN, Netflix")
        self.reason_entry.pack(fill="x", pady=(4, 18))
        self.reason_entry.bind("<Return>", lambda _e: self._save())
        if entry:
            self.reason_entry.insert(0, entry.reason)

        # --- mode switch ---
        mode_row = ctk.CTkFrame(pad, fg_color=style.SURFACE, corner_radius=8,
                                 border_width=1, border_color=style.BORDER)
        mode_row.pack(fill="x", pady=(0, 16))
        self.manual_btn = ctk.CTkButton(
            mode_row, text="I'll create it", height=36, corner_radius=6,
            fg_color=style.PRIMARY, hover_color=style.PRIMARY_HOVER,
            command=lambda: self._set_mode("manual"))
        self.manual_btn.pack(side="left", expand=True, fill="x", padx=4, pady=4)
        self.generate_btn_tab = ctk.CTkButton(
            mode_row, text="Generate for me", height=36, corner_radius=6,
            fg_color="transparent", text_color=style.INK, hover_color=style.ACCENT_LIGHT,
            command=lambda: self._set_mode("generate"))
        self.generate_btn_tab.pack(side="left", expand=True, fill="x", padx=4, pady=4)

        # --- container that swaps content ---
        self.content = ctk.CTkFrame(pad, fg_color="transparent")
        self.content.pack(fill="both", expand=True)

        self._build_manual_panel()
        self._build_generate_panel()
        self._set_mode("manual")

        self.error_label = ctk.CTkLabel(pad, text="", font=style.font(11),
                                         text_color=style.DANGER)
        self.error_label.pack(fill="x", pady=(4, 0))

        ctk.CTkButton(pad, text="Save changes" if entry else "Save to vault", height=42,
                      font=style.font(13, "bold"),
                      fg_color=style.SUCCESS, hover_color="#178A5C",
                      command=self._save).pack(fill="x", pady=(14, 0))

        if entry:
            try:
                existing_plain = cu.decrypt_value(controller.session.vault_key, entry.ciphertext)
                self.manual_entry.insert(0, existing_plain)
                self._on_manual_change()
            except ValueError:
                pass

    # ------------------------------------------------------------- manual --
    def _build_manual_panel(self):
        self.manual_panel = ctk.CTkFrame(self.content, fg_color="transparent")

        ctk.CTkLabel(self.manual_panel, text="Password", font=style.font(12, "bold"),
                     text_color=style.INK, anchor="w").pack(fill="x")
        row = ctk.CTkFrame(self.manual_panel, fg_color="transparent")
        row.pack(fill="x", pady=(4, 6))
        self.manual_entry = ctk.CTkEntry(row, height=38, show="•")
        self.manual_entry.pack(side="left", fill="x", expand=True)
        self.manual_entry.bind("<KeyRelease>", self._on_manual_change)
        self.manual_entry.bind("<Return>", lambda _e: self._save())
        self._manual_show = False
        self.manual_toggle = ctk.CTkButton(row, text="Show", width=64, height=38,
                                            fg_color=style.SURFACE, text_color=style.PRIMARY,
                                            hover_color=style.ACCENT_LIGHT,
                                            border_width=1, border_color=style.BORDER,
                                            command=self._toggle_manual_visibility)
        self.manual_toggle.pack(side="left", padx=(6, 0))

        self.manual_meter_track = ctk.CTkFrame(self.manual_panel, height=6, corner_radius=3,
                                                fg_color=style.BORDER)
        self.manual_meter_track.pack(fill="x", pady=(0, 4))
        self.manual_meter_fill = ctk.CTkFrame(self.manual_meter_track, height=6, corner_radius=3,
                                               fg_color=style.BORDER, width=0)
        self.manual_meter_fill.place(x=0, y=0)

        self.manual_strength_label = ctk.CTkLabel(self.manual_panel, text="",
                                                    font=style.font(11, "bold"),
                                                    text_color=style.INK_DIM, anchor="w")
        self.manual_strength_label.pack(fill="x", pady=(0, 6))

        self.manual_suggestion_label = ctk.CTkLabel(
            self.manual_panel, text="", font=style.font(11), text_color=style.INK_DIM,
            anchor="w", justify="left", wraplength=380)
        self.manual_suggestion_label.pack(fill="x")

        self.use_generated_instead_btn = ctk.CTkButton(
            self.manual_panel, text="This is weak — generate a strong one instead",
            height=32, font=style.font(11), fg_color="transparent", text_color=style.ACCENT,
            hover_color=style.ACCENT_LIGHT, command=lambda: self._set_mode("generate"))
        # shown conditionally

    def _on_manual_change(self, _e=None):
        pw = self.manual_entry.get()
        result = analyze_strength(pw)
        color = style.STRENGTH_COLORS.get(result.label, style.BORDER)
        width = int(self.METER_WIDTH * (result.score / 100)) if pw else 0
        self.manual_meter_fill.configure(width=max(width, 0), fg_color=color)
        self.manual_strength_label.configure(
            text=f"{result.label} · {result.score}/100" if pw else "")
        if pw and result.score < 60 and result.suggestions:
            self.manual_suggestion_label.configure(text="Suggestion: " + result.suggestions[0])
            self.use_generated_instead_btn.pack(fill="x", pady=(6, 0))
        else:
            self.manual_suggestion_label.configure(text="")
            self.use_generated_instead_btn.pack_forget()

    def _toggle_manual_visibility(self):
        self._manual_show = not self._manual_show
        self.manual_entry.configure(show="" if self._manual_show else "•")
        self.manual_toggle.configure(text="Hide" if self._manual_show else "Show")

    # ------------------------------------------------------------ generate --
    def _build_generate_panel(self):
        self.generate_panel = ctk.CTkFrame(self.content, fg_color="transparent")

        row = ctk.CTkFrame(self.generate_panel, fg_color="transparent")
        row.pack(fill="x")
        ctk.CTkLabel(row, text="Length", font=style.font(12, "bold"),
                     text_color=style.INK).pack(side="left")
        self.length_value_label = ctk.CTkLabel(row, text="20", font=style.font(12, "bold"),
                                                text_color=style.ACCENT)
        self.length_value_label.pack(side="right")
        self.length_slider = ctk.CTkSlider(self.generate_panel, from_=8, to=64,
                                            number_of_steps=56, progress_color=style.ACCENT,
                                            button_color=style.PRIMARY,
                                            command=self._on_length_change)
        self.length_slider.set(20)
        self.length_slider.pack(fill="x", pady=(4, 14))

        grid = ctk.CTkFrame(self.generate_panel, fg_color="transparent")
        grid.pack(fill="x", pady=(0, 6))
        self.opt_upper = ctk.CTkCheckBox(grid, text="A-Z", fg_color=style.PRIMARY)
        self.opt_lower = ctk.CTkCheckBox(grid, text="a-z", fg_color=style.PRIMARY)
        self.opt_digits = ctk.CTkCheckBox(grid, text="0-9", fg_color=style.PRIMARY)
        self.opt_symbols = ctk.CTkCheckBox(grid, text="!@#$", fg_color=style.PRIMARY)
        for cb in (self.opt_upper, self.opt_lower, self.opt_digits, self.opt_symbols):
            cb.select()
        self.opt_upper.grid(row=0, column=0, sticky="w", padx=(0, 20), pady=4)
        self.opt_lower.grid(row=0, column=1, sticky="w", pady=4)
        self.opt_digits.grid(row=1, column=0, sticky="w", padx=(0, 20), pady=4)
        self.opt_symbols.grid(row=1, column=1, sticky="w", pady=4)

        self.opt_ambiguous = ctk.CTkCheckBox(self.generate_panel,
                                              text="Exclude look-alike characters (0, O, l, 1, I)",
                                              fg_color=style.PRIMARY)
        self.opt_ambiguous.pack(anchor="w", pady=(0, 14))

        ctk.CTkButton(self.generate_panel, text="Generate", height=38,
                      fg_color=style.ACCENT, hover_color="#0B72C4",
                      command=self._do_generate).pack(fill="x")

        result_box = ctk.CTkFrame(self.generate_panel, fg_color=style.SURFACE,
                                   border_width=1, border_color=style.BORDER, corner_radius=8)
        result_box.pack(fill="x", pady=(14, 0))
        self.generated_label = ctk.CTkLabel(result_box, text="Click Generate to preview a password",
                                             font=style.font(13, "bold"), text_color=style.INK_DIM,
                                             wraplength=380)
        self.generated_label.pack(padx=14, pady=(12, 4))
        self.generated_strength_label = ctk.CTkLabel(result_box, text="",
                                                       font=style.font(11), text_color=style.INK_DIM)
        self.generated_strength_label.pack(padx=14, pady=(0, 12))
        self._generated_value = ""

    def _on_length_change(self, value):
        self.length_value_label.configure(text=str(int(value)))

    def _do_generate(self):
        pw = generate_password(
            length=int(self.length_slider.get()),
            use_upper=bool(self.opt_upper.get()),
            use_lower=bool(self.opt_lower.get()),
            use_digits=bool(self.opt_digits.get()),
            use_symbols=bool(self.opt_symbols.get()),
            exclude_ambiguous=bool(self.opt_ambiguous.get()),
        )
        if pw is None:
            self.generated_label.configure(text="Select at least one character type above.")
            self.generated_strength_label.configure(text="")
            self._generated_value = ""
            return
        self._generated_value = pw
        self.generated_label.configure(text=pw, text_color=style.INK, font=style.font(15, "bold"))
        result = analyze_strength(pw)
        self.generated_strength_label.configure(
            text=f"{result.label} · ~{round(result.entropy_bits)} bits of entropy",
            text_color=style.STRENGTH_COLORS.get(result.label, style.INK_DIM))

    # --------------------------------------------------------------- shared --
    def _set_mode(self, mode):
        self.mode.set(mode)
        active = dict(fg_color=style.PRIMARY, text_color="white", hover_color=style.PRIMARY_HOVER)
        inactive = dict(fg_color="transparent", text_color=style.INK, hover_color=style.ACCENT_LIGHT)
        self.manual_btn.configure(**(active if mode == "manual" else inactive))
        self.generate_btn_tab.configure(**(active if mode == "generate" else inactive))

        self.manual_panel.pack_forget()
        self.generate_panel.pack_forget()
        if mode == "manual":
            self.manual_panel.pack(fill="both", expand=True)
        else:
            self.generate_panel.pack(fill="both", expand=True)

    def _save(self):
        reason = self.reason_entry.get().strip()
        if not reason:
            self.error_label.configure(text="Give this password a reason or label first.")
            return

        if self.mode.get() == "manual":
            pw = self.manual_entry.get()
            if not pw:
                self.error_label.configure(text="Enter a password, or switch to Generate for me.")
                return
        else:
            pw = self._generated_value
            if not pw:
                self.error_label.configure(text="Click Generate first.")
                return

        result = analyze_strength(pw)
        ciphertext = cu.encrypt_value(self.controller.session.vault_key, pw)
        if self.editing_entry:
            self.controller.db.update_entry(self.editing_entry.id, reason, ciphertext,
                                             result.label, result.score)
        else:
            self.controller.db.add_entry(reason, ciphertext, result.label, result.score)
        self.on_saved()
        self.destroy()

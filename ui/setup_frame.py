import re
import customtkinter as ctk

from core import crypto_utils as cu
from core.password_tools import analyze_strength
from ui import style


class SetupFrame(ctk.CTkFrame):
    """Shown once, on first launch, to create the owner account."""

    def __init__(self, master, controller):
        super().__init__(master, fg_color=style.BG)
        self.controller = controller

        wrap = ctk.CTkFrame(self, fg_color=style.SURFACE, corner_radius=14,
                             border_width=1, border_color=style.BORDER)
        wrap.place(relx=0.5, rely=0.5, anchor="center")
        pad = ctk.CTkFrame(wrap, fg_color="transparent")
        pad.pack(padx=48, pady=40)

        controller.render_logo(pad, size=72).pack(pady=(0, 8))
        ctk.CTkLabel(pad, text="Set up your PassForge vault", font=style.font(20, "bold"),
                     text_color=style.INK).pack(pady=(4, 2))
        ctk.CTkLabel(pad, text="This runs once. Your master password unlocks everything —\n"
                               "PassForge never stores it, and can't recover it for you.",
                     font=style.font(12), text_color=style.INK_DIM, justify="center").pack(pady=(0, 20))

        ctk.CTkLabel(pad, text="Email", font=style.font(12, "bold"), text_color=style.INK,
                     anchor="w").pack(fill="x")
        self.email_entry = ctk.CTkEntry(pad, width=340, height=38,
                                         placeholder_text="you@example.com")
        self.email_entry.pack(pady=(4, 14))

        ctk.CTkLabel(pad, text="Master password", font=style.font(12, "bold"),
                     text_color=style.INK, anchor="w").pack(fill="x")
        self.pw_entry = ctk.CTkEntry(pad, width=340, height=38, show="•")
        self.pw_entry.pack(pady=(4, 6))
        self.pw_entry.bind("<KeyRelease>", self._on_pw_change)

        self.meter_track = ctk.CTkFrame(pad, width=340, height=6, corner_radius=3,
                                         fg_color=style.BORDER)
        self.meter_track.pack(pady=(0, 4))
        self.meter_track.pack_propagate(False)
        self.meter_fill = ctk.CTkFrame(self.meter_track, height=6, corner_radius=3,
                                        fg_color=style.BORDER, width=0)
        self.meter_fill.place(x=0, y=0)

        self.strength_label = ctk.CTkLabel(pad, text="", font=style.font(11),
                                            text_color=style.INK_DIM, anchor="w")
        self.strength_label.pack(fill="x", pady=(0, 14))

        ctk.CTkLabel(pad, text="Confirm master password", font=style.font(12, "bold"),
                     text_color=style.INK, anchor="w").pack(fill="x")
        self.confirm_entry = ctk.CTkEntry(pad, width=340, height=38, show="•")
        self.confirm_entry.pack(pady=(4, 18))
        self.confirm_entry.bind("<Return>", lambda _e: self._create())

        self.error_label = ctk.CTkLabel(pad, text="", font=style.font(11),
                                         text_color=style.DANGER)
        self.error_label.pack(fill="x")

        ctk.CTkButton(pad, text="Create vault", width=340, height=42,
                      font=style.font(13, "bold"), fg_color=style.PRIMARY,
                      hover_color=style.PRIMARY_HOVER,
                      command=self._create).pack(pady=(4, 0))

    def _on_pw_change(self, _event=None):
        result = analyze_strength(self.pw_entry.get())
        color = style.STRENGTH_COLORS.get(result.label, style.BORDER)
        width = int(340 * (result.score / 100))
        self.meter_fill.configure(width=width, fg_color=color)
        text = result.label if self.pw_entry.get() else ""
        if result.suggestions and self.pw_entry.get():
            text += "  ·  " + result.suggestions[0]
        self.strength_label.configure(text=text)

    def _create(self):
        email = self.email_entry.get().strip()
        pw = self.pw_entry.get()
        confirm = self.confirm_entry.get()

        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
            self.error_label.configure(text="Enter a valid email address.")
            return
        result = analyze_strength(pw)
        if result.score < 40:
            self.error_label.configure(
                text="Your master password is too weak — this is the one password "
                     "protecting all the others. " + (result.suggestions[0] if result.suggestions else ""))
            return
        if pw != confirm:
            self.error_label.configure(text="Passwords don't match.")
            return

        salt = cu.generate_salt()
        password_hash = cu.hash_master_password(pw, salt)
        self.controller.db.create_owner(email, salt, password_hash)
        self.controller.start_session(email, cu.derive_vault_key(pw, salt))
        self.controller.show_vault()

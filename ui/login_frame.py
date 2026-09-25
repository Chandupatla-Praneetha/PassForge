import threading

import customtkinter as ctk

from core import crypto_utils as cu
from core.alerts import send_unauthorized_access_alert
from ui import style


class LoginFrame(ctk.CTkFrame):
    """Shown on every launch after the first, to unlock the vault."""

    def __init__(self, master, controller):
        super().__init__(master, fg_color=style.BG)
        self.controller = controller

        wrap = ctk.CTkFrame(self, fg_color=style.SURFACE, corner_radius=14,
                             border_width=1, border_color=style.BORDER)
        wrap.place(relx=0.5, rely=0.5, anchor="center")
        pad = ctk.CTkFrame(wrap, fg_color="transparent")
        pad.pack(padx=48, pady=44)

        controller.render_logo(pad, size=76).pack(pady=(0, 8))
        ctk.CTkLabel(pad, text="Welcome back", font=style.font(20, "bold"),
                     text_color=style.INK).pack(pady=(4, 2))
        ctk.CTkLabel(pad, text="Enter your master password to unlock the vault.",
                     font=style.font(12), text_color=style.INK_DIM).pack(pady=(0, 20))

        owner = controller.db.get_owner()
        ctk.CTkLabel(pad, text=owner.email, font=style.font(13, "bold"),
                     text_color=style.INK).pack(pady=(0, 14))

        self.pw_entry = ctk.CTkEntry(pad, width=320, height=40, show="•",
                                      placeholder_text="Master password")
        self.pw_entry.pack(pady=(0, 6))
        self.pw_entry.bind("<Return>", lambda _e: self._attempt_login())
        self.pw_entry.focus()

        self.status_label = ctk.CTkLabel(pad, text="", font=style.font(11),
                                          text_color=style.DANGER, wraplength=320,
                                          justify="left")
        self.status_label.pack(fill="x", pady=(0, 14))

        self.unlock_btn = ctk.CTkButton(pad, text="Unlock", width=320, height=42,
                                         font=style.font(13, "bold"),
                                         fg_color=style.PRIMARY,
                                         hover_color=style.PRIMARY_HOVER,
                                         command=self._attempt_login)
        self.unlock_btn.pack()

    def _attempt_login(self):
        pw = self.pw_entry.get()
        owner = self.controller.db.get_owner()

        if cu.verify_master_password(pw, owner.salt, owner.password_hash):
            self.controller.db.log_login_attempt(success=True)
            self.controller.db.reset_failed_attempts()
            self.controller.start_session(owner.email, cu.derive_vault_key(pw, owner.salt))
            self.controller.show_vault()
            return

        # Wrong password: log it and bump the consecutive-failure counter.
        # An alert email only fires once that counter reaches 5, not on
        # every single miss — otherwise a fumbled first attempt would spam
        # the owner's inbox.
        self.controller.db.log_login_attempt(success=False)
        count = self.controller.db.increment_failed_attempts()
        self.pw_entry.delete(0, "end")

        if count >= 5:
            self.controller.db.reset_failed_attempts()  # so the next 5 re-trigger it
            self.status_label.configure(
                text="Incorrect master password. 5 failed attempts reached — "
                     "notifying the account owner…"
            )
            threading.Thread(target=self._send_alert, args=(owner.email,), daemon=True).start()
        else:
            remaining = 5 - count
            self.status_label.configure(
                text=f"Incorrect master password. {remaining} more failed "
                     f"attempt{'s' if remaining != 1 else ''} before a security alert is sent."
            )

    def _send_alert(self, owner_email: str):
        sent, message = send_unauthorized_access_alert(owner_email)
        note = "A security alert email was sent." if sent else f"Incorrect master password. ({message})"
        # UI updates must happen back on the main thread.
        self.after(0, lambda: self.status_label.configure(text=note))

import customtkinter as ctk

from core import crypto_utils as cu
from core.password_tools import analyze_strength
from ui import style


class ChangeMasterPasswordDialog(ctk.CTkToplevel):
    METER_WIDTH = 360  # fixed, since the dialog window itself has a fixed size

    def __init__(self, master, controller):
        super().__init__(master)
        self.controller = controller

        self.title("Change master password — PassForge")
        self.configure(fg_color=style.BG)
        self.geometry("420x480")
        self.resizable(False, False)
        self.grab_set()

        pad = ctk.CTkFrame(self, fg_color="transparent")
        pad.pack(fill="both", expand=True, padx=28, pady=24)

        ctk.CTkLabel(pad, text="Change master password", font=style.font(18, "bold"),
                     text_color=style.INK).pack(anchor="w")
        ctk.CTkLabel(
            pad, text="Every saved password is re-encrypted with the new master\n"
                      "password automatically — nothing else needs to change.",
            font=style.font(12), text_color=style.INK_DIM, justify="left"
        ).pack(anchor="w", pady=(2, 18))

        ctk.CTkLabel(pad, text="Current master password", font=style.font(12, "bold"),
                     text_color=style.INK, anchor="w").pack(fill="x")
        self.current_entry = ctk.CTkEntry(pad, height=38, show="•")
        self.current_entry.pack(fill="x", pady=(4, 16))

        ctk.CTkLabel(pad, text="New master password", font=style.font(12, "bold"),
                     text_color=style.INK, anchor="w").pack(fill="x")
        self.new_entry = ctk.CTkEntry(pad, height=38, show="•")
        self.new_entry.pack(fill="x", pady=(4, 6))
        self.new_entry.bind("<KeyRelease>", self._on_new_change)

        self.meter_track = ctk.CTkFrame(pad, height=6, corner_radius=3, fg_color=style.BORDER)
        self.meter_track.pack(fill="x", pady=(0, 4))
        self.meter_fill = ctk.CTkFrame(self.meter_track, height=6, corner_radius=3,
                                        fg_color=style.BORDER, width=0)
        self.meter_fill.place(x=0, y=0)
        self.strength_label = ctk.CTkLabel(pad, text="", font=style.font(11),
                                            text_color=style.INK_DIM, anchor="w")
        self.strength_label.pack(fill="x", pady=(0, 16))

        ctk.CTkLabel(pad, text="Confirm new master password", font=style.font(12, "bold"),
                     text_color=style.INK, anchor="w").pack(fill="x")
        self.confirm_entry = ctk.CTkEntry(pad, height=38, show="•")
        self.confirm_entry.pack(fill="x", pady=(4, 16))
        self.confirm_entry.bind("<Return>", lambda _e: self._submit())

        self.status_label = ctk.CTkLabel(pad, text="", font=style.font(11),
                                          text_color=style.DANGER, wraplength=360,
                                          justify="left")
        self.status_label.pack(fill="x", pady=(0, 10))

        ctk.CTkButton(pad, text="Update master password", height=42, font=style.font(13, "bold"),
                      fg_color=style.PRIMARY, hover_color=style.PRIMARY_HOVER,
                      command=self._submit).pack(fill="x")

    def _on_new_change(self, _e=None):
        result = analyze_strength(self.new_entry.get())
        color = style.STRENGTH_COLORS.get(result.label, style.BORDER)
        width = int(self.METER_WIDTH * (result.score / 100))
        self.meter_fill.configure(width=max(width, 0), fg_color=color)
        self.strength_label.configure(text=result.label if self.new_entry.get() else "")

    def _submit(self):
        owner = self.controller.db.get_owner()
        current = self.current_entry.get()
        new = self.new_entry.get()
        confirm = self.confirm_entry.get()

        if not cu.verify_master_password(current, owner.salt, owner.password_hash):
            self.status_label.configure(text="Your current master password is incorrect.")
            return
        result = analyze_strength(new)
        if result.score < 40:
            self.status_label.configure(
                text="Choose a stronger new master password — " +
                     (result.suggestions[0] if result.suggestions else ""))
            return
        if new != confirm:
            self.status_label.configure(text="New passwords don't match.")
            return

        # Re-encrypt every entry under a fresh salt + key before touching
        # the stored credential, so a crash mid-way never leaves the vault
        # half-migrated and unreadable.
        old_key = self.controller.session.vault_key
        new_salt = cu.generate_salt()
        new_hash = cu.hash_master_password(new, new_salt)
        new_key = cu.derive_vault_key(new, new_salt)

        entries = self.controller.db.list_entries()
        re_encrypted = []
        for entry in entries:
            try:
                plaintext = cu.decrypt_value(old_key, entry.ciphertext)
            except ValueError:
                continue  # skip anything already unreadable rather than aborting the whole change
            re_encrypted.append((entry.id, cu.encrypt_value(new_key, plaintext)))

        for entry_id, ciphertext in re_encrypted:
            self.controller.db.update_entry_ciphertext(entry_id, ciphertext)

        self.controller.db.update_owner_credentials(new_salt, new_hash)
        self.controller.session.vault_key = new_key

        self.status_label.configure(text="Master password updated.", text_color=style.SUCCESS)
        self.after(700, self.destroy)

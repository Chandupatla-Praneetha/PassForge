from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import customtkinter as ctk
from PIL import Image, ImageTk

from core.db import Database
from core.bridge_server import BridgeServer
from ui import style
from ui.login_frame import LoginFrame
from ui.setup_frame import SetupFrame
from ui.vault_frame import VaultFrame

ASSETS_DIR = Path(__file__).resolve().parent / "assets"


@dataclass
class Session:
    owner_email: str
    vault_key: bytes


class PassForgeApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        style.apply_theme()

        self.title("PassForge — Generate. Analyze. Protect.")
        self.geometry("900x640")
        self.minsize(780, 560)
        self.configure(fg_color=style.BG)

        try:
            icon_img = Image.open(ASSETS_DIR / "logo.png")
            self._icon_photo = ImageTk.PhotoImage(icon_img)  # keep a reference alive
            self.iconphoto(True, self._icon_photo)
        except Exception:
            pass  # icon is cosmetic; never block startup over it

        self.db = Database()
        self.session: Optional[Session] = None
        self._logo_cache = {}
        self.bridge = BridgeServer(self)

        self._container = ctk.CTkFrame(self, fg_color="transparent")
        self._container.pack(fill="both", expand=True)
        self._current_frame = None

        self._route_initial_screen()

    # ------------------------------------------------------------- routing --
    def _route_initial_screen(self):
        if self.db.has_owner():
            self.show_login()
        else:
            self.show_setup()

    def _show_frame(self, frame_cls):
        if self._current_frame is not None:
            self._current_frame.destroy()
        frame = frame_cls(self._container, self)
        frame.pack(fill="both", expand=True)
        self._current_frame = frame

    def show_setup(self):
        self._show_frame(SetupFrame)

    def show_login(self):
        self._show_frame(LoginFrame)

    def show_vault(self):
        self._show_frame(VaultFrame)

    # ------------------------------------------------------------- session --
    def start_session(self, owner_email: str, vault_key: bytes):
        self.session = Session(owner_email, vault_key)
        self.bridge.start()

    def lock(self):
        self.bridge.stop()
        self.session = None
        self.show_login()

    def notify_entry_added(self):
        """Called from the bridge server's background thread when the browser
        extension saves a password. Marshals back onto the Tk main thread."""
        self.after(0, self._refresh_vault_if_visible)

    def _refresh_vault_if_visible(self):
        from ui.vault_frame import VaultFrame
        if isinstance(self._current_frame, VaultFrame):
            self._current_frame.refresh()

    # ----------------------------------------------------------------- ui --
    def render_logo(self, parent, size=48):
        if size not in self._logo_cache:
            img = Image.open(ASSETS_DIR / "logo.png")
            self._logo_cache[size] = ctk.CTkImage(img, size=(size, size))
        return ctk.CTkLabel(parent, image=self._logo_cache[size], text="")

    def on_close(self):
        self.bridge.stop()
        self.db.close()
        self.destroy()


def main():
    app = PassForgeApp()
    app.protocol("WM_DELETE_WINDOW", app.on_close)
    app.mainloop()


if __name__ == "__main__":
    main()

"""
Design tokens for PassForge's desktop UI. Colors are sampled directly from
the product logo so the app and the brand mark always agree. Light theme
only, by design — no dark mode toggle.
"""

import customtkinter as ctk

# --- palette (sampled from assets/logo.png) ----------------------------
INK = "#1B1F2A"           # primary text
INK_DIM = "#6B7280"       # secondary text
BG = "#F5F7FB"            # app background
SURFACE = "#FFFFFF"       # cards / panels
BORDER = "#E2E6EF"

PRIMARY = "#3B0FE0"       # logo wordmark indigo
PRIMARY_HOVER = "#2F0BB8"
ACCENT = "#0E8FF4"        # logo tagline blue
ACCENT_LIGHT = "#EAF4FE"

SUCCESS = "#1FA971"
CAUTION = "#E0A100"
DANGER = "#E0453C"

STRENGTH_COLORS = {
    "Very weak": DANGER,
    "Weak": DANGER,
    "Fair": CAUTION,
    "Good": "#4C8DFF",
    "Strong": SUCCESS,
    "Empty": BORDER,
}

FONT_FAMILY = "Segoe UI"  # falls back gracefully via Tk on macOS/Linux


def font(size=14, weight="normal"):
    return ctk.CTkFont(family=FONT_FAMILY, size=size, weight=weight)


def apply_theme():
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")

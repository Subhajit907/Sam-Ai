"""First-run setup dialog — lets user pick Free (Ollama) or Paid (OpenAI) mode."""

import tkinter as tk
from tkinter import messagebox
import modules.config as config

_BG       = "#07091a"
_CARD     = "#0d1a2e"
_ACCENT   = "#00bfff"
_TEXT     = "#c0e8ff"
_MUTED    = "#4a7a9b"
_GREEN    = "#00cc77"
_BLUE     = "#4488ff"
_BTN_FG   = "#07091a"


def show_setup_dialog():
    """Blocking setup window. Call before main GUI starts."""
    root = tk.Tk()
    root.title("Alia AI — Setup")
    root.configure(bg=_BG)
    root.resizable(False, False)

    w, h = 500, 460
    sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
    root.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")

    selected_mode = tk.StringVar(value="")

    # ── Header ────────────────────────────────────────────────────────────────
    tk.Label(root, text="Welcome to Alia AI", font=("Helvetica", 22, "bold"),
             bg=_BG, fg=_ACCENT).pack(pady=(32, 4))
    tk.Label(root, text="Choose your AI mode to get started",
             font=("Helvetica", 11), bg=_BG, fg=_MUTED).pack(pady=(0, 22))

    cards = tk.Frame(root, bg=_BG)
    cards.pack(padx=36, fill="x")

    key_frame = tk.Frame(root, bg=_BG)
    key_entry: tk.Entry | None = None

    def _toggle_key(show: bool):
        if show:
            key_frame.pack(pady=(10, 0), fill="x")
        else:
            key_frame.pack_forget()

    # ── Free card ─────────────────────────────────────────────────────────────
    free_card = tk.Frame(cards, bg=_CARD, bd=0)
    free_card.pack(fill="x", pady=(0, 8))

    tk.Radiobutton(
        free_card, text="  Free Mode  —  Ollama (Local AI)",
        variable=selected_mode, value="free",
        font=("Helvetica", 13, "bold"), bg=_CARD, fg=_GREEN,
        selectcolor=_CARD, activebackground=_CARD,
        command=lambda: _toggle_key(False),
    ).pack(anchor="w", padx=14, pady=(12, 2))

    tk.Label(
        free_card,
        text="  Runs Llama 3.2 locally via Ollama — no API key, no cost, works offline.",
        font=("Helvetica", 9), bg=_CARD, fg=_MUTED,
    ).pack(anchor="w", padx=14, pady=(0, 12))

    tk.Label(
        free_card,
        text="  Requires: ollama.com installed + 'ollama pull llama3.2'",
        font=("Helvetica", 8, "italic"), bg=_CARD, fg=_MUTED,
    ).pack(anchor="w", padx=14, pady=(0, 12))

    # ── Paid card ─────────────────────────────────────────────────────────────
    paid_card = tk.Frame(cards, bg=_CARD, bd=0)
    paid_card.pack(fill="x")

    tk.Radiobutton(
        paid_card, text="  Paid Mode  —  OpenAI GPT-4o",
        variable=selected_mode, value="openai",
        font=("Helvetica", 13, "bold"), bg=_CARD, fg=_BLUE,
        selectcolor=_CARD, activebackground=_CARD,
        command=lambda: _toggle_key(True),
    ).pack(anchor="w", padx=14, pady=(12, 2))

    tk.Label(
        paid_card,
        text="  Best quality — GPT-4o chat, OpenAI TTS, vision. Requires API key.",
        font=("Helvetica", 9), bg=_CARD, fg=_MUTED,
    ).pack(anchor="w", padx=14, pady=(0, 12))

    # ── API key entry (shown only for paid mode) ───────────────────────────────
    tk.Label(key_frame, text="  OpenAI API Key:", font=("Helvetica", 10),
             bg=_BG, fg=_TEXT).pack(anchor="w", padx=36)
    key_entry = tk.Entry(
        key_frame, font=("Courier", 10), bg=_CARD, fg=_TEXT,
        insertbackground=_ACCENT, relief="flat", bd=1, width=54, show="*",
    )
    key_entry.pack(padx=36, pady=(4, 0), fill="x")
    existing = config.get_openai_key()
    if existing:
        key_entry.insert(0, existing)

    # ── Continue button ────────────────────────────────────────────────────────
    def _on_continue():
        mode = selected_mode.get()
        if not mode:
            messagebox.showwarning("Choose a Mode", "Please select Free or Paid mode.", parent=root)
            return
        if mode == "openai":
            key = key_entry.get().strip() if key_entry else ""
            if not key:
                messagebox.showwarning("API Key Required",
                                       "Please enter your OpenAI API key.", parent=root)
                return
            config.save_config("openai", key)
        else:
            config.save_config("free")
        root.destroy()

    tk.Button(
        root, text="Continue  →", font=("Helvetica", 12, "bold"),
        bg=_ACCENT, fg=_BTN_FG, relief="flat", padx=22, pady=9,
        command=_on_continue, cursor="hand2",
    ).pack(pady=28)

    # Prevent closing without completing setup
    root.protocol("WM_DELETE_WINDOW", lambda: None)
    root.mainloop()

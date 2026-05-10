"""First-run setup dialog — auto-installs Ollama for free mode, or takes API key for paid."""

import tkinter as tk
from tkinter import messagebox
import subprocess
import shutil
import threading
import time
import modules.config as config

_BG     = "#07091a"
_CARD   = "#0d1a2e"
_ACCENT = "#00bfff"
_TEXT   = "#c0e8ff"
_MUTED  = "#4a7a9b"
_GREEN  = "#00cc77"
_BLUE   = "#4488ff"
_BTN_FG = "#07091a"


# ── Ollama helpers ────────────────────────────────────────────────────────────

def _ollama_installed() -> bool:
    return shutil.which("ollama") is not None


def _install_ollama() -> tuple[bool, str]:
    """Install Ollama via Homebrew (macOS). Returns (success, message)."""
    if shutil.which("brew"):
        try:
            result = subprocess.run(
                ["brew", "install", "ollama"],
                capture_output=True, text=True, timeout=300,
            )
            if result.returncode == 0:
                return True, "Installed via Homebrew."
            return False, (result.stderr or result.stdout).strip()
        except subprocess.TimeoutExpired:
            return False, "Installation timed out."
        except Exception as e:
            return False, str(e)
    return False, "Homebrew not found. Install from brew.sh first, then re-run."


def _start_ollama_serve():
    """Launch ollama serve in the background (no-op if already running)."""
    try:
        subprocess.Popen(
            ["ollama", "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        time.sleep(2)   # give server time to bind
    except Exception:
        pass


def _pull_model(model: str, log_fn) -> bool:
    """Pull an Ollama model, streaming output to log_fn. Returns success."""
    try:
        proc = subprocess.Popen(
            ["ollama", "pull", model],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        for line in proc.stdout:
            log_fn(line.rstrip())
        proc.wait()
        return proc.returncode == 0
    except Exception as e:
        log_fn(f"Error: {e}")
        return False


# ── Dialog ────────────────────────────────────────────────────────────────────

def show_setup_dialog():
    """Blocking setup window shown before the main GUI starts."""
    root = tk.Tk()
    root.title("Alia AI — Setup")
    root.configure(bg=_BG)
    root.resizable(False, False)
    root.protocol("WM_DELETE_WINDOW", lambda: None)   # prevent closing mid-setup

    w, h = 520, 500
    sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
    root.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")

    # ══════════════════════════════════════════════════════════════════════════
    # SCREEN 1 — Mode selection
    # ══════════════════════════════════════════════════════════════════════════
    screen1 = tk.Frame(root, bg=_BG)
    screen1.pack(fill="both", expand=True)

    tk.Label(screen1, text="Welcome to Alia AI",
             font=("Helvetica", 22, "bold"), bg=_BG, fg=_ACCENT).pack(pady=(32, 4))
    tk.Label(screen1, text="Choose your AI mode to get started",
             font=("Helvetica", 11), bg=_BG, fg=_MUTED).pack(pady=(0, 22))

    selected_mode = tk.StringVar(value="")

    cards = tk.Frame(screen1, bg=_BG)
    cards.pack(padx=36, fill="x")

    # ── Free card ─────────────────────────────────────────────────────────────
    free_card = tk.Frame(cards, bg=_CARD)
    free_card.pack(fill="x", pady=(0, 8))

    tk.Radiobutton(
        free_card, text="  Free Mode  —  Ollama  (Local AI, Auto-Install)",
        variable=selected_mode, value="free",
        font=("Helvetica", 13, "bold"), bg=_CARD, fg=_GREEN,
        selectcolor=_CARD, activebackground=_CARD,
    ).pack(anchor="w", padx=14, pady=(12, 2))

    tk.Label(free_card,
             text="  Ollama + Llama 3.2 install automatically — free forever, works offline.",
             font=("Helvetica", 9), bg=_CARD, fg=_MUTED).pack(anchor="w", padx=14, pady=(0, 4))
    tk.Label(free_card,
             text="  macOS: requires Homebrew (brew.sh). One-time ~2 GB download.",
             font=("Helvetica", 8, "italic"), bg=_CARD, fg=_MUTED).pack(anchor="w", padx=14, pady=(0, 10))

    # ── Paid card ─────────────────────────────────────────────────────────────
    paid_card = tk.Frame(cards, bg=_CARD)
    paid_card.pack(fill="x")

    tk.Radiobutton(
        paid_card, text="  Paid Mode  —  OpenAI GPT-4o",
        variable=selected_mode, value="openai",
        font=("Helvetica", 13, "bold"), bg=_CARD, fg=_BLUE,
        selectcolor=_CARD, activebackground=_CARD,
        command=lambda: key_frame.pack(padx=36, pady=(12, 0), fill="x"),
    ).pack(anchor="w", padx=14, pady=(12, 2))

    tk.Label(paid_card,
             text="  GPT-4o + OpenAI TTS. Best quality. Requires your API key.",
             font=("Helvetica", 9), bg=_CARD, fg=_MUTED).pack(anchor="w", padx=14, pady=(0, 10))

    # hide free card radiobutton command — hide key_frame when free is selected
    free_card.winfo_children()[0].configure(command=lambda: key_frame.pack_forget())

    # ── API key entry (shown only when Paid is selected) ──────────────────────
    key_frame = tk.Frame(screen1, bg=_BG)
    tk.Label(key_frame, text="  OpenAI API Key:", font=("Helvetica", 10),
             bg=_BG, fg=_TEXT).pack(anchor="w")
    key_entry = tk.Entry(
        key_frame, font=("Courier", 10), bg=_CARD, fg=_TEXT,
        insertbackground=_ACCENT, relief="flat", bd=1, show="*",
    )
    key_entry.pack(pady=(4, 0), fill="x")
    existing = config.get_openai_key()
    if existing:
        key_entry.insert(0, existing)

    # ══════════════════════════════════════════════════════════════════════════
    # SCREEN 2 — Installation progress (free mode only)
    # ══════════════════════════════════════════════════════════════════════════
    screen2 = tk.Frame(root, bg=_BG)

    tk.Label(screen2, text="Installing Free Mode",
             font=("Helvetica", 18, "bold"), bg=_BG, fg=_GREEN).pack(pady=(32, 4))
    tk.Label(screen2, text="This only happens once — sit tight!",
             font=("Helvetica", 10), bg=_BG, fg=_MUTED).pack(pady=(0, 16))

    step_var = tk.StringVar(value="Starting...")
    tk.Label(screen2, textvariable=step_var,
             font=("Helvetica", 11, "bold"), bg=_BG, fg=_ACCENT).pack(pady=(0, 8))

    log_box = tk.Text(screen2, height=11, font=("Courier", 9),
                      bg=_CARD, fg=_TEXT, relief="flat", state="disabled", wrap="word")
    log_box.pack(padx=28, fill="x")

    done_btn = tk.Button(
        screen2, text="Start Alia  →",
        font=("Helvetica", 12, "bold"), bg=_ACCENT, fg=_BTN_FG,
        relief="flat", padx=22, pady=9, cursor="hand2",
        command=root.destroy, state="disabled",
    )
    done_btn.pack(pady=20)

    def _log(msg: str):
        log_box.configure(state="normal")
        log_box.insert("end", msg + "\n")
        log_box.see("end")
        log_box.configure(state="disabled")
        root.update_idletasks()

    def _run_free_install():
        # Step 1 — Install Ollama if not already present
        if _ollama_installed():
            _log("✓ Ollama already installed — skipping.")
        else:
            step_var.set("Step 1 / 3  —  Installing Ollama...")
            _log("Installing Ollama via Homebrew...")
            ok, msg = _install_ollama()
            _log(msg)
            if not ok:
                step_var.set("Installation failed.")
                _log("\nCould not install automatically.")
                _log("Please install Ollama from ollama.com/download, then re-run Alia.")
                done_btn.configure(state="normal", text="Close")
                return

        # Step 2 — Start the server
        step_var.set("Step 2 / 3  —  Starting Ollama server...")
        _log("Starting ollama serve in background...")
        _start_ollama_serve()
        _log("✓ Ollama server is running.")

        # Step 3 — Pull llama3.2
        step_var.set("Step 3 / 3  —  Downloading Llama 3.2  (~2 GB) ...")
        _log("Pulling llama3.2 — this may take a few minutes on first run...")
        ok = _pull_model("llama3.2", _log)

        if ok:
            _log("\n✓ Llama 3.2 is ready!")
            config.save_config("free")
            step_var.set("All done!  Alia is ready.")
            done_btn.configure(state="normal")
        else:
            step_var.set("Model download failed.")
            _log("Run manually: ollama pull llama3.2")
            done_btn.configure(state="normal", text="Close")

    # ── Continue button ────────────────────────────────────────────────────────
    def _on_continue():
        mode = selected_mode.get()
        if not mode:
            messagebox.showwarning("Choose a Mode",
                                   "Please select Free or Paid mode.", parent=root)
            return

        if mode == "openai":
            key = key_entry.get().strip()
            if not key:
                messagebox.showwarning("API Key Required",
                                       "Please enter your OpenAI API key.", parent=root)
                return
            config.save_config("openai", key)
            root.destroy()
            return

        # Free mode — switch to install screen and begin
        screen1.pack_forget()
        screen2.pack(fill="both", expand=True)
        root.update_idletasks()
        threading.Thread(target=_run_free_install, daemon=True).start()

    tk.Button(
        screen1, text="Continue  →",
        font=("Helvetica", 12, "bold"), bg=_ACCENT, fg=_BTN_FG,
        relief="flat", padx=22, pady=9, cursor="hand2",
        command=_on_continue,
    ).pack(pady=28)

    root.mainloop()

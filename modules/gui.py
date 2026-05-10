"""GUI Module - Jarvis-like frontend for Alia AI"""

import tkinter as tk
from tkinter import simpledialog, messagebox
import math
import random
import threading
import time
import os

try:
    from PIL import Image, ImageDraw, ImageFilter, ImageTk
    _PIL_OK = True
except ImportError:
    _PIL_OK = False

# Color palette
BG       = "#04040f"
RING1    = "#003d80"
RING2    = "#0066cc"
GLOW     = "#00b4ff"
BRIGHT   = "#66d9ff"
DIM      = "#001a3a"
WHITE    = "#e8f4ff"
TEXT_DIM = "#4488aa"

# Avatar-specific skin tones (holographic blue-tinted)
FACE_FILL  = "#010e20"
HAIR_DARK  = "#010b18"
HAIR_MID   = "#001e3a"
HAIR_HI    = "#003d6e"
LIP_COLOR  = "#0088cc"

# ── Photo avatar settings (tune these if face/mouth position is off) ──────────
_AVATAR_PATH      = os.path.join(os.path.dirname(__file__), "assets", "alia_avatar.jpg")
_AVATAR_TARGET_W  = 300    # display width in pixels (height scales automatically)
_MOUTH_Y_FRAC     = 0.565  # mouth centre Y as fraction from top of displayed image
_MOUTH_W_FRAC     = 0.108  # mouth half-width as fraction of displayed image width
_MOUTH_H_FRAC     = 0.032  # mouth half-height as fraction of displayed image height
_EYE_Y_FRAC       = 0.384  # eye row Y fraction
_EYE_X_FRAC       = 0.128  # each eye's X offset from centre (fraction of width)
_EYE_RX_FRAC      = 0.074  # eye half-width fraction
_EYE_RY_FRAC      = 0.027  # eye half-height fraction
_SKIN_COLOR       = "#d4a090"   # skin patch colour (cover original mouth/eyes)
_LIP_PHOTO_COLOR  = "#b83050"   # lip colour
_TEETH_COLOR      = "#f5ede8"   # teeth colour


class AliaGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Alia AI")
        self.root.configure(bg=BG)

        # Size to 90% of screen, centered, minimum 820×640
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        w  = max(820, min(1100, int(sw * 0.90)))
        h  = max(640, min(780,  int(sh * 0.88)))
        x  = (sw - w) // 2
        y  = (sh - h) // 2
        self.root.geometry(f"{w}x{h}+{x}+{y}")
        self.root.minsize(820, 640)
        self.root.resizable(True, True)

        self.state     = "idle"
        self.angle     = 0.0
        self.pulse     = 0.0
        self.pulse_dir = 1
        self._last_text    = ""
        self._video_active = False
        self._video_win    = None

        # Avatar mode
        self._avatar_mode    = False
        self._blink_progress = 0.0   # 0 = eyes open, 1 = eyes fully closed
        self._blink_phase    = "wait"
        self._blink_wait     = 0
        self._blink_wait_max = 160

        # Photo avatar
        self._avatar_photo   = None   # cached ImageTk.PhotoImage
        self._avatar_img_w   = 0
        self._avatar_img_h   = 0
        self._avatar_loaded  = False  # tried to load at least once

        # PIL avatar frame cache (prevent GC)
        self._tk_avatar_frame = None

        # Glow layer caches — built once, reused every frame (avoid repeated GaussianBlur)
        self._avatar_gl_base_cache  = None   # wide bloom (radius=26)
        self._avatar_gl2_base_cache = None   # skull-edge glow (radius=9)

        # Lip sync
        self._lip_sync_data  = []    # normalized amplitude per 30 ms frame
        self._lip_sync_start = 0.0   # time.time() when playback began
        self._lip_sync_amp   = 0.0   # current amplitude (0.0–1.0)

        self._build_ui()
        self._animate()

    # ------------------------------------------------------------------ #
    #  UI construction
    # ------------------------------------------------------------------ #
    def _build_ui(self):
        # ── Top bar ──────────────────────────────────────────────────────
        top = tk.Frame(self.root, bg=BG)
        top.pack(fill="x", padx=30, pady=(18, 0))

        tk.Label(top, text="ALIA", font=("Courier", 11, "bold"),
                 fg=GLOW, bg=BG).pack(side="left")
        tk.Label(top, text="ARTIFICIAL INTELLIGENCE ASSISTANT",
                 font=("Courier", 8), fg=DIM, bg=BG).pack(side="left", padx=12)

        self.status_dot = tk.Label(top, text="●", font=("Courier", 10),
                                   fg=GLOW, bg=BG)
        self.status_dot.pack(side="right")

        self._settings_win   = None   # floating settings panel reference
        self._settings_btn_w = tk.Button(
            top, text="⚙  Settings", font=("Courier", 8),
            fg=TEXT_DIM, bg=BG, activebackground=BG, activeforeground=GLOW,
            relief="flat", bd=0, padx=8, pady=2, cursor="hand2",
            command=self._toggle_settings_panel,
        )
        self._settings_btn_w.pack(side="right", padx=(0, 10))

        # ── Canvas ────────────────────────────────────────────────────────
        self.canvas = tk.Canvas(self.root, width=820, height=400,
                                bg=BG, highlightthickness=0)
        self.canvas.pack()

        # ── Divider ───────────────────────────────────────────────────────
        tk.Frame(self.root, bg=RING2, height=1).pack(fill="x", padx=40)

        # ── Status label ──────────────────────────────────────────────────
        self.status_var = tk.StringVar(value="STANDBY")
        tk.Label(self.root, textvariable=self.status_var,
                 font=("Courier", 11, "bold"), fg=GLOW, bg=BG).pack(pady=(10, 2))

        # ── Conversation text ─────────────────────────────────────────────
        self.text_var = tk.StringVar(value="")   # kept for compat; not shown in UI

        # ── Control panel ─────────────────────────────────────────────────
        ctrl = tk.Frame(self.root, bg=BG)
        ctrl.pack(pady=(4, 10))

        _BTN_BG  = "#0a1628"
        _BTN_BDR = "#1a3a5c"
        _BTN_ACT = "#112240"

        def _styled_btn(parent, text, command, fg=GLOW, bg=_BTN_BG, bdr=_BTN_BDR):
            f = tk.Frame(parent, bg=bdr, padx=1, pady=1)
            b = tk.Button(
                f, text=text, font=("Courier", 9, "bold"),
                fg=fg, bg=bg, activebackground=_BTN_ACT, activeforeground=BRIGHT,
                relief="flat", bd=0, padx=14, pady=6, cursor="hand2",
                command=command,
            )
            b.pack()
            return f, b

        # Single button row — all controls inline
        row1 = tk.Frame(ctrl, bg=BG)
        row1.pack(pady=(0, 4))

        vf, self._video_btn = _styled_btn(row1, "  VIDEO  ", self._toggle_video)
        vf.pack(side="left", padx=4)

        af, self._avatar_btn = _styled_btn(row1, "  AVATAR  ", self._toggle_avatar)
        af.pack(side="left", padx=4)

        # Mode var kept for _on_mode_change; actual switcher lives in Settings panel
        from modules.config import get_mode
        _initial = "Free (Ollama)" if get_mode() == "free" else "Paid (OpenAI)"
        self._mode_var = tk.StringVar(value=_initial)

        # Upload document button — same row
        uf, self._upload_btn = _styled_btn(
            row1, "  ⬆  UPLOAD  ", self._upload_document,
            fg="#00cc77", bg="#071a10", bdr="#0a3320",
        )
        uf.pack(side="left", padx=4)

        # Translator button — same row
        _TRANS_BG  = "#0d0a1a"
        _TRANS_BDR = "#2a1a4a"
        _TRANS_FG  = "#bb88ff"
        _TRANS_ACT = "#1a0d2e"

        tf, self._trans_btn = _styled_btn(
            row1, "  ⇄  TRANSLATOR  ", self._toggle_translator,
            fg=_TRANS_FG, bg=_TRANS_BG, bdr=_TRANS_BDR,
        )
        tf.pack(side="left", padx=4)

        # Expansion row — doc badge and translator panel appear here when active
        row2 = tk.Frame(ctrl, bg=BG)
        row2.pack()

        # Doc badge (hidden until a doc is loaded)
        self._doc_badge = tk.Frame(row2, bg="#0a1628", padx=1, pady=1)
        self._doc_name_var = tk.StringVar(value="")
        self._doc_label = tk.Label(
            self._doc_badge, textvariable=self._doc_name_var,
            font=("Courier", 8), fg=BRIGHT, bg="#0a1628", padx=10, pady=5,
        )
        self._doc_label.pack(side="left")
        self._clear_doc_btn = tk.Button(
            self._doc_badge, text=" × ",
            font=("Helvetica", 10, "bold"),
            fg="#ff5555", bg="#0a1628", activebackground="#1a0a0a",
            relief="flat", bd=0, padx=4, pady=4, cursor="hand2",
            command=self._clear_document,
        )
        self._clear_doc_btn.pack(side="left")

        # Language selector panel (shown only when translator is active)
        # Uses ttk.Combobox instead of OptionMenu — avoids macOS native-menu
        # freeze that occurs when the animation after() loop runs every 30 ms.
        self._trans_panel = tk.Frame(row2, bg=BG)

        from tkinter import ttk
        from modules.translator import LANG_NAMES
        self._from_lang_var = tk.StringVar(value="English")
        self._to_lang_var   = tk.StringVar(value="French")

        # Style comboboxes to match the dark theme
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Trans.TCombobox",
            fieldbackground=_TRANS_BG,
            background=_TRANS_BDR,
            foreground=_TRANS_FG,
            selectbackground=RING2,
            selectforeground=BRIGHT,
            bordercolor=_TRANS_BDR,
            arrowcolor=_TRANS_FG,
            padding=4,
        )
        style.map(
            "Trans.TCombobox",
            fieldbackground=[("readonly", _TRANS_BG)],
            foreground=[("readonly", _TRANS_FG)],
        )

        # FROM label + combobox
        tk.Label(self._trans_panel, text="FROM", font=("Courier", 7),
                 fg=TEXT_DIM, bg=BG).pack(side="left", padx=(10, 3))
        self._from_cb = ttk.Combobox(
            self._trans_panel, textvariable=self._from_lang_var,
            values=LANG_NAMES, state="readonly", width=11,
            style="Trans.TCombobox", font=("Courier", 9, "bold"),
        )
        self._from_cb.bind("<<ComboboxSelected>>", self._on_lang_change)
        self._from_cb.pack(side="left", padx=2)

        # Arrow
        tk.Label(self._trans_panel, text=" → ", font=("Courier", 13, "bold"),
                 fg=_TRANS_FG, bg=BG).pack(side="left")

        # TO label + combobox
        tk.Label(self._trans_panel, text="TO", font=("Courier", 7),
                 fg=TEXT_DIM, bg=BG).pack(side="left", padx=(0, 3))
        self._to_cb = ttk.Combobox(
            self._trans_panel, textvariable=self._to_lang_var,
            values=LANG_NAMES, state="readonly", width=11,
            style="Trans.TCombobox", font=("Courier", 9, "bold"),
        )
        self._to_cb.bind("<<ComboboxSelected>>", self._on_lang_change)
        self._to_cb.pack(side="left", padx=2)

    # ------------------------------------------------------------------ #
    #  Document upload
    # ------------------------------------------------------------------ #
    def _upload_document(self):
        from tkinter import filedialog
        from modules import document as doc_mod
        from modules.ai import (set_document_context, set_document_image_context,
                                describe_image_free, describe_image_paid)
        from modules.config import get_mode

        path = filedialog.askopenfilename(
            title="Upload a document",
            filetypes=[
                ("All supported", "*.pdf *.docx *.doc *.txt *.md *.csv *.jpg *.jpeg *.png *.webp *.bmp *.gif"),
                ("PDF",          "*.pdf"),
                ("Word",         "*.docx *.doc"),
                ("Text / CSV",   "*.txt *.md *.csv"),
                ("Images",       "*.jpg *.jpeg *.png *.webp *.bmp *.gif"),
            ],
        )
        if not path:
            return

        filename = os.path.basename(path)
        short = filename if len(filename) <= 28 else filename[:25] + "..."
        self._doc_name_var.set(f"  {short}  ")
        self._doc_badge.pack(side="left", padx=6)
        self.status_var.set(f"Reading {filename}...")
        self.root.update_idletasks()

        def _process():
            if doc_mod.is_image(path):
                b64 = doc_mod.to_base64(path)
                mime = doc_mod.mime_type(path)
                self.status_var.set("Analyzing image...")
                if get_mode() == "free":
                    desc = describe_image_free(b64)
                else:
                    desc = describe_image_paid(b64, mime)
                set_document_image_context(filename, desc)
            else:
                text = doc_mod.extract_text(path)
                set_document_context(filename, text)

            self.status_var.set(f"Ready — {filename} loaded. Ask me anything about it!")
            self.root.after(3000, lambda: self.status_var.set("STANDBY"))

        threading.Thread(target=_process, daemon=True).start()

    def _clear_document(self):
        from modules.ai import clear_document_context
        clear_document_context()
        self._doc_name_var.set("")
        self._doc_badge.pack_forget()
        self.status_var.set("Document cleared.")
        self.root.after(2000, lambda: self.status_var.set("STANDBY"))

    # ------------------------------------------------------------------ #
    #  Translator
    # ------------------------------------------------------------------ #
    def _toggle_translator(self):
        from modules import translator as trans_mod
        if trans_mod.is_active():
            trans_mod.clear()
            self._trans_btn.config(fg="#bb88ff", bg="#0d0a1a", text="  ⇄  TRANSLATOR  ")
            self._trans_panel.pack_forget()
            self.status_var.set("Translator off.")
            self.root.after(2000, lambda: self.status_var.set("STANDBY"))
        else:
            from_lang = self._from_lang_var.get()
            to_lang   = self._to_lang_var.get()
            trans_mod.set_languages(from_lang, to_lang)
            self._trans_btn.config(fg="#66d9ff", bg="#0d182a", text="  ⇄  TRANSLATING  ")
            self._trans_panel.pack(side="left", padx=4)
            self.status_var.set(f"Translating: {from_lang} → {to_lang}")
            self.root.after(3000, lambda: self.status_var.set("STANDBY"))

    def _on_lang_change(self, *_):
        # Called via <<ComboboxSelected>> event (arg is an Event object — ignored)
        from modules import translator as trans_mod
        if not trans_mod.is_active():
            return
        from_lang = self._from_lang_var.get()
        to_lang   = self._to_lang_var.get()
        trans_mod.set_languages(from_lang, to_lang)
        self.status_var.set(f"Translating: {from_lang} → {to_lang}")
        self.root.after(2000, lambda: self.status_var.set("STANDBY"))

    # ------------------------------------------------------------------ #
    #  Settings panel (floating, left-anchored)
    # ------------------------------------------------------------------ #
    def _toggle_settings_panel(self):
        if self._settings_win and self._settings_win.winfo_exists():
            self._settings_win.destroy()
            self._settings_win = None
            self._settings_btn_w.config(fg=TEXT_DIM)
            return

        self._settings_btn_w.config(fg=GLOW)

        win = tk.Toplevel(self.root)
        win.title("")
        win.overrideredirect(True)          # no title bar — floating card feel
        win.configure(bg="#0a1628")
        win.attributes("-topmost", True)

        # Position: left side of main window, just below top bar
        self.root.update_idletasks()
        rx = self.root.winfo_rootx()
        ry = self.root.winfo_rooty()
        win.geometry(f"220x180+{rx + 14}+{ry + 50}")

        # Card border frame
        border = tk.Frame(win, bg="#1a3a5c", padx=1, pady=1)
        border.pack(fill="both", expand=True)
        inner = tk.Frame(border, bg="#04040f")
        inner.pack(fill="both", expand=True, padx=1, pady=1)

        # Header
        hdr = tk.Frame(inner, bg="#071220")
        hdr.pack(fill="x")
        tk.Label(hdr, text="  ⚙  SETTINGS", font=("Courier", 9, "bold"),
                 fg=GLOW, bg="#071220", pady=8).pack(side="left")
        tk.Button(hdr, text="×", font=("Helvetica", 11, "bold"),
                  fg="#ff5555", bg="#071220", activebackground="#1a0a0a",
                  relief="flat", bd=0, padx=10, pady=6, cursor="hand2",
                  command=lambda: self._toggle_settings_panel()).pack(side="right")

        tk.Frame(inner, bg="#1a3a5c", height=1).pack(fill="x")

        # MODEL section
        tk.Label(inner, text="MODEL", font=("Courier", 7),
                 fg=TEXT_DIM, bg="#04040f", pady=(8)).pack(anchor="w", padx=14)

        btn_area = tk.Frame(inner, bg="#04040f")
        btn_area.pack(fill="x", padx=12, pady=(2, 10))

        from modules.config import get_mode

        def _pick_free():
            self._on_mode_change("Free (Ollama)")
            _refresh()

        def _pick_paid():
            self._on_mode_change("Paid (OpenAI)")
            _refresh()

        self._s_free_btn = tk.Button(
            btn_area, text="Free  (Ollama)", font=("Courier", 8, "bold"),
            relief="flat", bd=0, padx=10, pady=6, cursor="hand2",
            command=_pick_free,
        )
        self._s_free_btn.pack(fill="x", pady=(0, 4))

        self._s_paid_btn = tk.Button(
            btn_area, text="Paid  (OpenAI)", font=("Courier", 8, "bold"),
            relief="flat", bd=0, padx=10, pady=6, cursor="hand2",
            command=_pick_paid,
        )
        self._s_paid_btn.pack(fill="x")

        def _refresh():
            mode = get_mode()
            if mode == "free":
                self._s_free_btn.config(fg=BRIGHT, bg="#112240")
                self._s_paid_btn.config(fg=TEXT_DIM, bg="#0a1628")
            else:
                self._s_free_btn.config(fg=TEXT_DIM, bg="#0a1628")
                self._s_paid_btn.config(fg=BRIGHT, bg="#112240")

        _refresh()

        # Close when clicking outside
        def _on_focus_out(e):
            if self._settings_win and self._settings_win.winfo_exists():
                try:
                    if not str(e.widget).startswith(str(win)):
                        self._toggle_settings_panel()
                except Exception:
                    pass

        win.bind("<FocusOut>", _on_focus_out)
        win.focus_set()
        self._settings_win = win

    # ------------------------------------------------------------------ #
    #  Mode switcher
    # ------------------------------------------------------------------ #
    def _on_mode_change(self, selection: str):
        from modules.config import get_mode, get_openai_key, save_config
        new_mode = "free" if "Ollama" in selection else "openai"

        if new_mode == "openai" and not get_openai_key():
            key = simpledialog.askstring(
                "OpenAI API Key",
                "Enter your OpenAI API key:",
                parent=self.root, show="*",
            )
            if not key or not key.strip():
                # Revert dropdown — user cancelled
                self._mode_var.set("Free (Ollama)")
                return
            save_config("openai", key.strip())
        else:
            save_config(new_mode)

        # Keep mode_var in sync (used elsewhere in the codebase)
        self._mode_var.set("Free (Ollama)" if new_mode == "free" else "Paid (OpenAI)")

        # Confirm switch in the status label
        label = "Free Mode (Ollama)" if new_mode == "free" else "Paid Mode (OpenAI)"
        self.status_var.set(f"Switched to {label}")
        self.root.after(2500, lambda: self.status_var.set("STANDBY"))

    # ------------------------------------------------------------------ #
    #  Avatar toggle
    # ------------------------------------------------------------------ #
    def _toggle_avatar(self):
        self._avatar_mode = not self._avatar_mode
        if self._avatar_mode:
            self._avatar_btn.config(fg=BRIGHT, bg="#112240", text="  AVATAR ON  ")
            self._blink_progress = 0.0
            self._blink_phase    = "wait"
            self._blink_wait     = 0
            # Caches are built lazily on first draw — no action needed here
        else:
            self._avatar_btn.config(fg=GLOW, bg="#0a1628", text="  AVATAR  ")
            # Release glow cache memory when avatar is off
            self._avatar_gl_base_cache  = None
            self._avatar_gl2_base_cache = None

    # ------------------------------------------------------------------ #
    #  Photo avatar helpers
    # ------------------------------------------------------------------ #
    def _load_avatar_image(self) -> bool:
        """Load and cache the avatar photo. Returns True if photo is ready."""
        if self._avatar_loaded:
            return self._avatar_photo is not None
        self._avatar_loaded = True
        if not _PIL_OK or not os.path.exists(_AVATAR_PATH):
            return False
        try:
            img = Image.open(_AVATAR_PATH).convert("RGB")
            w, h = img.size
            scale = _AVATAR_TARGET_W / w
            nw, nh = int(w * scale), int(h * scale)
            nh = min(nh, 390)   # cap height to canvas
            img = img.resize((nw, nh), Image.LANCZOS)
            self._avatar_photo = ImageTk.PhotoImage(img)
            self._avatar_img_w = nw
            self._avatar_img_h = nh
            return True
        except Exception:
            return False

    def _draw_photo_avatar(self, c):
        """Display the real photo with animated mouth and blink overlays."""
        cx  = 410
        iw  = self._avatar_img_w
        ih  = self._avatar_img_h
        top = 5                          # image top edge on canvas
        icy = top + ih // 2              # image centre Y

        # Photo background
        c.create_image(cx, icy, image=self._avatar_photo, anchor="center")

        # ── Mouth region ─────────────────────────────────────────────────
        mw  = int(iw * _MOUTH_W_FRAC)   # half-width
        mh  = int(ih * _MOUTH_H_FRAC)   # half-height
        mcy = top + int(ih * _MOUTH_Y_FRAC)

        # Cover original mouth with skin patch (slightly larger than mouth)
        c.create_oval(cx - mw - 3, mcy - mh - 3,
                      cx + mw + 3, mcy + mh + 3,
                      fill=_SKIN_COLOR, outline=_SKIN_COLOR)

        self._draw_photo_mouth(c, cx, mcy, mw, mh)

        # ── Blink eyelid overlay ─────────────────────────────────────────
        if self._blink_progress > 0.05:
            ey  = top + int(ih * _EYE_Y_FRAC)
            exo = int(iw * _EYE_X_FRAC)
            erx = int(iw * _EYE_RX_FRAC)
            ery = int(ih * _EYE_RY_FRAC)
            lid = max(1, int(ery * 2 * self._blink_progress))
            for ex in (cx - exo, cx + exo):
                c.create_oval(ex - erx, ey - ery,
                              ex + erx, ey - ery + lid,
                              fill=_SKIN_COLOR, outline=_SKIN_COLOR)

        # ── Minimal state indicator ───────────────────────────────────────
        dot_colors = {"speaking": "#ff6b6b", "listening": "#66d9ff",
                      "thinking": "#ffd166", "idle": "#06d6a0"}
        dc = dot_colors.get(self.state, "#06d6a0")
        c.create_oval(cx - 208, 8, cx - 196, 20, fill=dc, outline="")
        c.create_text(cx - 192, 14, text=self.state.upper(),
                      font=("Courier", 7, "bold"), fill=dc, anchor="w")

        # Corner brackets
        self._draw_hud_corners(c, cx, icy)

    def _draw_photo_mouth(self, c, cx, cy, mw, mh):
        """Animated mouth drawn over the photo in the correct skin region."""
        state = self.state

        if state == "speaking":
            openness = abs(math.sin(self.angle * 0.22))
            oh = max(2, int(mh * 0.4 + openness * mh * 1.8))

            # Dark mouth cavity
            c.create_oval(cx - mw + 3, cy - oh,
                          cx + mw - 3, cy + oh,
                          fill="#1a0808", outline="")
            # Teeth visible when mouth open enough
            if openness > 0.25:
                th = max(1, int(oh * 0.55))
                c.create_oval(cx - mw + 6, cy - oh + 1,
                              cx + mw - 6, cy - oh + th * 2,
                              fill=_TEETH_COLOR, outline="")
            # Upper lip (cupid's bow shape)
            c.create_line(
                cx - mw,      cy - oh,
                cx - mw // 2, cy - oh - 3,
                cx,           cy - oh - 5,
                cx + mw // 2, cy - oh - 3,
                cx + mw,      cy - oh,
                fill=_LIP_PHOTO_COLOR, width=2, smooth=True,
            )
            # Lower lip
            c.create_arc(cx - mw, cy - oh // 2,
                         cx + mw, cy + oh + 2,
                         start=180, extent=180,
                         outline=_LIP_PHOTO_COLOR, width=2, style=tk.ARC)

        elif state == "listening":
            # Slightly parted, attentive
            c.create_oval(cx - mw + 6, cy - 2, cx + mw - 6, cy + 2,
                          fill="#2a0808", outline="")
            c.create_arc(cx - mw, cy - mh * 2, cx + mw, cy + mh,
                         start=205, extent=130,
                         outline=_LIP_PHOTO_COLOR, width=2, style=tk.ARC)
            # Upper lip
            c.create_line(
                cx - mw, cy - mh,
                cx - mw // 2, cy - mh - 2,
                cx, cy - mh - 3,
                cx + mw // 2, cy - mh - 2,
                cx + mw, cy - mh,
                fill=_LIP_PHOTO_COLOR, width=1, smooth=True,
            )

        elif state == "thinking":
            # Slight smirk
            c.create_line(
                cx - mw + 4, cy + 2,
                cx,          cy,
                cx + mw - 6, cy - 4,
                fill=_LIP_PHOTO_COLOR, width=2, smooth=True,
            )
            c.create_line(
                cx - mw + 4, cy + 2,
                cx - mw // 2 + 2, cy - 2,
                cx, cy,
                fill=_LIP_PHOTO_COLOR, width=1, smooth=True,
            )

        else:  # idle — warm smile (matching the photo's natural smile)
            # Teeth visible in smile
            c.create_arc(cx - mw + 4, cy - mh * 1.6,
                         cx + mw - 4, cy + mh * 0.5,
                         start=210, extent=120,
                         fill=_TEETH_COLOR, outline="", style=tk.CHORD)
            # Smile arc
            c.create_arc(cx - mw, cy - mh * 2, cx + mw, cy + mh,
                         start=205, extent=130,
                         outline=_LIP_PHOTO_COLOR, width=2, style=tk.ARC)
            # Upper lip cupid's bow
            c.create_line(
                cx - mw, cy - mh,
                cx - mw // 2, cy - mh - 3,
                cx, cy - mh - 4,
                cx + mw // 2, cy - mh - 3,
                cx + mw, cy - mh,
                fill=_LIP_PHOTO_COLOR, width=1, smooth=True,
            )
            # Lower lip hint
            c.create_arc(cx - mw + 5, cy - 2, cx + mw - 5, cy + mh,
                         start=180, extent=180,
                         outline=_LIP_PHOTO_COLOR, width=1, style=tk.ARC)

    # ------------------------------------------------------------------ #
    #  Drawing dispatcher
    # ------------------------------------------------------------------ #
    def _draw(self):
        c = self.canvas
        c.delete("all")
        self._draw_grid(c)
        if self._avatar_mode:
            self._draw_avatar(c)
        else:
            self._draw_rings(c)

    # ------------------------------------------------------------------ #
    #  Original rings / HUD
    # ------------------------------------------------------------------ #
    def _draw_rings(self, c):
        cx, cy = 410, 200
        self._draw_hud_corners(c, cx, cy)
        p = self.pulse

        self._arc_ring(c, cx, cy, 160 + p*4, self.angle,       12, DIM,   1)
        self._arc_ring(c, cx, cy, 140,       -self.angle*0.7,   8, RING1, 2)
        self._arc_ring(c, cx, cy, 115,        self.angle*1.3,   6, RING2, 2)
        self._arc_ring(c, cx, cy, 90,        -self.angle*2,     4, GLOW,  2)

        if self.state == "listening":
            for i in range(20):
                a  = math.radians(i * 18 + self.angle * 2)
                h  = 10 + (math.sin(self.angle * 0.15 + i * 1.2) ** 2) * 28
                x1 = cx + math.cos(a) * 152
                y1 = cy + math.sin(a) * 152
                x2 = cx + math.cos(a) * (152 + h)
                y2 = cy + math.sin(a) * (152 + h)
                c.create_line(x1, y1, x2, y2, fill=BRIGHT, width=2)

        elif self.state == "speaking":
            for i in range(4):
                r     = 158 + i * 14 + p * 8
                alpha = max(1, 3 - i)
                c.create_oval(cx-r, cy-r, cx+r, cy+r, outline=GLOW, width=alpha)

        elif self.state == "thinking":
            for i in range(6):
                a  = math.radians(self.angle * 3 + i * 60)
                x1 = cx + math.cos(a) * 150
                y1 = cy + math.sin(a) * 150
                x2 = cx + math.cos(a) * 165
                y2 = cy + math.sin(a) * 165
                c.create_line(x1, y1, x2, y2, fill=BRIGHT, width=3)

        c.create_oval(cx-168, cy-168, cx+168, cy+168, outline=DIM, width=1)

        ir = 70 + p * 3
        c.create_oval(cx-ir, cy-ir, cx+ir, cy+ir,
                      fill="#010118", outline=GLOW, width=2)

        for i in range(3):
            a  = math.radians(self.angle * 2 + i * 120)
            gx = cx + math.cos(a) * 40
            gy = cy + math.sin(a) * 40
            c.create_oval(gx-4, gy-4, gx+4, gy+4, fill=GLOW, outline="")

        c.create_line(cx-55, cy, cx-25, cy, fill=DIM, width=1)
        c.create_line(cx+25, cy, cx+55, cy, fill=DIM, width=1)
        c.create_line(cx, cy-55, cx, cy-25, fill=DIM, width=1)
        c.create_line(cx, cy+25, cx, cy+55, fill=DIM, width=1)

        c.create_text(cx, cy - 12, text="ALIA",
                      font=("Courier", 24, "bold"), fill=BRIGHT)
        c.create_text(cx, cy + 14, text="A . I",
                      font=("Courier", 9), fill=TEXT_DIM)

    # ------------------------------------------------------------------ #
    #  Avatar face drawing  (PIL-rendered, glow + compositing)
    # ------------------------------------------------------------------ #
    def _draw_avatar(self, c):
        if not _PIL_OK:
            self._draw_avatar_canvas_fallback(c)
            return

        W, H   = 820, 400
        cx, cy = 410, 186   # face centre
        fw, fh = 78, 118    # face half-width / half-height
        ey     = cy - 34    # eye row y
        erx, ery = 27, 15   # eye radii
        ny     = cy + 22    # nose tip y
        my     = cy + 62    # mouth centre y
        mw     = 30         # mouth half-width
        bp     = self._blink_progress
        p      = self.pulse

        HAIR_DARK   = (1, 8, 22)
        HAIR_MID    = (0, 18, 46)
        HAIR_EDGE   = (0, 32, 72)
        HAIR_STRAND = (0, 68, 138)
        HAIR_HI     = (0, 98, 185)

        # Realistic skull polygon (matches the reference head silhouette)
        head_pts = [
            (cx,       cy - fh - 4),
            (cx + 42,  cy - fh + 2),
            (cx + fw - 6, cy - fh + 28),
            (cx + fw + 6, cy - fh + 64),
            (cx + fw + 10, cy - 26),        # cheekbone — widest
            (cx + fw + 4,  cy + 18),
            (cx + fw - 14, cy + 58),
            (cx + fw - 36, cy + fh - 6),
            (cx + 22,  cy + fh + 6),
            (cx,       cy + fh + 10),
            (cx - 22,  cy + fh + 6),
            (cx - fw + 36, cy + fh - 6),
            (cx - fw + 14, cy + 58),
            (cx - fw - 4,  cy + 18),
            (cx - fw - 10, cy - 26),        # cheekbone — widest
            (cx - fw - 6,  cy - fh + 64),
            (cx - fw + 6,  cy - fh + 28),
            (cx - 42,  cy - fh + 2),
        ]

        # ── 1. Wide atmospheric bloom (cached — GaussianBlur radius=26 runs once) ──
        if self._avatar_gl_base_cache is None:
            self._build_gl_caches()
        img = Image.new("RGBA", (W, H), (4, 4, 15, 255))
        img.alpha_composite(self._avatar_gl_base_cache)
        d = ImageDraw.Draw(img)
        # Speaking mouth bloom added per-frame directly (no blur — fast, subtle)
        if self.state == "speaking":
            oh = max(2, int(3 + self._lip_sync_amp * 24))
            d.ellipse([cx-mw-16, my-oh-16, cx+mw+16, my+oh+16], fill=(0, 132, 255, 52))

        # Background grid
        for x in range(0, W, 40):
            d.line([(x, 0), (x, H)], fill=(10, 10, 26))
        for y in range(0, H, 40):
            d.line([(0, y), (W, y)], fill=(10, 10, 26))

        # ── 2. Long puffy hair ────────────────────────────────────────────
        d.polygon([
            (cx-50,  cy-fh-18),
            (cx-fw-46, cy-fh+4),  (cx-fw-110, cy-fh+50),
            (cx-fw-136, cy-16),   (cx-fw-130, cy+58),
            (cx-fw-116, cy+136),  (cx-fw-96,  cy+210),
            (cx-fw-74,  cy+282),  (cx-fw-48,  394),
            (cx-fw+6,   400),     (cx-20, 400),
            (cx-14, cy+fh+56),    (cx-fw+18, cy+fh+20),
        ], fill=HAIR_DARK, outline=HAIR_EDGE)
        d.polygon([
            (cx+50,  cy-fh-18),
            (cx+fw+46, cy-fh+4),  (cx+fw+110, cy-fh+50),
            (cx+fw+136, cy-16),   (cx+fw+130, cy+58),
            (cx+fw+116, cy+136),  (cx+fw+96,  cy+210),
            (cx+fw+74,  cy+282),  (cx+fw+48,  394),
            (cx+fw-6,   400),     (cx+20, 400),
            (cx+14, cy+fh+56),    (cx+fw-18, cy+fh+20),
        ], fill=HAIR_DARK, outline=HAIR_EDGE)
        d.pieslice([cx-fw-26, cy-fh-80, cx+fw+26, cy-fh+30],
                   start=0, end=180, fill=HAIR_DARK, outline=HAIR_EDGE)
        d.polygon([
            (cx-44, cy-fh-12),   (cx-fw-28, cy-fh+18),
            (cx-fw-80, cy-fh+64),(cx-fw-100, cy+8),
            (cx-fw-92, cy+88),   (cx-fw-78, cy+164),
            (cx-fw-60, cy+246),  (cx-fw-36, 390),
            (cx-20, 400),        (cx-14, cy+fh+56),
            (cx-fw+16, cy+fh+18),
        ], fill=HAIR_MID, outline=HAIR_STRAND)
        d.polygon([
            (cx+44, cy-fh-12),   (cx+fw+28, cy-fh+18),
            (cx+fw+80, cy-fh+64),(cx+fw+100, cy+8),
            (cx+fw+92, cy+88),   (cx+fw+78, cy+164),
            (cx+fw+60, cy+246),  (cx+fw+36, 390),
            (cx+20, 400),        (cx+14, cy+fh+56),
            (cx+fw-16, cy+fh+18),
        ], fill=HAIR_MID, outline=HAIR_STRAND)
        for bx_off, bl in [(-50,2),(-34,6),(-18,10),(0,12),(18,10),(34,6),(50,2)]:
            d.arc([cx+bx_off-22, cy-fh-6+bl, cx+bx_off+22, cy-fh+24+bl],
                  start=195, end=345, fill=HAIR_MID, width=3)
        for sx,sy,ex2,ey2,ex3,ey3 in [
            (cx-62,cy-fh+8, cx-fw-40,cy+fh+14, cx-fw-66,cy+224),
            (cx-50,cy-fh+3, cx-fw-26,cy+fh,    cx-fw-52,cy+208),
            (cx-40,cy-fh-2, cx-fw-12,cy+fh-10, cx-fw-32,cy+184),
            (cx-76,cy-fh+16,cx-fw-58,cy+116,   cx-fw-88,cy+282),
        ]:
            d.line([(sx,sy),(ex2,ey2),(ex3,ey3)], fill=HAIR_HI, width=1)
        for sx,sy,ex2,ey2,ex3,ey3 in [
            (cx+62,cy-fh+8, cx+fw+40,cy+fh+14, cx+fw+66,cy+224),
            (cx+50,cy-fh+3, cx+fw+26,cy+fh,    cx+fw+52,cy+208),
            (cx+40,cy-fh-2, cx+fw+12,cy+fh-10, cx+fw+32,cy+184),
            (cx+76,cy-fh+16,cx+fw+58,cy+116,   cx+fw+88,cy+282),
        ]:
            d.line([(sx,sy),(ex2,ey2),(ex3,ey3)], fill=HAIR_HI, width=1)

        # ── 3. Neck / shoulders ───────────────────────────────────────────
        nk_top = cy + fh - 8
        nk_bot = cy + fh + 56
        d.rectangle([cx-20, nk_top, cx+20, nk_bot], fill=(1,10,26), outline=(0,36,76))
        d.polygon([
            (cx-20,nk_bot),(cx-118,nk_bot+54),(cx-175,nk_bot+175),
            (cx+175,nk_bot+175),(cx+118,nk_bot+54),(cx+20,nk_bot),
        ], fill=(1,8,24), outline=(0,58,130))
        d.polygon([
            (cx-20,nk_bot),(cx,nk_bot+40),(cx+20,nk_bot),
        ], fill=(1,10,28), outline=(0,82,164))
        # Neck circuit mesh
        d.line([(cx,nk_top),(cx,nk_bot)], fill=(0,52,115), width=1)
        for yy in range(nk_top+12, nk_bot, 14):
            hw = int((yy - nk_top) * 0.22 + 5)
            d.line([(cx-hw,yy),(cx+hw,yy)], fill=(0,44,98), width=1)
        d.ellipse([cx-3,nk_top+18,cx+3,nk_top+24], fill=(0,80,170))
        d.ellipse([cx-3,nk_top+36,cx+3,nk_top+42], fill=(0,80,170))
        # Collarbone circuit dots & lines
        d.line([(cx-80,nk_bot+20),(cx+80,nk_bot+20)], fill=(0,42,92), width=1)
        for ox in (-65,-40,-15,15,40,65):
            d.ellipse([cx+ox-2,nk_bot+18,cx+ox+2,nk_bot+22], fill=(0,75,158))
        for ox in (-50,-28,28,50):
            d.line([(cx+ox,nk_bot+36),(cx+ox*2,nk_bot+128)], fill=(0,26,60), width=1)

        # ── 4. HUD rings ──────────────────────────────────────────────────
        for rr, segs, col, ww in [
            (170,10,(0,22,54),1),(152,8,(0,56,124),2),
            (130,6,(0,78,166),2),(106,4,(0,132,212),2),
        ]:
            gap   = 360.0 / segs
            a_off = self.angle * (1 if segs%2==0 else -0.7)
            for i in range(segs):
                s = int(a_off + i*gap) % 360
                e = int(s + gap*0.55) % 360
                d.arc([cx-rr,cy-rr,cx+rr,cy+rr], start=s, end=e, fill=col, width=ww)

        if self.state == "speaking":
            for i in range(4):
                rr  = int(164 + i*14 + p*8)
                col = (0, max(40, 176-i*40), 255)
                d.ellipse([cx-rr,cy-rr,cx+rr,cy+rr], outline=col, width=max(1,3-i))
        elif self.state == "listening":
            for i in range(20):
                a2 = math.radians(i*18 + self.angle*2)
                h  = 10 + (math.sin(self.angle*0.15 + i*1.2)**2)*28
                x1,y1 = int(cx+math.cos(a2)*162), int(cy+math.sin(a2)*162)
                x2,y2 = int(cx+math.cos(a2)*(162+h)), int(cy+math.sin(a2)*(162+h))
                d.line([(x1,y1),(x2,y2)], fill=(102,217,255), width=2)
        elif self.state == "thinking":
            for i in range(4):
                a2 = math.radians(self.angle*4 + i*90)
                tx = int(cx + fw + 30 + math.cos(a2)*18)
                ty = int(cy - 46     + math.sin(a2)*18)
                d.ellipse([tx-5,ty-5,tx+5,ty+5], fill=(0,100,200))

        # ── 5. Realistic skull head shape ─────────────────────────────────
        # Soft outer shell
        d.ellipse([cx-fw-12, cy-fh-12, cx+fw+12, cy+fh+12],
                  outline=(0,18,48), width=2)
        # Head fill using realistic polygon
        d.polygon(head_pts, fill=(1,11,28), outline=(0,178,255))

        # ── 6. Dense wireframe / circuit patterns ─────────────────────────
        # Horizontal mesh lines (clipped to face ellipse)
        for y_off in range(-int(fh*0.84), int(fh*0.90), 16):
            x_sp = int(fw * math.sqrt(max(0, 1-(y_off/fh)**2)) * 0.90)
            if x_sp > 5:
                d.line([(cx-x_sp, cy+y_off),(cx+x_sp, cy+y_off)],
                       fill=(0,20,50), width=1)

        # Central vertical spine
        d.line([(cx,cy-fh+6),(cx,cy+fh-6)], fill=(0,40,90), width=1)

        # Forehead circuit (bright central column like reference)
        d.line([(cx,cy-fh+6),(cx,cy-fh+50)], fill=(0,82,172), width=2)
        for y_off2, x_ext in [(cy-fh+16,10),(cy-fh+26,16),(cy-fh+36,22),(cy-fh+46,16)]:
            d.line([(cx-x_ext,y_off2),(cx+x_ext,y_off2)], fill=(0,60,132), width=1)
            d.ellipse([cx-2,y_off2-2,cx+2,y_off2+2], fill=(0,115,230))
        d.arc([cx-34,cy-fh+8,cx+34,cy-fh+34], start=202,end=338, fill=(0,68,144),width=1)
        d.arc([cx-22,cy-fh+12,cx+22,cy-fh+28], start=208,end=332, fill=(0,56,122),width=1)

        # Temple circuits (branching from skull sides like reference)
        for sign in (-1,1):
            tx = cx + sign*(fw+2)
            d.line([(tx-sign*10,cy-fh+62),(tx-sign*26,cy-fh+46)], fill=(0,54,118),width=1)
            d.line([(tx-sign*10,cy-fh+62),(tx-sign*28,cy-fh+76)], fill=(0,54,118),width=1)
            d.line([(tx-sign*28,cy-fh+76),(tx-sign*44,cy-fh+70)], fill=(0,50,110),width=1)
            d.line([(tx-sign*28,cy-fh+76),(tx-sign*38,cy-fh+88)], fill=(0,48,106),width=1)
            d.ellipse([tx-sign*10-2,cy-fh+60,tx-sign*10+2,cy-fh+64], fill=(0,110,224))
            d.ellipse([tx-sign*28-2,cy-fh+74,tx-sign*28+2,cy-fh+78], fill=(0,100,210))

        # Cheek vein network (the defining branching veins in the reference)
        for sign in (-1,1):
            bx = cx + sign*(fw-18)
            # Main vein trunk
            d.line([(bx,cy+8),(bx+sign*22,cy+16)], fill=(0,52,116),width=1)
            d.line([(bx+sign*22,cy+16),(bx+sign*38,cy+10)], fill=(0,48,108),width=1)
            d.line([(bx+sign*22,cy+16),(bx+sign*32,cy+30)], fill=(0,48,108),width=1)
            # Secondary branches
            d.line([(bx+sign*32,cy+30),(bx+sign*50,cy+36)], fill=(0,44,100),width=1)
            d.line([(bx+sign*32,cy+30),(bx+sign*42,cy+48)], fill=(0,44,100),width=1)
            d.line([(bx+sign*38,cy+10),(bx+sign*52,cy+6)],  fill=(0,42,94), width=1)
            d.line([(bx+sign*50,cy+36),(bx+sign*62,cy+28)], fill=(0,40,90), width=1)
            # Tertiary micro-branches
            d.line([(bx+sign*42,cy+48),(bx+sign*54,cy+46)], fill=(0,38,84),width=1)
            d.line([(bx+sign*42,cy+48),(bx+sign*48,cy+58)], fill=(0,36,80),width=1)
            # Nodes
            for nx2,ny2 in [(bx,cy+8),(bx+sign*22,cy+16),
                            (bx+sign*32,cy+30),(bx+sign*50,cy+36),
                            (bx+sign*42,cy+48)]:
                d.ellipse([nx2-2,ny2-2,nx2+2,ny2+2], fill=(0,98,208))

        # Jaw circuits
        d.arc([cx-fw+8,cy+int(fh*0.44),cx+fw-8,cy+fh+20],
              start=222,end=318, fill=(0,40,90), width=1)
        for sign in (-1,1):
            d.line([(cx+sign*26,cy+62),(cx+sign*48,cy+60)], fill=(0,44,98),width=1)
            d.line([(cx+sign*48,cy+60),(cx+sign*62,cy+50)], fill=(0,40,90),width=1)
            d.ellipse([cx+sign*48-2,cy+58,cx+sign*48+2,cy+62], fill=(0,88,188))

        # Nose bridge circuit
        d.line([(cx-6,ey+ery+6),(cx-14,cy)], fill=(0,38,85),width=1)
        d.line([(cx+6,ey+ery+6),(cx+14,cy)], fill=(0,38,85),width=1)
        d.line([(cx-14,cy),(cx-10,cy+16)], fill=(0,36,80),width=1)
        d.line([(cx+14,cy),(cx+10,cy+16)], fill=(0,36,80),width=1)

        # Eye-to-temple connectors
        for sign in (-1,1):
            d.line([(cx+sign*16,ey),(cx+sign*(fw-26),ey-14)], fill=(0,50,112),width=1)
            d.line([(cx+sign*(fw-26),ey-14),(cx+sign*(fw-12),ey-8)], fill=(0,46,104),width=1)

        # Skull crown nodes
        for nx2,ny2 in [
            (cx,cy-fh+6),(cx,cy-fh+50),
            (cx-fw+8,cy-fh+30),(cx+fw-8,cy-fh+30),
            (cx-fw+12,cy-22),(cx+fw-12,cy-22),
            (cx-fw+18,cy+58),(cx+fw-18,cy+58),
            (cx,cy+fh-16),
        ]:
            d.ellipse([nx2-3,ny2-3,nx2+3,ny2+3], fill=(0,108,220))

        # Animated scan line clipped to head polygon bounds
        scan_rel = int(self.angle*2.8)%(fh*2)-fh
        scan_y   = cy + scan_rel
        if cy-fh+4 < scan_y < cy+fh-4:
            x_sp = int(fw*math.sqrt(max(0,1-(scan_rel/fh)**2))*0.90)
            d.line([(cx-x_sp,scan_y),(cx+x_sp,scan_y)], fill=(0,60,138))

        # ── 7. Tight skull-edge glow (cached — GaussianBlur radius=9 runs once) ──
        img.alpha_composite(self._avatar_gl2_base_cache)
        d = ImageDraw.Draw(img)
        # Mouth area overlay per-frame (no blur needed — small element)
        if self.state == "speaking":
            oh = max(2, int(3 + self._lip_sync_amp * 24))
            d.ellipse([cx-mw-3,my-oh-3,cx+mw+3,my+oh+3],
                      outline=(0,180,255,152), width=3)
        else:
            d.ellipse([cx-mw-3,my-9,cx+mw+3,my+7], fill=(0,84,175,44))

        # ── 8. Eyebrows ───────────────────────────────────────────────────
        br_y    = cy - 55
        br_lift = {"listening":-8,"thinking":6,"speaking":-4}.get(self.state,0)
        d.line([(cx-58,br_y+br_lift+9),(cx-44,br_y+br_lift+2),
                (cx-30,br_y+br_lift-3),(cx-18,br_y+br_lift+2)],
               fill=(102,217,255), width=2)
        d.line([(cx+18,br_y+br_lift+2),(cx+30,br_y+br_lift-3),
                (cx+44,br_y+br_lift+2),(cx+58,br_y+br_lift+9)],
               fill=(102,217,255), width=2)

        # ── 9. Eyes ───────────────────────────────────────────────────────
        for ex in (cx-36,cx+36):
            open_ry = max(1,int(ery*(1.0-bp)))
            d.ellipse([ex-erx,ey-open_ry,ex+erx,ey+open_ry],
                      fill=(1,9,32), outline=(0,180,255), width=2)
            if bp < 0.75:
                iry = min(open_ry-1,12)
                if iry > 0:
                    d.ellipse([ex-15,ey-iry-1,ex+15,ey+iry+1],
                              outline=(0,72,172), width=1)
                    d.ellipse([ex-13,ey-iry+1,ex+13,ey+iry-1],
                              fill=(0,42,108), outline=(0,122,202), width=1)
                    for ia in range(0,360,45):
                        iax = math.cos(math.radians(ia))*8
                        iay = math.sin(math.radians(ia))*min(8,iry-1)
                        d.line([(ex,ey),(ex+int(iax),ey+int(iay))],
                               fill=(0,72,152), width=1)
                    d.ellipse([ex-5,ey-min(5,iry),ex+5,ey+min(5,iry)], fill=(0,2,8))
                    d.ellipse([ex-9,ey-iry+1,ex-3,ey-iry+6], fill=(102,217,255))
                    d.ellipse([ex+3,ey-iry+4,ex+7,ey-iry+8], fill=(232,244,255))
                    d.ellipse([ex-7,ey-min(7,iry)+1,ex+7,ey+min(7,iry)-1],
                              outline=(0,180,255), width=1)
            if bp > 0.05:
                lid_h = max(1,int(ery*2*bp))
                d.ellipse([ex-erx,ey-ery,ex+erx,ey-ery+lid_h], fill=(1,12,30))
            d.arc([ex-erx,ey-ery,ex+erx,ey+ery],
                  start=182,end=358,fill=(102,217,255),width=2)
            for lx_off in range(-erx+2,erx+1,4):
                lx2 = ex+lx_off
                ly2 = ey-max(1,open_ry)-1
                mid = abs(lx_off)/erx
                tip_len = int(7-mid*4)
                flick = (-1 if lx_off<-erx//2 else (1 if lx_off>erx//2 else 0))
                d.line([(lx2,ly2),(lx2+flick,ly2-max(2,tip_len))],
                       fill=(102,217,255), width=1)
            d.arc([ex-erx+4,ey-2,ex+erx-4,ey+10],
                  start=5,end=175,fill=(0,26,58),width=1)

        # ── 10. Nose ──────────────────────────────────────────────────────
        d.line([(cx,ey+ery+8),(cx,ny-2)], fill=(0,34,85), width=1)
        d.arc([cx-18,ny-5,cx-2,ny+10], start=0,  end=200, fill=(0,42,88), width=1)
        d.arc([cx+2, ny-5,cx+18,ny+10], start=340,end=180, fill=(0,42,88), width=1)
        d.ellipse([cx-2,ny-2,cx+2,ny+2], fill=(0,68,142))

        # ── 11. Lips ──────────────────────────────────────────────────────
        if self.state == "speaking":
            oh = max(2,int(3+self._lip_sync_amp*26))
            d.ellipse([cx-mw,my-oh,cx+mw,my+oh],
                      fill=(2,5,16), outline=(0,180,255), width=2)
            if oh > 8:
                d.arc([cx-mw+5,my-oh+1,cx+mw-5,my+3],
                      start=0,end=180,fill=(215,235,255))
            d.line([(cx-mw,my-oh+3),(cx-mw//2-3,my-oh-4),(cx-7,my-oh-8),
                    (cx,my-oh-5),(cx+7,my-oh-8),(cx+mw//2+3,my-oh-4),(cx+mw,my-oh+3)],
                   fill=(102,217,255), width=2)
            d.arc([cx-mw+2,my-oh//2,cx+mw-2,my+oh+4],
                  start=0,end=180,fill=(0,132,202),width=2)
        elif self.state == "listening":
            d.arc([cx-mw,my-14,cx+mw,my+8], start=15,end=165,
                  fill=(0,180,255), width=2)
            d.line([(cx-mw,my-7),(cx-mw//2-3,my-12),(cx-7,my-14),
                    (cx,my-11),(cx+7,my-14),(cx+mw//2+3,my-12),(cx+mw,my-7)],
                   fill=(0,136,204), width=1)
        elif self.state == "thinking":
            d.line([(cx-mw+6,my+5),(cx-4,my+2),(cx+7,my-2),(cx+mw-5,my-8)],
                   fill=(0,180,255), width=2)
            d.line([(cx-mw+6,my+5),(cx-mw//2+2,my-2),(cx-4,my)],
                   fill=(0,80,160), width=1)
        else:
            d.arc([cx-mw,my-14,cx+mw,my+10], start=15,end=165,
                  fill=(0,180,255), width=2)
            d.line([(cx-mw,my-7),(cx-mw//2-3,my-12),(cx-7,my-14),
                    (cx,my-11),(cx+7,my-14),(cx+mw//2+3,my-12),(cx+mw,my-7)],
                   fill=(102,217,255), width=1)
            d.arc([cx-mw+3,my-4,cx+mw-3,my+10],
                  start=0,end=180,fill=(0,102,192),width=2)
            d.line([(cx-10,my+4),(cx+10,my+4)], fill=(0,180,255), width=1)

        # ── 12. Particles ─────────────────────────────────────────────────
        for i in range(10):
            a2  = math.radians(self.angle*0.9 + i*36)
            r   = 162 + (i*17%38)
            px  = int(cx + math.cos(a2)*r)
            py2 = int(cy + math.sin(a2)*r*0.52)
            sz  = 2 if i%2==0 else 1
            col = (0,180,255) if i%3==0 else ((0,102,204) if i%3==1 else (0,26,58))
            d.ellipse([px-sz,py2-sz,px+sz,py2+sz], fill=col)

        # ── 13. Blit to canvas ────────────────────────────────────────────
        photo = ImageTk.PhotoImage(img)
        self._tk_avatar_frame = photo
        c.create_image(0, 0, image=photo, anchor="nw")

        for i,txt in enumerate(["ID : ALIA-1","VER: 2.0",
                                 f"MOD: {self.state.upper()}","NET: ACTIVE"]):
            c.create_text(cx+fw+18, cy-36+i*14,
                          text=txt, font=("Courier",7), fill=TEXT_DIM, anchor="w")
        for i,txt in enumerate(["NEURAL LINK","EMOTION: ON","VOICE: SYNC"]):
            c.create_text(cx-fw-18, cy-36+i*14,
                          text=txt, font=("Courier",7), fill=TEXT_DIM, anchor="e")
        self._draw_hud_corners(c, cx, cy)

    def _build_gl_caches(self):
        """Pre-render and blur both glow layers once; reused every animation frame."""
        W, H   = 820, 400
        cx, cy = 410, 186
        fw, fh = 78, 118
        ey     = cy - 34
        mw     = 30
        my     = cy + 62

        # Wide atmospheric bloom — radius=26 blur (the most expensive operation)
        gl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        gd = ImageDraw.Draw(gl)
        for off, alp in [(96, 6), (72, 15), (46, 32), (22, 58)]:
            gd.ellipse([cx-fw-off, cy-fh-int(off*0.7),
                        cx+fw+off, cy+fh+int(off*0.7)],
                       fill=(0, 138, 228, alp))
        gd.polygon([
            (cx-fw-136, cy-fh-24), (cx+fw+136, cy-fh-24),
            (cx+fw+98,  H),        (cx-fw-98,  H),
        ], fill=(0, 44, 110, 11))
        for ex in (cx-36, cx+36):
            gd.ellipse([ex-40, ey-30, ex+40, ey+30], fill=(0, 150, 255, 65))
        self._avatar_gl_base_cache = gl.filter(ImageFilter.GaussianBlur(radius=26))

        # Skull-edge glow — radius=9 blur (static parts only; mouth added per-frame)
        head_pts = [
            (cx,          cy - fh - 4),  (cx + 42,     cy - fh + 2),
            (cx + fw - 6, cy - fh + 28), (cx + fw + 6, cy - fh + 64),
            (cx + fw + 10, cy - 26),     (cx + fw + 4,  cy + 18),
            (cx + fw - 14, cy + 58),     (cx + fw - 36, cy + fh - 6),
            (cx + 22,  cy + fh + 6),     (cx,           cy + fh + 10),
            (cx - 22,  cy + fh + 6),     (cx - fw + 36, cy + fh - 6),
            (cx - fw + 14, cy + 58),     (cx - fw - 4,  cy + 18),
            (cx - fw - 10, cy - 26),     (cx - fw - 6,  cy - fh + 64),
            (cx - fw + 6,  cy - fh + 28),(cx - 42,      cy - fh + 2),
        ]
        gl2 = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        g2  = ImageDraw.Draw(gl2)
        g2.polygon(head_pts, outline=(0, 180, 255, 218))
        g2.ellipse([cx-fw-4, cy-fh-4, cx+fw+4, cy+fh+4],
                   outline=(0, 100, 192, 88), width=12)
        for ex in (cx-36, cx+36):
            g2.ellipse([ex-25, ey-21, ex+25, ey+21], fill=(0, 145, 242, 95))
        self._avatar_gl2_base_cache = gl2.filter(ImageFilter.GaussianBlur(radius=9))

    def _draw_avatar_canvas_fallback(self, c):
        """Canvas-only avatar used when PIL is unavailable."""
        cx, cy = 410, 188
        fw, fh = 82, 104

        c.create_rectangle(cx-17, cy+fh-6, cx+17, cy+fh+48,
                           fill=FACE_FILL, outline="#002244", width=1)
        c.create_polygon(
            cx-17, cy+fh+44, cx-105, cy+fh+95, cx-165, cy+fh+200,
            cx+165, cy+fh+200, cx+105, cy+fh+95, cx+17, cy+fh+44,
            fill="#01091c", outline=RING1, width=1,
        )
        c.create_oval(cx-fw, cy-fh, cx+fw, cy+fh,
                      fill=FACE_FILL, outline=GLOW, width=2)
        c.create_text(cx, cy, text="ALIA", font=("Courier", 18, "bold"), fill=BRIGHT)
        self._draw_hud_corners(c, cx, cy)

    # ------------------------------------------------------------------ #
    #  Shared drawing helpers
    # ------------------------------------------------------------------ #
    def _draw_grid(self, c):
        for x in range(0, 820, 40):
            c.create_line(x, 0, x, 400, fill="#0a0a1a", width=1)
        for y in range(0, 400, 40):
            c.create_line(0, y, 820, y, fill="#0a0a1a", width=1)

    def _draw_hud_corners(self, c, cx, cy):
        for ox, oy, sx, sy in [(-1, -1, 1, 1), (1, -1, -1, 1),
                                (-1, 1, 1, -1), (1, 1, -1, -1)]:
            bx = cx + ox * 195
            by = cy + oy * 185
            c.create_line(bx, by, bx + sx*20, by, fill=RING2, width=1)
            c.create_line(bx, by, bx, by + sy*20, fill=RING2, width=1)

    def _arc_ring(self, c, cx, cy, r, angle_offset, segments, color, width):
        gap = 360 / segments
        for i in range(segments):
            start = angle_offset + i * gap
            c.create_arc(cx-r, cy-r, cx+r, cy+r,
                         start=start, extent=gap * 0.55,
                         style=tk.ARC, outline=color, width=width)

    # ------------------------------------------------------------------ #
    #  Animation loop
    # ------------------------------------------------------------------ #
    def _animate(self):
        # Adaptive frame rate — slow down when idle so UI events (dropdowns, clicks)
        # get CPU time; only run at full 30ms when speaking (lip sync needs it).
        _interval_ms = {"idle": 100, "listening": 60, "speaking": 30, "thinking": 60}
        _interval    = _interval_ms.get(self.state, 100)
        _scale       = _interval / 30.0   # keep apparent animation speed constant

        _speeds = {"idle": 0.8, "listening": 2.0, "speaking": 1.5, "thinking": 2.5}
        self.angle = (self.angle + _speeds.get(self.state, 0.8) * _scale) % 360

        self.pulse += 0.05 * self.pulse_dir * _scale
        if self.pulse >= 1.0: self.pulse_dir = -1
        if self.pulse <= 0.0: self.pulse_dir =  1

        # Lip sync amplitude update
        if self.state == "speaking" and self._lip_sync_data and self._lip_sync_start > 0:
            elapsed   = time.time() - self._lip_sync_start
            frame_idx = int(elapsed / 0.030)
            if frame_idx < len(self._lip_sync_data):
                self._lip_sync_amp = self._lip_sync_data[frame_idx]
            else:
                self._lip_sync_amp = 0.0
        else:
            self._lip_sync_amp = 0.0

        # Blink animation (avatar mode only) — speed-scaled to frame rate
        if self._avatar_mode:
            if self._blink_phase == "wait":
                self._blink_wait += 1
                if self._blink_wait >= self._blink_wait_max:
                    self._blink_phase = "closing"
                    self._blink_wait  = 0
            elif self._blink_phase == "closing":
                self._blink_progress = min(1.0, self._blink_progress + 0.2 * _scale)
                if self._blink_progress >= 1.0:
                    self._blink_phase = "opening"
            elif self._blink_phase == "opening":
                self._blink_progress = max(0.0, self._blink_progress - 0.2 * _scale)
                if self._blink_progress <= 0.0:
                    self._blink_phase    = "wait"
                    self._blink_wait_max = random.randint(110, 270)

        # Status dot blink
        dot_colors = {"idle": DIM, "listening": BRIGHT,
                      "speaking": GLOW, "thinking": RING2}
        blink = int(self.angle / 30) % 2
        self.status_dot.config(
            fg=dot_colors.get(self.state, GLOW) if blink or self.state == "idle" else BG
        )

        self._draw()
        self.root.after(_interval, self._animate)

    # ------------------------------------------------------------------ #
    #  Thread-safe public API
    # ------------------------------------------------------------------ #
    def set_state(self, state, text=""):
        """Call from any thread to update state and optional display text."""
        def _update():
            self.state = state
            labels = {
                "idle":      "STANDBY",
                "listening": "LISTENING ...",
                "speaking":  "SPEAKING",
                "thinking":  "PROCESSING ...",
            }
            self.status_var.set(labels.get(state) or state.upper())
            if text:
                self._last_text = text   # retained internally; not shown in UI
        self.root.after(0, _update)

    def show_text(self, text):
        self._last_text = text   # retained internally; not shown in UI

    # ------------------------------------------------------------------ #
    #  Video / Camera
    # ------------------------------------------------------------------ #
    def _toggle_video(self):
        if self._video_active:
            self._stop_video()
        else:
            self._start_video()

    def _start_video(self):
        from modules import vision
        try:
            vision.start_camera()
        except RuntimeError as e:
            self.show_text(str(e))
            return

        self._video_active = True
        self._video_btn.config(fg=BRIGHT, bg="#112240", text="  VIDEO ON  ")
        self.set_state("idle", "Camera is on — show me something and ask!")

        self._video_win = tk.Toplevel(self.root)
        self._video_win.title("Alia — Camera")
        self._video_win.configure(bg=BG)
        self._video_win.resizable(False, False)
        self._video_win.protocol("WM_DELETE_WINDOW", self._stop_video)

        tk.Label(self._video_win, text="CAMERA FEED",
                 font=("Courier", 8), fg=TEXT_DIM, bg=BG).pack(pady=(8, 2))
        self._video_label = tk.Label(self._video_win, bg=BG)
        self._video_label.pack(padx=10, pady=(0, 10))

        self._refresh_video_frame()

    def _refresh_video_frame(self):
        if not self._video_active:
            return
        from modules import vision
        try:
            from PIL import Image, ImageTk
            import cv2
            frame = vision.get_frame()
            if frame is not None:
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(frame_rgb).resize((400, 300))
                photo = ImageTk.PhotoImage(img)
                if self._video_label.winfo_exists():
                    self._video_label.config(image=photo)
                    self._video_label.image = photo  # type: ignore[attr-defined]
        except Exception:
            pass
        if self._video_active:
            self.root.after(66, self._refresh_video_frame)   # ~15 fps

    def _stop_video(self):
        if not self._video_active:
            return   # guard against double-call
        from modules import vision
        self._video_active = False
        vision.stop_camera()
        try:
            self._video_btn.config(fg=GLOW, bg="#0a1628", text="  VIDEO  ")
        except Exception:
            pass
        self.set_state("idle", "Camera off.")
        win = self._video_win
        self._video_win = None
        if win:
            try:
                win.destroy()
            except Exception:
                pass

    # ------------------------------------------------------------------ #
    #  Lip sync API (called from voice thread)
    # ------------------------------------------------------------------ #
    def load_lip_sync(self, data: list):
        """Store amplitude envelope before playback starts. Thread-safe."""
        self._lip_sync_data  = data
        self._lip_sync_start = 0.0
        self._lip_sync_amp   = 0.0

    def start_lip_sync(self, t_start: float):
        """Record exact playback start time. Thread-safe (CPython GIL)."""
        self._lip_sync_start = t_start

    def run(self):
        self.root.mainloop()

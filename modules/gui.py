"""GUI Module - Jarvis-like frontend for Alia AI"""

import tkinter as tk
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
        self.root.geometry("820x640")
        self.root.resizable(False, False)

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
        self.text_var = tk.StringVar(value="Say something to Alia...")
        tk.Label(self.root, textvariable=self.text_var,
                 font=("Courier", 10), fg=WHITE, bg=BG,
                 wraplength=740, justify="center").pack(pady=(0, 6))

        # ── Button bar ────────────────────────────────────────────────────
        btn_frame = tk.Frame(self.root, bg=BG)
        btn_frame.pack(pady=(0, 12))

        self._video_btn = tk.Button(
            btn_frame, text="[ VIDEO ]",
            font=("Courier", 10, "bold"),
            fg=GLOW, bg=BG, activebackground=DIM,
            activeforeground=BRIGHT, relief="flat", bd=0,
            cursor="hand2", command=self._toggle_video,
        )
        self._video_btn.pack(side="left", padx=20)

        self._avatar_btn = tk.Button(
            btn_frame, text="[ AVATAR MODE ]",
            font=("Courier", 10, "bold"),
            fg=GLOW, bg=BG, activebackground=DIM,
            activeforeground=BRIGHT, relief="flat", bd=0,
            cursor="hand2", command=self._toggle_avatar,
        )
        self._avatar_btn.pack(side="left", padx=20)

    # ------------------------------------------------------------------ #
    #  Avatar toggle
    # ------------------------------------------------------------------ #
    def _toggle_avatar(self):
        self._avatar_mode = not self._avatar_mode
        if self._avatar_mode:
            self._avatar_btn.config(fg=BRIGHT, text="[ AVATAR ON ]")
            self._blink_progress = 0.0
            self._blink_phase    = "wait"
            self._blink_wait     = 0
        else:
            self._avatar_btn.config(fg=GLOW, text="[ AVATAR MODE ]")

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
        cx, cy = 410, 175   # moved up for long hair
        fw, fh = 78, 112    # slimmer, taller oval = feminine
        ey     = cy - 28    # eyes higher
        erx, ery = 28, 16   # large almond eyes
        ny     = cy + 22
        my     = cy + 62
        mw     = 32
        bp     = self._blink_progress
        p      = self.pulse

        HAIR_DARK   = (1, 8, 22)
        HAIR_MID    = (0, 16, 44)
        HAIR_EDGE   = (0, 28, 62)
        HAIR_STRAND = (0, 65, 132)
        HAIR_HI     = (0, 95, 178)

        # ── Glow pass 1: wide atmospheric bloom ──────────────────────────
        gl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        gd = ImageDraw.Draw(gl)

        for off, alp in [(75, 10), (55, 20), (32, 40), (14, 68)]:
            r = fw + off
            gd.ellipse([cx - int(r * 1.12), cy - r, cx + int(r * 1.12), cy + r],
                       fill=(0, 160, 240, alp))

        # Long hair glow column
        gd.polygon([
            (cx - fw - 125, cy - fh),
            (cx + fw + 125, cy - fh),
            (cx + fw + 85,  H),
            (cx - fw - 85,  H),
        ], fill=(0, 55, 128, 14))

        for rr in (112, 138, 162):
            gd.ellipse([cx-rr, cy-rr, cx+rr, cy+rr],
                       outline=(0, 100, 200, 40), width=4)

        for ex in (cx - 34, cx + 34):
            gd.ellipse([ex-32, ey-22, ex+32, ey+22], fill=(0, 180, 255, 85))

        if self.state == "speaking":
            oh = max(2, int(3 + self._lip_sync_amp * 24))
            gd.ellipse([cx-mw-10, my-oh-10, cx+mw+10, my+oh+10],
                       fill=(0, 150, 255, 68))

        gl = gl.filter(ImageFilter.GaussianBlur(radius=20))

        # ── Compose base image ────────────────────────────────────────────
        img = Image.new("RGBA", (W, H), (4, 4, 15, 255))
        img.alpha_composite(gl)
        d = ImageDraw.Draw(img)

        # Grid
        for x in range(0, W, 40):
            d.line([(x, 0), (x, H)], fill=(10, 10, 26))
        for y in range(0, H, 40):
            d.line([(0, y), (W, y)], fill=(10, 10, 26))

        # ── HUD rings ────────────────────────────────────────────────────
        ring_defs = [
            (164, 8,  (0, 26,  64), 1),
            (144, 6,  (0, 61, 128), 2),
            (120, 5,  (0, 80, 170), 2),
            (96,  4,  (0,140, 220), 2),
        ]
        for rr, segs, col, ww in ring_defs:
            gap   = 360.0 / segs
            a_off = self.angle * (1 if segs % 2 == 0 else -0.7)
            for i in range(segs):
                s = int(a_off + i * gap) % 360
                e = int(s + gap * 0.55) % 360
                d.arc([cx-rr, cy-rr, cx+rr, cy+rr], start=s, end=e, fill=col, width=ww)

        if self.state == "speaking":
            for i in range(4):
                rr  = int(160 + i*14 + p*8)
                col = (0, max(40, 180-i*40), 255)
                d.ellipse([cx-rr, cy-rr, cx+rr, cy+rr], outline=col, width=max(1, 3-i))
        elif self.state == "listening":
            for i in range(20):
                a2 = math.radians(i*18 + self.angle*2)
                h  = 10 + (math.sin(self.angle*0.15 + i*1.2)**2)*28
                x1, y1 = int(cx+math.cos(a2)*154), int(cy+math.sin(a2)*154)
                x2, y2 = int(cx+math.cos(a2)*(154+h)), int(cy+math.sin(a2)*(154+h))
                d.line([(x1,y1),(x2,y2)], fill=(102,217,255), width=2)
        elif self.state == "thinking":
            for i in range(4):
                a2 = math.radians(self.angle*4 + i*90)
                tx = int(cx + fw + 24 + math.cos(a2)*16)
                ty = int(cy - 42  + math.sin(a2)*16)
                d.ellipse([tx-4, ty-4, tx+4, ty+4], fill=(0, 102, 204))

        # ── HAIR — long, voluminous, puffy ───────────────────────────────

        # Outer volume mass (widest at ear level, flows to canvas bottom)
        d.polygon([
            (cx-50, cy-fh-14),   (cx-fw-42, cy-fh+8),
            (cx-fw-100, cy-fh+52), (cx-fw-126, cy-12),
            (cx-fw-120, cy+62),  (cx-fw-108, cy+135),
            (cx-fw-90, cy+205),  (cx-fw-68, cy+278),
            (cx-fw-42, 392),     (cx-fw+8,  400),
            (cx-22,    400),     (cx-16, cy+fh+48),
            (cx-fw+14, cy+fh+15),
        ], fill=HAIR_DARK, outline=HAIR_EDGE)
        d.polygon([
            (cx+50, cy-fh-14),   (cx+fw+42, cy-fh+8),
            (cx+fw+100, cy-fh+52), (cx+fw+126, cy-12),
            (cx+fw+120, cy+62),  (cx+fw+108, cy+135),
            (cx+fw+90, cy+205),  (cx+fw+68, cy+278),
            (cx+fw+42, 392),     (cx+fw-8,  400),
            (cx+22,    400),     (cx+16, cy+fh+48),
            (cx+fw-14, cy+fh+15),
        ], fill=HAIR_DARK, outline=HAIR_EDGE)

        # Crown arc
        d.pieslice([cx-fw-22, cy-fh-72, cx+fw+22, cy-fh+26],
                   start=0, end=180, fill=HAIR_DARK, outline=HAIR_EDGE)

        # Inner layer (lighter — layered volume depth)
        d.polygon([
            (cx-44, cy-fh-8),    (cx-fw-24, cy-fh+18),
            (cx-fw-72, cy-fh+65), (cx-fw-92, cy+5),
            (cx-fw-84, cy+82),   (cx-fw-70, cy+158),
            (cx-fw-52, cy+240),  (cx-fw-30, 388),
            (cx-22,    400),     (cx-16, cy+fh+48),
            (cx-fw+12, cy+fh+14),
        ], fill=HAIR_MID, outline=HAIR_STRAND)
        d.polygon([
            (cx+44, cy-fh-8),    (cx+fw+24, cy-fh+18),
            (cx+fw+72, cy-fh+65), (cx+fw+92, cy+5),
            (cx+fw+84, cy+82),   (cx+fw+70, cy+158),
            (cx+fw+52, cy+240),  (cx+fw+30, 388),
            (cx+22,    400),     (cx+16, cy+fh+48),
            (cx+fw-12, cy+fh+14),
        ], fill=HAIR_MID, outline=HAIR_STRAND)

        # Bangs sweeping across forehead
        for bx, bl in [(-46, 2), (-30, 6), (-14, 10), (0, 12), (14, 10), (30, 6), (46, 2)]:
            d.arc([cx+bx-20, cy-fh-6+bl, cx+bx+20, cy-fh+22+bl],
                  start=195, end=345, fill=HAIR_MID, width=3)

        # Energy strand highlights
        for sx, sy, ex2, ey2, ex3, ey3 in [
            (cx-58, cy-fh+5,  cx-fw-34, cy+fh+10, cx-fw-58, cy+215),
            (cx-46, cy-fh+1,  cx-fw-22, cy+fh-2,  cx-fw-44, cy+200),
            (cx-36, cy-fh-4,  cx-fw-8,  cy+fh-13, cx-fw-26, cy+178),
            (cx-68, cy-fh+12, cx-fw-50, cy+108,   cx-fw-78, cy+272),
            (cx-80, cy-fh+20, cx-fw-65, cy+128,   cx-fw-96, cy+285),
        ]:
            d.line([(sx, sy), (ex2, ey2), (ex3, ey3)], fill=HAIR_HI, width=1)
        for sx, sy, ex2, ey2, ex3, ey3 in [
            (cx+58, cy-fh+5,  cx+fw+34, cy+fh+10, cx+fw+58, cy+215),
            (cx+46, cy-fh+1,  cx+fw+22, cy+fh-2,  cx+fw+44, cy+200),
            (cx+36, cy-fh-4,  cx+fw+8,  cy+fh-13, cx+fw+26, cy+178),
            (cx+68, cy-fh+12, cx+fw+50, cy+108,   cx+fw+78, cy+272),
            (cx+80, cy-fh+20, cx+fw+65, cy+128,   cx+fw+96, cy+285),
        ]:
            d.line([(sx, sy), (ex2, ey2), (ex3, ey3)], fill=HAIR_HI, width=1)

        # ── Body / neck ───────────────────────────────────────────────────
        d.rectangle([cx-16, cy+fh-6, cx+16, cy+fh+46],
                    fill=(1, 14, 32), outline=(0, 34, 68))
        d.polygon([
            (cx-16, cy+fh+42), (cx-102, cy+fh+92), (cx-162, cy+fh+210),
            (cx+162, cy+fh+210), (cx+102, cy+fh+92), (cx+16, cy+fh+42)],
            fill=(1, 9, 28), outline=(0, 61, 128))
        d.polygon([
            (cx-16, cy+fh+42), (cx, cy+fh+78), (cx+16, cy+fh+42)],
            fill=(1, 13, 34), outline=(0, 80, 160))

        # ── Face oval ─────────────────────────────────────────────────────
        d.ellipse([cx-fw-7, cy-fh-7, cx+fw+7, cy+fh+7],
                  outline=(0, 30, 66), width=2)
        d.ellipse([cx-fw, cy-fh, cx+fw, cy+fh],
                  fill=(1, 14, 32), outline=(0, 180, 255), width=2)

        # Subtle cheekbone definition
        for sign in (-1, 1):
            bx2 = cx + sign * (fw - 22)
            d.arc([bx2-22, cy+8, bx2+22, cy+36],
                  start=(215 if sign < 0 else 325),
                  end=(325 if sign < 0 else 430),
                  fill=(0, 55, 115), width=1)

        # Scan line
        scan_rel = int(self.angle * 2.5) % (fh * 2) - fh
        scan_y   = cy + scan_rel
        if cy - fh + 4 < scan_y < cy + fh - 4:
            d.line([(cx-fw+8, scan_y), (cx+fw-8, scan_y)], fill=(0, 30, 78))

        # ── Glow pass 2: tight feature glow ──────────────────────────────
        gl2 = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        g2  = ImageDraw.Draw(gl2)
        g2.ellipse([cx-fw, cy-fh, cx+fw, cy+fh],
                   outline=(0, 180, 255, 155), width=4)
        for ex in (cx-34, cx+34):
            g2.ellipse([ex-20, ey-16, ex+20, ey+16], fill=(0, 160, 240, 115))
        g2.ellipse([cx-mw-4, my-8, cx+mw+4, my+6], fill=(0, 100, 200, 55))
        if self.state == "speaking":
            oh = max(2, int(3 + self._lip_sync_amp * 24))
            g2.ellipse([cx-mw-2, my-oh-2, cx+mw+2, my+oh+2],
                       outline=(0, 180, 255, 160), width=3)
        gl2 = gl2.filter(ImageFilter.GaussianBlur(radius=6))
        img.alpha_composite(gl2)
        d = ImageDraw.Draw(img)

        # ── Eyebrows — arched, feminine ───────────────────────────────────
        br_y    = cy - 54
        br_lift = {"listening": -8, "thinking": 6, "speaking": -4}.get(self.state, 0)
        d.line([
            (cx-58, br_y+br_lift+9), (cx-44, br_y+br_lift+2),
            (cx-30, br_y+br_lift-3), (cx-18, br_y+br_lift+2),
        ], fill=(102, 217, 255), width=2)
        d.line([
            (cx+18, br_y+br_lift+2), (cx+30, br_y+br_lift-3),
            (cx+44, br_y+br_lift+2), (cx+58, br_y+br_lift+9),
        ], fill=(102, 217, 255), width=2)

        # ── Eyes — large almond with layered iris ─────────────────────────
        for ex in (cx-34, cx+34):
            open_ry = max(1, int(ery * (1.0 - bp)))

            d.ellipse([ex-erx, ey-open_ry, ex+erx, ey+open_ry],
                      fill=(1, 9, 32), outline=(0, 180, 255), width=2)

            if bp < 0.75:
                iry = min(open_ry - 1, 13)
                if iry > 0:
                    # Iris rings
                    d.ellipse([ex-16, ey-iry-1, ex+16, ey+iry+1],
                              outline=(0, 75, 175), width=1)
                    d.ellipse([ex-14, ey-iry+1, ex+14, ey+iry-1],
                              fill=(0, 45, 112), outline=(0, 125, 205), width=1)
                    # Iris spokes
                    for ia in range(0, 360, 40):
                        iax = math.cos(math.radians(ia)) * 9
                        iay = math.sin(math.radians(ia)) * min(9, iry-1)
                        d.line([(ex, ey), (ex+int(iax), ey+int(iay))],
                               fill=(0, 75, 155), width=1)
                    d.ellipse([ex-6, ey-min(6,iry), ex+6, ey+min(6,iry)],
                              fill=(0, 2, 8))
                    # Two catchlights = life
                    d.ellipse([ex-9, ey-iry+1, ex-3, ey-iry+6],
                              fill=(102, 217, 255))
                    d.ellipse([ex+3, ey-iry+4, ex+7,  ey-iry+8],
                              fill=(232, 244, 255))
                    d.ellipse([ex-7, ey-min(7,iry)+1, ex+7, ey+min(7,iry)-1],
                              outline=(0, 180, 255), width=1)

            if bp > 0.05:
                lid_h = max(1, int(ery * 2 * bp))
                d.ellipse([ex-erx, ey-ery, ex+erx, ey-ery+lid_h],
                          fill=(1, 14, 32))

            # Upper lash arc (top of eye)
            d.arc([ex-erx, ey-ery, ex+erx, ey+ery],
                  start=182, end=358, fill=(102, 217, 255), width=2)

            # Dramatic lash tips — longer, fanning at corners
            for lx_off in range(-erx+2, erx+1, 4):
                lx  = ex + lx_off
                ly  = ey - max(1, open_ry) - 1
                mid = abs(lx_off) / erx
                tip_len = int(7 - mid * 4)
                flick   = (-1 if lx_off < -erx//2 else (1 if lx_off > erx//2 else 0))
                d.line([(lx, ly), (lx + flick, ly - max(2, tip_len))],
                       fill=(102, 217, 255), width=1)

            # Lower lash and liner
            d.arc([ex-erx+4, ey-2, ex+erx-4, ey+10],
                  start=5, end=175, fill=(0, 26, 58), width=1)
            d.arc([ex-erx+3, ey-open_ry+3, ex+erx-3, ey+open_ry+5],
                  start=0, end=180, fill=(0, 55, 115), width=1)

        # ── Nose — delicate ───────────────────────────────────────────────
        d.line([(cx, ey+ery+6), (cx, ny-2)], fill=(0, 34, 85))
        d.arc([cx-17, ny-5, cx-2, ny+8],  start=0,   end=195, fill=(0, 42, 88), width=1)
        d.arc([cx+2,  ny-5, cx+17, ny+8], start=345, end=180, fill=(0, 42, 88), width=1)

        # ── Lips — full, beautiful ────────────────────────────────────────
        if self.state == "speaking":
            oh = max(2, int(3 + self._lip_sync_amp * 26))
            d.ellipse([cx-mw, my-oh, cx+mw, my+oh],
                      fill=(2, 6, 18), outline=(0, 180, 255), width=2)
            if oh > 8:
                d.arc([cx-mw+5, my-oh+1, cx+mw-5, my+3],
                      start=0, end=180, fill=(215, 235, 255))
            d.line([
                (cx-mw, my-oh+3), (cx-mw//2-3, my-oh-3),
                (cx-7,  my-oh-8), (cx,  my-oh-5),
                (cx+7,  my-oh-8), (cx+mw//2+3, my-oh-3),
                (cx+mw, my-oh+3),
            ], fill=(102, 217, 255), width=2)
            d.arc([cx-mw+2, my-oh//2, cx+mw-2, my+oh+4],
                  start=0, end=180, fill=(0, 136, 204), width=2)

        elif self.state == "listening":
            d.arc([cx-mw, my-15, cx+mw, my+7],
                  start=15, end=165, fill=(0, 180, 255), width=2)
            d.line([
                (cx-mw, my-8), (cx-mw//2-3, my-13), (cx-7, my-15),
                (cx, my-12), (cx+7, my-15), (cx+mw//2+3, my-13), (cx+mw, my-8)
            ], fill=(0, 136, 204), width=1)
            d.arc([cx-mw+4, my-5, cx+mw-4, my+7],
                  start=0, end=180, fill=(0, 80, 165), width=1)

        elif self.state == "thinking":
            d.line([
                (cx-mw+6, my+5), (cx-4, my+2), (cx+7, my-2), (cx+mw-5, my-8)
            ], fill=(0, 180, 255), width=2)
            d.line([
                (cx-mw+6, my+5), (cx-mw//2+2, my-2), (cx-4, my)
            ], fill=(0, 80, 160), width=1)

        else:  # idle — warm beautiful smile
            d.arc([cx-mw, my-15, cx+mw, my+9],
                  start=15, end=165, fill=(0, 180, 255), width=2)
            d.line([
                (cx-mw, my-8), (cx-mw//2-3, my-13), (cx-7, my-15),
                (cx, my-12), (cx+7, my-15), (cx+mw//2+3, my-13), (cx+mw, my-8)
            ], fill=(102, 217, 255), width=1)
            d.arc([cx-mw+3, my-5, cx+mw-3, my+9],
                  start=0, end=180, fill=(0, 105, 195), width=2)
            d.line([(cx-10, my+3), (cx+10, my+3)], fill=(0, 180, 255), width=1)

        # ── Particles ─────────────────────────────────────────────────────
        for i in range(10):
            a2  = math.radians(self.angle * 0.9 + i * 36)
            r   = 158 + (i * 17 % 36)
            px  = int(cx + math.cos(a2) * r)
            py  = int(cy + math.sin(a2) * r * 0.52)
            sz  = 2 if i % 2 == 0 else 1
            col = (0, 180, 255) if i % 3 == 0 else ((0, 102, 204) if i % 3 == 1 else (0, 26, 58))
            d.ellipse([px-sz, py-sz, px+sz, py+sz], fill=col)

        # ── Blit to canvas ────────────────────────────────────────────────
        photo = ImageTk.PhotoImage(img)
        self._tk_avatar_frame = photo
        c.create_image(0, 0, image=photo, anchor="nw")

        # Canvas text on top (Tkinter font rendering > PIL default)
        for i, txt in enumerate(["ID : ALIA-1", "VER: 2.0",
                                  f"MOD: {self.state.upper()}", "NET: ACTIVE"]):
            c.create_text(cx+fw+16, cy-36+i*14,
                          text=txt, font=("Courier", 7), fill=TEXT_DIM, anchor="w")
        for i, txt in enumerate(["NEURAL LINK", "EMOTION: ON", "VOICE: SYNC"]):
            c.create_text(cx-fw-16, cy-36+i*14,
                          text=txt, font=("Courier", 7), fill=TEXT_DIM, anchor="e")
        self._draw_hud_corners(c, cx, cy)

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
        speed = {"idle": 0.8, "listening": 2.0, "speaking": 1.5, "thinking": 2.5}
        self.angle = (self.angle + speed.get(self.state, 1.0)) % 360

        self.pulse += 0.05 * self.pulse_dir
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

        # Blink animation (avatar mode only)
        if self._avatar_mode:
            if self._blink_phase == "wait":
                self._blink_wait += 1
                if self._blink_wait >= self._blink_wait_max:
                    self._blink_phase = "closing"
                    self._blink_wait  = 0
            elif self._blink_phase == "closing":
                self._blink_progress = min(1.0, self._blink_progress + 0.2)
                if self._blink_progress >= 1.0:
                    self._blink_phase = "opening"
            elif self._blink_phase == "opening":
                self._blink_progress = max(0.0, self._blink_progress - 0.2)
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
        self.root.after(30, self._animate)   # ~33 fps

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
                self._last_text = text
                self.text_var.set(text)
        self.root.after(0, _update)

    def show_text(self, text):
        self.root.after(0, lambda: self.text_var.set(text))

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
        self._video_btn.config(fg=BRIGHT, text="[ VIDEO ON ]")
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
                self._video_label.config(image=photo)
                self._video_label.image = photo  # type: ignore[attr-defined]
        except Exception:
            pass
        self.root.after(66, self._refresh_video_frame)   # ~15 fps

    def _stop_video(self):
        from modules import vision
        self._video_active = False
        vision.stop_camera()
        self._video_btn.config(fg=GLOW, text="[ VIDEO ]")
        self.set_state("idle", "Camera off.")
        if self._video_win:
            self._video_win.destroy()
            self._video_win = None

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

"""GUI Module - Jarvis-like frontend for Alia AI"""

import tkinter as tk
import math
import threading

# Color palette
BG       = "#04040f"
RING1    = "#003d80"
RING2    = "#0066cc"
GLOW     = "#00b4ff"
BRIGHT   = "#66d9ff"
DIM      = "#001a3a"
WHITE    = "#e8f4ff"
TEXT_DIM = "#4488aa"


class AliaGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Alia AI")
        self.root.configure(bg=BG)
        self.root.geometry("820x640")
        self.root.resizable(False, False)

        self.state  = "idle"
        self.angle  = 0.0
        self.pulse  = 0.0
        self.pulse_dir = 1
        self._last_text = ""
        self._video_active = False
        self._video_win = None

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

        # ── Canvas (logo area) ────────────────────────────────────────────
        self.canvas = tk.Canvas(self.root, width=820, height=400,
                                bg=BG, highlightthickness=0)
        self.canvas.pack()

        # ── Divider line ──────────────────────────────────────────────────
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

    # ------------------------------------------------------------------ #
    #  Drawing
    # ------------------------------------------------------------------ #
    def _draw(self):
        c  = self.canvas
        cx, cy = 410, 200
        c.delete("all")

        self._draw_grid(c)
        self._draw_hud_corners(c, cx, cy)

        p = self.pulse

        # ── Outermost faint ring ──────────────────────────────────────────
        self._arc_ring(c, cx, cy, 160 + p*4, self.angle,        12, DIM,   1)

        # ── Outer rotating ring ───────────────────────────────────────────
        self._arc_ring(c, cx, cy, 140,       -self.angle*0.7,   8,  RING1, 2)

        # ── Mid ring ─────────────────────────────────────────────────────
        self._arc_ring(c, cx, cy, 115,        self.angle*1.3,   6,  RING2, 2)

        # ── Inner fast ring ───────────────────────────────────────────────
        self._arc_ring(c, cx, cy, 90,        -self.angle*2,     4,  GLOW,  2)

        # ── State-specific outer effect ───────────────────────────────────
        if self.state == "listening":
            for i in range(20):
                a = math.radians(i * 18 + self.angle * 2)
                h = 10 + (math.sin(self.angle * 0.15 + i * 1.2) ** 2) * 28
                x1 = cx + math.cos(a) * 152
                y1 = cy + math.sin(a) * 152
                x2 = cx + math.cos(a) * (152 + h)
                y2 = cy + math.sin(a) * (152 + h)
                c.create_line(x1, y1, x2, y2, fill=BRIGHT, width=2)

        elif self.state == "speaking":
            for i in range(4):
                r = 158 + i * 14 + p * 8
                alpha = max(1, 3 - i)
                c.create_oval(cx-r, cy-r, cx+r, cy+r,
                              outline=GLOW, width=alpha)

        elif self.state == "thinking":
            # Spinning dashes
            for i in range(6):
                a = math.radians(self.angle * 3 + i * 60)
                x1 = cx + math.cos(a) * 150
                y1 = cy + math.sin(a) * 150
                x2 = cx + math.cos(a) * 165
                y2 = cy + math.sin(a) * 165
                c.create_line(x1, y1, x2, y2, fill=BRIGHT, width=3)

        # ── Static outer border ───────────────────────────────────────────
        c.create_oval(cx-168, cy-168, cx+168, cy+168, outline=DIM, width=1)

        # ── Inner filled circle ───────────────────────────────────────────
        ir = 70 + p * 3
        c.create_oval(cx-ir, cy-ir, cx+ir, cy+ir,
                      fill="#010118", outline=GLOW, width=2)

        # ── Orbiting dots ─────────────────────────────────────────────────
        for i in range(3):
            a = math.radians(self.angle * 2 + i * 120)
            gx = cx + math.cos(a) * 40
            gy = cy + math.sin(a) * 40
            c.create_oval(gx-4, gy-4, gx+4, gy+4, fill=GLOW, outline="")

        # ── Center cross-hair lines ───────────────────────────────────────
        c.create_line(cx-55, cy, cx-25, cy, fill=DIM, width=1)
        c.create_line(cx+25, cy, cx+55, cy, fill=DIM, width=1)
        c.create_line(cx, cy-55, cx, cy-25, fill=DIM, width=1)
        c.create_line(cx, cy+25, cx, cy+55, fill=DIM, width=1)

        # ── ALIA text ─────────────────────────────────────────────────────
        c.create_text(cx, cy - 12, text="ALIA",
                      font=("Courier", 24, "bold"), fill=BRIGHT)
        c.create_text(cx, cy + 14, text="A . I",
                      font=("Courier", 9), fill=TEXT_DIM)

    def _draw_grid(self, c):
        """Subtle HUD grid background"""
        for x in range(0, 820, 40):
            c.create_line(x, 0, x, 400, fill="#0a0a1a", width=1)
        for y in range(0, 400, 40):
            c.create_line(0, y, 820, y, fill="#0a0a1a", width=1)

    def _draw_hud_corners(self, c, cx, cy):
        """Corner bracket decorations"""
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

        # Blink status dot
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

        # Floating preview window
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
                self._video_label.image = photo  # type: ignore[attr-defined]  # keep reference
        except Exception:
            pass
        self.root.after(66, self._refresh_video_frame)  # ~15 fps

    def _stop_video(self):
        from modules import vision
        self._video_active = False
        vision.stop_camera()
        self._video_btn.config(fg=GLOW, text="[ VIDEO ]")
        self.set_state("idle", "Camera off.")
        if self._video_win:
            self._video_win.destroy()
            self._video_win = None

    def run(self):
        self.root.mainloop()

#!/usr/bin/env python3
"""
HydroPi terminal dashboard.
- Refreshes every 5 seconds.
- Every 2 minutes runs a plasma wave screensaver (OLED burn-in prevention).
- Press any key to skip the screensaver.
- Press q to quit.
"""

import curses
import json
import math
import os
import time
import socket
import psutil
from datetime import datetime
from pathlib import Path

BASE_DIR   = Path(__file__).resolve().parent.parent
RESULTS_FILE = BASE_DIR / "tilt_results.json"
QUEUE_FILE   = BASE_DIR / "offline_queue.json"
SENT_FILE    = BASE_DIR / "last_sent_time.json"

REFRESH_S          = 5
SCREENSAVER_AFTER  = 120   # seconds between screensaver runs
SCREENSAVER_FPS    = 15
BOTTOM_H = 7
HYDRO_H  = 6
MIN_HYDRO_W = 22
GRAD = " ░▒▓█"

# ── Data ──────────────────────────────────────────────────────────────────────

def load_json(path):
    try:
        with open(path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None

def file_mtime(path):
    try:
        return os.path.getmtime(path)
    except OSError:
        return None

def pi_stats():
    try:
        with open("/sys/class/thermal/thermal_zone0/temp") as f:
            temp = round(int(f.read().strip()) / 1000.0, 1)
    except OSError:
        temp = 0.0
    return {
        "hostname": socket.gethostname(),
        "cpu":      psutil.cpu_percent(interval=0.2),
        "mem":      round(psutil.virtual_memory().percent, 1),
        "temp":     temp,
        "uptime":   int(time.time() - psutil.boot_time()),
    }

# ── Formatting ────────────────────────────────────────────────────────────────

def fmt_uptime(s):
    d, s = divmod(s, 86400)
    h, s = divmod(s, 3600)
    m    = s // 60
    if d: return f"{d}d {h}h"
    if h: return f"{h}h {m}m"
    return f"{m}m"

def fmt_ago(ts):
    if ts is None: return "never"
    s = int(time.time() - ts)
    if s < 0:  return "just now"
    if s < 60: return f"{s}s ago"
    m = s // 60
    if m < 60: return f"{m}m ago"
    h = m // 60
    if h < 24: return f"{h}h ago"
    return f"{h // 24}d ago"

# ── Drawing ───────────────────────────────────────────────────────────────────

def draw_box(w, y, x, h, bw, title=""):
    try:
        w.addch(y,     x,      curses.ACS_ULCORNER)
        w.addch(y,     x+bw-1, curses.ACS_URCORNER)
        w.addch(y+h-1, x,      curses.ACS_LLCORNER)
        w.addch(y+h-1, x+bw-1, curses.ACS_LRCORNER)
        for i in range(1, bw-1):
            w.addch(y,     x+i, curses.ACS_HLINE)
            w.addch(y+h-1, x+i, curses.ACS_HLINE)
        for i in range(1, h-1):
            w.addch(y+i, x,      curses.ACS_VLINE)
            w.addch(y+i, x+bw-1, curses.ACS_VLINE)
        if title:
            label = f" {title} "[:bw-4]
            w.addstr(y, x+2, label, curses.A_BOLD)
    except curses.error:
        pass

def put(w, y, x, text, max_w, attr=0):
    try:
        if max_w > 0:
            w.addstr(y, x, str(text)[:max_w], attr)
    except curses.error:
        pass

def draw_hydro(w, y, x, h, bw, device):
    iw = bw - 4
    draw_box(w, y, x, h, bw, device.get("color", "?"))
    g = device.get("avg_gravity")
    t = device.get("avg_temp_c")
    m = device.get("_mtime")
    if g is not None: put(w, y+1, x+2, f"SG    {g:.3f}", iw, curses.A_BOLD)
    if t is not None: put(w, y+2, x+2, f"Temp  {t:.1f}\u00b0C", iw)
    put(w, y+3, x+2, fmt_ago(m), iw, curses.A_DIM)

def draw_pi(w, y, x, h, bw, s):
    iw = bw - 4
    draw_box(w, y, x, h, bw, s["hostname"])
    put(w, y+1, x+2, f"CPU   {s['cpu']:5.1f}%",         iw)
    put(w, y+2, x+2, f"Mem   {s['mem']:5.1f}%",         iw)
    put(w, y+3, x+2, f"Temp  {s['temp']:5.1f}\u00b0C",  iw)
    put(w, y+4, x+2, f"Up    {fmt_uptime(s['uptime'])}", iw)

def draw_posting(w, y, x, h, bw, queue, sent):
    iw = bw - 4
    q  = len(queue) if isinstance(queue, list) else 0
    if q > 0:
        draw_box(w, y, x, h, bw, "Offline Queue")
        put(w, y+1, x+2, f"{q} reading(s) queued", iw,
            curses.A_BOLD | curses.color_pair(2))
        colors = ", ".join(sorted({r.get("color","?") for r in queue}))
        oldest = min((r.get("recordedAt",0)/1000 for r in queue), default=None)
        put(w, y+2, x+2, f"Colors: {colors}",    iw)
        put(w, y+3, x+2, f"Oldest: {fmt_ago(oldest)}", iw)
    else:
        draw_box(w, y, x, h, bw, "Last Post")
        if sent and "last_sent_time" in sent:
            try:
                ts = datetime.fromisoformat(sent["last_sent_time"])
                put(w, y+1, x+2, fmt_ago(ts.timestamp()), iw, curses.color_pair(1))
                put(w, y+2, x+2, ts.strftime("%Y-%m-%d  %H:%M"), iw, curses.A_DIM)
            except (ValueError, AttributeError):
                put(w, y+1, x+2, "unknown", iw)
        else:
            put(w, y+1, x+2, "No posts yet", iw)
        put(w, y+3, x+2, "Queue: empty", iw, curses.A_DIM)

# ── Screensaver ───────────────────────────────────────────────────────────────

def screensaver(stdscr):
    """Plasma wave across all pixels. Any key returns to dashboard."""
    curses.curs_set(0)
    stdscr.nodelay(True)
    max_h, max_w = stdscr.getmaxyx()

    # Build palette: cycle through available color pairs
    PAIRS = [1, 2, 3, 4, 5]

    t = 0.0
    frame_time = 1.0 / SCREENSAVER_FPS

    while True:
        k = stdscr.getch()
        if k != -1:
            return

        t0 = time.time()
        stdscr.erase()

        for y in range(max_h - 1):
            for x in range(max_w - 1):
                # Plasma: sum of overlapping sine waves
                v = (math.sin(x * 0.12 + t)
                   + math.sin(y * 0.18 + t * 0.8)
                   + math.sin((x + y) * 0.10 + t * 0.6)
                   + math.sin(math.sqrt(x*x + y*y) * 0.09 + t)) / 4.0
                # v in [-1, 1] → [0, 1]
                norm = (v + 1.0) / 2.0
                char = GRAD[int(norm * (len(GRAD) - 1))]
                pair = PAIRS[int(norm * (len(PAIRS) - 1))]
                try:
                    stdscr.addch(y, x, char, curses.color_pair(pair))
                except curses.error:
                    pass

        stdscr.refresh()
        t += 0.12

        elapsed = time.time() - t0
        sleep   = frame_time - elapsed
        if sleep > 0:
            time.sleep(sleep)

# ── Main loop ─────────────────────────────────────────────────────────────────

def draw_dashboard(stdscr):
    stdscr.erase()
    max_h, max_w = stdscr.getmaxyx()

    results  = load_json(RESULTS_FILE) or {}
    queue    = load_json(QUEUE_FILE)   or []
    sent     = load_json(SENT_FILE)
    stats    = pi_stats()
    mtime    = file_mtime(RESULTS_FILE)

    devices = []
    if isinstance(results, dict):
        for uuid, data in results.items():
            if isinstance(data, dict):
                d = dict(data)
                d["_mtime"] = mtime
                if mtime and (time.time() - mtime) < 86400:
                    devices.append(d)

    cols   = max(1, max_w // (MIN_HYDRO_W + 1))
    hyd_w  = max_w // cols
    half_w = max_w // 2
    by     = max_h - BOTTOM_H

    # Header
    now_str = datetime.now().strftime("%H:%M:%S")
    put(stdscr, 0, 0, " HydroPi", max_w, curses.A_BOLD | curses.color_pair(3))
    put(stdscr, 0, max_w - 9, now_str, 9, curses.A_DIM)

    # Hydro boxes
    if devices:
        for i, dev in enumerate(devices):
            col = i % cols
            row = i // cols
            bx  = col * hyd_w
            dy  = 1 + row * (HYDRO_H + 1)
            if dy + HYDRO_H >= by:
                break
            draw_hydro(stdscr, dy, bx, HYDRO_H, hyd_w, dev)
    else:
        msg = "No Tilt readings in the last 24h"
        put(stdscr, 1 + (by - 1) // 2, (max_w - len(msg)) // 2, msg, max_w, curses.A_DIM)

    # Bottom row
    draw_pi     (stdscr, by, 0,      BOTTOM_H, half_w,         stats)
    draw_posting(stdscr, by, half_w, BOTTOM_H, max_w - half_w, queue, sent)

    put(stdscr, max_h-1, max_w - 12, " q to quit ", 12, curses.A_DIM)
    stdscr.refresh()


def main(stdscr):
    curses.curs_set(0)
    stdscr.nodelay(True)
    stdscr.timeout(REFRESH_S * 1000)

    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_GREEN,   -1)
    curses.init_pair(2, curses.COLOR_YELLOW,  -1)
    curses.init_pair(3, curses.COLOR_CYAN,    -1)
    curses.init_pair(4, curses.COLOR_MAGENTA, -1)
    curses.init_pair(5, curses.COLOR_BLUE,    -1)

    last_screensaver = time.time()

    while True:
        # Screensaver check
        if time.time() - last_screensaver >= SCREENSAVER_AFTER:
            screensaver(stdscr)
            last_screensaver = time.time()
            stdscr.timeout(REFRESH_S * 1000)
            stdscr.nodelay(True)
            curses.curs_set(0)

        key = stdscr.getch()
        if key == ord('q'):
            break
        if key != -1:
            last_screensaver = time.time()  # reset on any activity

        draw_dashboard(stdscr)


if __name__ == "__main__":
    curses.wrapper(main)

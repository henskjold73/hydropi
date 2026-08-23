#!/usr/bin/env python3
"""
HydroPi terminal dashboard.
Shows hydrometer readings, Pi stats, and posting status.
Reads local JSON files — no network required.

Press q to quit.
"""

import curses
import json
import os
import time
import socket
import psutil
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
RESULTS_FILE = BASE_DIR / "tilt_results.json"
QUEUE_FILE   = BASE_DIR / "offline_queue.json"
SENT_FILE    = BASE_DIR / "last_sent_time.json"

REFRESH_MS   = 5000
DAY_S        = 86400
BOTTOM_H     = 7   # height of bottom row
HYDRO_H      = 6   # height of each hydrometer box
MIN_HYDRO_W  = 22  # minimum width of a hydrometer box

# ── Data loading ──────────────────────────────────────────────────────────────

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
        "hostname":    socket.gethostname(),
        "cpu":         psutil.cpu_percent(interval=0.2),
        "mem":         round(psutil.virtual_memory().percent, 1),
        "temp":        temp,
        "uptime":      int(time.time() - psutil.boot_time()),
    }

# ── Formatting ────────────────────────────────────────────────────────────────

def fmt_uptime(s):
    d, s = divmod(s, 86400)
    h, s = divmod(s, 3600)
    m     = s // 60
    if d:  return f"{d}d {h}h"
    if h:  return f"{h}h {m}m"
    return f"{m}m"

def fmt_ago(ts):
    """ts is a unix timestamp (seconds)."""
    if ts is None:
        return "never"
    s = int(time.time() - ts)
    if s < 0:    return "just now"
    if s < 60:   return f"{s}s ago"
    m = s // 60
    if m < 60:   return f"{m}m ago"
    h = m // 60
    if h < 24:   return f"{h}h ago"
    return f"{h // 24}d ago"

# ── Drawing helpers ───────────────────────────────────────────────────────────

def box(w, y, x, h, bw, title=""):
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

# ── Box renderers ─────────────────────────────────────────────────────────────

def draw_hydro(w, y, x, h, bw, device):
    color   = device.get("color", "?")
    gravity = device.get("avg_gravity")
    temp    = device.get("avg_temp_c")
    mtime   = device.get("_mtime")
    iw      = bw - 4

    box(w, y, x, h, bw, color)
    if gravity is not None:
        put(w, y+1, x+2, f"SG    {gravity:.3f}", iw, curses.A_BOLD)
    if temp is not None:
        put(w, y+2, x+2, f"Temp  {temp:.1f}\u00b0C", iw)
    put(w, y+3, x+2, fmt_ago(mtime), iw, curses.A_DIM)

def draw_pi(w, y, x, h, bw, stats):
    iw = bw - 4
    box(w, y, x, h, bw, stats["hostname"])
    put(w, y+1, x+2, f"CPU   {stats['cpu']:5.1f}%",          iw)
    put(w, y+2, x+2, f"Mem   {stats['mem']:5.1f}%",          iw)
    put(w, y+3, x+2, f"Temp  {stats['temp']:5.1f}\u00b0C",   iw)
    put(w, y+4, x+2, f"Up    {fmt_uptime(stats['uptime'])}",  iw)

def draw_posting(w, y, x, h, bw, queue, sent_data):
    iw = bw - 4
    q_size = len(queue) if isinstance(queue, list) else 0

    if q_size > 0:
        box(w, y, x, h, bw, "Offline Queue")
        put(w, y+1, x+2, f"{q_size} reading(s) queued", iw, curses.A_BOLD | curses.color_pair(2))
        if isinstance(queue, list) and queue:
            colors  = ", ".join(sorted({r.get("color","?") for r in queue}))
            oldest  = min((r.get("recordedAt", 0) / 1000 for r in queue), default=None)
            put(w, y+2, x+2, f"Colors: {colors}",       iw)
            put(w, y+3, x+2, f"Oldest: {fmt_ago(oldest)}", iw)
    else:
        box(w, y, x, h, bw, "Last Post")
        if sent_data and "last_sent_time" in sent_data:
            try:
                ts = datetime.fromisoformat(sent_data["last_sent_time"])
                put(w, y+1, x+2, fmt_ago(ts.timestamp()),          iw, curses.color_pair(1))
                put(w, y+2, x+2, ts.strftime("%Y-%m-%d  %H:%M"),   iw, curses.A_DIM)
            except (ValueError, AttributeError):
                put(w, y+1, x+2, "unknown", iw)
        else:
            put(w, y+1, x+2, "No posts yet", iw)
        put(w, y+3, x+2, "Queue: empty", iw, curses.A_DIM)

# ── Main loop ─────────────────────────────────────────────────────────────────

def main(stdscr):
    curses.curs_set(0)
    stdscr.nodelay(True)
    stdscr.timeout(REFRESH_MS)

    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_GREEN,  -1)
    curses.init_pair(2, curses.COLOR_YELLOW, -1)
    curses.init_pair(3, curses.COLOR_CYAN,   -1)

    while True:
        if stdscr.getch() == ord('q'):
            break

        stdscr.erase()
        max_h, max_w = stdscr.getmaxyx()

        # ── Load data ─────────────────────────────────────────────────────────
        results   = load_json(RESULTS_FILE) or {}
        queue     = load_json(QUEUE_FILE)   or []
        sent_data = load_json(SENT_FILE)
        stats     = pi_stats()
        mtime     = file_mtime(RESULTS_FILE)

        # Build device list: filter readings seen within last 24h
        devices = []
        if isinstance(results, dict):
            for uuid, data in results.items():
                if isinstance(data, dict):
                    data = dict(data)
                    data["_mtime"] = mtime
                    if mtime and (time.time() - mtime) < DAY_S:
                        devices.append(data)

        # ── Layout ────────────────────────────────────────────────────────────
        top_h   = max_h - BOTTOM_H - 1
        cols    = max(1, max_w // (MIN_HYDRO_W + 1))
        hydro_w = (max_w) // cols

        # Header
        now_str = datetime.now().strftime("%H:%M:%S")
        title   = " HydroPi"
        put(stdscr, 0, 0,          title,   max_w, curses.A_BOLD | curses.color_pair(3))
        put(stdscr, 0, max_w - 9,  now_str, 9,     curses.A_DIM)

        # Hydrometer boxes
        if devices:
            for i, device in enumerate(devices):
                col = i % cols
                row = i // cols
                bx  = col * hydro_w
                by  = 1 + row * (HYDRO_H + 1)
                if by + HYDRO_H >= max_h - BOTTOM_H:
                    break
                draw_hydro(stdscr, by, bx, HYDRO_H, hydro_w, device)
        else:
            msg = "No Tilt readings in the last 24h"
            put(stdscr, 1 + top_h // 2, (max_w - len(msg)) // 2, msg, max_w, curses.A_DIM)

        # Bottom row: Pi stats | Posting info
        by      = max_h - BOTTOM_H
        half_w  = max_w // 2
        draw_pi     (stdscr, by, 0,       BOTTOM_H, half_w,          stats)
        draw_posting(stdscr, by, half_w,  BOTTOM_H, max_w - half_w,  queue, sent_data)

        # Footer hint
        put(stdscr, max_h-1, max_w - 12, " q to quit ", 12, curses.A_DIM)

        stdscr.refresh()


if __name__ == "__main__":
    curses.wrapper(main)

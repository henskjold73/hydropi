#!/usr/bin/env python3
"""
HydroPi terminal dashboard — big digit edition.
- Refreshes every 5 seconds.
- Every 5 minutes runs a 15-second plasma wave screensaver.
- Press any key to skip screensaver. Press q to quit.
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

BASE_DIR     = Path(__file__).resolve().parent.parent
RESULTS_FILE = BASE_DIR / "tilt_results.json"
QUEUE_FILE   = BASE_DIR / "offline_queue.json"
SENT_FILE    = BASE_DIR / "last_sent_time.json"

REFRESH_S         = 5
SCREENSAVER_AFTER    = 300   # seconds between screensaver runs
SCREENSAVER_DURATION = 15    # seconds the screensaver runs before returning
SCREENSAVER_FPS   = 15
BOTTOM_H          = 7
GRAD              = " ░▒▓█"

# Color pair numbers
CP_GREEN  = 1
CP_YELLOW = 2
CP_CYAN   = 3
CP_MAGENTA= 4
CP_BLUE   = 5
CP_RED    = 6
CP_BLACK  = 7   # black fg on white bg — visible on dark terminals

# Tilt color → (pair, extra_attr)
# Bold red reads as orange on most terminals; bold magenta reads as pink.
TILT_COLOR_MAP = {
    'red':    (CP_RED,    0),
    'green':  (CP_GREEN,  0),
    'black':  (CP_BLACK,  0),
    'purple': (CP_MAGENTA,0),
    'orange': (CP_RED,    curses.A_BOLD),
    'blue':   (CP_BLUE,   0),
    'yellow': (CP_YELLOW, 0),
    'pink':   (CP_MAGENTA,curses.A_BOLD),
}

def tilt_attrs(color_name):
    """Return (pair, extra_attr) for a named Tilt colour."""
    return TILT_COLOR_MAP.get(color_name.lower(), (CP_CYAN, 0))

def temp_attr(temp_c):
    """Return color attr based on fermentation temperature range."""
    if temp_c is None:
        return curses.A_DIM
    if temp_c < 18:
        return curses.color_pair(CP_BLUE) | curses.A_BOLD
    if temp_c <= 22:
        return curses.color_pair(CP_GREEN) | curses.A_BOLD
    return curses.color_pair(CP_RED) | curses.A_BOLD

# ── Big digit font (5 rows × 4 cols each) ────────────────────────────────────

BIGFONT = {
    '0': ['▄██▄','█  █','█  █','█  █','▀██▀'],
    '1': [' ██ ','███ ',' ██ ',' ██ ','████'],
    '2': ['███▄','   █','▄██▀','█   ','████'],
    '3': ['███▄','   █',' ██▄','   █','███▀'],
    '4': ['█  █','█  █','████','   █','   █'],
    '5': ['████','█   ','███▄','   █','███▀'],
    '6': ['▄██▄','█   ','███▄','█  █','▀██▀'],
    '7': ['████','  █ ',' █  ',' █  ',' █  '],
    '8': ['▄██▄','█  █','▄██▄','█  █','▀██▀'],
    '9': ['▄██▄','█  █','▀███','   █','▄██▀'],
    '.': ['    ','    ','    ',' ▄  ',' ▀  '],
    '°': [' ▄  ','▐ ▌ ',' ▀  ','    ','    '],
    'C': ['▄██▄','█   ','█   ','█   ','▀██▀'],
    ' ': ['    ','    ','    ','    ','    '],
}
BIGFONT_H  = 5
BIGFONT_CW = 4   # char width including trailing space

def big_width(text):
    return sum(BIGFONT_CW for _ in text)

def draw_big(w, y, x, text, attr=0):
    """Render text in big block digits at (y, x)."""
    for row in range(BIGFONT_H):
        cx = x
        for ch in text:
            glyph = BIGFONT.get(ch, BIGFONT[' '])
            try:
                w.addstr(y + row, cx, glyph[row], attr)
            except curses.error:
                pass
            cx += BIGFONT_CW

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

def draw_box(w, y, x, h, bw, title="", color_attr=0):
    try:
        w.addch(y,     x,      curses.ACS_ULCORNER, color_attr)
        w.addch(y,     x+bw-1, curses.ACS_URCORNER, color_attr)
        w.addch(y+h-1, x,      curses.ACS_LLCORNER, color_attr)
        w.addch(y+h-1, x+bw-1, curses.ACS_LRCORNER, color_attr)
        for i in range(1, bw-1):
            w.addch(y,     x+i, curses.ACS_HLINE, color_attr)
            w.addch(y+h-1, x+i, curses.ACS_HLINE, color_attr)
        for i in range(1, h-1):
            w.addch(y+i, x,      curses.ACS_VLINE, color_attr)
            w.addch(y+i, x+bw-1, curses.ACS_VLINE, color_attr)
        if title:
            label = f" {title} "[:bw-4]
            w.addstr(y, x+2, label, curses.A_BOLD | color_attr)
    except curses.error:
        pass

def put(w, y, x, text, max_w, attr=0):
    try:
        if max_w > 0:
            w.addstr(y, x, str(text)[:max_w], attr)
    except curses.error:
        pass

def draw_hydro(w, y, x, h, bw, device):
    """Draw a Tilt hydrometer box with vertically centered big digits."""
    iw      = bw - 4
    color   = device.get("color", "?")
    gravity = device.get("avg_gravity")
    temp    = device.get("avg_temp_c")
    mtime   = device.get("_mtime")

    pair, extra = tilt_attrs(color)
    c_attr = curses.color_pair(pair) | extra

    draw_box(w, y, x, h, bw, color.upper(), color_attr=c_attr)

    # Interior rows: y+1 .. y+h-2 (h-2 usable rows)
    # Reserve: top label row (y+1), bottom info row (y+h-2)
    # Big digits go in the middle of what remains
    inner_h   = h - 2          # rows inside border
    label_row = y + 1
    info_row  = y + h - 2

    if gravity is not None:
        sg_str  = f"{gravity:.3f}"
        bw_text = big_width(sg_str)
        bx      = x + max(2, (bw - bw_text) // 2)

        # Vertically center the 5-row big digits in the space between label and info rows
        usable_start = label_row + 1
        usable_end   = info_row - 1
        usable_rows  = usable_end - usable_start
        digit_y      = usable_start + max(0, (usable_rows - BIGFONT_H) // 2)

        put(w, label_row, x+2, "Specific Gravity", iw, curses.A_DIM)
        draw_big(w, digit_y, bx, sg_str, curses.A_BOLD | c_attr)
    else:
        mid = y + h // 2
        put(w, mid, x+2, "No reading", iw, curses.A_DIM)

    # Temp (colored by range) + last seen age — two separate rows if space allows
    ago      = fmt_ago(mtime)
    temp_str = f"{temp:.1f}\u00b0C" if temp is not None else "--.-\u00b0C"
    t_attr   = temp_attr(temp)

    if h >= 13:
        # Enough room: temp on info_row-1, age on info_row
        put(w, info_row - 1, x+2, temp_str, iw, t_attr)
        put(w, info_row,     x+2, ago,       iw, curses.A_DIM)
    else:
        # Tight: temp left, age right, same line
        put(w, info_row, x+2, temp_str, iw, t_attr)
        put(w, info_row, x + bw - 2 - len(ago), ago, iw, curses.A_DIM)

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
        put(w, y+2, x+2, f"Colors: {colors}",       iw)
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
    curses.curs_set(0)
    stdscr.nodelay(True)
    max_h, max_w = stdscr.getmaxyx()
    PAIRS = [1, 2, 3, 4, 5]
    t = 0.0
    frame_time = 1.0 / SCREENSAVER_FPS
    end_time = time.time() + SCREENSAVER_DURATION
    while time.time() < end_time:
        if stdscr.getch() != -1:
            return
        t0 = time.time()
        stdscr.erase()
        for y in range(max_h - 1):
            for x in range(max_w - 1):
                v = (math.sin(x * 0.12 + t)
                   + math.sin(y * 0.18 + t * 0.8)
                   + math.sin((x + y) * 0.10 + t * 0.6)
                   + math.sin(math.sqrt(x*x + y*y) * 0.09 + t)) / 4.0
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
        if frame_time - elapsed > 0:
            time.sleep(frame_time - elapsed)

# ── Main ──────────────────────────────────────────────────────────────────────

GRID_ROWS = 2   # always 2 rows of Tilt boxes

def draw_dashboard(stdscr):
    stdscr.erase()
    max_h, max_w = stdscr.getmaxyx()

    results = load_json(RESULTS_FILE) or {}
    queue   = load_json(QUEUE_FILE)   or []
    sent    = load_json(SENT_FILE)
    stats   = pi_stats()
    mtime   = file_mtime(RESULTS_FILE)

    devices = []
    if isinstance(results, dict):
        for uuid, data in results.items():
            if isinstance(data, dict):
                d = dict(data)
                d["_mtime"] = mtime
                if mtime and (time.time() - mtime) < 86400:
                    devices.append(d)

    # Header row (1) + bottom panel (BOTTOM_H) + quit hint (1)
    header_h   = 1
    available_h = max_h - header_h - BOTTOM_H

    # Choose grid: 2, 3, or 4 columns; always GRID_ROWS rows
    if devices:
        cols = min(max(2, math.ceil(len(devices) / GRID_ROWS)), 4)
    else:
        cols = 2

    box_h = available_h // GRID_ROWS
    by    = header_h + GRID_ROWS * box_h   # where bottom panel starts

    # Header
    now_str = datetime.now().strftime("%H:%M:%S")
    put(stdscr, 0, 0, " HydroPi", max_w, curses.A_BOLD | curses.color_pair(3))
    put(stdscr, 0, max_w - 9, now_str, 9, curses.A_DIM)

    # Tilt boxes — 2-row grid filling the available space
    if devices:
        for i, dev in enumerate(devices):
            col = i % cols
            row = i // cols
            if row >= GRID_ROWS:
                break
            # Distribute width: last col gets any remainder pixels
            bx    = (max_w * col) // cols
            bx_end = (max_w * (col + 1)) // cols
            bw    = bx_end - bx
            dy    = header_h + row * box_h
            draw_hydro(stdscr, dy, bx, box_h, bw, dev)
    else:
        msg = "No Tilt readings in the last 24h"
        put(stdscr, header_h + available_h // 2, (max_w - len(msg)) // 2,
            msg, max_w, curses.A_DIM)

    half_w = max_w // 2
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
    curses.init_pair(CP_GREEN,   curses.COLOR_GREEN,   -1)
    curses.init_pair(CP_YELLOW,  curses.COLOR_YELLOW,  -1)
    curses.init_pair(CP_CYAN,    curses.COLOR_CYAN,    -1)
    curses.init_pair(CP_MAGENTA, curses.COLOR_MAGENTA, -1)
    curses.init_pair(CP_BLUE,    curses.COLOR_BLUE,    -1)
    curses.init_pair(CP_RED,     curses.COLOR_RED,     -1)
    curses.init_pair(CP_BLACK,   curses.COLOR_BLACK,   curses.COLOR_WHITE)

    last_screensaver = time.time()

    while True:
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
            last_screensaver = time.time()

        draw_dashboard(stdscr)


if __name__ == "__main__":
    curses.wrapper(main)

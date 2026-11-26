#!/usr/bin/env python3
"""The World in One Page -- Wednesday 25 November 2026.

Renders a broadsheet-style front page that summarises one day of world
news as a single 1024x1024 PNG.  Pure standard library: the picture is
drawn with a hand-made stroke font on a 4096x4096 canvas and reduced
with a 4x4 area average.  Output is deterministic.
"""

import math
import os
import struct
import zlib

# ---------------------------------------------------------------- output

OUT_PATH = os.environ.get("ENTRY_OUT") or "/output/entry.png"

SS = 4                      # supersampling factor
W = 1024 * SS               # internal canvas size
H = 1024 * SS

PAPER = (246, 243, 235)
INK = (26, 26, 31)
BODY = (48, 48, 54)
FAINT = (105, 102, 94)
RULE = (150, 146, 136)
RED = (176, 32, 30)
RED_SOFT = (198, 84, 70)
WHITE = (250, 248, 242)

buf = bytearray(W * H * 3)


def _fill_bg():
    row = bytes(PAPER) * W
    for y in range(H):
        buf[y * W * 3:(y + 1) * W * 3] = row


def px(x, y, color):
    if 0 <= x < W and 0 <= y < H:
        i = (y * W + x) * 3
        buf[i] = color[0]
        buf[i + 1] = color[1]
        buf[i + 2] = color[2]


def disc(cx, cy, r, color):
    r = int(math.ceil(r))
    rr = r * r
    for dy in range(-r, r + 1):
        dx = int(math.sqrt(rr - dy * dy))
        y = cy + dy
        if 0 <= y < H:
            base = y * W * 3
            for x in range(cx - dx, cx + dx + 1):
                if 0 <= x < W:
                    i = base + x * 3
                    buf[i] = color[0]
                    buf[i + 1] = color[1]
                    buf[i + 2] = color[2]


def line(x0, y0, x1, y1, r, color):
    """Thick line with round caps, drawn by stamping discs."""
    dist = math.hypot(x1 - x0, y1 - y0)
    steps = max(1, int(dist / max(1.0, r * 0.8)))
    for i in range(steps + 1):
        t = i / steps
        disc(int(x0 + (x1 - x0) * t), int(y0 + (y1 - y0) * t), r, color)


def rect(x, y, w, h, color):
    x = int(x)
    y = int(y)
    w = int(w)
    h = int(h)
    seg = bytes(color) * max(0, w)
    for yy in range(y, y + h):
        if 0 <= yy < H:
            i = (yy * W + x) * 3
            buf[i:i + w * 3] = seg


def frame(x, y, w, h, r, color):
    line(x, y, x + w, y, r, color)
    line(x, y + h, x + w, y + h, r, color)
    line(x, y, x, y + h, r, color)
    line(x + w, y, x + w, y + h, r, color)


def S(v):
    """Design units (1024 grid) -> internal pixels."""
    return v * SS


# ---------------------------------------------------------------- font
# Stroke glyphs on a 10-unit em: cap height 10, x-height 7, descender -3.
# Each entry: (advance, [stroke, ...]); a stroke is a list of (x, y).

GLYPHS = {
    'A': (8.8, [[(0, 0), (4, 10), (8, 0)], [(1.7, 3.8), (6.3, 3.8)]]),
    'B': (8.6, [[(0, 0), (0, 10)],
                [(0, 10), (4.2, 10), (5.8, 8.6), (4.6, 6.2), (0, 5.6)],
                [(0, 5.6), (4.8, 5.6), (6.4, 3.6), (5.2, 0.8), (0, 0)]]),
    'C': (8.6, [[(7.6, 8.2), (5.4, 10), (2.4, 9.6), (0.6, 6.8), (0.6, 3.2),
                 (2.4, 0.4), (5.4, 0), (7.6, 1.8)]]),
    'D': (8.8, [[(0, 0), (0, 10)],
                [(0, 10), (4.6, 10), (7.2, 7.6), (7.2, 2.4), (4.6, 0), (0, 0)]]),
    'E': (8.2, [[(7, 10), (0, 10), (0, 0), (7.4, 0)], [(0, 5.4), (5.6, 5.4)]]),
    'F': (7.8, [[(0, 0), (0, 10), (7.2, 10)], [(0, 5.4), (5.4, 5.4)]]),
    'G': (9.0, [[(7.6, 8.2), (5.4, 10), (2.4, 9.6), (0.6, 6.8), (0.6, 3.2),
                 (2.4, 0.4), (5.6, 0), (7.8, 1.6), (7.8, 4.6), (4.8, 4.6)]]),
    'H': (8.8, [[(0, 0), (0, 10)], [(7.6, 0), (7.6, 10)],
                [(0, 5.2), (7.6, 5.2)]]),
    'I': (4.6, [[(3.8, 0), (3.8, 10)], [(1.4, 10), (6.2, 10)],
                [(1.4, 0), (6.2, 0)]]),
    'J': (7.6, [[(6.8, 10), (6.8, 2.2), (5.2, 0.2), (2.6, 0), (0.8, 1.6)]]),
    'K': (8.8, [[(0, 0), (0, 10)], [(7.4, 10), (0.6, 4.6)],
                [(1.8, 5.6), (7.6, 0)]]),
    'L': (7.8, [[(0, 10), (0, 0), (7.2, 0)]]),
    'M': (9.8, [[(0, 0), (0, 10), (4, 3.6), (8, 10), (8, 0)]]),
    'N': (8.8, [[(0, 0), (0, 10), (7.6, 0), (7.6, 10)]]),
    'O': (9.0, [[(2.4, 0.4), (0.6, 2.6), (0.6, 7.4), (2.4, 9.6), (5.6, 9.6),
                 (7.4, 7.4), (7.4, 2.6), (5.6, 0.4), (2.4, 0.4)]]),
    'P': (8.4, [[(0, 0), (0, 10)],
                [(0, 10), (5, 10), (6.8, 8.2), (5.2, 5.4), (0, 5.4)]]),
    'Q': (9.0, [[(2.4, 0.4), (0.6, 2.6), (0.6, 7.4), (2.4, 9.6), (5.6, 9.6),
                 (7.4, 7.4), (7.4, 2.6), (5.6, 0.4), (2.4, 0.4)],
                [(5, 2.6), (8.2, -0.6)]]),
    'R': (8.6, [[(0, 0), (0, 10)],
                [(0, 10), (5, 10), (6.8, 8.2), (5.2, 5.4), (0, 5.4)],
                [(4.4, 5.4), (7.6, 0)]]),
    'S': (8.2, [[(7.2, 8.6), (5, 10), (2.2, 9.2), (1.8, 6.8), (3.4, 5.2),
                 (6, 3.6), (6.6, 1.6), (4.8, 0.2), (1.6, 0.6), (0.4, 1.8)]]),
    'T': (8.4, [[(0.4, 10), (7.6, 10)], [(4, 10), (4, 0)]]),
    'U': (8.8, [[(0, 10), (0, 2.6), (1.8, 0.4), (5.8, 0.4), (7.6, 2.6),
                 (7.6, 10)]]),
    'V': (8.8, [[(0, 10), (4, 0), (8, 10)]]),
    'W': (9.8, [[(0, 10), (1.8, 0), (4, 6.4), (6.2, 0), (8, 10)]]),
    'X': (8.6, [[(0, 0), (7.6, 10)], [(0, 10), (7.6, 0)]]),
    'Y': (8.6, [[(0, 10), (3.8, 5.2), (7.6, 10)], [(3.8, 5.2), (3.8, 0)]]),
    'Z': (8.4, [[(0.4, 10), (7.6, 10), (0.4, 0), (7.6, 0)]]),
    'a': (7.0, [[(6.4, 0), (6.4, 7)],
                [(6.4, 5.4), (4.6, 7), (2, 6.8), (0.6, 4.8), (0.8, 2),
                 (2.6, 0.2), (5, 0.4), (6.4, 1.8)]]),
    'b': (7.2, [[(0, 0), (0, 10)],
                [(0, 1.8), (1.8, 0.2), (4.6, 0.2), (6.2, 2), (6, 5),
                 (4.4, 6.8), (1.8, 6.6), (0, 5)]]),
    'c': (6.8, [[(6.2, 5.8), (4.4, 7), (2, 6.6), (0.8, 4.6), (0.8, 2.2),
                 (2.2, 0.4), (4.6, 0.2), (6.2, 1.4)]]),
    'd': (7.2, [[(6.4, 0), (6.4, 10)],
                [(6.4, 5.2), (4.8, 6.8), (2, 6.8), (0.6, 4.8), (0.8, 2),
                 (2.6, 0.2), (5, 0.4), (6.4, 1.8)]]),
    'e': (6.9, [[(0.8, 3.6), (6.2, 3.6), (5.8, 5.6), (4, 7), (1.8, 6.4),
                 (0.8, 4.2), (0.8, 2.2), (2.2, 0.4), (4.8, 0.2),
                 (6.2, 1.6)]]),
    'f': (5.6, [[(6.2, 9.6), (4.2, 10), (2.6, 8.6), (2.6, 0)],
                [(0.6, 6.8), (5, 6.8)]]),
    'g': (7.2, [[(6.4, 7), (6.4, -1.6), (5, -3), (2.4, -2.8), (0.8, -1.6)],
                [(6.4, 5.2), (4.8, 6.8), (2, 6.8), (0.6, 4.8), (0.8, 2),
                 (2.6, 0.2), (5, 0.4), (6.4, 1.8)]]),
    'h': (7.2, [[(0, 0), (0, 10)],
                [(0, 5), (2, 6.8), (4.8, 6.8), (6.2, 5), (6.2, 0)]]),
    'i': (3.4, [[(3, 0), (3, 7)]]),
    'j': (4.2, [[(3, 7), (3, -1.6), (1.8, -2.8), (0.4, -2.2)]]),
    'k': (7.0, [[(0, 0), (0, 10)], [(6, 7), (0.8, 3.2)], [(2, 4.2), (6.2, 0)]]),
    'l': (3.4, [[(2.6, 0), (2.6, 10)]]),
    'm': (11.6, [[(0, 0), (0, 7)],
                 [(0, 5.2), (1.8, 7), (4, 6.8), (5.4, 5.2), (5.4, 0)],
                 [(5.4, 5.2), (7, 7), (9.4, 6.8), (10.6, 5), (10.6, 0)]]),
    'n': (7.2, [[(0, 0), (0, 7)],
                [(0, 5.2), (2, 7), (4.8, 6.8), (6.2, 5), (6.2, 0)]]),
    'o': (7.2, [[(2, 0.4), (0.6, 2), (0.6, 5), (2, 6.8), (4.8, 6.8),
                 (6.2, 5), (6.2, 2), (4.8, 0.4), (2, 0.4)]]),
    'p': (7.2, [[(0, -3), (0, 7)],
                [(0, 1.8), (1.8, 0.2), (4.6, 0.2), (6.2, 2), (6, 5),
                 (4.4, 6.8), (1.8, 6.6), (0, 5)]]),
    'q': (7.2, [[(6.4, -3), (6.4, 7)],
                [(6.4, 5.2), (4.8, 6.8), (2, 6.8), (0.6, 4.8), (0.8, 2),
                 (2.6, 0.2), (5, 0.4), (6.4, 1.8)]]),
    'r': (5.2, [[(0, 0), (0, 7)], [(0, 4.6), (2.2, 6.8), (4.6, 6.6)]]),
    's': (6.4, [[(6, 6), (4.2, 7), (1.8, 6.4), (1.4, 4.8), (2.8, 3.6),
                 (5.2, 2.4), (5.6, 0.8), (3.8, 0), (1.2, 0.4), (0.4, 1.4)]]),
    't': (5.4, [[(2.8, 10), (2.8, 1.6), (4, 0.2), (5.6, 0.4)],
                [(0.6, 6.8), (5.2, 6.8)]]),
    'u': (7.2, [[(0, 7), (0, 2), (1.8, 0.2), (4.8, 0.2), (6.2, 1.8), (6.2, 0)],
                [(6.2, 7), (6.2, 0)]]),
    'v': (7.4, [[(0, 7), (3.2, 0), (6.4, 7)]]),
    'w': (10.4, [[(0, 7), (1.6, 0), (3.6, 4.6), (5.6, 0), (7.6, 7)]]),
    'x': (6.8, [[(0, 0), (6, 7)], [(0, 7), (6, 0)]]),
    'y': (7.4, [[(0, 7), (3.2, 0.6), (6.4, 7)], [(3.2, 0.6), (2.2, -2.6)]]),
    'z': (6.8, [[(0.4, 7), (6, 7), (0.4, 0), (6.2, 0)]]),
    '0': (7.6, [[(2, 0.4), (0.8, 2.6), (0.8, 7.4), (2, 9.6), (4.8, 9.6),
                 (6, 7.4), (6, 2.6), (4.8, 0.4), (2, 0.4)]]),
    '1': (7.0, [[(1.2, 7.6), (3.6, 10), (3.6, 0)], [(1.2, 0), (6, 0)]]),
    '2': (7.4, [[(0.8, 8.2), (2.4, 9.8), (5, 9.4), (5.8, 7.2), (0.8, 0),
                 (6.2, 0)]]),
    '3': (7.4, [[(0.8, 8.6), (2.6, 10), (5, 9.2), (4.6, 6.6), (2.4, 5.6)],
                [(2.4, 5.6), (5, 5.2), (6, 2.6), (4.4, 0.4), (1.6, 0.4),
                 (0.6, 1.6)]]),
    '4': (7.8, [[(4.6, 0), (4.6, 10), (0.6, 3.4), (7, 3.4)]]),
    '5': (7.4, [[(6, 10), (1, 10), (0.8, 6), (2.6, 6.8), (5.2, 6.2),
                 (6, 3.6), (4.6, 0.6), (1.8, 0.2), (0.6, 1.4)]]),
    '6': (7.4, [[(5.8, 9.4), (3.4, 7.6), (1.4, 4.6), (1.2, 2.2), (2.6, 0.4),
                 (4.8, 0.6), (6, 2.4), (5, 4.6), (2.8, 5), (1.4, 3.8)]]),
    '7': (7.4, [[(0.6, 10), (6.8, 10), (3.8, 0)]]),
    '8': (7.6, [[(3.4, 5.2), (1.6, 6.6), (2, 9.2), (3.6, 10), (5.4, 9.4),
                 (6, 7), (4.8, 5.4), (3.4, 5.2)],
                [(3.4, 5.2), (1.6, 4), (1.4, 1.6), (3, 0.2), (5.2, 0.2),
                 (6.4, 1.8), (6, 4.2), (4.8, 5.4)]]),
    '9': (7.4, [[(1.2, 0.6), (3.6, 2.4), (5.6, 5.4), (5.8, 7.8), (4.4, 9.6),
                 (2.2, 9.4), (1, 7.6), (2, 5.4), (4.2, 5), (5.6, 6.2)]]),
    ' ': (4.6, []),
    '.': (3.6, []),
    ',': (3.8, [[(3.2, 1.2), (2.4, -1.6)]]),
    ':': (3.6, []),
    ';': (3.8, [[(3.2, 1.2), (2.4, -1.6)]]),
    "'": (3.4, [[(3, 10), (2.5, 7.6)]]),
    '-': (5.6, [[(0.6, 3.6), (5, 3.6)]]),
    '\u2013': (7.4, [[(0.6, 3.6), (6.8, 3.6)]]),
    '\u2014': (10.4, [[(0.6, 3.6), (9.8, 3.6)]]),
    '/': (6.4, [[(0.6, -0.4), (5.8, 10.4)]]),
    '(': (5.4, [[(5.4, 10), (3, 7.6), (2, 5), (3, 2.4), (5.4, 0)]]),
    ')': (5.4, [[(0.6, 10), (3, 7.6), (4, 5), (3, 2.4), (0.6, 0)]]),
    '%': (11.0, [[(2, 6.6), (0.9, 7.6), (1, 9.2), (2.2, 10), (3.4, 9.4),
                  (3.6, 7.8), (2.8, 6.7), (2, 6.6)],
                 [(9.8, 10.4), (3, -0.4)],
                 [(7.6, 0.2), (6.5, 1.2), (6.6, 2.8), (7.8, 3.4), (9, 2.8),
                  (9.2, 1.2), (8.4, 0.3), (7.6, 0.2)]]),
    '+': (7.6, [[(3.4, 0.6), (3.4, 7.4)], [(0.4, 4), (6.4, 4)]]),
    '$': (8.2, [[(7.2, 8.6), (5, 10), (2.2, 9.2), (1.8, 6.8), (3.4, 5.2),
                 (6, 3.6), (6.6, 1.6), (4.8, 0.2), (1.6, 0.6), (0.4, 1.8)],
                [(4, 11), (4, -1)]]),
    '?': (7.2, [[(1, 8.2), (2.6, 9.8), (5.2, 9.6), (6, 7.6), (4.6, 5.6),
                 (3.6, 4.4), (3.6, 2.8)]]),
    '!': (3.8, [[(3.2, 10), (3.2, 3)]]),
    '"': (5.6, [[(1.4, 10), (1, 7.6)], [(4.4, 10), (4, 7.6)]]),
    '\u00b7': (3.4, []),
    '=': (7.6, [[(0.6, 6.6), (6.8, 6.6)], [(0.6, 2.8), (6.8, 2.8)]]),
    '*': (6.4, [[(3.2, 0.8), (3.2, 8.8)], [(0.8, 2.6), (5.6, 7)],
                [(5.6, 2.6), (0.8, 7)]]),
}

DOT_CHARS = {'.', ':', '\u00b7'}
SEMI_CHARS = {';'}


def text_width(s, cap, spacing=0.0):
    """Width in design units for string s at cap height `cap`."""
    scale = cap / 10.0
    total = 0.0
    for ch in s:
        adv = GLYPHS.get(ch, GLYPHS[' '])[0]
        total += adv * scale + spacing
    return total - (spacing if s else 0.0)


def draw_text(x, y_base, s, cap, weight, color, spacing=0.0, align='left'):
    """Draw s with baseline at y_base (design units). Returns end x."""
    if align != 'left':
        w = text_width(s, cap, spacing)
        if align == 'center':
            x -= w / 2.0
        elif align == 'right':
            x -= w
    scale = cap / 10.0
    r = S(weight) / 2.0
    cx = x
    for ch in s:
        adv, strokes = GLYPHS.get(ch, GLYPHS[' '])
        gx = S(cx)
        gy = S(y_base)
        if ch in DOT_CHARS:
            dy = 5.0 if ch == '\u00b7' else 0.7
            if ch == ':':
                disc(int(gx + 1.8 * scale * SS), int(gy - 6.8 * scale * SS),
                     r * 1.15, color)
            disc(int(gx + 1.8 * scale * SS), int(gy - dy * scale * SS),
                 r * 1.15, color)
        if ch in SEMI_CHARS:
            disc(int(gx + 1.9 * scale * SS), int(gy - 6.8 * scale * SS),
                 r * 1.15, color)
        if ch in ('i', 'j'):
            disc(int(gx + 3.0 * scale * SS), int(gy - 9.3 * scale * SS),
                 r * 1.15, color)
        if ch == '?':
            disc(int(gx + 3.6 * scale * SS), int(gy - 0.7 * scale * SS),
                 r * 1.15, color)
        if ch == '!':
            disc(int(gx + 3.2 * scale * SS), int(gy - 0.7 * scale * SS),
                 r * 1.15, color)
        for stroke in strokes:
            pts = [(gx + ux * scale * SS, gy - uy * scale * SS)
                   for (ux, uy) in stroke]
            for i in range(len(pts) - 1):
                line(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1],
                     r, color)
            if len(pts) == 1:
                disc(int(pts[0][0]), int(pts[0][1]), r, color)
        cx += adv * scale + spacing
    return cx


def wrap(s, cap, max_width, spacing=0.0):
    """Greedy word wrap; returns list of lines."""
    words = s.split()
    lines = []
    cur = ''
    for w_ in words:
        trial = (cur + ' ' + w_) if cur else w_
        if text_width(trial, cap, spacing) <= max_width or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w_
    if cur:
        lines.append(cur)
    return lines


def hline(x, y, w, weight, color):
    line(S(x), S(y), S(x + w), S(y), S(weight) / 2.0, color)


def vline(x, y, h, weight, color):
    line(S(x), S(y), S(x), S(y + h), S(weight) / 2.0, color)


# ---------------------------------------------------------------- content

CARDS = [
    dict(n=1, place='STRAIT OF HORMUZ', cat='ENERGY', tag='CLAIM',
         head='TANKERS BLAZE AFTER MINES IN THE STRAIT',
         body="Tehran's Revolutionary Guard says two oil tankers struck "
              "mines and caught fire after straying off the "
              "approved lane.",
         src='IRGC STATEMENT', pin=(56, 26)),
    dict(n=2, place='RAS TANURA, SAUDI ARABIA', cat='ENERGY', tag='CLAIM',
         head='HOUTHIS SAY REFINERY STRIKE SPARKED FIRE',
         body="The Yemeni group claims its strike set part of the Ras "
              "Tanura refinery alight; Riyadh has not confirmed it.",
         src='HOUTHI STATEMENT', pin=(49, 27)),
    dict(n=3, place='GAZA CITY', cat='CONFLICT', tag='REPORTED',
         head='AIRSTRIKE KILLS HAMAS SECURITY CHIEF AT HOME',
         body="An Israeli strike killed Mohammad Abuelouf, his wife "
              "and two children, in the day's deadliest "
              "single attack.",
         src='GAZA REPORTS', pin=(34, 31)),
    dict(n=4, place='SAMARA, RUSSIA', cat='CONFLICT', tag='REPORTED',
         head='DRONES SET TWO ROSNEFT REFINERIES ABLAZE',
         body="Ukrainian drones hit the Syzran and Kuibyshev plants "
              "before dawn, killing one; Moscow says 145 were downed.",
         src='RUSSIAN OFFICIALS', pin=(50, 53)),
    dict(n=5, place='GLOBAL MARKETS', cat='FINANCE', tag='ON RECORD',
         head='ASIA ROUTS AS DOW CLOSES ABOVE 50,000',
         body="Seoul fell 6.16% and Tokyo 2.78% as chip shares slid; "
              "the Dow rose 0.9% to 50,018.70, a first finish "
              "past the 50,000 line.",
         src='EXCHANGE DATA', pin=(133, 37)),
    dict(n=6, place='WASHINGTON', cat='TRADE', tag='ON RECORD',
         head='US FLOATS TARIFFS OF UP TO 25% ON 14 PARTNERS',
         body="New duties were proposed after a trade probe, with "
              "China facing 20 extra points; hearings precede "
              "any start in January.",
         src='USTR NOTICE', pin=(-77, 39)),
    dict(n=7, place='SHANGHAI', cat='POLITICS', tag='ON RECORD',
         head='CITY PARTY CHIEF PLACED UNDER INVESTIGATION',
         body="Chen Jining faces a discipline probe, the fourth "
              "Politburo case since 2022; the body now counts 21.",
         src='PARTY NOTICE', pin=(121, 31)),
    dict(n=8, place='PYONGYANG', cat='DIPLOMACY', tag='ON RECORD',
         head='SWISS ENVOY GIVEN 48 HOURS TO LEAVE',
         body="Pyongyang expelled the Swiss office chief and closed "
              "the office, answering sanctions tied to a "
              "children's camp.",
         src='STATE MEDIA', pin=(126, 39)),
    dict(n=9, place='CANBERRA', cat='DIPLOMACY', tag='ON RECORD',
         head='AUSTRALIA AND SOLOMONS SIGN SECURITY PACT',
         body="The treaty bars foreign military bases in the Solomons "
              "and names Australia its main security partner "
              "in the Pacific.",
         src='TREATY TEXT', pin=(149, -35)),
    dict(n=10, place='ORBIT', cat='SPACE', tag='ON RECORD',
         head='SHENZHOU-24 DOCKS WITH PAKISTANI ASTRONAUT',
         body="The capsule docked with Tiangong at 04:56 UTC, some "
              "3.5 hours after launch, carrying Pakistan's "
              "first astronaut.",
         src='MISSION LOG', pin=(104, 34)),
    dict(n=11, place='BLUE NILE, SUDAN', cat='CONFLICT', tag='REPORTED',
         head='RSF DRONE STRIKE KILLS 19 CIVILIANS',
         body="Rights lawyers reported a paramilitary drone strike on "
              "two towns, killing 19 civilians and wounding 20.",
         src='EMERGENCY LAWYERS', pin=(33, 12)),
    dict(n=12, place='VATICAN CITY', cat='CLIMATE', tag='ON RECORD',
         head="POPE CALLS COP31 FAILURE 'TROUBLING'",
         body="Leo XIV criticised the collapsed Antalya talks, the "
              "first summit since Copenhagen in 2009 to end "
              "without a deal.",
         src='VATICAN REMARKS', pin=(13, 42)),
]

BRIEFS = [
    ('BROOKLYN', "Jury convicts Huawei on 10 of 12 counts; cleared of "
                 "racketeering."),
    ('CARTAGENA', "Hostages freed as forces storm a supermarket; one "
                  "gunman killed."),
    ('COLOMBIA', "Bomb outside government offices wounds 23 people."),
    ('GULF OF FINLAND', "Kyiv confirms an attack on Russian naval "
                        "vessels."),
    ('DR CONGO', "WHO evacuates staff from a hospital amid insecurity."),
    ('BENGHAZI', "Two naval officers die of wounds from the 22 Nov "
                 "sea-drone strike."),
    ('POLAND', "Warsaw renews call for US troops after 2 airspace "
               "breaches in 4 days."),
    ('DELL', "Q3 sales jump 103% to $54.9bn as AI server revenue surges."),
    ('US PRICES', "PCE inflation runs at 3.8% year on year in October, "
                  "as forecast."),
    ('NVIDIA', "CEO Jensen Huang says he is in therapy, admits a "
               "'terrible mistake'."),
    ('WASHINGTON', "Trump awards Giuliani the nation's highest civilian "
                   "honour."),
    ('INDIA', "Cabinet approves a Silchar airport in an Rs 11,000 crore "
              "package."),
    ('FOOTBALL', "Senegal regain the Africa Cup title from Morocco on a "
                 "CAS ruling."),
    ('CHESS', "Gukesh holds Sindarov to a draw under time pressure in "
              "the title match."),
    ('DENMARK', "Prosecutors are barred from wearing the hijab in court."),
    ('LONDON', "Met Police still institutionally racist, a report "
               "concludes."),
]

NUMBERS = [
    ('50,018.70', 'Dow close, its first ever above 50,000'),
    ('-6.16%', 'KOSPI one-day fall as chip shares slid'),
    ('145', 'drones Moscow says it downed overnight'),
    ('25%', 'top rate in the proposed new US tariffs'),
    ('19', 'civilians killed in the Blue Nile strike'),
    ('$132.3bn', "Dell's backlog of AI server orders"),
    ('04:56 UTC', 'Shenzhou-24 docks at Tiangong'),
]

CHIPS = [('MIDDLE EAST', 3), ('EUROPE', 6), ('ASIA-PACIFIC', 5),
         ('AMERICAS', 8), ('AFRICA', 4), ('GLOBAL + SPACE', 2)]

# ---------------------------------------------------------------- map
# Rough land polygons as (lon, lat) outlines, drawn from memory.

LAND = [
    # North America
    [(-168, 66), (-140, 70), (-125, 72), (-110, 68), (-95, 69), (-85, 66),
     (-80, 73), (-75, 62), (-65, 60), (-55, 52), (-60, 46), (-70, 42),
     (-74, 38), (-76, 34), (-80, 31), (-81, 25), (-84, 28), (-87, 21),
     (-90, 20), (-94, 17), (-97, 16), (-105, 20), (-110, 23), (-114, 28),
     (-117, 33), (-122, 37), (-124, 44), (-124, 48), (-130, 55),
     (-145, 60), (-158, 58), (-165, 60)],
    # Central America
    [(-97, 16), (-92, 15), (-86, 13), (-83, 9), (-79, 9), (-77, 7),
     (-80, 8), (-85, 11), (-90, 13), (-95, 15)],
    # South America
    [(-77, 7), (-72, 11), (-64, 10), (-55, 6), (-50, 0), (-44, -3),
     (-35, -8), (-39, -13), (-40, -20), (-48, -26), (-56, -33), (-62, -39),
     (-65, -45), (-67, -50), (-68, -54), (-71, -54), (-73, -46),
     (-73, -37), (-71, -30), (-70, -20), (-75, -15), (-79, -8), (-80, -4),
     (-77, 1)],
    # Greenland
    [(-45, 60), (-40, 62), (-32, 68), (-22, 70), (-20, 76), (-30, 80),
     (-50, 78), (-58, 72), (-55, 65), (-52, 60)],
    # Iceland
    [(-22, 64), (-14, 64), (-14, 66.5), (-22, 66.5)],
    # Britain
    [(-5, 50), (-3, 53), (-5, 55), (-3, 57), (-5, 58.5), (-7.5, 55),
     (-8, 52), (-6, 50)],
    # Ireland
    [(-10.5, 52), (-8, 51.5), (-6, 52), (-6, 54.5), (-8, 55), (-10.5, 54)],
    # Europe with Scandinavia
    [(-9, 37), (-9, 43), (-2, 44), (-1, 46), (-5, 48), (0, 51), (3, 53),
     (8, 55), (7, 57), (10, 59), (5, 60), (5, 62), (11, 65), (16, 68),
     (24, 71), (31, 70), (40, 67), (45, 64), (40, 58), (35, 53),
     (30, 50), (28, 46), (23, 40), (19, 40), (15, 38), (10, 38),
     (3, 37), (-2, 37)],
    # Africa
    [(-6, 35), (0, 36), (10, 37), (20, 32), (30, 31), (34, 28), (38, 22),
     (40, 15), (43, 12), (48, 11), (51, 10), (46, 4), (41, -2), (40, -10),
     (38, -18), (36, -22), (32, -28), (27, -33), (20, -35), (17, -32),
     (15, -27), (13, -18), (12, -12), (13, -6), (9, -1), (9, 4), (4, 6),
     (-3, 5), (-8, 4), (-13, 8), (-17, 15), (-17, 21), (-16, 27),
     (-10, 31)],
    # Madagascar
    [(43, -16), (47, -15), (50, -16), (49, -20), (47, -24), (45, -25),
     (44, -20), (43, -17)],
    # Russia and Siberia
    [(30, 50), (45, 55), (60, 55), (75, 58), (90, 62), (105, 66),
     (120, 68), (135, 70), (150, 70), (165, 68), (178, 66), (175, 62),
     (160, 58), (150, 55), (142, 50), (135, 46), (130, 42), (125, 40),
     (118, 45), (110, 50), (95, 50), (85, 48), (75, 47), (65, 48),
     (55, 48), (45, 47), (38, 46), (32, 46)],
    # Arabia and the Middle East
    [(34, 31), (36, 36), (42, 37), (44, 33), (48, 30), (50, 29),
     (50, 26), (54, 26), (56, 24), (59, 22), (55, 17), (52, 15),
     (45, 12), (43, 12), (40, 15), (38, 20), (35, 28)],
    # India
    [(68, 24), (74, 21), (77, 9), (80, 14), (86, 20), (91, 22),
     (88, 23), (80, 26), (72, 25)],
    # South-east Asia
    [(92, 16), (94, 17), (98, 12), (100, 8), (103, 6), (106, 9),
     (108, 12), (107, 16), (105, 19), (103, 21), (100, 20), (97, 22),
     (94, 22)],
    # China and East Asia
    [(105, 22), (108, 21), (110, 20), (115, 23), (118, 26), (121, 29),
     (122, 32), (120, 35), (119, 37), (122, 38), (126, 41), (130, 42),
     (129, 44), (126, 45), (118, 45), (112, 42), (108, 38), (105, 35),
     (102, 30), (100, 25)],
    # Korea
    [(126, 35), (127, 36), (129, 38), (130, 42), (128, 41), (127, 39),
     (126, 37)],
    # Japan: Honshu and Hokkaido
    [(130, 31), (132, 33), (135, 34), (137, 35), (139, 36), (140, 38),
     (141, 40), (140, 41), (138, 37), (135, 35), (133, 34), (131, 32)],
    [(140, 42), (142, 44), (144, 44), (143, 42), (141, 41)],
    # Philippines
    [(120, 18), (122, 16), (121, 13), (123, 10), (122, 9), (120, 12),
     (119, 16)],
    # Sumatra
    [(95, 5), (100, 0), (104, -3), (106, -5), (103, -4), (99, 1),
     (96, 4)],
    # Borneo
    [(109, 1), (113, 4), (117, 6), (119, 2), (117, -2), (113, -3),
     (110, -2)],
    # Java
    [(105, -6), (110, -7), (114, -8), (114, -9.5), (106, -8)],
    # New Guinea
    [(131, -1), (136, -2), (141, -3), (146, -6), (150, -9), (147, -9),
     (142, -8), (137, -6), (132, -4)],
    # Australia
    [(113, -22), (114, -28), (115, -34), (118, -35), (124, -33),
     (129, -32), (132, -32), (135, -35), (138, -35), (140, -38),
     (145, -38), (150, -37), (153, -32), (153, -27), (151, -24),
     (146, -19), (142, -15), (142, -11), (140, -17), (136, -15),
     (135, -12), (132, -11), (130, -12), (126, -14), (122, -17),
     (118, -20)],
    # New Zealand
    [(167, -45), (170, -43), (172, -41), (174, -39), (176, -38),
     (178, -37), (176, -36), (174, -41), (172, -43), (169, -46)],
]


def in_land(lon, lat):
    for poly in LAND:
        inside = False
        j = len(poly) - 1
        for i in range(len(poly)):
            xi, yi = poly[i]
            xj, yj = poly[j]
            if (yi > lat) != (yj > lat):
                xint = (xj - xi) * (lat - yi) / (yj - yi) + xi
                if lon < xint:
                    inside = not inside
            j = i
        if inside:
            return True
    return False


# ---------------------------------------------------------------- layout

MX = 26                     # page margin
CW = 1024 - 2 * MX          # content width


def tag_chip(x, y, tag):
    """Small status tag; returns its width."""
    w = text_width(tag, 6.8) + 10
    col = {'ON RECORD': INK, 'REPORTED': FAINT, 'CLAIM': RED}[tag]
    frame(S(x), S(y), S(w), S(11), S(0.55), col)
    draw_text(x + 5, y + 8.2, tag, 6.8, 1.05, col)
    return w


def draw_card(x, y, w, h, card):
    hline(x, y, w, 2.2, INK)
    num = '%02d' % card['n']
    draw_text(x, y + 15, num, 11, 2.6, RED)
    pw = text_width(card['place'], 9.0, 0.2)
    avail = w - 26 - text_width(card['tag'], 6.8) - 22
    place = card['place']
    cap = 9.0
    while pw > avail and cap > 6.4:
        cap -= 0.4
        pw = text_width(place, cap, 0.2)
    draw_text(x + 24, y + 14.5, place, cap, 2.0, INK, spacing=0.2)
    tw = text_width(card['tag'], 6.8) + 10
    tag_chip(x + w - tw, y + 4, card['tag'])
    cat_y = y + 26
    draw_text(x, cat_y, card['cat'], 7.0, 1.5, FAINT, spacing=0.5)
    lines = wrap(card['head'], 12.0, w - 2)
    ly = y + 44
    for ln in lines[:2]:
        draw_text(x, ly, ln, 12.0, 2.5, INK)
        ly += 15.5
    blines = wrap(card['body'], 9.0, w - 2)
    by = ly + 3
    for ln in blines[:3]:
        draw_text(x, by, ln, 9.0, 1.3, BODY)
        by += 12.5
    draw_text(x, y + h - 4, '- ' + card['src'], 6.8, 1.1, FAINT,
              spacing=0.3)


def draw_map(x, y, w, h):
    draw_text(x, y + 10, 'WHERE IT HAPPENED', 9.5, 2.2, INK, spacing=0.6)
    draw_text(x + w, y + 10, 'DOTS = LAND · PINS = STORIES 1-12', 7.2,
              1.2, FAINT, align='right')
    top = y + 20
    mh = h - 24
    lon0, lon1 = -172.0, 188.0
    lat0, lat1 = 80.0, -60.0

    def mx(lon):
        return x + (lon - lon0) / (lon1 - lon0) * w

    def my(lat):
        return top + (lat0 - lat) / (lat0 - lat1) * mh

    step = 3.6
    lat = 78.0
    while lat > -58:
        lon = -170.0
        while lon < 186:
            if in_land(lon, lat):
                disc(int(S(mx(lon))), int(S(my(lat))), S(1.05),
                     (140, 136, 126))
            lon += step
        lat -= step
    for card in CARDS:
        lon, lat = card['pin']
        cxp, cyp = mx(lon), my(lat)
        disc(int(S(cxp)), int(S(cyp)), S(7.6), RED)
        label = str(card['n'])
        lw = text_width(label, 7.4, 0)
        draw_text(cxp - lw / 2.0, cyp + 2.7, label, 7.4, 1.7, WHITE)


def draw_numbers(x, y, w, h):
    rect(S(x), S(y), S(w), S(24), INK)
    draw_text(x + 10, y + 17, 'THE DAY IN NUMBERS', 11.5, 2.4, WHITE,
              spacing=0.6)
    rows = NUMBERS
    rh = (h - 30) / len(rows)
    for i, (val, lab) in enumerate(rows):
        ry = y + 30 + i * rh
        draw_text(x + 4, ry + 13, val, 14.5, 2.7, RED)
        vw = text_width(val, 14.5)
        lw = w - vw - 22
        lns = wrap(lab, 8.2, lw)
        ly = ry + 8.5
        for ln in lns[:2]:
            draw_text(x + vw + 16, ly, ln, 8.2, 1.25, BODY)
            ly += 10.5
        if i < len(rows) - 1:
            hline(x + 4, ry + rh - 1.5, w - 8, 0.5, RULE)


def render():
    _fill_bg()

    # --- masthead
    draw_text(MX, 34, 'THE GLOBAL DAILY RECORD', 10.5, 2.0, RED,
              spacing=1.2)
    draw_text(1024 - MX, 34, 'ALL TIMES UTC', 10.5, 2.0, RED,
              spacing=1.2, align='right')
    draw_text(512, 92, 'THE WORLD IN ONE PAGE', 46, 4.6, INK,
              spacing=0.5, align='center')
    hline(MX, 104, CW, 2.6, INK)
    hline(MX, 108.5, CW, 0.8, INK)
    draw_text(512, 126, 'WEDNESDAY 25 NOVEMBER 2026', 14.5, 2.6, INK,
              spacing=1.6, align='center')
    draw_text(512, 141, 'ONE IMAGE - TWENTY-EIGHT STORIES - EVERY '
                        'CONTINENT', 8.2, 1.3, FAINT, spacing=1.0,
              align='center')

    # --- region chips
    cy = 152
    total = sum(text_width(nm, 8.6, 0.4) + 16 for nm, _ in CHIPS) \
        + 8 * (len(CHIPS) - 1)
    cx = 512 - total / 2.0
    for nm, cnt in CHIPS:
        label = '%s %d' % (nm, cnt)
        wch = text_width(label, 8.6, 0.4) + 16
        rect(S(cx), S(cy), S(wch), S(17), INK)
        draw_text(cx + 8, cy + 12.4, label, 8.6, 1.5, WHITE, spacing=0.4)
        cx += wch + 8

    # --- UTC timeline
    ty = 190
    draw_text(MX, ty - 8, 'THE DAY IN UTC', 8.6, 2.0, INK, spacing=0.8)
    draw_text(MX + 300, ty - 8, 'PRE-DAWN STRIKES AT SAMARA AND '
                                'CARTAGENA', 7.6, 1.2, FAINT, spacing=0.3)
    hline(MX, ty, CW, 1.0, INK)
    for hr in range(0, 25, 4):
        tx = MX + CW * hr / 24.0
        vline(tx, ty, 6, 0.9, INK)
        draw_text(tx, ty + 15, '%02d' % hr, 7.4, 1.2, FAINT,
                  align='center')
    dx = MX + CW * (4 + 56 / 60.0) / 24.0
    disc(int(S(dx)), int(S(ty)), S(3.4), RED)
    draw_text(dx, ty - 8, '04:56 SHENZHOU-24 DOCKS', 7.6, 1.6, RED,
              align='center')

    # --- cards grid
    gy = 216
    gh = 372
    gap = 8
    cw4 = (CW - 3 * gap) / 4.0
    chh = (gh - 2 * gap) / 3.0
    for i, card in enumerate(CARDS):
        col = i % 4
        row = i // 4
        draw_card(MX + col * (cw4 + gap), gy + row * (chh + gap),
                  cw4, chh, card)

    # --- map and numbers band
    by = 606
    bh = 168
    draw_map(MX, by, 596, bh)
    draw_numbers(MX + 622, by, CW - 622, bh)

    # --- briefs
    ay = 792
    hline(MX, ay, CW, 2.2, INK)
    draw_text(MX, ay + 17, 'ALSO ON WEDNESDAY', 12.5, 2.6, INK,
              spacing=0.8)
    draw_text(1024 - MX, ay + 17, 'SIXTEEN MORE STORIES', 8.4, 1.4,
              FAINT, spacing=0.6, align='right')
    colw = (CW - 16) / 2.0
    brow = 17.5
    for i, (lead, text) in enumerate(BRIEFS):
        col = i // 8
        row = i % 8
        bx = MX + col * (colw + 16)
        byy = ay + 32 + row * brow
        draw_text(bx, byy, lead, 9.0, 2.3, INK)
        lw = text_width(lead, 9.0) + 8
        t = text
        while text_width(t, 8.5) > colw - lw and ' ' in t:
            t = t.rsplit(' ', 1)[0]
        draw_text(bx + lw, byy, t, 8.5, 1.25, BODY)

    # --- footer
    fy = 958
    hline(MX, fy, CW, 1.6, INK)
    draw_text(MX, fy + 15, 'DATE CHECK', 8.8, 2.2, RED, spacing=0.5)
    dlines = wrap('Every story on this page was first reported on '
                  'Wednesday 25 November 2026, UTC. Earlier stories with '
                  'no fresh development that day are excluded.', 8.6, 560)
    ly = fy + 15
    for ln in dlines[:2]:
        draw_text(MX + 86, ly, ln, 8.6, 1.25, BODY)
        ly += 11.5
    lx = 1024 - MX
    draw_text(lx, fy + 15, 'CLAIM = UNVERIFIED ASSERTION', 7.4, 1.2,
              FAINT, align='right')
    draw_text(lx, fy + 26.5, 'REPORTED = NEWSROOM REPORT', 7.4, 1.2,
              FAINT, align='right')
    draw_text(lx, fy + 38, 'ON RECORD = OFFICIAL STATEMENT', 7.4, 1.2,
              FAINT, align='right')
    draw_text(512, 1014, 'SET IN A HAND-DRAWN STROKE FACE - RENDERED '
                         'ENTIRELY BY PROGRAM - NO PHOTOGRAPHS', 7.0,
              1.1, FAINT, spacing=0.8, align='center')


# ---------------------------------------------------------------- png out

def downscale():
    out = bytearray(1024 * 1024 * 3)
    n = 16
    for oy in range(1024):
        for ox in range(1024):
            r = g = b = 0
            base_x = ox * SS
            for dy in range(SS):
                row = (oy * SS + dy) * W * 3 + base_x * 3
                for dx in range(SS):
                    i = row + dx * 3
                    r += buf[i]
                    g += buf[i + 1]
                    b += buf[i + 2]
            o = (oy * 1024 + ox) * 3
            out[o] = r // n
            out[o + 1] = g // n
            out[o + 2] = b // n
    return out


def save_png(pixels, path):
    raw = bytearray()
    stride = 1024 * 3
    for y in range(1024):
        raw.append(0)
        raw += pixels[y * stride:(y + 1) * stride]

    def chunk(tag, data):
        c = struct.pack('>I', len(data)) + tag + data
        c += struct.pack('>I', zlib.crc32(tag + data) & 0xffffffff)
        return c

    ihdr = struct.pack('>IIBBBBB', 1024, 1024, 8, 2, 0, 0, 0)
    png = b'\x89PNG\r\n\x1a\n'
    png += chunk(b'IHDR', ihdr)
    png += chunk(b'IDAT', zlib.compress(bytes(raw), 9))
    png += chunk(b'IEND', b'')
    d = os.path.dirname(path)
    if d:
        os.makedirs(d, exist_ok=True)
    with open(path, 'wb') as f:
        f.write(png)
    return len(png)


def main():
    render()
    pixels = downscale()
    size = save_png(pixels, OUT_PATH)
    print('wrote %s (%d bytes)' % (OUT_PATH, size))


if __name__ == '__main__':
    main()

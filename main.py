#!/usr/bin/env python3
"""news-image-20261125: one-page broadsheet summary of world news on
25 November 2026 (UTC). Pure standard library. Renders at 4096x4096,
downscales with a 4x4 box average to 1024x1024, writes a PNG.
Deterministic: no randomness, no timestamps, fixed content.
"""
import hashlib
import math
import os
import struct
import zlib

W = 4096
H = 4096
OUT_W = 1024
OUT_H = 1024

PAPER = (253, 252, 247)
INK = (17, 17, 17)
SOFT = (52, 52, 52)
RED = (178, 28, 28)
DARKRED = (140, 20, 20)
RULE = (17, 17, 17)
LIGHT_RULE = (120, 120, 120)
CHIP_BG = (238, 236, 228)
CARD_BG = (255, 255, 255)
TAG_BG = (17, 17, 17)
TAG_FG = (255, 255, 255)
MAP_DOT = (70, 70, 70)
WHITE = (255, 255, 255)

# ---------------------------------------------------------------- font
# 5x7 bitmap font, '#' = on. Lowercase uses rows 2..6 (x-height) with
# descenders on row 6.
FONT = {
    'A': ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    'B': ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    'C': ("01110", "10001", "10000", "10000", "10000", "10001", "01110"),
    'D': ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    'E': ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    'F': ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    'G': ("01110", "10001", "10000", "10111", "10001", "10001", "01111"),
    'H': ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    'I': ("01110", "00100", "00100", "00100", "00100", "00100", "01110"),
    'J': ("00111", "00010", "00010", "00010", "00010", "10010", "01100"),
    'K': ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    'L': ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    'M': ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    'N': ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    'O': ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    'P': ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    'Q': ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    'R': ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    'S': ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    'T': ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    'U': ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    'V': ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    'W': ("10001", "10001", "10001", "10101", "10101", "11011", "10001"),
    'X': ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    'Y': ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    'Z': ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
    'a': (".....", ".....", "01110", "00001", "01111", "10001", "01111"),
    'b': ("10000", "10000", "11110", "10001", "10001", "10001", "11110"),
    'c': (".....", ".....", "01110", "10000", "10000", "10001", "01110"),
    'd': ("00001", "00001", "01111", "10001", "10001", "10001", "01111"),
    'e': (".....", ".....", "01110", "10001", "11111", "10000", "01110"),
    'f': ("00110", "01000", "01000", "11110", "01000", "01000", "01000"),
    'g': (".....", "01111", "10001", "10001", "01111", "00001", "01110"),
    'h': ("10000", "10000", "11110", "10001", "10001", "10001", "10001"),
    'i': (".....", "00100", ".....", "01100", "00100", "00100", "01110"),
    'j': (".....", "00010", ".....", "00110", "00010", "00010", "01100"),
    'k': ("10000", "10000", "10010", "10100", "11000", "10100", "10010"),
    'l': ("01100", "00100", "00100", "00100", "00100", "00100", "01110"),
    'm': (".....", ".....", "11010", "10101", "10101", "10101", "10101"),
    'n': (".....", ".....", "11110", "10001", "10001", "10001", "10001"),
    'o': (".....", ".....", "01110", "10001", "10001", "10001", "01110"),
    'p': (".....", ".....", "11110", "10001", "10001", "11110", "10000"),
    'q': (".....", ".....", "01111", "10001", "10001", "01111", "00001"),
    'r': (".....", ".....", "10110", "11001", "10000", "10000", "10000"),
    's': (".....", ".....", "01111", "10000", "01110", "00001", "11110"),
    't': ("00100", "00100", "11110", "00100", "00100", "00100", "00110"),
    'u': (".....", ".....", "10001", "10001", "10001", "10011", "01101"),
    'v': (".....", ".....", "10001", "10001", "10001", "01010", "00100"),
    'w': (".....", ".....", "10001", "10101", "10101", "10101", "01010"),
    'x': (".....", ".....", "10001", "01010", "00100", "01010", "10001"),
    'y': (".....", ".....", "10001", "10001", "10001", "01111", "00001"),
    'z': (".....", ".....", "11111", "00010", "00100", "01000", "11111"),
    '0': ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    '1': ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    '2': ("01110", "10001", "00001", "00110", "01000", "10000", "11111"),
    '3': ("11110", "00001", "00001", "01110", "00001", "00001", "11110"),
    '4': ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    '5': ("11111", "10000", "11110", "00001", "00001", "10001", "01110"),
    '6': ("01110", "10000", "10000", "11110", "10001", "10001", "01110"),
    '7': ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    '8': ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    '9': ("01110", "10001", "10001", "01111", "00001", "00001", "01110"),
    ' ': (".....", ".....", ".....", ".....", ".....", ".....", "....."),
    '.': (".....", ".....", ".....", ".....", ".....", "01100", "01100"),
    ',': (".....", ".....", ".....", ".....", "01100", "00100", "01000"),
    ':': (".....", "01100", "01100", ".....", "01100", "01100", "....."),
    ';': (".....", "01100", "01100", ".....", "01100", "00100", "01000"),
    '!': ("00100", "00100", "00100", "00100", "00100", ".....", "00100"),
    '?': ("01110", "10001", "00001", "00110", "00100", ".....", "00100"),
    "'": ("00100", "00100", "01000", ".....", ".....", ".....", "....."),
    '"': ("01010", "01010", ".....", ".....", ".....", ".....", "....."),
    '(': ("00010", "00100", "01000", "01000", "01000", "00100", "00010"),
    ')': ("01000", "00100", "00010", "00010", "00010", "00100", "01000"),
    '-': (".....", ".....", ".....", "01110", ".....", ".....", "....."),
    '/': ("00001", "00010", "00010", "00100", "01000", "01000", "10000"),
    '%': ("11001", "11010", "00010", "00100", "01000", "01011", "10011"),
    '$': ("00100", "01111", "10100", "01110", "00101", "11110", "00100"),
    '&': ("01100", "10010", "10100", "01000", "10101", "10010", "01101"),
    '+': (".....", "00100", "00100", "11111", "00100", "00100", "....."),
    '=': (".....", ".....", "11111", ".....", "11111", ".....", "....."),
    '*': (".....", "00100", "10101", "01110", "10101", "00100", "....."),
    '#': ("01010", "01010", "11111", "01010", "11111", "01010", "01010"),
    '@': ("01110", "10001", "10111", "10101", "10110", "10000", "01110"),
    '_': (".....", ".....", ".....", ".....", ".....", ".....", "11111"),
    '[': ("01110", "01000", "01000", "01000", "01000", "01000", "01110"),
    ']': ("01110", "00010", "00010", "00010", "00010", "00010", "01110"),
    '<': ("00010", "00100", "01000", "10000", "01000", "00100", "00010"),
    '>': ("01000", "00100", "00010", "00001", "00010", "00100", "01000"),
    '\u00b7': (".....", ".....", "01100", "01100", ".....", ".....", "....."),
    '~': (".....", ".....", "01001", "10110", ".....", ".....", "....."),
    '|': ("00100", "00100", "00100", "00100", "00100", "00100", "00100"),
    '\\': ("10000", "01000", "01000", "00100", "00010", "00010", "00001"),
    '^': ("00100", "01010", "10001", ".....", ".....", ".....", "....."),
    '`': ("00100", "01000", ".....", ".....", ".....", ".....", "....."),
    '{': ("00010", "00100", "00100", "01100", "00100", "00100", "00010"),
    '}': ("01000", "00100", "00100", "00110", "00100", "00100", "01000"),
    '\u2022': (".....", "01110", "11111", "11111", "11111", "01110", "....."),
    '\u00b7': (".....", ".....", "01100", "01100", ".....", ".....", "....."),
}

# ---------------------------------------------------------------- canvas
buf = bytearray(W * H * 3)


def fill_rect(x, y, w, h, color):
    if w <= 0 or h <= 0:
        return
    x0 = max(0, x)
    y0 = max(0, y)
    x1 = min(W, x + w)
    y1 = min(H, y + h)
    if x0 >= x1 or y0 >= y1:
        return
    row = bytes(color) * (x1 - x0)
    n = (x1 - x0) * 3
    for yy in range(y0, y1):
        i = (yy * W + x0) * 3
        buf[i:i + n] = row


def hline(x0, x1, y, thick, color):
    fill_rect(x0, y, x1 - x0, thick, color)


def vline(x, y0, y1, thick, color):
    fill_rect(x, y0, thick, y1 - y0, color)


def fill_circle(cx, cy, r, color):
    for dy in range(-r, r + 1):
        dx = int(math.sqrt(max(0, r * r - dy * dy)))
        fill_rect(cx - dx, cy + dy, 2 * dx + 1, 1, color)


def ring(cx, cy, r, thick, color):
    # Annulus only: draw left/right segments per scanline, never paint
    # over the interior.
    inner = r - thick
    for dy in range(-r, r + 1):
        dx = int(math.sqrt(max(0, r * r - dy * dy)))
        if abs(dy) < inner:
            dx2 = int(math.sqrt(max(0, inner * inner - dy * dy)))
            fill_rect(cx - dx, cy + dy, dx - dx2, 1, color)
            fill_rect(cx + dx2 + 1, cy + dy, dx - dx2, 1, color)
        else:
            fill_rect(cx - dx, cy + dy, 2 * dx + 1, 1, color)


# ---------------------------------------------------------------- text
def text_w(s, scale):
    return len(s) * 6 * scale - scale


def _glyph_runs(row):
    runs = []
    i = 0
    while i < 5:
        if row[i] == '1':
            j = i
            while j < 5 and row[j] == '1':
                j += 1
            runs.append((i, j - i))
            i = j
        else:
            i += 1
    return runs


def draw_glyph(x, y, scale, glyph, color):
    for r in range(7):
        for (c0, ln) in _glyph_runs(glyph[r]):
            fill_rect(x + c0 * scale, y + r * scale, ln * scale, scale, color)


def draw_text(x, y, scale, text, color, bold=False):
    cx = x
    shift = max(1, scale // 5) if bold else 0
    for ch in text:
        g = FONT.get(ch)
        if g is None:
            g = FONT['?']
        draw_glyph(cx, y, scale, g, color)
        if bold:
            draw_glyph(cx + shift, y, scale, g, color)
        cx += 6 * scale
    return cx


def draw_text_center(cx, y, scale, text, color, bold=False):
    w = text_w(text, scale)
    return draw_text(cx - w // 2, y, scale, text, color, bold)


def wrap(text, scale, maxw):
    words = text.split(' ')
    lines = []
    cur = ''
    for wd in words:
        t = wd if not cur else cur + ' ' + wd
        if text_w(t, scale) <= maxw:
            cur = t
        else:
            if cur:
                lines.append(cur)
            cur = wd
    if cur:
        lines.append(cur)
    return lines


def draw_para(x, y, scale, text, maxw, color, line_h, max_lines=None,
              bold=False):
    lines = wrap(text, scale, maxw)
    if max_lines is not None:
        lines = lines[:max_lines]
    yy = y
    for ln in lines:
        draw_text(x, yy, scale, ln, color, bold=bold)
        yy += line_h
    return yy


# ---------------------------------------------------------------- map
# Rough continent outlines as (lon, lat) polygons.
CONTINENTS = [
    # North America
    [(-168, 66), (-140, 70), (-125, 72), (-110, 73), (-95, 80), (-85, 76),
     (-80, 73), (-75, 72), (-65, 60), (-60, 55), (-55, 47), (-65, 45),
     (-70, 42), (-75, 35), (-80, 32), (-81, 26), (-84, 30), (-90, 29),
     (-97, 26), (-105, 22), (-110, 24), (-114, 28), (-120, 34),
     (-125, 40), (-124, 48), (-130, 55), (-140, 60), (-155, 58),
     (-165, 60), (-168, 66)],
    # Greenland
    [(-58, 64), (-45, 60), (-40, 65), (-32, 68), (-22, 70), (-25, 76),
     (-40, 80), (-58, 76), (-60, 70), (-58, 64)],
    # South America
    [(-80, 9), (-77, 4), (-75, -5), (-81, -12), (-78, -20), (-70, -30),
     (-70, -40), (-68, -52), (-65, -55), (-60, -45), (-55, -35),
     (-48, -28), (-40, -22), (-35, -8), (-45, -2), (-52, 4), (-60, 8),
     (-70, 11), (-80, 9)],
    # Africa
    [(-17, 15), (-10, 30), (-5, 35), (10, 37), (20, 32), (30, 31),
     (35, 28), (40, 15), (43, 11), (48, 10), (51, 12), (44, 5),
     (40, -5), (38, -18), (35, -28), (32, -32), (28, -35), (20, -35),
     (15, -28), (12, -18), (13, -10), (9, 4), (4, 6), (-8, 5),
     (-13, 8), (-17, 15)],
    # Eurasia
    [(-10, 36), (-9, 43), (-2, 48), (0, 50), (5, 53), (8, 57), (10, 59),
     (18, 56), (21, 55), (24, 58), (28, 60), (30, 62), (32, 68),
     (40, 68), (55, 68), (68, 73), (75, 73), (85, 75), (100, 76),
     (110, 74), (120, 73), (130, 72), (140, 72), (150, 70), (160, 70),
     (170, 67), (178, 65), (170, 60), (162, 56), (158, 52), (150, 60),
     (142, 55), (140, 50), (135, 43), (130, 42), (127, 40), (122, 38),
     (120, 32), (115, 23), (110, 20), (108, 12), (105, 9), (100, 8),
     (98, 12), (95, 16), (92, 21), (88, 22), (85, 19), (80, 15),
     (77, 8), (75, 12), (72, 20), (68, 23), (62, 25), (58, 26),
     (56, 27), (52, 26), (50, 29), (48, 30), (44, 29), (40, 32),
     (36, 36), (33, 36), (30, 36), (27, 37), (23, 36), (19, 40),
     (15, 44), (12, 44), (8, 44), (3, 43), (0, 40), (-2, 37),
     (-6, 36), (-10, 36)],
    # Australia
    [(113, -22), (114, -30), (115, -35), (120, -34), (129, -32),
     (132, -32), (135, -35), (138, -35), (140, -38), (145, -38),
     (150, -37), (153, -32), (153, -27), (150, -23), (146, -19),
     (142, -15), (142, -11), (137, -12), (135, -15), (132, -12),
     (130, -13), (126, -14), (122, -17), (118, -20), (113, -22)],
    # United Kingdom
    [(-5, 50), (-3, 53), (-5, 56), (-3, 58), (-1, 57), (0, 53), (1, 51),
     (-5, 50)],
    # Japan
    [(130, 31), (132, 33), (135, 34), (137, 35), (139, 37), (140, 39),
     (141, 41), (142, 44), (144, 44), (141, 40), (140, 36), (137, 34),
     (133, 34), (131, 33), (130, 31)],
    # Indonesia
    [(95, 5), (98, 2), (100, -2), (104, -4), (108, -6), (112, -7),
     (115, -8), (118, -9), (120, -10), (122, -8), (118, -5), (112, -2),
     (106, 0), (100, 3), (95, 5)],
    # New Guinea
    [(131, -1), (136, -2), (141, -3), (146, -6), (150, -9), (147, -9),
     (143, -8), (138, -8), (134, -4), (131, -1)],
]


def _inside_poly(lon, lat, poly):
    inside = False
    n = len(poly)
    j = n - 1
    for i in range(n):
        xi, yi = poly[i]
        xj, yj = poly[j]
        if (yi > lat) != (yj > lat):
            xint = (xj - xi) * (lat - yi) / (yj - yi) + xi
            if lon < xint:
                inside = not inside
        j = i
    return inside


def _on_land(lon, lat):
    for poly in CONTINENTS:
        if _inside_poly(lon, lat, poly):
            return True
    return False


# ---------------------------------------------------------------- content
CARDS = [
    dict(num=1, place="STRAIT OF HORMUZ", cat="ENERGY", tag="BREAKING",
         head="TANKERS ABLAZE IN THE STRAIT OF HORMUZ",
         body="Iran's IRGC says two oil tankers struck mines and caught fire, blaming unauthorised routes. 25 Nov, UTC.",
         lon=56.3, lat=26.5),
    dict(num=2, place="RAS TANURA, SAUDI ARABIA", cat="ENERGY",
         tag="BREAKING",
         head="HOUTHI STRIKE SETS SAUDI REFINERY ON FIRE",
         body="The Houthis say they attacked the Ras Tanura refinery and started a fire. Saudi Arabia has not confirmed damage.",
         lon=50.1, lat=26.6),
    dict(num=3, place="GAZA CITY", cat="CONFLICT", tag="BREAKING",
         head="ISRAELI STRIKE KILLS HAMAS SECURITY CHIEF",
         body="An Israeli air strike killed Hamas security chief Mohammad Abuelouf, his wife and two children in Gaza City.",
         lon=34.5, lat=31.5),
    dict(num=4, place="SAMARA, RUSSIA", cat="CONFLICT", tag="BREAKING",
         head="DRONES HIT TWO ROSNEFT REFINERIES IN SAMARA",
         body="Ukrainian drones hit the Syzran and Kuibyshev refineries, setting fires. One died. Russia says 145 downed.",
         lon=50.1, lat=53.2),
    dict(num=5, place="SEOUL - TOKYO - NEW YORK", cat="MARKETS",
         tag="DEVELOPING",
         head="TECH ROUT SINKS ASIA; DOW PASSES 50,000",
         body="KOSPI fell 6.16% and the Nikkei 2.78% as chip stocks slid. In New York the Dow closed above 50,000, a first.",
         lon=127.0, lat=37.5),
    dict(num=6, place="WASHINGTON", cat="TRADE", tag="DEVELOPING",
         head="US PROPOSES NEW TARIFFS OF UP TO 25%",
         body="Trump proposes new tariffs of up to 25% on 14 trading partners, plus 20% on China, from January.",
         lon=-77.0, lat=38.9),
    dict(num=7, place="SHANGHAI, CHINA", cat="POLITICS", tag="DEVELOPING",
         head="CHINA INVESTIGATES TOP SHANGHAI PARTY CHIEF",
         body="Shanghai party chief Chen Jining, a Politburo member, is under investigation for suspected discipline violations.",
         lon=121.5, lat=31.2),
    dict(num=8, place="PYONGYANG", cat="DIPLOMACY", tag="DEVELOPING",
         head="NORTH KOREA EXPELS SWISS DIPLOMAT IN 48 HOURS",
         body="Pyongyang expelled the head of the Swiss foreign office and ordered the office shut, under a 48-hour deadline.",
         lon=125.8, lat=39.0),
    dict(num=9, place="CANBERRA", cat="SECURITY", tag="DEVELOPING",
         head="AUSTRALIA SIGNS SECURITY PACT WITH SOLOMONS",
         body="Australia and Solomon Islands signed a treaty barring foreign bases, naming Australia the key security partner.",
         lon=149.1, lat=-35.3),
    dict(num=10, place="TIANGONG STATION", cat="SPACE", tag="CONFIRMED",
         head="SHENZHOU-24 DOCKS WITH FIRST PAKISTANI IN SPACE",
         body="Shenzhou-24 docked with Tiangong about 3.5 hours after launch, carrying Pakistan's first astronaut. 04:56 UTC.",
         lon=100.3, lat=40.9),
    dict(num=11, place="BLUE NILE, SUDAN", cat="CONFLICT", tag="CONFIRMED",
         head="DRONE STRIKES KILL 19 CIVILIANS IN BLUE NILE",
         body="Rights group Emergency Lawyers says RSF drone strikes killed 19 civilians and injured 20 in two Blue Nile towns.",
         lon=34.0, lat=11.0),
    dict(num=12, place="VATICAN CITY", cat="CLIMATE", tag="CONFIRMED",
         head="POPE CALLS FAILED CLIMATE DEAL 'TROUBLING'",
         body="Pope Leo XIV called the COP31 failure 'troubling'. The Antalya talks ended on 22 Nov with no deal, a first since 2009.",
         lon=12.45, lat=41.9),
]

BRIEFS = [
    ("HUAWEI", "A Brooklyn jury convicts the firm on 10 of 12 counts, including bank fraud."),
    ("CARTAGENA", "Troops free all hostages at an Exito store; one gunman is killed."),
    ("COLOMBIA", "A bomb outside a government building injures 23 people."),
    ("GULF OF FINLAND", "Ukraine confirms strikes on Russian ships."),
    ("DR CONGO", "The WHO evacuates staff from a hospital."),
    ("BENGHAZI", "Two Libyan naval officers die from wounds in a 22 Nov drone attack."),
    ("POLAND", "Warsaw again asks for a permanent US presence after two airspace violations."),
    ("DELL", "Third-quarter sales reach $54.9bn, up 103%; AI server sales hit $22.0bn."),
    ("US PRICES", "October PCE inflation is 3.8% year on year, as expected."),
    ("NVIDIA", "Chief Jensen Huang says he is in therapy and admits a 'terrible mistake'."),
    ("WASHINGTON", "Trump awards Rudy Giuliani the top civilian honour."),
    ("INDIA", "The cabinet approves a new Silchar airport in Assam for Rs 2,014 crore."),
    ("FOOTBALL", "Senegal regain the Africa Cup title from Morocco after a CAS ruling."),
    ("CHESS", "Gukesh draws with Sindarov in time trouble at the World Championship."),
    ("DENMARK", "Prosecutors are banned from wearing the hijab."),
    ("LONDON", "The Metropolitan Police still has institutional racism, a report says."),
]

NUMBERS = [
    ("-6.16%", "KOSPI FALL, SEOUL"),
    ("50,018.70", "DOW CLOSE, FIRST ABOVE 50,000"),
    ("$132.3BN", "DELL AI ORDER BACKLOG"),
    ("+3.8%", "US PCE INFLATION, OCT Y/Y"),
    ("145", "DRONES RUSSIA SAYS IT DOWNED"),
    ("19", "CIVILIANS KILLED, BLUE NILE"),
]

CHIPS = [
    ("MIDDLE EAST", 3), ("ASIA", 4), ("EUROPE", 2),
    ("AMERICAS", 1), ("OCEANIA", 1), ("AFRICA", 1),
]

TIMELINE = [
    (3.0, "DRONES HIT SAMARA REFINERIES", True),
    (4.93, "SHENZHOU-24 DOCKS 04:56 UTC", False),
    (7.0, "ASIA MARKETS PLUNGE", True),
    (13.5, "US PCE +3.8% 13:30 UTC", False),
    (16.0, "TARIFF PLAN PUBLISHED", True),
    (19.0, "POPE ON COP31 FAILURE", False),
]

# ---------------------------------------------------------------- layout
MX = 120          # left margin
RX = 3976         # right edge
CW = RX - MX      # 3856 content width


def draw_masthead():
    hline(MX, RX, 44, 10, INK)
    draw_text_center(W // 2, 78, 26, "THE GLOBAL LEDGER", INK, bold=True)
    hline(MX, RX, 292, 4, INK)
    draw_text(MX, 322, 8, "WEDNESDAY 25 NOVEMBER 2026", INK, bold=True)
    right = "28 STORIES  -  12 TOP  -  16 IN BRIEF"
    draw_text(RX - text_w(right, 6), 332, 6, right, SOFT)
    # red kicker bar
    fill_rect(MX, 396, CW, 84, RED)
    draw_text_center(W // 2, 418, 7,
                     "THE WORLD IN ONE PAGE  -  ALL TIMES UTC",
                     WHITE, bold=True)
    hline(MX, RX, 504, 6, INK)


def draw_chips(y):
    x = MX
    for (name, n) in CHIPS:
        label = "%s %d" % (name, n)
        w = text_w(label, 6) + 56
        fill_rect(x, y, w, 72, CHIP_BG)
        hline(x, x + w, y, 4, INK)
        hline(x, x + w, y + 68, 4, INK)
        draw_text(x + 28, y + 14, 6, label, INK, bold=True)
        x += w + 24
    right = "12 TOP STORIES  +  16 BRIEFS"
    draw_text(RX - text_w(right, 6), y + 14, 6, right, RED, bold=True)


def draw_timeline(y0, y1):
    # band label
    draw_text(MX, y0, 6, "THE DAY IN UTC", INK, bold=True)
    draw_text(RX - text_w("24 HOURS, 25 NOVEMBER 2026", 5), y0 + 4, 5,
              "24 HOURS, 25 NOVEMBER 2026", SOFT)
    line_y = y0 + 88
    hline(MX, RX, line_y, 4, INK)
    for h in range(0, 25, 2):
        tx = MX + int(h / 24.0 * CW)
        vline(tx, line_y - 14, line_y + 14, 4, INK)
        if h % 6 == 0:
            lab = "%02d:00" % h
            draw_text(tx - text_w(lab, 4) // 2, line_y + 18, 4, lab, SOFT)
    for (hour, label, above) in TIMELINE:
        ex = MX + int(hour / 24.0 * CW)
        ring(ex, line_y, 14, 4, RED)
        fill_circle(ex, line_y, 9, RED)
        lw = text_w(label, 4)
        lx = min(max(MX, ex - lw // 2), RX - lw)
        if above:
            draw_text(lx, y0 + 44, 4, label, INK, bold=True)
        else:
            draw_text(lx, line_y + 48, 4, label, INK, bold=True)


def draw_card(x, y, w, h, c):
    fill_rect(x, y, w, h, CARD_BG)
    hline(x, x + w, y, 6, INK)
    hline(x, x + w, y + h - 4, 4, INK)
    px = x + 26
    pw = w - 52
    # number badge
    fill_rect(px, y + 20, 58, 58, RED)
    num = str(c["num"])
    draw_text(px + 29 - text_w(num, 7) // 2, y + 28, 7, num, WHITE,
              bold=True)
    # dateline
    draw_text(px + 74, y + 30, 6, c["place"], INK, bold=True)
    # category tag
    tag = c["cat"]
    tw = text_w(tag, 5) + 28
    fill_rect(x + w - 26 - tw, y + 22, tw, 46, TAG_BG)
    draw_text(x + w - 26 - tw + 14, y + 30, 5, tag, TAG_FG, bold=True)
    # status tag line
    draw_text(px, y + 92, 5, c["tag"], RED, bold=True)
    # headline, up to 2 lines
    hy = y + 132
    lines = wrap(c["head"], 8, pw)
    lines = lines[:2]
    for ln in lines:
        draw_text(px, hy, 8, ln, INK, bold=True)
        hy += 62
    # summary, up to 3 lines
    sy = y + 256
    draw_para(px, sy, 5, c["body"], pw, SOFT, 38, max_lines=3)
    # source line
    draw_text(px, y + h - 40, 4, "SOURCE: WIRE REPORTS", LIGHT_RULE)


def draw_cards(y0, y1):
    cols = 3
    rows = 4
    gap_x = 28
    gap_y = 20
    cw = (CW - (cols - 1) * gap_x) // cols
    ch = (y1 - y0 - (rows - 1) * gap_y) // rows
    for i, c in enumerate(CARDS):
        r = i // cols
        col = i % cols
        x = MX + col * (cw + gap_x)
        y = y0 + r * (ch + gap_y)
        draw_card(x, y, cw, ch, c)


def draw_map_numbers(y0, y1):
    map_x0 = MX
    map_x1 = 1790
    map_y0 = y0 + 52
    map_y1 = y1 - 8
    draw_text(map_x0, y0, 6, "WHERE IT HAPPENED", INK, bold=True)
    draw_text(map_x1 - text_w("NUMBERED PINS MATCH THE 12 TOP STORIES", 4),
              y0 + 6, 4, "NUMBERED PINS MATCH THE 12 TOP STORIES", SOFT)
    # dotted world map, equirectangular lon -180..180, lat 80..-55
    mw = map_x1 - map_x0
    mh = map_y1 - map_y0
    lat_top, lat_bot = 80.0, -55.0
    step = 2.4
    lat = lat_top
    while lat > lat_bot:
        lon = -180.0
        while lon < 180.0:
            if _on_land(lon, lat):
                px = map_x0 + int((lon + 180.0) / 360.0 * mw)
                py = map_y0 + int((lat_top - lat) / (lat_top - lat_bot) * mh)
                fill_circle(px, py, 5, MAP_DOT)
            lon += step
        lat -= step
    # pins (small manual offsets keep near-identical locations readable)
    PIN_OFF = {1: (28, -28), 2: (-28, 20), 3: (-24, -20), 5: (34, -26),
               7: (-30, -24), 8: (6, 30), 10: (-20, -24)}
    for c in CARDS:
        px = map_x0 + int((c["lon"] + 180.0) / 360.0 * mw)
        py = map_y0 + int((lat_top - c["lat"]) / (lat_top - lat_bot) * mh)
        ox, oy = PIN_OFF.get(c["num"], (0, 0))
        px += ox
        py += oy
        fill_circle(px, py, 34, RED)
        ring(px, py, 40, 4, INK)
        num = str(c["num"])
        draw_text(px - text_w(num, 6) // 2, py - 21, 6, num, WHITE,
                  bold=True)
    # numbers block
    nx0 = 1830
    nx1 = RX
    draw_text(nx0, y0, 6, "THE DAY IN NUMBERS", INK, bold=True)
    draw_text(nx1 - text_w("SIX FIGURES THAT DEFINE 25 NOVEMBER", 4),
              y0 + 6, 4, "SIX FIGURES THAT DEFINE 25 NOVEMBER", SOFT)
    ncols = 3
    nrows = 2
    ngap_x = 24
    ngap_y = 20
    nw = (nx1 - nx0 - (ncols - 1) * ngap_x) // ncols
    nh = (y1 - y0 - 52 - (nrows - 1) * ngap_y) // nrows
    ny0 = y0 + 52
    for i, (big, label) in enumerate(NUMBERS):
        r = i // ncols
        col = i % ncols
        x = nx0 + col * (nw + ngap_x)
        y = ny0 + r * (nh + ngap_y)
        fill_rect(x, y, nw, nh, CHIP_BG)
        hline(x, x + nw, y, 6, RED)
        draw_text_center(x + nw // 2, y + 34, 11, big, INK, bold=True)
        lines = wrap(label, 5, nw - 40)
        ly = y + 34 + 88
        for ln in lines[:2]:
            draw_text_center(x + nw // 2, ly, 5, ln, SOFT)
            ly += 48


def draw_briefs(y0, y1):
    draw_text(MX, y0, 7, "IN BRIEF", INK, bold=True)
    draw_text(MX + text_w("IN BRIEF", 7) + 30, y0 + 6, 5,
              "16 MORE STORIES FROM 25 NOVEMBER 2026 (UTC)", SOFT)
    hline(MX, RX, y0 + 56, 6, INK)
    cols = 4
    rows = 4
    gap_x = 28
    gap_y = 14
    gy0 = y0 + 76
    cw = (CW - (cols - 1) * gap_x) // cols
    ch = (y1 - gy0 - (rows - 1) * gap_y) // rows
    for i, (lead, text) in enumerate(BRIEFS):
        r = i // cols
        col = i % cols
        x = MX + col * (cw + gap_x)
        y = gy0 + r * (ch + gap_y)
        full = "%d. %s - %s" % (i + 1, lead, text)
        draw_para(x, y, 5, full, cw - 8, INK, 46, max_lines=3)


def draw_footer(y0, y1):
    hline(MX, RX, y0, 6, INK)
    # DATE CHECK box
    fill_rect(MX, y0 + 14, CW, 136, CHIP_BG)
    hline(MX, RX, y0 + 14, 4, RED)
    draw_text(MX + 24, y0 + 28, 6, "DATE CHECK", RED, bold=True)
    dc = ("Every item on this page happened on, or was first reported on, "
          "25 November 2026 (UTC). Events from 24 November or earlier are "
          "excluded, except where a 25 November report covers an earlier event.")
    draw_para(MX + 24, y0 + 70, 5, dc, CW - 48, INK, 40, max_lines=2)
    # legend + colophon
    ly = y0 + 160
    draw_text(MX, ly, 5, "LEGEND:", INK, bold=True)
    lx = MX + text_w("LEGEND: ", 5) + 20
    fill_rect(lx, ly + 6, 34, 34, RED)
    draw_text(lx + 46, ly, 5, "BREAKING", INK)
    lx += 46 + text_w("BREAKING", 5) + 40
    fill_rect(lx, ly + 6, 34, 34, INK)
    draw_text(lx + 46, ly, 5, "DEVELOPING", INK)
    lx += 46 + text_w("DEVELOPING", 5) + 40
    fill_rect(lx, ly + 6, 34, 34, SOFT)
    draw_text(lx + 46, ly, 5, "CONFIRMED", INK)
    right = "THE GLOBAL LEDGER  -  PAGE 1  -  SOURCES: WIRE REPORTS"
    draw_text(RX - text_w(right, 5), ly, 5, right, SOFT)


# ---------------------------------------------------------------- output
def downscale(src, w, h, f=4):
    ow, oh = w // f, h // f
    out = bytearray(ow * oh * 3)
    for oy in range(oh):
        base_y = oy * f
        for ox in range(ow):
            base_x = ox * f
            r = g = b = 0
            for dy in range(f):
                i = ((base_y + dy) * w + base_x) * 3
                for dx in range(f):
                    j = i + dx * 3
                    r += src[j]
                    g += src[j + 1]
                    b += src[j + 2]
            o = (oy * ow + ox) * 3
            out[o] = r // 16
            out[o + 1] = g // 16
            out[o + 2] = b // 16
    return out


def save_png(path, px, w, h):
    raw = bytearray()
    stride = w * 3
    for y in range(h):
        raw.append(0)
        raw += px[y * stride:(y + 1) * stride]
    comp = zlib.compress(bytes(raw), 9)

    def chunk(typ, data):
        c = struct.pack('>I', len(data)) + typ + data
        c += struct.pack('>I', zlib.crc32(typ + data) & 0xffffffff)
        return c

    ihdr = struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0)
    data = (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', ihdr)
            + chunk(b'IDAT', comp) + chunk(b'IEND', b''))
    with open(path, 'wb') as fh:
        fh.write(data)
    return len(data)


def render():
    fill_rect(0, 0, W, H, PAPER)
    draw_masthead()            # 0 - 510
    draw_chips(528)            # 528 - 600
    draw_timeline(612, 780)    # 612 - 780
    draw_cards(780, 2500)      # 780 - 2500
    draw_map_numbers(2520, 3130)  # 2520 - 3130
    draw_briefs(3150, 3860)    # 3150 - 3860
    draw_footer(3880, 4075)    # 3880 - 4075


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    render()
    small = downscale(buf, W, H, 4)
    out = os.path.join(here, "news-image-20261125.png")
    n = save_png(out, small, OUT_W, OUT_H)
    digest = hashlib.sha256(open(out, 'rb').read()).hexdigest()
    print("WROTE %s" % out)
    print("SIZE %d" % n)
    print("SHA256 %s" % digest)
    print("DIMS %dx%d" % (OUT_W, OUT_H))


if __name__ == '__main__':
    main()

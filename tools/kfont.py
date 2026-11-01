"""Korean font.gim: keep original symbol/ASCII glyphs, put Hangul into the kana/kanji slots.
slot layout: 8 frames of 288x504 8bpp swizzled, 16x28 cells of 18x18. palette 0: idx 128+k = white, alpha ~2k."""
import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))
from jtab import FONT
from gim_tool import unswizzle, swizzle
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
SRC = os.path.join(ROOT, 'work/iso/PSP_GAME/USRDIR/Font/font.gim')
W, H, CELL, COLS, PER = 288, 504, 18, 16, 448
BASE = 0x90
HSTART = FONT.index('ぁ')
LAST = len(FONT)          # slots the game already uses
HALF = {' ': '　', '!': '！', '?': '？', '~': '〜', ',': '，', '.': '．', ':': '：', ';': '；',
        '(': '（', ')': '）', '/': '／', '%': '％', '&': '＆', '+': '＋', '-': '−', '=': '＝',
        '#': '＃', '*': '＊', '@': '＠', '<': '＜', '>': '＞', '"': '”', "'": '’'}
for c in '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz':
    HALF[c] = chr(ord(c) + 0xFEE0)

def ks_hangul():
    out = []
    for hi in range(0xb0, 0xc9):
        for lo in range(0xa1, 0xff):
            out.append(bytes([hi, lo]).decode('euc-kr'))
    return out

def charmap(extra=''):
    m = {c: i for i, c in enumerate(FONT[:HSTART])}
    hs = ks_hangul()
    # slots with slot % 448 < 10 are half width in the patched renderer: keep them out of the Hangul range
    for k in range(1, 8):
        for j in range(10):
            if HSTART <= k * PER + j < LAST: hs.insert(k * PER + j - HSTART, None)
    for c in sorted(set(extra)):
        if '가' <= c <= '힣' and c not in hs: hs.append(c)
    assert HSTART + len(hs) <= LAST, len(hs)
    for i, c in enumerate(hs):
        if c: m[c] = HSTART + i
    for a, b in HALF.items(): m[a] = m[b]
    return m

def build(cmap, ttf, size, out, dy=0):
    d = bytearray(open(SRC, 'rb').read())
    fr = [bytearray(unswizzle(d[BASE + f*W*H: BASE + (f+1)*W*H], W, H)) for f in range(8)]
    font = ImageFont.truetype(ttf, size)
    # each frame has its own palette (frame f uses palette f): map alpha -> nearest index already used there
    import collections
    lut, blank = [], []
    for f in range(8):
        pb = 0x11b8f0 + f * 0x400
        cnt = collections.Counter(fr[f])
        cand = [i for i in cnt if d[pb + i*4: pb + i*4 + 3] == bytes([255, 255, 255])]
        alpha = {i: d[pb + i*4 + 3] for i in cand}
        lut.append([min(cand, key=lambda i: abs(alpha[i] - a)) for a in range(256)])
        blank.append(lut[f][0])
    for c, slot in cmap.items():
        if slot < HSTART or not ('가' <= c <= '힣'): continue
        im = Image.new('L', (CELL, CELL), 0)
        dr = ImageDraw.Draw(im)
        adv = font.getlength(c)
        x = 2 + (14 - adv) / 2
        y = 2 - 1 + dy
        dr.text((x, y), c, font=font, fill=255)
        f, k = divmod(slot, PER); cy, cx = divmod(k, COLS)
        px = im.load()
        for yy in range(CELL):
            row = (cy*CELL + yy) * W + cx*CELL
            for xx in range(CELL):
                fr[f][row + xx] = lut[f][px[xx, yy]]
    # half-width punctuation (advance 7): redraw left-aligned inside the 7px the renderer now gives them
    for slot, ch in {3: ',', 4: '.', 5: '·', 6: ':', 7: ';', 8: '?', 9: '!'}.items():
        im = Image.new('L', (CELL, CELL), 0); dr = ImageDraw.Draw(im)
        adv = font.getlength(ch)
        dr.text((2 + (7 - adv) / 2, 2 - 1 + dy - (2 if ch in ',;' else 0)), ch, font=font, fill=255)
        px = im.load(); cy, cx = divmod(slot, COLS)
        for yy in range(CELL):
            row = (cy*CELL + yy) * W + cx*CELL
            for xx in range(CELL):
                fr[0][row + xx] = lut[0][px[xx, yy]]
    # blank unused old slots (leftover kana/kanji) to avoid confusion
    used = set(cmap.values())
    for slot in range(HSTART, LAST):
        if slot in used: continue
        f, k = divmod(slot, PER); cy, cx = divmod(k, COLS)
        for yy in range(CELL):
            row = (cy*CELL + yy) * W + cx*CELL
            fr[f][row:row+CELL] = bytes([blank[f]]) * CELL
    for f in range(8):
        d[BASE + f*W*H: BASE + (f+1)*W*H] = swizzle(bytes(fr[f]), W, H)
    open(out, 'wb').write(d)
    return fr

if __name__ == '__main__':
    cm = charmap()
    fr = build(cm, os.path.join(ROOT, sys.argv[1]), int(sys.argv[2]), sys.argv[3], int(sys.argv[4]) if len(sys.argv) > 4 else 0)
    Image.frombytes('L', (W, H), bytes(fr[1])).save(os.path.join(ROOT, 'work/font/k1.png'))

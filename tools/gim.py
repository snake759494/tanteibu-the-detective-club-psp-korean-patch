"""Generic GIM read/write (formats 0-3 direct colour, 4/5 indexed). picture k, frame (level) f."""
import struct
from PIL import Image
from gim_tool import unswizzle, swizzle

def _chunks(b, start, end, out):
    p = start
    while p + 16 <= end:
        kind, _, size, nxt, data = struct.unpack_from('<HHIII', b, p)
        if size < 16: break
        out.append((kind, p, size, data))
        if kind in (2, 3): _chunks(b, p + data, p + size, out)
        p += size
    return out

def count(b):
    return sum(1 for c in _chunks(b, 16, len(b), []) if c[0] == 4)

def _frame_off(b, h, f):
    n = struct.unpack_from('<H', b, h + 0x2e)[0]
    if n <= 1 and f == 0: return struct.unpack_from('<I', b, h + 0x1c)[0]
    f = min(f, n - 1)
    return struct.unpack_from('<I', b, h + 0x30 + 4 * f)[0]

def frames(b, k=0):
    ch = _chunks(b, 16, len(b), [])
    idx = [i for i, c in enumerate(ch) if c[0] == 4][k]
    h = ch[idx][1] + ch[idx][3]
    return max(1, struct.unpack_from('<H', b, h + 0x2e)[0])

def info(b, k=0, f=0):
    ch = _chunks(b, 16, len(b), [])
    idx = [i for i, c in enumerate(ch) if c[0] == 4][k]
    img = ch[idx]
    pal = [c for c in ch[idx+1:idx+2] if c[0] == 5]
    h = img[1] + img[3]
    fmt, order, w, hgt, bpp, pa, ha = struct.unpack_from('<HHHHHHH', b, h + 4)
    pix = h + _frame_off(b, h, f)
    pitch = (w * bpp // 8 + pa - 1) // pa * pa
    rows = (hgt + ha - 1) // ha * ha
    pinfo = None
    if pal:
        ph = pal[0][1] + pal[0][3]
        pfmt = struct.unpack_from('<H', b, ph + 4)[0]
        pw = struct.unpack_from('<H', b, ph + 8)[0]
        poff = ph + _frame_off(b, ph, f)
        pinfo = (pfmt, pw, poff)
    return dict(fmt=fmt, order=order, w=w, h=hgt, bpp=bpp, pitch=pitch, rows=rows, pix=pix, pal=pinfo)

def _col16(v, fmt):
    if fmt == 0:   # 5650
        return ((v & 31) * 255 // 31, (v >> 5 & 63) * 255 // 63, (v >> 11 & 31) * 255 // 31, 255)
    if fmt == 1:   # 5551
        return ((v & 31) * 255 // 31, (v >> 5 & 31) * 255 // 31, (v >> 10 & 31) * 255 // 31, 255 if v >> 15 else 0)
    return ((v & 15) * 17, (v >> 4 & 15) * 17, (v >> 8 & 15) * 17, (v >> 12) * 17)

def palette(b, I):
    pfmt, n, off = I['pal']
    if pfmt == 3: return [tuple(b[off + i*4: off + i*4 + 4]) for i in range(n)]
    return [_col16(struct.unpack_from('<H', b, off + i*2)[0], pfmt) for i in range(n)]

def raster(b, I):
    n = I['pitch'] * I['rows']
    raw = b[I['pix']: I['pix'] + n]
    return bytearray(unswizzle(raw, I['pitch'], I['rows'])) if I['order'] else bytearray(raw)

def to_png(b, k=0, f=0):
    I = info(b, k, f); r = raster(b, I); w, h, p = I['w'], I['h'], I['pitch']
    im = Image.new('RGBA', (w, h)); px = im.load()
    if I['fmt'] in (4, 5):
        pal = palette(b, I)
        for y in range(h):
            for x in range(w):
                if I['fmt'] == 5: v = r[y*p + x]
                else: v = (r[y*p + x//2] >> (4 * (x & 1))) & 15
                px[x, y] = pal[v] if v < len(pal) else (0, 0, 0, 0)
    elif I['fmt'] == 3:
        im = Image.frombytes('RGBA', (w, h), bytes(b''.join(bytes(r[y*p: y*p + w*4]) for y in range(h))))
    else:
        for y in range(h):
            for x in range(w):
                px[x, y] = _col16(struct.unpack_from('<H', r, y*p + x*2)[0], I['fmt'])
    return im

def from_png(b, im, k=0, f=0):
    """write RGBA image back (same size). indexed formats: nearest palette colour."""
    I = info(b, k, f); w, h, p = I['w'], I['h'], I['pitch']
    r = raster(b, I); px = im.convert('RGBA').load()
    if I['fmt'] == 3:
        for y in range(h):
            for x in range(w): r[y*p + x*4: y*p + x*4 + 4] = bytes(px[x, y])
    elif I['fmt'] in (4, 5):
        pal = palette(b, I); cache = {}
        def near(c):
            if c not in cache:
                if c[3] == 0:
                    z = [i for i, q in enumerate(pal) if q[3] == 0]
                    if z: cache[c] = z[0]; return z[0]
                cache[c] = min(range(len(pal)), key=lambda i: sum((a - q) ** 2 for a, q in zip(c, pal[i])) )
            return cache[c]
        for y in range(h):
            for x in range(w):
                v = near(px[x, y])
                if I['fmt'] == 5: r[y*p + x] = v
                else:
                    o = y*p + x//2; s = 4 * (x & 1)
                    r[o] = (r[o] & ~(15 << s) & 255) | (v << s)
    else:
        fmt = I['fmt']
        for y in range(h):
            for x in range(w):
                R, G, B, A = px[x, y]
                if fmt == 0: v = (R >> 3) | (G >> 2) << 5 | (B >> 3) << 11
                elif fmt == 1: v = (R >> 3) | (G >> 3) << 5 | (B >> 3) << 10 | (1 << 15 if A >= 128 else 0)
                else: v = (R >> 4) | (G >> 4) << 4 | (B >> 4) << 8 | (A >> 4) << 12
                struct.pack_into('<H', r, y*p + x*2, v)
    raw = swizzle(bytes(r), p, I['rows']) if I['order'] else r
    out = bytearray(b); out[I['pix']: I['pix'] + len(raw)] = raw
    return bytes(out)

"""Korean redraw of text inside GIM pictures.

Spec: trans/images.json  -> list of entries
  {"file": "Menu/title/title.gim", "k": 17, "jp": "...", "ops": [op, ...]}
or the short form {"file", "k", "jp", "ko": ...} which means ops=[{"op":"label","ko":...}].

ops
  label : find text lines/segments (by alpha, or by colour difference inside "box" on opaque
          pictures), erase them and draw "ko" in the same place/colour/height.
          ko = [line, ...]; line = "text" (replace all segments after "keep")
                                 | [seg_or_null, ...] (null = keep that segment)
          options: box, keep, sgap, lgap, font, align, grow, stroke, sfill, fill, reflow, squash
  erase : inpaint "boxes" (mask = pixels far from local median, or near "color")
  clear : make "boxes" transparent
  text  : draw text  {t, x, y, anchor, font, size, fill, stroke, sfill, angle, spacing, maxw, shadow}
  ransom: ransom-note collage letters {t, x, y, h}
  pink  : clear picture and draw outlined title {t, fill, stroke, outer}
python tools/images.py [--preview DIR] [filter]   -> writes before/after previews
"""
import os, sys, json, random
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gim

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
USR = os.path.join(ROOT, 'work/iso/PSP_GAME/USRDIR')
SPEC = os.path.join(ROOT, 'trans/images.json')
FONTS = {'L': 'NanumSquareNeo-aLt.ttf', 'R': 'NanumSquareNeo-bRg.ttf', 'B': 'NanumSquareNeo-cBd.ttf',
         'EB': 'NanumSquareNeo-dEb.ttf', 'H': 'NanumSquareNeo-eHv.ttf',
         'mL': 'SeoulHangangL.ttf', 'mM': 'SeoulHangangM.ttf', 'mB': 'SeoulHangangB.ttf', 'mEB': 'SeoulHangangEB.ttf',
         'g11': 'fonts/Galmuri11.ttf', 'g9': 'fonts/Galmuri9.ttf'}
_fc = {}

def font(name, size):
    key = (name, size)
    if key not in _fc:
        _fc[key] = ImageFont.truetype(os.path.join(ROOT, FONTS.get(name, name)), size)
    return _fc[key]

def load_spec():
    return json.load(open(SPEC, encoding='utf8'))

# ---------------------------------------------------------------- text rendering
TRACK = [0]
def render(t, fname, size, fill, stroke=0, sfill=(0, 0, 0, 255), spacing=0, align='left', squash=1.0, shadow=None):
    """returns tight RGBA image of the text block (multi-line with \n)."""
    f = font(fname, size)
    tr = TRACK[0]
    lines = t.split('\n')
    lh = size + spacing
    widths = [f.getlength(l) + tr * max(0, len(l) - 1) for l in lines] if lines else [0]
    W = int(max(widths) + 4 * stroke + 8 + (abs(shadow[0]) if shadow else 0))
    H = int(lh * len(lines) + size + 4 * stroke + 8 + (abs(shadow[1]) if shadow else 0))
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for i, l in enumerate(lines):
        x = 2 * stroke + 4
        if align == 'center': x += (max(widths) - widths[i]) / 2
        elif align == 'right': x += max(widths) - widths[i]
        y = 2 * stroke + 4 + i * lh
        chunks = [l] if not tr else list(l)
        for passno in ((0, 1) if shadow else (1,)):
            xx = x
            for c in chunks:
                if passno == 0:
                    d.text((xx + shadow[0], y + shadow[1]), c, font=f, fill=tuple(shadow[2]), stroke_width=stroke, stroke_fill=tuple(shadow[2]))
                xx += f.getlength(c) + tr
        if tr and stroke:   # strokes first so neighbours do not cover fills
            xx = x
            for c in chunks:
                d.text((xx, y), c, font=f, fill=tuple(sfill), stroke_width=stroke, stroke_fill=tuple(sfill)); xx += f.getlength(c) + tr
        xx = x
        for c in chunks:
            d.text((xx, y), c, font=f, fill=tuple(fill), stroke_width=0 if (tr and stroke) else stroke, stroke_fill=tuple(sfill)); xx += f.getlength(c) + tr
    bb = im.getbbox()
    if bb: im = im.crop(bb)
    if squash != 1.0 and im.width > 1:
        im = im.resize((max(1, round(im.width * squash)), im.height), Image.LANCZOS)
    return im

def ink_h(fname, size):
    m = font(fname, size).getmask('가힣한글')
    bb = m.getbbox()
    return bb[3] - bb[1] if bb else size

def size_for(fname, h):
    s = 6
    while ink_h(fname, s + 1) <= h: s += 1
    return s

def fit(t, fname, h, maxw, fill, stroke=0, sfill=(0, 0, 0, 255), grow=0, minsq=0.78, spacing=0, align='left', shadow=None):
    s = size_for(fname, h) + grow
    im = render(t, fname, s, fill, stroke, sfill, spacing, align, shadow=shadow)
    if maxw and im.width > maxw:
        sq = maxw / im.width
        if sq >= minsq:
            im = render(t, fname, s, fill, stroke, sfill, spacing, align, sq, shadow)
        else:
            while s > 6:
                s -= 1
                im = render(t, fname, s, fill, stroke, sfill, spacing, align, shadow=shadow)
                if im.width * minsq <= maxw: break
            if im.width > maxw:
                im = render(t, fname, s, fill, stroke, sfill, spacing, align, max(0.5, maxw / im.width), shadow)
    return im

# ---------------------------------------------------------------- analysis helpers
def ink_mask(a, box, opaque):
    x, y, w, h = box
    sub = a[y:y+h, x:x+w]
    if not opaque:
        return sub[..., 3] > 24
    rgb = sub[..., :3].astype(int)
    med = np.median(rgb.reshape(-1, 3), axis=0)
    return np.abs(rgb - med).sum(-1) > 90

def runs(v, gap):
    out = []; start = None; last = None
    for i, on in enumerate(v):
        if on:
            if start is None: start = i
            elif i - last > gap:
                out.append((start, last + 1)); start = i
            last = i
    if start is not None: out.append((start, last + 1))
    return out

def analyse(im, box=None, lgap=1, sgap=6, opaque=None, icons=False, nlines=None):
    a = np.array(im)
    H, W = a.shape[:2]
    box = box or [0, 0, W, H]
    if opaque is None: opaque = (a[..., 3] > 250).mean() > 0.6
    m = ink_mask(a, box, opaque)
    lines = []
    rr = runs(m.any(1), lgap)
    if nlines and len(rr) == 1:
        y0, y1 = rr[0]; step = (y1 - y0) / nlines
        rr = [(int(y0 + i * step), int(y0 + (i + 1) * step)) for i in range(nlines)]
    for y0, y1 in rr:
        cols = runs(m[y0:y1].any(0), sgap - 1)
        if icons:
            raw = runs(m[y0:y1].any(0), 1)
            parts = []
            for x0, x1 in raw:
                while x1 - x0 > 0:
                    span = lambda c: (lambda ys: ys[-1] - ys[0] if len(ys) else 0)(np.where(m[y0:y1, c])[0])
                    if x1 - x0 >= 14 and span(min(x0 + 3, x1 - 1)) >= 12 and span(min(x0 + 8, x1 - 1)) >= 14:
                        cand = range(x0 + 14, min(x0 + 20, x1))
                        cut = min(cand, key=lambda c: m[y0:y1, c].sum()) if len(cand) else x1
                        cut = cut + 1 if cut < x1 else x1
                        parts.append((x0, cut, True)); x0 = cut
                        while x0 < x1 and not m[y0:y1, x0].any(): x0 += 1
                    else:
                        parts.append((x0, x1, False)); break
            cols = []; cur = None
            for x0, x1, isicon in parts:
                if isicon:
                    if cur: cols.append(cur); cur = None
                    cols.append((x0, x1))
                elif cur and x0 - cur[1] < sgap: cur = (cur[0], x1)
                else:
                    if cur: cols.append(cur)
                    cur = (x0, x1)
            if cur: cols.append(cur)
        segs = [(box[0] + x0, box[1] + y0, box[0] + x1, box[1] + y1) for x0, x1 in cols]
        # tighten each segment vertically
        tight = []
        for (x0, yy0, x1, yy1) in segs:
            sub = m[yy0 - box[1]:yy1 - box[1], x0 - box[0]:x1 - box[0]]
            ys = np.where(sub.any(1))[0]
            tight.append((x0, yy0 + ys[0], x1, yy0 + ys[-1] + 1))
        lines.append(tight)
    return lines, opaque

def colours(im, bb, opaque):
    a = np.array(im.crop(bb)).reshape(-1, 4).astype(int)
    if opaque:
        med = np.median(a[:, :3], axis=0)
        d = np.abs(a[:, :3] - med).sum(-1)
        px = a[d > max(90, d.max() * 0.6)]
    else:
        px = a[a[:, 3] >= min(200, a[:, 3].max())]
    if len(px) == 0: return (255, 255, 255, 255), None
    q = (px[:, :3] // 24)
    keys, cnt = np.unique(q, axis=0, return_counts=True)
    main_k = keys[cnt.argmax()]
    sel = px[(q == main_k).all(1)]
    main = tuple(int(v) for v in sel[:, :3].mean(0)) + (255,)
    lum = lambda c: 0.3 * c[0] + 0.59 * c[1] + 0.11 * c[2]
    others = px[np.abs(0.3 * px[:, 0] + 0.59 * px[:, 1] + 0.11 * px[:, 2] - lum(main)) > 90]
    stroke = None
    if not opaque and len(others) > 0.3 * len(sel):
        stroke = tuple(int(v) for v in np.median(others[:, :3], 0)) + (255,)
    return main, stroke

def inpaint(im, mask, radius=4, alpha=False):
    import cv2
    a = np.array(im)
    m = (mask.astype(np.uint8) * 255)
    rgb = cv2.inpaint(np.ascontiguousarray(a[..., :3]), m, radius, cv2.INPAINT_TELEA)
    a[..., :3] = rgb
    if alpha:
        al = cv2.inpaint(np.ascontiguousarray(a[..., 3]), m, radius, cv2.INPAINT_TELEA)
        a[..., 3] = al
    return Image.fromarray(a, 'RGBA')

def dilate(m, n):
    if n <= 0: return m
    import cv2
    return cv2.dilate(m.astype(np.uint8), np.ones((2 * n + 1, 2 * n + 1), np.uint8)) > 0

def paste(im, t, x, y):
    layer = Image.new('RGBA', im.size, (0, 0, 0, 0))
    layer.paste(t, (int(round(x)), int(round(y))))
    return Image.alpha_composite(im, layer)

# ---------------------------------------------------------------- ops
def op_label(im, o):
    lines, opaque = analyse(im, o.get('box'), o.get('lgap', 1), o.get('sgap', 7), o.get('opaque'), o.get('icons', False), o.get('nlines'))
    ko = o['ko']
    if isinstance(ko, str): ko = [ko]
    if len(ko) != len(lines):
        raise ValueError(f'label: {len(lines)} lines found, {len(ko)} given: {[len(l) for l in lines]}')
    W, H = im.size
    box = o.get('box') or [0, 0, W, H]
    regL, regR = box[0], box[0] + box[2]
    draws = []
    a = np.array(im)
    for li, (segs, item) in enumerate(zip(lines, ko)):
        keep = o.get('keep', 0)
        if isinstance(item, str) or item is None:
            if item is None: continue
            groups = [(segs[keep:], item)]
            kept = segs[:keep]
        else:
            if len(item) != len(segs):
                raise ValueError(f'label line {li}: {len(segs)} segs, {len(item)} given')
            groups = [([s], t) for s, t in zip(segs, item) if t is not None]
            kept = [s for s, t in zip(segs, item) if t is None]
        for gsegs, t in groups:
            if not gsegs: continue
            x0 = min(s[0] for s in gsegs); y0 = min(s[1] for s in gsegs)
            x1 = max(s[2] for s in gsegs); y1 = max(s[3] for s in gsegs)
            fill, stroke = colours(im, (x0, y0, x1, y1), opaque)
            if 'fill' in o: fill = tuple(o['fill'])
            if 'sfill' in o: stroke = tuple(o['sfill'])
            sw = o.get('stroke', 1 if stroke else 0)
            # limits for the new text: next kept segment to the right / region edge
            nxt = [s[0] for s in segs if s[0] >= x1]
            right = (min(nxt) - 3) if nxt and not o.get('reflow') else regR - 1
            prv = [s[2] for s in segs if s[2] <= x0]
            left = (max(prv) + 2) if prv else regL
            cx = (x0 + x1) / 2
            align = o.get('align', 'auto')
            if align == 'auto':
                align = 'center' if abs(cx - (regL + regR) / 2) <= 3 and len(segs) == len(gsegs) and (x1 - x0) < (regR - regL) - 4 else 'left'
            if align == 'center': maxw = 2 * min(cx - left, right - cx)
            elif align == 'right': maxw = x1 - left
            else: maxw = right - x0
            h = o.get('h', y1 - y0)
            if o.get('hcap'): h = min(h, o['hcap'])
            fn = o.get('font', 'B')
            if 'size' in o:
                tim = render(t, fn, o['size'], fill, sw, stroke or (0, 0, 0, 255))
                if tim.width > maxw: tim = render(t, fn, o['size'], fill, sw, stroke or (0, 0, 0, 255), squash=maxw / tim.width)
            else:
                tim = fit(t, fn, h, int(maxw), fill, sw, stroke or (0, 0, 0, 255), o.get('grow', 1), o.get('minsq', 0.78))
            cy = (y0 + y1) / 2 + o.get('dy', 0)
            if align == 'center': tx = cx - tim.width / 2
            elif align == 'right': tx = x1 - tim.width
            else: tx = x0
            draws.append((tim, tx, cy - tim.height / 2, (x0, y0, x1, y1), kept, x1))
        # erase
        for gsegs, t in groups:
            if not gsegs: continue
            x0 = min(s[0] for s in gsegs) - 1; y0 = min(s[1] for s in gsegs) - 1
            x1 = max(s[2] for s in gsegs) + 1; y1 = max(s[3] for s in gsegs) + 1
            x0, y0 = max(0, x0), max(0, y0)
            if opaque:
                sub = np.zeros(a.shape[:2], bool)
                bx = [x0, y0, x1 - x0, y1 - y0]
                sub[y0:y1, x0:x1] = ink_mask(a, bx, True)
                im = inpaint(im, dilate(sub, 1), 3)
                a = np.array(im)
            else:
                a[y0:y1, x0:x1] = 0
                im = Image.fromarray(a, 'RGBA')
    if o.get('tail') and draws:
        x0, x1 = o['tail']
        orig = np.array(im)
        piece = Image.fromarray(orig[:, x0:x1].copy(), 'RGBA')
        orig[:, x0:x1] = 0; im = Image.fromarray(orig, 'RGBA')
        tim, tx = draws[-1][0], draws[-1][1]
        layer = Image.new('RGBA', im.size, (0, 0, 0, 0)); layer.paste(piece, (min(int(tx + tim.width + 3), W - piece.width), 0))
        im = Image.alpha_composite(im, layer)
    # reflow kept segments placed after replaced text (e.g. "文字速度 text")
    if o.get('reflow'):
        for tim, tx, ty, bb, kept, x1 in draws:
            for s in kept:
                if s[0] >= x1:
                    gap = s[0] - x1
                    piece = Image.fromarray(np.array(im)[s[1]:s[3], s[0]:s[2]].copy(), 'RGBA')
                    a = np.array(im); a[s[1]:s[3], s[0]:s[2]] = 0; im = Image.fromarray(a, 'RGBA')
                    nx = min(int(tx + tim.width + gap), W - piece.width)
                    layer = Image.new('RGBA', im.size, (0, 0, 0, 0)); layer.paste(piece, (nx, s[1]))
                    im = Image.alpha_composite(im, layer)
    for tim, tx, ty, *_ in draws:
        im = paste(im, tim, tx, ty)
    return im

def box_mask(im, boxes, color=None, thr=None, opaque=None, grow=1):
    a = np.array(im)
    M = np.zeros(a.shape[:2], bool)
    for b in boxes:
        x, y, w, h = b[:4]
        sub = a[y:y+h, x:x+w].astype(int)
        if b[4:] and b[4] == 'all':
            m = np.ones(sub.shape[:2], bool)
        elif color is not None:
            m = np.abs(sub[..., :3] - np.array(color[:3])).sum(-1) < (thr or 120)
            m &= sub[..., 3] > 24
        else:
            med = np.median(sub[..., :3].reshape(-1, 3), 0)
            m = np.abs(sub[..., :3] - med).sum(-1) > (thr or 80)
        M[y:y+h, x:x+w] |= m
    return dilate(M, grow)

def op_erase(im, o):
    m = box_mask(im, o['boxes'], o.get('color'), o.get('thr'), grow=o.get('grow', 1))
    return inpaint(im, m, o.get('radius', 4), o.get('alpha', False))

def op_clear(im, o):
    a = np.array(im)
    for x, y, w, h in o['boxes']: a[y:y+h, x:x+w] = 0
    return Image.fromarray(a, 'RGBA')

def op_template(im, o):
    """fill masked pixels from sibling pictures that share the same artwork (where their own text is absent)."""
    a = np.array(im)
    me = box_mask(im, o['boxes'], o.get('color'), o.get('thr'), grow=o.get('grow', 2))
    left = me.copy()
    for src in o['src']:
        f, k = src[0], src[1]
        b = open(os.path.join(USR, f), 'rb').read()
        sim = gim.to_png(b, k, src[2] if len(src) > 2 else 0)
        sm = box_mask(sim, o['boxes'], o.get('color'), o.get('thr'), grow=o.get('grow', 2))
        sa = np.array(sim)
        take = left & ~sm
        a[take] = sa[take]
        left &= ~take
    im = Image.fromarray(a, 'RGBA')
    if left.any(): im = inpaint(im, left, 4)
    return im

def op_copy(im, o):
    a = np.array(im); src = a.copy()
    for x, y, w, h, dx, dy in o['boxes']: a[y:y+h, x:x+w] = src[y+dy:y+dy+h, x+dx:x+dx+w]
    return Image.fromarray(a, 'RGBA')

def op_rect(im, o):
    a = np.array(im)
    for x, y, w, h in o['boxes']: a[y:y+h, x:x+w] = o['color']
    return Image.fromarray(a, 'RGBA')

def wrap(t, fname, size, width):
    f = font(fname, size); out = []
    for para in t.split(chr(10)):
        line = ''
        for w in para.split(' '):
            cand = (line + ' ' + w) if line else w
            if f.getlength(cand) + TRACK[0] * len(cand) <= width: line = cand
            else:
                out.append(line); line = w
        out.append(line)
    return chr(10).join(out)

def op_text(im, o):
    fn = o.get('font', 'B')
    if o.get('wrap'): o = dict(o, t=wrap(o['t'], fn, o['size'], o['wrap']))
    fill = tuple(o.get('fill', (255, 255, 255, 255)))
    sf = tuple(o.get('sfill', (0, 0, 0, 255)))
    sh = o.get('shadow')
    if 'size' in o:
        tim = render(o['t'], fn, o['size'], fill, o.get('stroke', 0), sf, o.get('spacing', 0), o.get('align', 'left'), o.get('squash', 1.0), sh)
        if o.get('maxw') and tim.width > o['maxw']:
            tim = tim.resize((o['maxw'], tim.height), Image.LANCZOS)
    else:
        tim = fit(o['t'], fn, o['h'], o.get('maxw'), fill, o.get('stroke', 0), sf, 0, o.get('minsq', 0.78), o.get('spacing', 0), o.get('align', 'left'), sh)
    if o.get('angle'):
        tim = tim.rotate(o['angle'], Image.BICUBIC, expand=True)
    anc = o.get('anchor', 'lt')
    x, y = o['x'], o['y']
    if anc[0] == 'm': x -= tim.width / 2
    elif anc[0] == 'r': x -= tim.width
    if anc[1] == 'm': y -= tim.height / 2
    elif anc[1] == 'b': y -= tim.height
    return paste(im, tim, x, y)

def op_ransom(im, o):
    """collage of paper scraps, one per character (white/black/red/gray), slightly rotated."""
    rnd = random.Random(o.get('seed', 7))
    styles = o.get('styles') or ['wb', 'rw', 'wb', 'gw', 'bw', 'wr', 'wb', 'bw']
    pal = {'w': (250, 250, 248, 255), 'b': (20, 18, 20, 255), 'r': (215, 20, 50, 255), 'g': (120, 120, 120, 255)}
    x, y, h = o['x'], o['y'], o['h']
    fonts = o.get('fonts', ['H', 'mEB'])
    for i, ch in enumerate(o['t']):
        if ch == ' ':
            x += h * 0.3; continue
        st = styles[i % len(styles)]
        sc = o.get('scales', [1.0, 0.8, 0.92, 0.78, 0.95, 0.84])[i % 6] if not o.get('flat') else 1.0
        ch_h = int(h * sc)
        fn = fonts[i % len(fonts)]
        g = render(ch, fn, max(6, int(ch_h * 0.95)), pal[st[1]])
        pad = max(1, ch_h // 10)
        sw = g.width + 2 * pad; shh = g.height + 2 * pad
        scrap = Image.new('RGBA', (sw + 4, shh + 4), (0, 0, 0, 0))
        d = ImageDraw.Draw(scrap)
        j = lambda: rnd.randint(-1, 1)
        poly = [(2 + j(), 2 + j()), (sw + 1 + j(), 2 + j()), (sw + 1 + j(), shh + 1 + j()), (2 + j(), shh + 1 + j())]
        d.polygon(poly, fill=pal[st[0]])
        if st[0] == 'w':
            d.line(poly + [poly[0]], fill=(150, 150, 150, 255), width=1)
        else:
            d.line(poly + [poly[0]], fill=(245, 245, 245, 255), width=1)
        scrap.alpha_composite(g, (2 + pad, 2 + pad))
        ang = rnd.choice([-1, 1]) * rnd.uniform(5, 14) if not o.get('flat') else 0
        scrap = scrap.rotate(ang, Image.BICUBIC, expand=True)
        # drop shadow
        shd = Image.new('RGBA', scrap.size, (0, 0, 0, 0))
        al = scrap.split()[3].point(lambda v: v * 0.6)
        shd.putalpha(al)
        base_y = y + (h - ch_h) * (0.75 if i % 2 else 0.1)
        im = paste(im, shd, x + 1, base_y + 2)
        im = paste(im, scrap, x, base_y)
        x += scrap.width - max(3, h // 5)
    return im

def op_pink(im, o):
    a = np.array(im)
    W, H = im.size
    if o.get('clear', True): a[:] = 0
    im = Image.fromarray(a, 'RGBA')
    fn = o.get('font', 'H')
    t = o['t']
    s = o.get('size', 20)
    fill = tuple(o.get('fill', (240, 85, 105, 255))); white = tuple(o.get('sfill', (255, 255, 255, 255)))
    dark = tuple(o.get('outer', (105, 25, 35, 255))); sw = o.get('stroke', 2)
    lay = [render(t, fn, s, dark, sw + 2, dark, spacing=o.get('spacing', 0), align='center'),
           render(t, fn, s, white, sw, white, spacing=o.get('spacing', 0), align='center'),
           render(t, fn, s, fill, 0, spacing=o.get('spacing', 0), align='center')]
    maxw = W - 2
    if lay[0].width > maxw:
        r = maxw / lay[0].width
        lay = [l.resize((max(1, int(l.width * r)), l.height), Image.LANCZOS) for l in lay]
    x = (W - lay[0].width) / 2 + o.get('dx', 0); y = (H - lay[0].height) / 2 + o.get('dy', 0)
    im = paste(im, lay[0], x + 1, y + 2)
    im = paste(im, lay[0], x, y)
    for l in lay[1:]:
        im = paste(im, l, x + (lay[0].width - l.width) / 2, y + (lay[0].height - l.height) / 2)
    return im

def _edge(col_alpha):
    ys = np.where(col_alpha > 128)[0]
    return ys[-1] if len(ys) else 0

def op_rebar(im, o):
    """rebuild the slanted title bar (dark band + white stripe) under ransom letters, then draw new letters."""
    a = np.array(im).astype(np.int32)
    H, W = a.shape[:2]
    c0, c1 = o.get('c0', 300), o.get('c1', 420)
    e0, e1 = _edge(a[:, c0, 3]), _edge(a[:, c1, 3])
    slope = (e1 - e0) / (c1 - c0)
    model = np.zeros_like(a)
    for x in range(W):
        sh = int(round(slope * (x - c0)))
        col = a[:, c0]
        if sh >= 0:
            model[sh:, x] = col[:H - sh] if sh < H else 0
            model[:sh, x] = col[0]
        else:
            model[:H + sh, x] = col[-sh:]
            model[H + sh:, x] = 0
    diff = np.abs(model - a).sum(-1) > 60
    cols = np.where(diff.any(0))[0]
    x1 = (cols[cols < W * 0.6].max() + 3) if len(cols) else 0
    out = a.copy(); out[:, :x1] = model[:, :x1]
    im = Image.fromarray(out.astype(np.uint8), 'RGBA')
    r = dict(o); r.setdefault('x', 3); r.setdefault('y', 1); r.setdefault('h', int(H * 0.66))
    return op_ransom(im, r)

def op_glow(im, o):
    """one big glyph with a blurred colour glow (game over tiles)."""
    W, H = im.size
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    g = render(o['t'], o.get('font', 'mEB'), o.get('size', 36), tuple(o.get('fill', (8, 5, 15, 255))), 1, (8, 5, 15, 255))
    gl = render(o['t'], o.get('font', 'mEB'), o.get('size', 36), tuple(o.get('glow', (140, 160, 255, 255))), 3, tuple(o.get('glow', (140, 160, 255, 255))))
    gl = gl.filter(ImageFilter.GaussianBlur(2))
    x = (W - gl.width) / 2; y = (H - gl.height) / 2
    im = paste(im, gl, x, y)
    im = paste(im, g, x + (gl.width - g.width) / 2, y + (gl.height - g.height) / 2)
    return im

def op_yesno(im, o):
    """dialog buttons: pink strips with (icon + white text); replace the text part with o['t'] list."""
    a = np.array(im)
    col = np.array(o.get('strip', (241, 89, 103)))
    strip = (np.abs(a[..., :3].astype(int) - col).sum(-1) < 40) & (a[..., 3] > 100)
    ys = np.where(strip.sum(1) > 20)[0]
    if not len(ys): return im
    y0, y1 = ys.min(), ys.max() + 1
    xs = [r for r in runs(strip[y0:y1].sum(0) > 0, 14) if r[1] - r[0] > 30]
    stripcol = a[y1 - 2, xs[0][1] - 2].copy()
    for (x0, x1), t in zip(xs, o['t']):
        cx0 = x0 + o.get('icon', 23)
        a[max(0, y0 - 12):y1 + 2, cx0:x1 + 1] = 0
        a[y0:y1, cx0:x1] = stripcol
        im = Image.fromarray(a, 'RGBA')
        tim = render(t, o.get('font', 'EB'), o.get('size', 13), (255, 255, 255, 255), 1, tuple(o.get('sfill', (90, 25, 35, 255))))
        im = paste(im, tim, (cx0 + x1) / 2 - tim.width / 2, y1 - 1 - tim.height)
        a = np.array(im)
    return im

def op_hilite(im, o):
    """title menu selected item: white text, dark red outline, pink glow; keeps a pink bar if present."""
    a = np.array(im).astype(np.int32)
    H, W = a.shape[:2]
    if o.get('bar'):
        # rebuild bar from its own text-free column profile (left edge column per x is a horizontal gradient)
        row = a[2].copy()
        for y in range(H):
            if a[y, :, 3].max() > 0: pass
        prof = a[:, 3:4].copy()
        ys = np.where(a[:, :, 3].max(1) > 0)[0]
        bar = a.copy()
        for y in range(H): bar[y] = a[y] if y < ys.min() or y > ys.max() else a[ys.min() + 1]
        # horizontal gradient from the clean top row of the bar
        top = a[ys.min() + 1]
        for y in range(ys.min(), ys.max() + 1): bar[y] = top
        a = bar
    else:
        a[:] = 0
    im = Image.fromarray(a.astype(np.uint8), 'RGBA')
    fn, sz = o.get('font', 'H'), o.get('size', 15)
    glow = render(o['t'], fn, sz, (250, 110, 125, 255), 4, (250, 110, 125, 255)).filter(ImageFilter.GaussianBlur(1.5))
    out = render(o['t'], fn, sz, (110, 15, 30, 255), 2, (110, 15, 30, 255))
    inn = render(o['t'], fn, sz, (255, 255, 255, 255))
    cx, cy = o.get('cx', W / 2), o.get('cy', H / 2)
    for l in (glow, out, inn): im = paste(im, l, cx - l.width / 2, cy - l.height / 2)
    return im

def op_greylogo(im, o):
    """omake_select locked logos: erase reddish logo text on grey paper (outside keep boxes), draw dark text."""
    a = np.array(im).astype(int)
    red = (a[..., 0] - a[..., 2] > 18) & (a[..., 3] > 200)
    if o.get('dark'):
        x, y, w, h = o['dark']; dk = np.zeros(red.shape, bool)
        lum = a[..., :3].sum(-1)
        dk[y:y+h, x:x+w] = (lum[y:y+h, x:x+w] < o.get('dthr', 200)) & (a[y:y+h, x:x+w, 3] > 60)
        red |= dk
    keep = np.zeros(red.shape, bool)
    for x, y, w, h in o.get('keep', []): keep[y:y+h, x:x+w] = True
    m = dilate(red & ~keep, 2) & ~keep & (a[..., 3] > 60)
    if o.get('dark'):
        lum = a[..., :3].sum(-1)
        paper = (~m) & (lum > 175) & (lum < 240) & (a[..., 3] > 250)
        med = np.median(a[paper][:, :4], 0).astype(int)
        b2 = a.copy(); b2[m] = med
        im = Image.fromarray(b2.astype(np.uint8), 'RGBA')
        im = Image.fromarray(np.where(m[..., None], np.array(im.filter(ImageFilter.GaussianBlur(1))), b2).astype(np.uint8), 'RGBA')
    else:
        im = inpaint(im, m, 4)
    t = o['t']; fn = o.get('font', 'H'); s = o.get('size', 20)
    out = render(t, fn, s, (45, 20, 22, 255), 3, (45, 20, 22, 255), spacing=o.get('spacing', 0), align='center')
    inn = render(t, fn, s, (115, 40, 45, 255), 0, spacing=o.get('spacing', 0), align='center')
    if out.width > o.get('maxw', 150):
        r = o.get('maxw', 150) / out.width
        out = out.resize((int(out.width * r), out.height), Image.LANCZOS); inn = inn.resize((max(1, int(inn.width * r)), inn.height), Image.LANCZOS)
    cx, cy = o['cx'], o['cy']
    im = paste(im, out, cx - out.width / 2, cy - out.height / 2)
    im = paste(im, inn, cx - inn.width / 2, cy - inn.height / 2)
    return im

def op_titlelogo(im, o):
    """title logo: redraw the plaid letters (black rim, white ring, brown line) and the ribbon caption."""
    W, H = im.size
    a = np.array(im)
    rib = Image.new('L', im.size, 0); ImageDraw.Draw(rib).polygon([tuple(p) for p in o['ribbon']], fill=255)
    rib = np.array(rib) > 0
    # ribbon caption: erase dark text inside the inner polygon, draw the new one
    inner = Image.new('L', im.size, 0); ImageDraw.Draw(inner).polygon([tuple(p) for p in o['inner']], fill=255)
    inner = np.array(inner) > 0
    txt = dilate(inner & (a[..., :3].astype(int).sum(-1) < o.get('thr', 560)), 1) & inner
    r = inpaint(im, txt, 3)
    cap = render(o['cap'], o.get('cfont', 'mEB'), o.get('csize', 20), tuple(o.get('cfill', (75, 25, 25, 255))))
    bb = cap.getbbox(); cap = cap.crop(bb)
    if cap.width > o.get('cmaxw', 150):
        cap = cap.resize((o['cmaxw'], cap.height), Image.LANCZOS)
    cap = cap.rotate(o.get('cangle', -5), Image.BICUBIC, expand=True)
    cx, cy = o['ccenter']
    r = paste(r, cap, cx - cap.width / 2, cy - cap.height / 2)
    ribbon = np.array(r); ribbon[~rib] = 0
    # letters
    M = Image.new('L', im.size, 0)
    for ch, x, y, ang, sz in o['chars']:
        f = font(o.get('font', 'H'), sz)
        g = Image.new('L', (sz * 2, sz * 2), 0)
        ImageDraw.Draw(g).text((sz, sz), ch, font=f, fill=255, anchor='mm')
        g = g.rotate(ang, Image.BICUBIC)
        M.paste(Image.new('L', g.size, 255), (int(x - sz), int(y - sz)), g)
    m = np.array(M).astype(np.float32) / 255
    import cv2
    def grow(n, blur=0):
        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * n + 1, 2 * n + 1))
        g = cv2.dilate(m, k)
        return cv2.GaussianBlur(g, (0, 0), blur) if blur else g
    yy, xx = np.mgrid[0:H, 0:W]
    y0, y1 = o.get('grad', (20, 115))
    t = np.clip((yy - y0) / (y1 - y0), 0, 1)[..., None]
    top = np.array(o.get('top', (255, 216, 112))); bot = np.array(o.get('bot', (208, 96, 40)))
    base = top * (1 - t) + bot * t
    P = o.get('period', 14)
    d1 = ((xx + yy) % P < 3); d2 = ((xx - yy) % P < 3)
    l1 = ((xx + yy) % P == 7) | ((xx - yy) % P == 7)
    shade = 1 - 0.09 * d1 - 0.09 * d2 + 0.07 * l1
    plaid = np.clip(base * shade[..., None], 0, 255)
    out = np.zeros((H, W, 4), np.float32)
    def over(col, al):
        al = np.clip(al, 0, 1)[..., None]
        c = np.broadcast_to(np.array(col, np.float32)[:3] if np.ndim(col) == 1 else col, (H, W, 3))
        oa = out[..., 3:] / 255
        na = al + oa * (1 - al)
        out[..., :3] = np.where(na > 0, (c * al + out[..., :3] * oa * (1 - al)) / np.maximum(na, 1e-6), 0)
        out[..., 3:] = na * 255
    over(np.array((0, 0, 0)), grow(o.get('rim', 8), 1.2))
    over(np.array((255, 255, 255)), grow(3))
    over(np.array((95, 45, 20)), grow(1))
    over(plaid, m)
    logo = Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), 'RGBA')
    return Image.alpha_composite(logo, Image.fromarray(ribbon, 'RGBA'))

OPS = dict(titlelogo=op_titlelogo, label=op_label, erase=op_erase, clear=op_clear, text=op_text, ransom=op_ransom, pink=op_pink, rebar=op_rebar, rect=op_rect, yesno=op_yesno, hilite=op_hilite, greylogo=op_greylogo, copy=op_copy, template=op_template, glow=op_glow)

def apply(im, entry):
    ops = entry.get('ops') or [{'op': 'label', **{k: v for k, v in entry.items() if k not in ('file', 'k', 'jp')}}]
    for o in ops:
        TRACK[0] = o.get('track', 0)
        im = OPS[o['op']](im, o)
        TRACK[0] = 0
    return im

# ---------------------------------------------------------------- GIM writing with fresh palette
def write_requant(b, im, k, f=0):
    I = gim.info(b, k, f)
    pfmt, n, off = I['pal']
    assert I['fmt'] in (4, 5) and pfmt == 3
    a = np.array(im.convert('RGBA'))
    a[a[..., 3] == 0] = 0
    im = Image.fromarray(a, 'RGBA')
    uniq = np.unique(a.reshape(-1, 4), axis=0)
    if len(uniq) <= n:
        cols = [tuple(int(v) for v in c) for c in uniq]
    else:
        if (a[..., 3] == 255).all():
            q = im.convert('RGB').quantize(n, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
            p = q.getpalette()[:3 * n]
            cols = [tuple(p[i*3:i*3+3]) + (255,) for i in range(len(p) // 3)]
        else:
            q = im.quantize(n, method=Image.Quantize.FASTOCTREE, dither=Image.Dither.NONE)
            p = q.getpalette(rawmode='RGBA')[:4 * n]
            cols = [tuple(p[i*4:i*4+4]) for i in range(len(p) // 4)]
    cols = (cols + [(0, 0, 0, 0)] * n)[:n]
    out = bytearray(b)
    for i, c in enumerate(cols): out[off + 4*i: off + 4*i + 4] = bytes(c)
    cand = [gim.from_png(bytes(out), im, k, f)]
    if len(uniq) > n:
        # also try a palette built by k-means, and the original palette; keep the closest result
        try:
            import cv2
            data = a.reshape(-1, 4).astype(np.float32)
            crit = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 12, 1.0)
            init = np.array([c for c in cols], np.float32)
            _, lab, cen = cv2.kmeans(data, n, None, crit, 1, cv2.KMEANS_PP_CENTERS)
            out2 = bytearray(b)
            for i, c in enumerate(np.clip(np.round(cen), 0, 255).astype(np.uint8)):
                out2[off + 4*i: off + 4*i + 4] = bytes(c)
            cand.append(gim.from_png(bytes(out2), im, k, f))
        except Exception:
            pass
        cand.append(gim.from_png(b, im, k, f))
        ref = a.astype(int)
        cand.sort(key=lambda c: np.abs(np.array(gim.to_png(c, k, f)).astype(int) - ref).sum())
    return cand[0]

# ---------------------------------------------------------------- API used by build.py
def _korean(o):
    s = ''
    for key in ('ko', 't'):
        v = o.get(key)
        if isinstance(v, str): s += v
        elif isinstance(v, list):
            for x in v:
                if isinstance(x, str): s += x
                elif isinstance(x, list): s += ''.join(y for y in x if y)
    return s

def text():
    s = ''
    for e in load_spec():
        for o in e.get('ops') or [e]: s += _korean(o)
    return s.replace(chr(10), '')

def results(flt=None):
    """yields (entry, original image, new image)"""
    for e in load_spec():
        if flt and flt not in f"{e['file']}#{e['k']}": continue
        b = open(os.path.join(USR, e['file']), 'rb').read()
        im = gim.to_png(b, e['k'], e.get('f', 0))
        yield e, im, apply(im.copy(), e)

def patched():
    files = {}
    for e in load_spec():
        files.setdefault(e['file'], []).append(e)
    out = []
    for f, es in sorted(files.items()):
        b = open(os.path.join(USR, f), 'rb').read()
        for e in es:
            fr = e.get('f', 0)
            im = apply(gim.to_png(b, e['k'], fr), e)
            b = write_requant(b, im, e['k'], fr)
        out.append(('/PSP_GAME/USRDIR/' + f.replace('\\', '/'), b))
    return out

# home-menu pictures: the title logo (title.gim #12) and English caption (#13) sit at these scale/offsets
HOME = {'ICON0.PNG': ((0.39, 4, 19), (0.4, 7, 15)), 'PIC1.PNG': ((0.66, 248, 168), (0.665, 254, 162))}

def home_pngs():
    """yields (iso path, png bytes) for ICON0/PIC1 with the Korean logo pasted over the Japanese one"""
    import cv2, io
    b = open(os.path.join(USR, 'Menu/title/title.gim'), 'rb').read()
    old, en = gim.to_png(b, 12), gim.to_png(b, 13)
    e = [x for x in load_spec() if x['file'] == 'Menu/title/title.gim' and x['k'] == 12][0]
    new = apply(old.copy(), e)
    def alpha_at(pic, shape, s, x, y):
        w, h = int(pic.width * s), int(pic.height * s)
        a = np.zeros(shape, np.uint8); a[y:y+h, x:x+w] = np.array(pic.resize((w, h), Image.LANCZOS))[..., 3]
        return a, (w, h)
    for f, ((s, x, y), (s2, x2, y2)) in HOME.items():
        O = np.array(Image.open(os.path.join(USR, '..', f)).convert('RGB'))
        a, (w, h) = alpha_at(old, O.shape[:2], s, x, y)
        m = cv2.dilate((a > 40).astype(np.uint8), np.ones((3, 3), np.uint8))
        Q = Image.fromarray(cv2.inpaint(np.ascontiguousarray(O), m * 255, 5, cv2.INPAINT_TELEA)).convert('RGBA')
        Q.alpha_composite(new.resize((w, h), Image.LANCZOS), (x, y))
        N = np.array(Q.convert('RGB'))
        a2, _ = alpha_at(en, O.shape[:2], s2, x2, y2)
        k = cv2.dilate((a2 > 20).astype(np.uint8), np.ones((3, 3), np.uint8)) > 0
        N[k] = O[k]
        bio = io.BytesIO(); Image.fromarray(N).save(bio, 'PNG', optimize=True)
        yield '/PSP_GAME/' + f, bio.getvalue()

def preview(outdir, flt=None, scale=2):
    os.makedirs(outdir, exist_ok=True)
    for e in load_spec():
        fr = e.get('f', 0)
        if flt and flt not in f"{e['file']}#{e['k']}.{fr}": continue
        b = open(os.path.join(USR, e['file']), 'rb').read()
        im = gim.to_png(b, e['k'], fr)
        try:
            new = apply(im.copy(), e)
        except Exception as ex:
            print('ERR', e['file'], e['k'], ex); continue
        nb = write_requant(b, new, e['k'], fr)
        new = gim.to_png(nb, e['k'], fr)
        W, H = im.size
        c = Image.new('RGBA', (W, 2 * H + 4), (40, 110, 60, 255))
        c.alpha_composite(im, (0, 0)); c.alpha_composite(new, (0, H + 4))
        if scale != 1: c = c.resize((c.width * scale, c.height * scale), Image.NEAREST)
        name = e['file'].replace('/', '_')[:-4] + f"#{e['k']:02d}.{fr:02d}.png"
        c.convert('RGB').save(os.path.join(outdir, name))
    print('preview ->', outdir)

if __name__ == '__main__':
    args = sys.argv[1:]
    if args and args[0] == '--preview':
        preview(args[1], args[2] if len(args) > 2 else None)
    elif args and args[0] == '--analyse':
        b = open(os.path.join(USR, args[1]), 'rb').read()
        lines, op = analyse(gim.to_png(b, int(args[2])), json.loads(args[3]) if len(args) > 3 else None)
        print('opaque' if op else 'alpha', gim.to_png(b, int(args[2])).size)
        for l in lines: print(l)

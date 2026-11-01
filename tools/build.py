"""Build the Korean ISO.  python tools/build.py [--test]"""
import sys, os, json, glob, re, struct, time
sys.path.insert(0, os.path.dirname(__file__))
from blt import parse, build as blt_build
from kfont import charmap, build as font_build
from isobuild import Iso
import ebootpatch, images
from check_ko import check

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
SRC_ISO = os.path.join(ROOT, 'Tanteibu - The Detective Club - Tantei to Yuurei to Kaitou to (Japan) (v1.01).iso')
OUT_ISO = os.path.join(ROOT, 'Tanteibu - The Detective Club (Korean).iso')
USR = os.path.join(ROOT, 'work/iso/PSP_GAME/USRDIR')
TTF = os.path.join(ROOT, 'NanumSquareNeo-cBd.ttf')
TAG = {'<5>': 0x8005, '<8>': 0x8008}

def encode(s, cm):
    out = []
    for tok in re.findall(r'<[0-9A-F]+>|\n|.', s, re.S):
        if tok == '\n': out.append(0x8001)
        elif tok.startswith('<') and len(tok) > 1: out.append(int(tok[1:-1], 16) | 0x8000)
        else: out.append(cm[tok])
    return out

def sfo_title(d, title):
    d = bytearray(d)
    _, _, kt, dt, n = struct.unpack_from('<IIIII', d, 0)
    for i in range(n):
        ko, fmt, ln, mx, do = struct.unpack_from('<HHIII', d, 20 + i*16)
        if d[kt+ko: kt+ko+6] == b'TITLE' + bytes(1):
            v = title.encode() + bytes(1)
            assert len(v) <= mx
            d[dt+do: dt+do+mx] = v + bytes(mx - len(v))
            struct.pack_into('<I', d, 20 + i*16 + 4, len(v))
    return bytes(d)

def sfo_add_int(d, key, val):
    """rebuild the SFO with an extra int entry (keys stay sorted)"""
    _, _, kt, dt, n = struct.unpack_from('<IIIII', d, 0)
    ent = []
    for i in range(n):
        ko, fmt, ln, mx, do = struct.unpack_from('<HHIII', d, 20 + i*16)
        ent.append((d[kt+ko:d.index(b'\0', kt+ko)], fmt, ln, mx, d[dt+do:dt+do+mx]))
    ent.append((key.encode(), 0x404, 4, 4, struct.pack('<I', val)))
    ent.sort()
    keys = b''.join(e[0] + b'\0' for e in ent); keys += bytes(-len(keys) % 4)
    kt = 20 + 16 * len(ent); dt = kt + len(keys)
    hdr = struct.pack('<4sIIII', b'\0PSF', 0x101, kt, dt, len(ent))
    idx = b''; data = b''; ko = 0
    for k, fmt, ln, mx, v in ent:
        idx += struct.pack('<HHIII', ko, fmt, ln, mx, len(data)); ko += len(k) + 1; data += v
    return hdr + idx + keys + data

def main():
    t0 = time.time()
    names = [os.path.basename(f)[:-4] for f in sorted(glob.glob(os.path.join(USR, 'Script/*.blt')))]
    ko = {}
    for n in names:
        p = os.path.join(ROOT, f'work/ko/{n}.json')
        if os.path.exists(p):
            try:
                if check(n): print('skip (check errors)', n); continue
            except Exception as e: print('skip', n, e); continue
            ko[n] = json.load(open(p, encoding='utf8'))
    alltext = ''.join(''.join(v) for v in ko.values()) + ebootpatch.text() + images.text()
    cm = charmap(alltext)
    os.makedirs(os.path.join(ROOT, 'work/out'), exist_ok=True)
    fpath = os.path.join(ROOT, 'work/out/font.gim')
    font_build(cm, TTF, 13, fpath)
    iso = Iso(SRC_ISO, OUT_ISO)
    iso.replace('/PSP_GAME/USRDIR/Font/font.gim', open(fpath, 'rb').read())
    for n in names:
        if n not in ko: continue
        d = open(os.path.join(USR, f'Script/{n}.blt'), 'rb').read()
        h, secs, strs, tail = parse(d)
        assert len(ko[n]) == len(strs), n
        new = [encode(s, cm) for s in ko[n]]
        iso.replace(f'/PSP_GAME/USRDIR/Script/{n}.blt', blt_build(h, secs, new, tail))
    eb = ebootpatch.patch()
    if eb: iso.replace('/PSP_GAME/SYSDIR/EBOOT.BIN', eb)
    iso.replace('/PSP_GAME/PARAM.SFO', sfo_add_int(sfo_title(open(os.path.join(ROOT, 'work/iso/PSP_GAME/PARAM.SFO'), 'rb').read(),
                                                   '탐정부 THE DETECTIVE CLUB -탐정과 유령과 괴도와-'), 'MEMSIZE', 1))
    for path, data in images.patched():
        iso.replace(path, data)
    iso.close()
    print(f'built {OUT_ISO} scripts={len(ko)}/{len(names)} {time.time()-t0:.1f}s')

if __name__ == '__main__':
    main()

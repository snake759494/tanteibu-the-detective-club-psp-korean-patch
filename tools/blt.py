"""BLT script: header (magic, 0xea60, 4x offset, 4x size); sec2 = u32 byte offsets into sec3; sec3 = u16 glyph strings ended by 0x8000."""
import struct
def parse(d):
    h = struct.unpack_from('<10I', d, 0)
    offs, sizes = list(h[2:6]), list(h[6:10])
    secs = [d[o:o+s] for o, s in zip(offs, sizes)]
    n = sizes[1] // 4
    ptr = struct.unpack_from('<%dI' % n, secs[1])
    strs = []
    for p in ptr:
        w = []; i = p
        while True:
            v = struct.unpack_from('<H', secs[2], i)[0]; i += 2
            if v == 0x8000: break
            w.append(v)
        strs.append(w)
    return h, secs, strs, d[offs[3]+sizes[3]:]

def build(h, secs, strs, tail):
    data = bytearray(); ptr = []
    for w in strs:
        ptr.append(len(data))
        data += struct.pack('<%dH' % (len(w)+1), *w, 0x8000)
    s1 = struct.pack('<%dI' % len(ptr), *ptr)
    sec = [secs[0], s1, bytes(data), secs[3]]
    out = bytearray(0x28); o = 0x28; offs = []
    for s in sec:
        offs.append(o); out += s; o += len(s)
    struct.pack_into('<10I', out, 0, h[0], h[1], *offs, *[len(s) for s in sec])
    out += bytes(16 - len(out) % 16)
    return bytes(out)

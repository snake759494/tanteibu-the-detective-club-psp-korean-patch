"""EBOOT: plain (decrypted) ELF with translated UTF-8 save-dialog strings, written in place."""
import os, json
ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
DEC = os.path.join(ROOT, 'work/eboot/EBOOT.dec')
TR = os.path.join(ROOT, 'trans/eboot.json')
def _load():
    if os.environ.get('NO_EBSTR'): return []
    return json.load(open(TR, encoding='utf8')) if os.path.exists(TR) else []
def text():
    return ''.join(e['ko'] for e in _load() if not e.get('keep'))
# renderer (0x4b3dc..): x = column * (spacing + 14)  ->  x = pixel accumulator, slots with slot % 448 < 10 (space 、。，．・：；？！) advance half
CODE = {
    0x4b470: [0x8c980040,                 # lw    t8, 0x40(a0)
              0xa6580008,                 # sh    t8, 8(s2)
              0x8481001c,                 # lh    at, 0x1c(a0)
              0x2421000e,                 # addiu at, at, 14
              0x2e36000a,                 # sltiu s6, s1, 10   (slot % 448 < 10 -> half width)
              0x02c10806],                # srlv  at, at, s6
    0x4b554: [0x0301c021],                # addu  t8, t8, at
}
HEAP_GLOBAL = 0x9b6d8
def code(d):
    import struct
    old = {0x4b470: [0x8498001c, 0x8c960040, 0x2718000e, 0x02d80018, 0x0000c012, 0xa6580008], 0x4b554: [0x27180001]}
    for a, ws in CODE.items():
        for i, w in enumerate(ws):
            o = 0xc0 + a + i * 4
            assert struct.unpack_from('<I', d, o)[0] == old[a][i], hex(a + i * 4)
            struct.pack_into('<I', d, o, w)
    # HeapGlobal VPL 16MB -> 24MB (needs MEMSIZE=1 in PARAM.SFO); the stock pool runs dry at the first script on some play paths
    assert struct.unpack_from('<I', d, 0xc0 + HEAP_GLOBAL)[0] == 0x1000000
    struct.pack_into('<I', d, 0xc0 + HEAP_GLOBAL, 0x1800000)

def patch():
    ent = _load()
    d = bytearray(open(DEC, 'rb').read())
    code(d)
    for e in ent:
        if e.get('keep'): continue
        off = int(e['off'], 16)
        jp = e['jp'].encode('utf-8'); ko = e['ko'].encode('utf-8')
        assert d[off:off+len(jp)] == jp, e['off']
        room = len(jp)
        while d[off+room] == 0 and room < len(jp) + 3 and (off + room + 1) % 4: room += 1
        assert len(ko) <= len(jp), (e['off'], len(ko), len(jp))
        d[off:off+len(jp)] = ko + bytes(len(jp) - len(ko))
    return bytes(d)

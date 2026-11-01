"""Original font slot <-> char (JIS X 0208 rows 1-47 in SJIS order, 74 extra glyphs inserted before 亜)."""
EXTRA = list('①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳ⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩ瀧嵜贊爛會憔悴跪懺蛛埃嗅媚彗琥珀㎜㎝㎞㎎㏄'
             ) + ['㎏'][:0]
EXTRA = list('①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳ⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩ瀧嵜贊爛會憔悴跪懺蛛埃嗅媚彗琥珀㎜㎝㎞㎎㎏㏄㎡輒〝〟№鼈峙愍慂寮罠洒綺俯頷丼腑蹂∮∑∟⊿')
assert len(EXTRA) == 74, len(EXTRA)
def _jis():
    t = []
    for hi in range(0x81, 0xa0):
        for lo in list(range(0x40, 0x7f)) + list(range(0x80, 0xfd)):
            try: c = bytes([hi, lo]).decode('shift_jis')
            except UnicodeDecodeError: continue
            t.append(c)
            if c == '腕': return t
JIS = _jis()
FONT = JIS[:524] + EXTRA + JIS[524:] + list('躙怏喩奢炒')   # slot -> char
CTRL = {0x8001: '\n', 0x8005: '<5>', 0x8008: '<8>'}

def decode(words):
    out = []
    for v in words:
        if v in CTRL: out.append(CTRL[v])
        elif v >= 0x8000: out.append('<%X>' % v)
        else: out.append(FONT[v])
    return ''.join(out)

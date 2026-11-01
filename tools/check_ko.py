"""validate work/ko/<name>.json against work/jp/<name>.json.  usage: python tools/check_ko.py name [name...]"""
import sys, json, re, os
sys.path.insert(0, os.path.dirname(__file__))
from jtab import FONT
KEEP = set(FONT[:FONT.index('ぁ')])
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
MAXW = 27
def ok_char(c):
    return '가' <= c <= '힣' or c in KEEP or ' ' <= c <= '~' or c in '\n'
def tags(s): return re.findall('<[0-9A-F]+>', s)
def check(name):
    jp = json.load(open(f'{ROOT}/work/jp/{name}.json', encoding='utf8'))
    ko = json.load(open(f'{ROOT}/work/ko/{name}.json', encoding='utf8'))
    err = []
    if len(jp) != len(ko): return [f'length {len(ko)} != {len(jp)}']
    for i, (j, k) in enumerate(zip(jp, ko)):
        if (j == '') != (k == ''): err.append(f'{i}: empty mismatch')
        if tags(j) != tags(k): err.append(f'{i}: tags {tags(k)} != {tags(j)}')
        jl, kl = j.split('\n'), k.split('\n')
        if len(kl) > max(len(jl), 1): err.append(f'{i}: {len(kl)} lines > {len(jl)}')
        for ln in kl:
            w = len(re.sub('<[0-9A-F]+>', '', ln))
            if w > MAXW: err.append(f'{i}: line too long ({w}) {ln}')
        bad = {c for c in re.sub('<[0-9A-F]+>', '', k) if not ok_char(c)}
        if bad: err.append(f'{i}: bad chars {"".join(sorted(bad))}')
        if re.search('[ぁ-んァ-ヶ一-龠]', k): err.append(f'{i}: japanese left')
    return err
if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    for n in sys.argv[1:]:
        e = check(n); print(n, 'OK' if not e else f'{len(e)} errors'); [print('  ', x) for x in e[:40]]

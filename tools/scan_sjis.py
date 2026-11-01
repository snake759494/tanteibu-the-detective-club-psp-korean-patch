import re,os,sys,collections
pat=re.compile(rb'(?:[\x81-\x9f\xe0-\xea][\x40-\x7e\x80-\xfc]|[\x20-\x7e]){2,}')
def scan(b,minj=2):
    for m in pat.finditer(b):
        s=m.group()
        j=sum(1 for i in range(0,len(s)) if s[i]>=0x81)//2
        if j>=minj:
            try: yield m.start(), s.decode('cp932')
            except: pass
if __name__=='__main__':
    root=sys.argv[1]; c=collections.Counter(); ex={}
    for dp,_,fs in os.walk(root):
        for f in fs:
            p=os.path.join(dp,f); b=open(p,'rb').read()
            n=sum(1 for _ in scan(b))
            if n: c[os.path.splitext(f)[1]]+=n; ex.setdefault(os.path.splitext(f)[1],[]).append((n,p))
    for k,v in c.most_common(): print(k,v,sorted(ex[k])[-3:])

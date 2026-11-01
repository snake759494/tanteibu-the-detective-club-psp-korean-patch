"""ISO -> work/iso (pycdlib)"""
import pycdlib, os, sys
src, dst = sys.argv[1], sys.argv[2]
iso = pycdlib.PyCdlib(); iso.open(src)
for root, dirs, files in iso.walk(iso_path='/'):
    for f in files:
        p = (root.rstrip('/') + '/' + f)
        out = os.path.join(dst, p.lstrip('/').split(';')[0])
        os.makedirs(os.path.dirname(out), exist_ok=True)
        iso.get_file_from_iso(out, iso_path=p)
iso.close()

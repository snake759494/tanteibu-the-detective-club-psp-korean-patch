import struct,sys
from capstone import *
d=open('work/eboot/EBOOT.dec','rb').read()
md=Cs(CS_ARCH_MIPS,CS_MODE_MIPS32+CS_MODE_LITTLE_ENDIAN)
a=int(sys.argv[1],16);b=int(sys.argv[2],16)
for ins in md.disasm(d[0xc0+a:0xc0+b],a):
    print(hex(ins.address),ins.mnemonic,ins.op_str)

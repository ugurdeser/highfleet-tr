import sys
def crypt(data):
    out=bytearray(len(data)); b=2531011
    for i,c in enumerate(data):
        out[i]=(b ^ (b>>15) ^ c)&0xff
        b=(b+214013)&0xffffffff
    return bytes(out)
src,dst=sys.argv[1],sys.argv[2]
open(dst,'wb').write(crypt(open(src,'rb').read()))

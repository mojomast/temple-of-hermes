#!/usr/bin/env python3
"""Numeric-only checks for the Dojo QEMU shots. Never displays pixels."""
import json, struct
from pathlib import Path
from PIL import Image
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
try:
    from fontocr import ocr
except Exception:
    ocr=None
SH=Path(__file__).resolve().parent
PAL=[(0x00,0x00,0x00),(0x00,0x00,0xAA),(0x00,0xAA,0x00),(0x00,0xAA,0xAA),
     (0xAA,0x00,0x00),(0xAA,0x00,0xAA),(0xAA,0x55,0x00),(0xAA,0xAA,0xAA),
     (0x55,0x55,0x55),(0x55,0x55,0xFF),(0x55,0xFF,0x55),(0x55,0xFF,0xFF),
     (0xFF,0x55,0x55),(0xFF,0x55,0xFF),(0xFF,0xFF,0x55),(0xFF,0xFF,0xFF)]
PALMAP={c:i for i,c in enumerate(PAL)}
def read_gr(path):
    b=Path(path).read_bytes()
    _,_,_,w,wi,h,_=struct.unpack_from('<qiiiiii',b,0)
    body=b[32:32+wi*h]
    return w,h,wi,body
def idx_img(im):
    px=im.convert('RGB').load(); w,h=im.size
    out=[[PALMAP.get(px[x,y],-1) for x in range(w)] for y in range(h)]
    return out
def match_region(shot, grpath, x0, y0):
    w,h,wi,body=read_gr(grpath)
    si=idx_img(shot)
    best=(0,0,0)
    for dy in range(-2,17):
        for dx in range(-2,9):
            same=tot=0
            for y in range(h):
                sy=y0+dy+y
                if sy<0 or sy>=len(si): continue
                for x in range(w):
                    sx=x0+dx+x
                    if sx<0 or sx>=len(si[0]): continue
                    tot+=1
                    if si[sy][sx]==body[y*wi+x]: same+=1
            pct=100.0*same/tot if tot else 0
            if pct>best[2]: best=(dx,dy,pct)
    return {'dx':best[0],'dy':best[1],'match_pct':round(best[2],2),'size':[w,h]}
res={}
for name in ['01-dojo-window.png','02-challenge-result.png','03-dojo-second.png','04-final-shell.png']:
    im=Image.open(SH/name)
    px=im.convert('RGB').load(); w,h=im.size
    cols=set(); xs=[]; ys=[]
    for y in range(h):
        for x in range(w):
            c=px[x,y]; cols.add(c)
            if c!=(0,0,0): xs.append(x); ys.append(y)
    res[name]={'size':[w,h],'unique_colors':len(cols),
               'palette_ok':cols<=set(PAL),
               'bbox':[min(xs),min(ys),max(xs),max(ys)] if xs else None}
res['header_plate']=match_region(Image.open(SH/'01-dojo-window.png'),ROOT/'Hermes/Apps/Dojo/header-dojo-plate.GR',0,0)
res['teknium_icon']=match_region(Image.open(SH/'01-dojo-window.png'),ROOT/'Hermes/Apps/Dojo/teknium-icon.GR',24,96)
# scoreboard crop: count green/red/yellow text pixels
im=Image.open(SH/'02-challenge-result.png').convert('RGB'); px=im.load(); w,h=im.size
cnt={i:0 for i in range(16)}
for y in range(h):
    for x in range(w):
        i=PALMAP.get(px[x,y],-1)
        if i>=0: cnt[i]+=1
res['scoreboard_colors']={k:v for k,v in cnt.items() if v}
# final shell OCR text saved during the QEMU run
t=(SH/'04-final-shell.txt').read_text() if (SH/'04-final-shell.txt').exists() else ''
res['final_shell_text']={'has_C_Home':'C:/Home' in t,'has_public_domain':'Public Domain' in t}
t2=(SH/'02-challenge-result.txt').read_text() if (SH/'02-challenge-result.txt').exists() else ''
res['challenge_result_text']={'has_PASS_100':'PASS 100' in t2,'has_DolDoc':'DolDoc' in t2}
# result files
for n in [1,2,4]:
    p=SH/f'result{n}.txt'
    txt=p.read_text() if p.exists() else ''
    res[f'result{n}']={'exists':p.exists(),'pass':'STATUS: PASS' in txt,'score100':'SCORE: 100' in txt}
print(json.dumps(res,indent=2))
(SH/'pil-checks.json').write_text(json.dumps(res,indent=2))
lines=[]
for k,v in res.items():
    lines.append(f'{k}: {json.dumps(v,sort_keys=True)}')
(SH/'pil-checks.txt').write_text('\n'.join(lines)+'\n')

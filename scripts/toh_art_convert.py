#!/usr/bin/env python3
"""Temple of Hermes art converter — Pillow only, no QEMU.

TempleOS 16-color palette from Adam/Gr/GrPalette.HC gr32_palette_std.
Writes 640x480 wallpapers, 32/16 icons, uncompressed .GR, and CSprite .SP.
"""
from __future__ import annotations
import argparse, json, struct, sys
from pathlib import Path
from PIL import Image

PALETTE_RGB = [
    (0x00,0x00,0x00),(0x00,0x00,0xAA),(0x00,0xAA,0x00),(0x00,0xAA,0xAA),
    (0xAA,0x00,0x00),(0xAA,0x00,0xAA),(0xAA,0x55,0x00),(0xAA,0xAA,0xAA),
    (0x55,0x55,0x55),(0x55,0x55,0xFF),(0x55,0xFF,0x55),(0x55,0xFF,0xFF),
    (0xFF,0x55,0x55),(0xFF,0x55,0xFF),(0xFF,0xFF,0x55),(0xFF,0xFF,0xFF),
]
PALETTE_NAMES = ["BLACK","BLUE","GREEN","CYAN","RED","PURPLE","BROWN","LTGRAY",
                 "DKGRAY","LTBLUE","LTGREEN","LTCYAN","LTRED","LTPURPLE","YELLOW","WHITE"]
SPT_END, SPT_BITMAP = 0, 23
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "art" / "source"

def pal_image():
    im = Image.new("P", (1,1))
    pal = []
    for rgb in PALETTE_RGB: pal.extend(rgb)
    pal.extend([0]*(768-len(pal)))
    im.putpalette(pal)
    return im

def nearest(r,g,b):
    best,bd=0,1<<30
    for i,(pr,pg,pb) in enumerate(PALETTE_RGB):
        d=(r-pr)**2+(g-pg)**2+(b-pb)**2
        if d<bd: bd,best=d,i
    return best

def quantize(img, dither=True):
    img = img.convert("RGB")
    if dither:
        return img.quantize(palette=pal_image(), dither=Image.Dither.FLOYDSTEINBERG)
    w,h=img.size; px=img.load()
    out=Image.new("P",(w,h)); out.putpalette(pal_image().getpalette())
    op=out.load()
    for y in range(h):
        for x in range(w):
            op[x,y]=nearest(*px[x,y])
    return out

def width_internal(w): return (w+7)&~7

def body_bytes(p_img):
    w,h=p_img.size; wi=width_internal(w); px=p_img.load()
    out=bytearray(wi*h)
    for y in range(h):
        row=y*wi
        for x in range(w):
            out[row+x]=px[x,y]&0x0F
    return bytes(out)

def write_gr(path, p_img):
    w,h=p_img.size; wi=width_internal(w); body=body_bytes(p_img)
    header=struct.pack("<qiiiiii",0,0,0,w,wi,h,0)  # uncompressed CDC, no palette flag
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(header+body); return len(header)+len(body)

def write_sprite(path, p_img):
    w,h=p_img.size; body=body_bytes(p_img)
    elem=bytearray([SPT_BITMAP,0,0,0]); elem.extend(struct.pack("<iiii",0,0,w,h)); elem.extend(body); elem.append(SPT_END)
    path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(bytes(elem)); return len(elem)

def fit_cover(img,tw,th):
    img=img.convert("RGB"); sw,sh=img.size; sc=max(tw/sw,th/sh)
    nw,nh=max(1,int(sw*sc+0.5)),max(1,int(sh*sc+0.5))
    img=img.resize((nw,nh), Image.Resampling.NEAREST)
    L,T=(nw-tw)//2,(nh-th)//2
    return img.crop((L,T,L+tw,T+th))

def fit_contain(img,tw,th,fill=(0,0,0)):
    img=img.convert("RGB"); sw,sh=img.size; sc=min(tw/sw,th/sh)
    nw,nh=max(1,int(sw*sc+0.5)),max(1,int(sh*sc+0.5))
    img=img.resize((nw,nh), Image.Resampling.NEAREST)
    canvas=Image.new("RGB",(tw,th),fill); canvas.paste(img,((tw-nw)//2,(th-nh)//2)); return canvas

def save_png(path, p_img):
    path.parent.mkdir(parents=True, exist_ok=True)
    p_img.convert("RGB").save(path, format="PNG", optimize=True)

def do_wallpaper(src, stem):
    q=quantize(fit_cover(Image.open(src),640,480), True)
    save_png(ROOT/"art"/"wallpaper"/f"{stem}.png", q)
    save_png(ROOT/"Hermes"/"Art"/"Wallpaper"/f"{stem}.PNG", q)
    g=write_gr(ROOT/"Hermes"/"Art"/"Wallpaper"/f"{stem}.GR", q)
    s=write_sprite(ROOT/"Hermes"/"Art"/"Sprites"/f"{stem}.SP", q)
    print(f"wallpaper {stem} gr={g} sp={s}")

def do_splash(src, stem):
    q=quantize(fit_cover(Image.open(src),640,480), True)
    save_png(ROOT/"art"/"splash"/f"{stem}.png", q)
    save_png(ROOT/"Hermes"/"Art"/"Splash"/f"{stem}.PNG", q)
    g=write_gr(ROOT/"Hermes"/"Art"/"Splash"/f"{stem}.GR", q)
    print(f"splash {stem} gr={g}")

def do_preview(src, stem, size=(1280,640)):
    q=quantize(fit_cover(Image.open(src),*size), True)
    save_png(ROOT/"art"/"preview"/f"{stem}.png", q)
    print(f"preview {stem} {size}")

def do_header(src, stem="pane-header"):
    q=quantize(fit_cover(Image.open(src),1280,80), True)
    save_png(ROOT/"art"/"ui"/f"{stem}.png", q)
    qos=quantize(fit_cover(Image.open(src),640,40), True)
    save_png(ROOT/"Hermes"/"Art"/"UI"/f"{stem}.PNG", qos)
    write_gr(ROOT/"Hermes"/"Art"/"UI"/f"{stem}.GR", qos)
    print(f"header {stem}")

def do_sheet(src, stem, size):
    q=quantize(fit_contain(Image.open(src),*size), True)
    save_png(ROOT/"art"/"sprites"/f"{stem}.png", q)
    save_png(ROOT/"Hermes"/"Art"/"Sprites"/f"{stem}.PNG", q)
    g=write_gr(ROOT/"Hermes"/"Art"/"Sprites"/f"{stem}.GR", q)
    s=write_sprite(ROOT/"Hermes"/"Art"/"Sprites"/f"{stem}.SP", q)
    print(f"sheet {stem} {q.size} gr={g} sp={s}")

def do_grid(src, rows, cols, names, margin=0.10):
    img=Image.open(src).convert("RGB"); w,h=img.size; cw,ch=w//cols,h//rows
    for i,name in enumerate(names):
        r,c=i//cols,i%cols
        cell=img.crop((c*cw,r*ch,(c+1)*cw,(r+1)*ch))
        mw,mh=int(cw*margin),int(ch*margin)
        cell=cell.crop((mw,mh,cw-mw,ch-mh))
        for size in (32,16):
            q=quantize(fit_contain(cell,size,size), False)
            save_png(ROOT/"art"/"icons"/str(size)/f"{name}.png", q)
            save_png(ROOT/"Hermes"/"Art"/"Icons"/str(size)/f"{name}.PNG", q)
            write_gr(ROOT/"Hermes"/"Art"/"Icons"/str(size)/f"{name}.GR", q)
            write_sprite(ROOT/"Hermes"/"Art"/"Icons"/str(size)/f"{name}.SP", q)
        print(f"icon {name}")

def do_badge(src, stem="nous-girl"):
    img=Image.open(src)
    for size in (64,32,16):
        q=quantize(fit_contain(img,size,size), False)
        save_png(ROOT/"art"/"icons"/str(size)/f"{stem}.png", q)
        save_png(ROOT/"Hermes"/"Art"/"Icons"/str(size)/f"{stem}.PNG", q)
        write_gr(ROOT/"Hermes"/"Art"/"Icons"/str(size)/f"{stem}.GR", q)
        write_sprite(ROOT/"Hermes"/"Art"/"Icons"/str(size)/f"{stem}.SP", q)
    print(f"badge {stem}")

def write_palette_json():
    p=ROOT/"art"/"palette.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps([{"i":i,"name":n,"rgb":list(rgb)} for i,(n,rgb) in enumerate(zip(PALETTE_NAMES,PALETTE_RGB))], indent=2))
    print("palette", p)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("cmd")
    ap.add_argument("args", nargs="*")
    a=ap.parse_args()
    if a.cmd=="palette": write_palette_json()
    elif a.cmd=="wallpaper": do_wallpaper(Path(a.args[0]), a.args[1])
    elif a.cmd=="splash": do_splash(Path(a.args[0]), a.args[1])
    elif a.cmd=="preview": do_preview(Path(a.args[0]), a.args[1])
    elif a.cmd=="header": do_header(Path(a.args[0]), a.args[1] if len(a.args)>1 else "pane-header")
    elif a.cmd=="sheet": do_sheet(Path(a.args[0]), a.args[1], (int(a.args[2]), int(a.args[3])))
    elif a.cmd=="grid":
        src,rows,cols=Path(a.args[0]),int(a.args[1]),int(a.args[2]); names=a.args[3:]
        do_grid(src,rows,cols,names)
    elif a.cmd=="badge": do_badge(Path(a.args[0]), a.args[1] if len(a.args)>1 else "nous-girl")
    else:
        print("unknown", a.cmd); sys.exit(2)

if __name__=="__main__":
    main()

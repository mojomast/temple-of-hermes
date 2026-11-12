#!/usr/bin/env python3
import sys
from pathlib import Path
from PIL import Image
src=Path(sys.argv[1]); dst=Path(sys.argv[2])
im=Image.open(src).convert('RGB')
if im.size!=(640,480):
    im=im.resize((640,480),Image.Resampling.NEAREST)
q=im.quantize(colors=16,method=Image.Quantize.MEDIANCUT,dither=Image.Dither.NONE)
if q.size!=(640,480): raise SystemExit('bad size')
idx=set(q.getdata())
if max(idx)>15: raise SystemExit('palette index >15')
q.save(dst)
print({'path':str(dst),'size':q.size,'mode':q.mode,'indices':sorted(idx),'unique':len(idx),'max_index':max(idx),'off_palette':sum(1 for i in idx if i>15)})

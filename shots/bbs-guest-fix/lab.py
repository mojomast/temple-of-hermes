#!/usr/bin/env python3
import json, os, re, shutil, socket, subprocess, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'scripts'))
from qemu_hermes import QMP, glyph_text, Serial
from PIL import Image
RUN = ROOT/'run'/'lab'

def log(msg, path=None):
    line=time.strftime('%H:%M:%S ')+msg
    print(line, flush=True)
    with (RUN/'lab.log').open('a') as f: f.write(line+'\n')

def start(name, args, extra_socks=True):
    d=RUN/name; d.mkdir(parents=True, exist_ok=True)
    for s in d.glob('*.sock'): s.unlink()
    qmp=d/'qmp.sock'; vnc=d/'vnc.sock'; com1=d/'com1.sock'; com2=d/'com2.sock'
    cmd=['qemu-system-x86_64','-name',name,'-machine','pc,kernel-irqchip=off','-accel','tcg','-cpu','qemu64','-m','2G','-smp','1','-vga','std','-display','none','-nic','none',
         '-qmp',f'unix:{qmp},server=on,wait=off','-vnc',f'unix:{vnc}',
         '-serial',f'unix:{com1},server=on,wait=off','-serial',f'unix:{com2},server=on,wait=off']+args
    lf=(d/'qemu.log').open('ab')
    p=subprocess.Popen(cmd,stdout=lf,stderr=lf)
    meta={'pid':p.pid,'cmd':cmd,'qmp':str(qmp),'vnc':str(vnc),'com1':str(com1),'com2':str(com2),'dir':str(d)}
    (d/'meta.json').write_text(json.dumps(meta,indent=2))
    log('qemu pid %d argv=%s'%(p.pid,' '.join(cmd)))
    return meta

def shot(q,name,label=None):
    d=RUN/label if label else q.path.parent; d.mkdir(parents=True,exist_ok=True)
    dest=d/f'{name}.png'
    q.screendump(dest)
    text=''
    try: text=glyph_text(dest)
    except Exception as e: text=f'<ocr {e}>'
    (d/f'{name}.txt').write_text(text)
    im=Image.open(dest)
    log(f'shot {d.name}/{name} size={im.size} mode={im.mode} colors={len(im.convert("RGB").getcolors(maxcolors=1000000) or [])}')
    log('OCR '+text.replace('\n',' | ')[:500])
    return text,dest

def pil_check(path):
    im=Image.open(path)
    im2=im.convert('RGB')
    cols=im2.getcolors(maxcolors=1000000) or []
    uniq=len(cols)
    if im.mode=='P':
        idx=set(im.getdata()); off=sum(1 for i in idx if i>15)
        maxi=max(idx) if idx else -1
    else:
        idx=None; off=-1; maxi=-1
    return {'size':list(im.size),'mode':im.mode,'unique':uniq,'max_index':maxi,'off_palette_pixels':off}

class Q: pass

def qmp(meta, timeout=60):
    return QMP(Path(meta['qmp']),timeout=timeout)

class Hrpc2:
    def __init__(self, path, timeout=30.0):
        self.sock=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM); self.sock.settimeout(timeout)
        deadline=time.time()+timeout; last=None
        while time.time()<deadline:
            try: self.sock.connect(str(path)); break
            except OSError as e: last=e; time.sleep(0.1)
        else: raise RuntimeError(f'connect {path}: {last}')
        self.buf=b''; self.next_id=1; self.events=[]
    def close(self):
        try: self.sock.close()
        except OSError: pass
    def _parse(self):
        # normalise leading CR/LF
        while True:
            self.buf=self.buf.lstrip(b'\r\n')
            # find earliest header
            cands=[]
            for p in (b'HBEACON ',b'HEVT ',b'HRPL '):
                i=self.buf.find(p)
                if i>=0: cands.append((i,p))
            if not cands: return
            cands.sort(); i,p=cands[0]
            if i>0:
                self.buf=self.buf[i:]; i=0
            nl=self.buf.find(b'\n')
            if nl<0: return
            line=self.buf[:nl]; rest=self.buf[nl+1:]
            parts=line.decode('ascii','replace').split()
            if p==b'HBEACON ':
                self.buf=rest; continue
            if len(parts)<4: self.buf=rest; continue
            try: ln=int(parts[3])
            except ValueError: self.buf=rest; continue
            if len(rest)<ln: return
            payload=rest[:ln]; self.buf=rest[ln:]
            if parts[0]=='HEVT': self.events.append(payload)
            else: self.last=(int(parts[1]),parts[2],payload)
    def request(self, op, payload=b'', timeout=20.0):
        rid=self.next_id; self.next_id+=1
        self.sock.sendall(f'HREQ {rid} {op} {len(payload)}\n'.encode()+payload)
        self.last=None; end=time.time()+timeout
        while time.time()<end:
            self._parse()
            if self.last is not None:
                i,st,data=self.last; self.last=None
                if i==rid: return st,data
            self.sock.settimeout(min(0.5,max(0.05,end-time.time())))
            try: chunk=self.sock.recv(65536)
            except socket.timeout: continue
            except OSError as e: raise RuntimeError(str(e))
            if not chunk: raise RuntimeError('closed')
            self.buf+=chunk
        raise TimeoutError(f'no HRPL {op} id={rid}, buf={self.buf[-300:]!r}')

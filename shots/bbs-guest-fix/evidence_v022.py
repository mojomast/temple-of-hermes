#!/usr/bin/env python3
from lab import *
import os, sys
name='v022-evidence'
d=RUN/name; d.mkdir(parents=True,exist_ok=True)
extra=['-boot','order=c,menu=on','-drive',f'file={ROOT}/run/final/clean-test.qcow2,format=qcow2,if=ide,index=0,media=disk','-drive',f'file={ROOT}/run/TempleOfHermes-0.1.3.ISO,media=cdrom,format=raw,if=ide,index=3,readonly=on']
m=start(name,extra); q=qmp(m)
res={}
try:
    end=time.time()+150; n=0; text=''
    while time.time()<end:
        n+=1; text,_=shot(q,f'wait-{n:03d}')
        low=text.lower()
        if ('hermes apps' in low or 'click an icon' in low) and 'install onto hard drive' not in low: break
        time.sleep(3)
    h=Hrpc2(Path(m['com1']),timeout=30)
    h.request('eval',b'if (IsFile("C:/Hermes/Apps/HermesBBS/token.txt")) Del("C:/Hermes/Apps/HermesBBS/token.txt"); "cleared\\n";',timeout=10)
    st,dd=h.request('stat',b'C:/Hermes/Apps/HermesBBS/token.txt',timeout=10); res['stat_before']=dd.decode()
    h.close(); time.sleep(0.3)
    home=Path('/tmp/toh-home'); (home/'exchange').mkdir(parents=True,exist_ok=True)
    tok=home/'token.txt'; tok.write_text('test-token-not-real\n')
    os.environ['TEMPLEOS_HOME']=str(home)
    sys.path.insert(0,'/tmp/hermes-templeos-v022')
    from templeos.serial import SerialPort
    from templeos import files
    p=SerialPort(); p.open(Path(m['com1']),timeout_s=5); files.bind_serial(p)
    t0=time.time(); r1=files.list_guest('C:/Hermes/Apps/HermesBBS/'); dt1=time.time()-t0
    t0=time.time(); r2=files.push(tok,'C:/Hermes/Apps/HermesBBS/token.txt'); dt2=time.time()-t0
    p.close(); time.sleep(0.3)
    res.update(list_seconds=round(dt1,2), list=r1, push_seconds=round(dt2,2), push=r2)
    try:
        h2=Hrpc2(Path(m['com1']),timeout=30)
        st,dd=h2.request('stat',b'C:/Hermes/Apps/HermesBBS/token.txt',timeout=20); res['stat_after']=dd.decode()
        h2.close()
    except Exception as e:
        res['stat_after']=type(e).__name__+': '+str(e)
    (d/'result.json').write_text(json.dumps(res,indent=2))
    log('V022 '+json.dumps(res))
finally:
    try: q.quit()
    except Exception: pass
    time.sleep(1)
    try: os.kill(m['pid'],9)
    except Exception: pass

#!/usr/bin/env python3
from lab import *
import os, sys
name='host-ops'
extra=['-boot','order=c,menu=on','-drive',f'file={ROOT}/run/final/clean-test.qcow2,format=qcow2,if=ide,index=0,media=disk','-drive',f'file={ROOT}/run/TempleOfHermes-0.1.3.ISO,media=cdrom,format=raw,if=ide,index=3,readonly=on']
m=start(name,extra); q=qmp(m)
try:
    end=time.time()+150; n=0; text=''
    while time.time()<end:
        n+=1; text,_=shot(q,f'wait-{n:03d}')
        low=text.lower()
        if ('hermes apps' in low or 'click an icon' in low) and 'install onto hard drive' not in low: break
        time.sleep(3)
    home=Path('/tmp/toh-home'); os.environ['TEMPLEOS_HOME']=str(home)
    sys.path.insert(0,'/tmp/hermes-templeos')
    from templeos.serial import SerialPort
    from templeos import files
    p=SerialPort(); p.open(Path(m['com1']),timeout_s=5); files.bind_serial(p)
    r1=files.list_guest('C:/Hermes/Apps/HermesBBS/')
    log('list via=%s count=%s sample=%s'%(r1.get('via'),r1.get('count'),[e.get('name') for e in r1.get('entries',[])[:5]]))
    home=Path('/tmp/toh-home'); (home/'exchange').mkdir(parents=True,exist_ok=True)
    tok=home/'token.txt'; tok.write_text('test-token-not-real\n')
    rp=files.push(tok,'C:/Hermes/Apps/HermesBBS/token.txt'); log('push via=%s ok=%s'%(rp.get('via'),rp.get('ok')))
    dest=home/'pulled-token.txt'
    r2=files.pull('C:/Hermes/Apps/HermesBBS/token.txt',dest)
    log('pull via=%s ok=%s bytes=%s'%(r2.get('via'),r2.get('ok'),r2.get('bytes')))
    p.close()
finally:
    try: q.quit()
    except Exception: pass
    time.sleep(1)
    try: os.kill(m['pid'],9)
    except Exception: pass

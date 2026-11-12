#!/usr/bin/env python3
from lab import *
import os, sys
name='final-disk'
d=RUN/name; d.mkdir(parents=True,exist_ok=True)
extra=['-boot','order=c,menu=on','-drive',f'file={ROOT}/run/final/TempleOfHermes-0.1.4-test2-disk-clean.qcow2,format=qcow2,if=ide,index=0,media=disk','-drive',f'file={ROOT}/run/TempleOfHermes-0.1.3.ISO,media=cdrom,format=raw,if=ide,index=3,readonly=on']
m=start(name,extra); q=qmp(m); relay=None
try:
    end=time.time()+150; n=0; text=''
    while time.time()<end:
        n+=1; text,_=shot(q,f'wait-{n:03d}')
        low=text.lower()
        if ('hermes apps' in low or 'click an icon' in low) and 'install onto hard drive' not in low:
            log('launcher visible'); break
        time.sleep(3)
    h=Hrpc2(Path(m['com1']),timeout=30)
    st,dd=h.request('ping',b'',timeout=10); log('ping '+st+' '+dd.decode())
    st,dd=h.request('eval',b'if (IsFile("C:/Hermes/Apps/HermesBBS/token.txt")) Del("C:/Hermes/Apps/HermesBBS/token.txt"); "cleared\\n";',timeout=10); log('clear '+st+' '+dd.decode()[:200])
    st,dd=h.request('stat',b'C:/Hermes/Apps/HermesBBS/token.txt',timeout=10); log('stat before '+dd.decode())
    h.close(); time.sleep(0.3)
    cert=d/'cert.pem'; key=d/'key.pem'
    if not cert.exists():
        subprocess.check_call(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-keyout',str(key),'-out',str(cert),'-days','2','-subj','/CN=localhost'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    portfile=d/'port'
    tls=subprocess.Popen([sys.executable,str(ROOT/'shots/bbs-guest-fix/hbbs_tls_server.py'),'--port-file',str(portfile),'--log',str(d/'tls-server.log'),'--cert',str(cert),'--key',str(key)])
    endp=time.time()+10
    while not portfile.exists() and time.time()<endp: time.sleep(0.05)
    port=int(portfile.read_text())
    relay=subprocess.Popen([sys.executable,str(ROOT/'shots/bbs-guest-fix/bbs_relay.py'),'--serial',m['com2'],'--tls-port',str(port),'--log',str(d/'relay.log'),'--modem-log',str(d/'modem.log')])
    log('relay pid %d'%relay.pid); time.sleep(1.0)
    home=Path('/tmp/toh-home'); (home/'exchange').mkdir(parents=True,exist_ok=True)
    tok=home/'token.txt'; tok.write_text('test-token-not-real\n')
    os.environ['TEMPLEOS_HOME']=str(home)
    sys.path.insert(0,'/tmp/hermes-templeos')
    from templeos.serial import SerialPort
    from templeos import files
    p=SerialPort(); p.open(Path(m['com1']),timeout_s=5); files.bind_serial(p)
    t0=time.time(); r=files.push(tok,'C:/Hermes/Apps/HermesBBS/token.txt'); log('token push %.2fs %s'%(time.time()-t0,json.dumps(r))); p.close()
    time.sleep(0.3)
    q.type_text('s',delay=0.1); log('pressed s')
    end=time.time()+50; n=0; got=''
    while time.time()<end:
        n+=1; got,_=shot(q,f'poll-{n:03d}')
        if 'Connected to dest bbs' in got:
            log('CONNECTED after %d polls'%n); break
        time.sleep(2)
    final,_=shot(q,'final')
    (d/'final.ocr.txt').write_text(final)
    log('FINAL OCR '+final.replace('\n',' | ')[:1200])
    st,dd=h.request('ping',b'',timeout=10) if False else ('skip',b'')
finally:
    try:
        if relay: relay.terminate(); relay.wait(timeout=5)
    except Exception: pass
    try:
        if 'tls' in dir() and tls: tls.terminate(); tls.wait(timeout=5)
    except Exception: pass
    try: q.quit()
    except Exception: pass
    time.sleep(1)
    try: os.kill(m['pid'],9)
    except Exception: pass

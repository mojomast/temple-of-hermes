#!/usr/bin/env python3
"""COM2 unix socket <-> host/hermes_modem.py <-> TLS HBBS/1 endpoint.

Mirrors the real bbs_modem_relay.py wiring: the guest only names the
destination "bbs"; this relay owns the TLS endpoint.  Logs command names and
byte counts only; never logs payloads or token values.
"""
from __future__ import annotations
import argparse, os, select, socket, ssl, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'host'))
from hermes_modem import CRLF, HermesModem  # noqa: E402

class TlsTransport:
    def __init__(self, host: str, port: int, log_path: Path):
        self.host=host; self.port=port; self.log_path=log_path; self.sock=None; self.ctx=None
    def _log(self,msg):
        with self.log_path.open('a') as f: f.write(time.strftime('%H:%M:%S ')+msg+'\n')
    def connect(self, destination: str) -> None:
        if destination.strip().lower()!='bbs':
            raise RuntimeError('destination not allowed')
        self.disconnect()
        ctx=ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE
        raw=socket.create_connection((self.host,self.port),timeout=5)
        raw.settimeout(5)
        self.sock=ctx.wrap_socket(raw,server_hostname=None)
        self.sock.setblocking(False)
        self._log('TLS connect dest=bbs')
    def send(self, data: bytes) -> int:
        if self.sock is None: raise RuntimeError('not connected')
        total=0
        while total<len(data):
            try:
                total+=self.sock.send(data[total:])
            except (ssl.SSLWantWriteError,BlockingIOError):
                select.select([],[self.sock],[],1.0)
        return total
    def recv(self, max_bytes: int, timeout: float | None = None) -> bytes:
        if self.sock is None or max_bytes<=0: return b''
        pending=self.sock.pending()
        if not pending:
            try:
                r,_,_=select.select([self.sock],[],[],0 if timeout in (None,0) else timeout)
            except (OSError,ValueError):
                return b''
            if not r: return b''
        try: return self.sock.recv(max_bytes)
        except (ssl.SSLWantReadError,BlockingIOError): return b''
    def disconnect(self) -> None:
        if self.sock is not None:
            try: self.sock.close()
            except OSError: pass
            self.sock=None; self._log('TLS disconnect')

def connect_unix(path: Path, timeout: float=20.0) -> socket.socket:
    end=time.time()+timeout; last=None
    while time.time()<end:
        s=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
        try:
            s.connect(str(path)); return s
        except OSError as e:
            last=e; s.close(); time.sleep(0.2)
    raise RuntimeError(f'unix connect {path}: {last}')

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--serial',required=True)
    ap.add_argument('--tls-host',default='localhost')
    ap.add_argument('--tls-port',type=int,required=True)
    ap.add_argument('--log',required=True)
    ap.add_argument('--modem-log',required=True)
    a=ap.parse_args()
    log=Path(a.log); log.parent.mkdir(parents=True,exist_ok=True)
    mlog=Path(a.modem_log); mlog.parent.mkdir(parents=True,exist_ok=True)
    serial=connect_unix(Path(a.serial))
    serial.setblocking(False)
    tr=TlsTransport(a.tls_host,a.tls_port,log)
    modem=HermesModem(enabled=True,allow_list=('bbs',),transport=tr,log_path=mlog)
    log.write_text(time.strftime('%H:%M:%S ')+'relay up: modem.sock -> tls dest=bbs\n')
    try:
        while True:
            r,_,_=select.select([serial],[],[],0.2)
            if not r: continue
            try: chunk=serial.recv(4096)
            except BlockingIOError: continue
            if not chunk: break
            reply=modem.feed(chunk)
            if reply:
                off=0
                while off<len(reply):
                    try: off+=serial.send(reply[off:])
                    except BlockingIOError: select.select([],[serial],[],0.5)
    except KeyboardInterrupt:
        pass
    finally:
        try: modem.reset()
        except Exception: pass
        try: serial.close()
        except OSError: pass
        log.write(time.strftime('%H:%M:%S ')+'relay down\n')

if __name__=='__main__': main()

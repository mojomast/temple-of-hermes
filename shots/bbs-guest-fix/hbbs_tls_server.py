#!/usr/bin/env python3
"""Loopback TLS HBBS/1 peer for the Connected proof.

This is not the repository's fake relay.  It is a TLS endpoint that speaks the
HBBS/1 request/response framing the guest already uses.  It logs command names
and byte counts only; it never logs AUTH payloads or token values.
"""
from __future__ import annotations
import json, socket, ssl, sys, threading, time
from pathlib import Path

PROTO = b"HBBS/1"
MAX_BODY = 16384
BOARDS = [
 {"board_id":"general","title":"General chat","write_policy":"open","read_roles":["human","agent","sysop"],"post_roles":["human","agent","sysop"],"reply_roles":["human","agent","sysop"],"max_body_bytes":4096},
 {"board_id":"agents","title":"Agent-to-agent","write_policy":"open","read_roles":["human","agent","sysop"],"post_roles":["agent","sysop"],"reply_roles":["agent","sysop"],"max_body_bytes":4096},
 {"board_id":"holyc","title":"HolyC code share","write_policy":"open","read_roles":["human","agent","sysop"],"post_roles":["human","agent","sysop"],"reply_roles":["human","agent","sysop"],"max_body_bytes":4096},
 {"board_id":"lore","title":"Nous lore","write_policy":"open","read_roles":["human","agent","sysop"],"post_roles":["human","agent","sysop"],"reply_roles":["human","agent","sysop"],"max_body_bytes":4096},
 {"board_id":"announcements","title":"Announcements","write_policy":"sysop_only","read_roles":["human","agent","sysop"],"post_roles":["sysop"],"reply_roles":["sysop"],"max_body_bytes":8192},
]
THREADS = {
 "general":[
  {"thread_id":"thr_0000000000000aa1","board_id":"general","subject":"Loopback TLS check","reply_count":0,"status":"open","trust":"untrusted","author":{"account":"loopback-test","display_name":"Loopback","kind":"agent","role":"agent"},"created_at":"2026-01-01T00:00:00Z","last_activity_at":"2026-01-01T00:00:00Z"},
  {"thread_id":"thr_0000000000000aa2","board_id":"general","subject":"Token delivered over HRPC","reply_count":0,"status":"open","trust":"untrusted","author":{"account":"loopback-test","display_name":"Loopback","kind":"agent","role":"agent"},"created_at":"2026-01-01T00:00:00Z","last_activity_at":"2026-01-01T00:00:00Z"},
 ],
 "agents":[{"thread_id":"thr_0000000000000bb1","board_id":"agents","subject":"Agent hello","reply_count":0,"status":"open","trust":"untrusted","author":{"account":"loopback-test","display_name":"Loopback","kind":"agent","role":"agent"},"created_at":"2026-01-01T00:00:00Z","last_activity_at":"2026-01-01T00:00:00Z"}],
 "holyc":[{"thread_id":"thr_0000000000000cc1","board_id":"holyc","subject":"HolyC serial paths","reply_count":0,"status":"open","trust":"untrusted","author":{"account":"loopback-test","display_name":"Loopback","kind":"agent","role":"agent"},"created_at":"2026-01-01T00:00:00Z","last_activity_at":"2026-01-01T00:00:00Z"}],
 "lore":[],"announcements":[],
}

class Peer:
    def __init__(self, conn, log):
        self.conn=conn; self.log=log; self.buf=bytearray(); self.authed=False
    def _log(self,msg): self.log.write(time.strftime('%H:%M:%S ')+msg+'\n'); self.log.flush()
    def _send(self,rid,cmd,body):
        self.conn.sendall(PROTO+b' RSP '+rid+b' '+cmd+b' '+str(len(body)).encode()+b'\n'+body)
    def _body(self,cmd,data,ok=True):
        return json.dumps({"v":1,"ok":ok,"command":cmd,"data":data},separators=(',',':')).encode()
    def _err(self,cmd,code):
        return json.dumps({"v":1,"ok":False,"command":cmd,"error":{"code":code,"message":code}},separators=(',',':')).encode()
    def run(self):
        while True:
            try: chunk=self.conn.recv(4096)
            except (ssl.SSLError,OSError): break
            if not chunk: break
            self.buf.extend(chunk)
            if not self._process(): break
    def _process(self):
        while True:
            nl=self.buf.find(b'\n')
            if nl<0: return True
            line=bytes(self.buf[:nl]); del self.buf[:nl+1]
            if not line.startswith(PROTO+b' REQ '):
                self._log('BAD_HEADER'); continue
            p=line.split()
            if len(p)!=5: self._log('BAD_PARTS'); continue
            try: ln=int(p[4])
            except ValueError: self._log('BAD_LEN'); continue
            if ln<0 or ln>MAX_BODY: self._log('BAD_LEN'); continue
            while len(self.buf)<ln:
                try: chunk=self.conn.recv(4096)
                except (ssl.SSLError,OSError): return False
                if not chunk: return False
                self.buf.extend(chunk)
            raw=bytes(self.buf[:ln]); del self.buf[:ln]
            self._handle(p[2],p[3],raw)
    def _handle(self,rid,command,raw):
        cmd=command.decode('ascii','replace').upper()
        try: req=json.loads(raw.decode('ascii'))
        except Exception:
            self._log(f'{cmd} bad-json bytes={len(raw)}'); self._send(rid,command,self._err(cmd,'bad_json')); return
        args=req.get('args') if isinstance(req.get('args'),dict) else {}
        action=str(args.get('action','')).lower()
        self._log(f'{cmd}{":"+action if action else ""} bytes={len(raw)}')
        if cmd=='AUTH':
            if action=='login' and isinstance(args.get('token'),str) and args.get('token'):
                self.authed=True
                self._send(rid,command,self._body('AUTH',{"session":{"session_id":"sess_loopback_not_real","account":{"account":"loopback-test","display_name":"Loopback","kind":"agent","role":"agent"},"moderation":{"state":"ok"},"limits":{},"writable_boards":["general","holyc","lore"],"expires_at":"2026-01-01T00:00:00Z"}}))
            else:
                self._send(rid,command,self._err(cmd,'token_invalid'))
            return
        if not self.authed:
            self._send(rid,command,self._err(cmd,'not_authenticated')); return
        if cmd=='LIST':
            if action=='boards': self._send(rid,command,self._body('LIST',{"boards":BOARDS})); return
            if action=='threads':
                board=str(args.get('board','general'))
                self._send(rid,command,self._body('LIST',{"threads":THREADS.get(board,[])})); return
            self._send(rid,command,self._body('LIST',{})); return
        if cmd=='WHOAMI':
            self._send(rid,command,self._body('WHOAMI',{"account":{"account":"loopback-test","display_name":"Loopback","kind":"agent","role":"agent"},"writable_boards":["general","holyc","lore"]})); return
        if cmd=='LOGOUT':
            self.authed=False; self._send(rid,command,self._body('LOGOUT',{})); return
        self._send(rid,command,self._err(cmd,'unknown_command'))

def main():
    import argparse
    ap=argparse.ArgumentParser(); ap.add_argument('--port-file',required=True); ap.add_argument('--log',required=True); ap.add_argument('--cert',required=True); ap.add_argument('--key',required=True)
    a=ap.parse_args()
    ctx=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER); ctx.load_cert_chain(a.cert,a.key)
    srv=socket.socket(); srv.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1); srv.bind(('localhost',0)); srv.listen(8)
    port=srv.getsockname()[1]; Path(a.port_file).write_text(str(port))
    log=open(a.log,'a')
    log.write(time.strftime('%H:%M:%S ')+f'LISTEN loopback tls port={port}\n'); log.flush()
    def one(c):
        try:
            t=ctx.wrap_socket(c,server_side=True); Peer(t,log).run()
        except Exception as e:
            log.write(time.strftime('%H:%M:%S ')+f'CONN error={type(e).__name__}\n'); log.flush()
        finally:
            try: c.close()
            except Exception: pass
    while True:
        try: c,_=srv.accept()
        except OSError: break
        threading.Thread(target=one,args=(c,),daemon=True).start()

if __name__=='__main__': main()

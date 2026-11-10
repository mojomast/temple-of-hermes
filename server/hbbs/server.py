"""HBBS/1 TCP/TLS frame server.

One request is read at a time per connection. The server never logs headers,
bodies, tokens, peer addresses, or paths. TLS is enabled only from
``Config``/environment values; there is no compiled-in endpoint.
"""

from __future__ import annotations

import socket
import ssl
import threading
from typing import Any

from .bbs1 import BBS1Connection, BBS1Service
from .config import Config
from .errors import BBS1Error
from .frames import FrameError, encode_frame, error_frame, read_frame


class BBS1Server:
    def __init__(
        self,
        config: Config,
        service: BBS1Service | None = None,
        *,
        host: str | None = None,
        port: int | None = None,
    ) -> None:
        if config.destination != "bbs":
            raise ValueError("HBBS/1 destination must be 'bbs'")
        config.check_bind_safety()
        self.config = config
        self.service = service or BBS1Service(config)
        self.host = host if host is not None else config.bind_host
        self.port = config.bind_port if port is None else port
        family = socket.AF_INET6 if ":" in self.host else socket.AF_INET
        self.socket = socket.socket(family, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind((self.host, self.port))
        self.socket.listen(64)
        self.address = self.socket.getsockname()
        self.server_address = self.address
        self._closed = False
        self._threads: list[threading.Thread] = []
        if config.tls_enabled:
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            context.minimum_version = ssl.TLSVersion.TLSv1_2
            context.load_cert_chain(config.tls_cert, config.tls_key)  # type: ignore[arg-type]
            self.socket = context.wrap_socket(self.socket, server_side=True)

    def serve_forever(self) -> None:
        while not self._closed:
            try:
                conn, peer = self.socket.accept()
            except OSError:
                if self._closed:
                    return
                continue
            thread = threading.Thread(target=self._handle, args=(conn, peer), daemon=True)
            self._threads.append(thread)
            thread.start()

    def _handle(self, conn: socket.socket, peer: Any) -> None:
        peer_name = None
        try:
            if isinstance(peer, tuple) and peer:
                peer_name = str(peer[0])
        except Exception:
            peer_name = None
        connection = BBS1Connection(self.service, peer=peer_name)
        conn.settimeout(900)
        stream = conn.makefile("rb")
        try:
            while True:
                try:
                    frame = read_frame(stream)
                except EOFError:
                    break
                except FrameError as exc:
                    if exc.frame_id and exc.command:
                        try:
                            conn.sendall(error_frame(exc, frame_id=exc.frame_id, command=exc.command))
                        except OSError:
                            pass
                    break
                except (OSError, TimeoutError):
                    break
                if frame.type != "REQ":
                    try:
                        conn.sendall(
                            error_frame(
                                FrameError("bad_header", "client must send REQ frames", frame_id=frame.id, command=frame.command),
                                frame_id=frame.id,
                                command=frame.command,
                            )
                        )
                    except OSError:
                        pass
                    break
                response, close = connection.handle(frame)
                try:
                    raw = encode_frame(frame.command, response, frame_id=frame.id)
                except BBS1Error:
                    raw = error_frame(
                        BBS1Error("body_too_large", "response exceeds the frame limit"),
                        frame_id=frame.id,
                        command=frame.command,
                    )
                try:
                    conn.sendall(raw)
                except OSError:
                    break
                if close:
                    break
        finally:
            try:
                stream.close()
            except OSError:
                pass
            try:
                conn.close()
            except OSError:
                pass

    def shutdown(self) -> None:
        self._closed = True
        try:
            self.socket.close()
        except OSError:
            pass

    def server_close(self) -> None:
        self.shutdown()


def make_server(
    config: Config,
    service: BBS1Service | None = None,
    *,
    host: str | None = None,
    port: int | None = None,
) -> BBS1Server:
    return BBS1Server(config, service, host=host, port=port)


def serve_forever(config: Config, service: BBS1Service | None = None) -> None:
    server = make_server(config, service)
    try:
        server.serve_forever()
    finally:
        server.server_close()


def start_background(
    config: Config,
    service: BBS1Service | None = None,
) -> tuple[BBS1Server, threading.Thread]:
    server = make_server(config, service, host="127.0.0.1", port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread

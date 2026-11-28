# SPDX-License-Identifier: GPL-3.0-only
"""Exercise two emulated Ethernet devices with the same guest HTTP client."""
import functools
import hashlib
import secrets
import sys
import tempfile
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from compact_windows_w6_native import session
from phase9_busybox_report import check_hash


def main(image):
    out = Path('artifacts/phase3').resolve()
    with tempfile.TemporaryDirectory() as directory:
        payload = secrets.token_bytes(512)
        (Path(directory) / 'challenge').write_bytes(payload)
        handler = functools.partial(SimpleHTTPRequestHandler, directory=directory)
        with ThreadingHTTPServer(('127.0.0.1', 0), handler) as server:
            threading.Thread(target=server.serve_forever, daemon=True).start()
            try:
                port = server.server_port
                commands = ['ip/ipconfig -d ether /net/ether0; webfs',
                            f'hget http://10.0.2.2:{port}/challenge >/tmp/h3-net && echo H3_FETCH_OK',
                            'sha1sum -2 256 /tmp/h3-net']
                for model, driver in [('virtio-net-pci', 'virtio'), ('e1000', 'igbe')]:
                    log = session(image, commands, out, 'h3-' + model, 150,
                                  required={1: 'H3_FETCH_OK'}, net_model=model)
                    if not any(line.startswith(f'#l0: {driver}:'.encode()) for line in log.splitlines()):
                        raise ValueError(f'missing guest attachment for {model}')
                    check_hash(log, '/tmp/h3-net', hashlib.sha256(payload).hexdigest())
            finally:
                server.shutdown()


if __name__ == '__main__':
    main(Path(sys.argv[1]))

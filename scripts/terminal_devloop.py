# SPDX-License-Identifier: GPL-3.0-only
"""Exercise a clean guest C project and export its guest-requested macOS build."""
import hashlib
import secrets
import subprocess
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from compact_windows_w6_native import session, standalone
from phase9_busybox_report import check_hash


def main(image):
    out = Path('artifacts/phase3').resolve()
    first, second = [secrets.token_hex(8) for _ in range(2)]
    body = lambda token: f'int main(void){{puts("{token}");return 0;}}'
    source = ('#include <stdio.h>\n' + body(second) + '\n').encode()
    project = Path('rc/lib/ryz-env').read_bytes()
    endpoint = '/' + secrets.token_hex(20)
    with tempfile.TemporaryDirectory() as tmp:
        directory = Path(tmp)
        # The CI adapter only compiles the exact generated fixture. Its result is
        # sent back to the guest and later executed on the macOS reference runner.
        class Adapter(BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path != endpoint:
                    self.send_error(404)
                    return
                self.reply(project)

            def reply(self, data):
                self.send_response(200)
                self.send_header('Content-Length', str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def do_POST(self):
                if self.path != endpoint or self.headers.get('Content-Length') != str(len(source)):
                    self.send_error(400)
                    return
                received = self.rfile.read(len(source))
                if received != source:
                    self.send_error(422)
                    return
                unit = directory / 'main.c'
                unit.write_bytes(received)
                binary = directory / 'app'
                subprocess.run([sys.executable, '-m', 'ziglang', 'cc', '-target',
                                'x86_64-macos', '-Os', str(unit), '-o', str(binary)],
                               check=True, timeout=180)
                self.reply(binary.read_bytes())

        with ThreadingHTTPServer(('127.0.0.1', 0), Adapter) as server:
            threading.Thread(target=server.serve_forever, daemon=True).start()
            url = f'http://10.0.2.2:{server.server_port}{endpoint}'
            commands = [
                'ip/ipconfig -d ether /net/ether0; webfs',
                f'hget {url} >/tmp/devloop-rc && . /tmp/devloop-rc',
                'mkdir /tmp/devloop && cd /tmp/devloop && ryz env native',
                f"echo '#include <stdio.h>' >main.c; echo '{body(first)}' >>main.c",
                'ryz build && ryz run && echo RYZ_FIRST_OK',
                f"echo '{body(second)}' >/tmp/updated-line; {{ echo 2d; echo '$r /tmp/updated-line'; echo w; echo q }} | ed main.c",
                'ryz build && ryz run && echo RYZ_EDIT_OK',
                f"fn crosscc {{ hget -r 'Content-Length: '^\x60{{wc -c <$1}} -P {url} <$1 >$2 }}",
                'ryzmaccc=crosscc; ryz env trans windows macos && ryz status',
                'ryz build && echo RYZ_MAC_BUILD_OK',
                'sha1sum -2 256 build/macos/app',
            ]
            try:
                log = session(image, commands, out, 'terminal-devloop', 420,
                              required={4: 'RYZ_FIRST_OK', 6: 'RYZ_EDIT_OK', 9: 'RYZ_MAC_BUILD_OK'})
            finally:
                server.shutdown()
        for token in (first, second, 'workflow windows', 'target macos'):
            if not standalone(log, token):
                raise ValueError(f'missing guest output: {token}')
        binary = (directory / 'app').read_bytes()
        check_hash(log, 'build/macos/app', hashlib.sha256(binary).hexdigest())
        export = out / 'terminal-macos'
        export.mkdir(exist_ok=True)
        (export / 'app').write_bytes(binary)
        (export / 'expected.txt').write_text(second + '\n')
        (export / 'digest.txt').write_text(hashlib.sha256(binary).hexdigest() + '\n')


if __name__ == '__main__':
    main(Path(sys.argv[1]))

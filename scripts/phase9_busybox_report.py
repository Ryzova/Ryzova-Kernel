# SPDX-License-Identifier: GPL-3.0-only
"""Compare a two-file BusyBox report on Linux and across Ryzova guest boots."""
import functools
import hashlib
import http.server
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import threading

from compact_windows_w6_native import session
from phase9_shell import DIGEST

SCRIPT = b"""set -e
cd "$1"
printf '%s\\n' "$2" >first
printf '%s\\n' "$3" >second
{ read -r a <first && read -r b <second && printf '%s %s\\n' "$a" "$b"; } |
    { read -r a b && printf 'sum=%s\\n' "$((a+b))"; } >report
"""
STATE = '/usr/glenda/compact-report'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def check_hash(log, path, expected):
    pattern = rb'(?m)^([0-9a-f]{64})[ \t]+' + re.escape(path.encode()) + rb'\r?$'
    if re.findall(pattern, log) != [expected.encode()]:
        raise ValueError(f'guest SHA-256 mismatch for {path}')


def main(image):
    out = Path('artifacts/phase3').resolve()
    binary = out / 'busybox'
    if digest(binary.read_bytes()) != DIGEST:
        raise ValueError('BusyBox SHA-256 mismatch')
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
    a, b = [str(int(head[i:i+4], 16)) for i in (0, 4)]
    script = out / 'busybox-report.sh'
    script.write_bytes(SCRIPT)
    with tempfile.TemporaryDirectory() as work:
        subprocess.run([binary, 'ash', script, work, a, b], check=True, timeout=15)
        expected = (Path(work) / 'report').read_bytes()
    if expected != f'sum={int(a)+int(b)}\n'.encode():
        raise ValueError('incorrect Linux report')

    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=out)
    commands = ["ip/ipconfig -d ether /net/ether0; webfs",
                f'mkdir {STATE} && echo REPORT_DIR_OK',
                f'hget http://10.0.2.2:8000/busybox > {STATE}/busybox; sha1sum -2 256 {STATE}/busybox',
                f'hget http://10.0.2.2:8000/busybox-report.sh >/tmp/report.sh; sha1sum -2 256 /tmp/report.sh',
                f'/amd64/bin/compact-linux -j -W {STATE}/snapshot -i /tmp/report.sh {STATE}/busybox ash /input /tmp {a} {b} && echo REPORT_CREATED',
                f'sha1sum -2 256 {STATE}/snapshot; echo sync >> /srv/hjfs.cmd; sleep 5']
    with http.server.ThreadingHTTPServer(('127.0.0.1', 8000), handler) as server:
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            before = session(image, commands, out, 'busybox-report-write', 180,
                             required={1: 'REPORT_DIR_OK', 4: 'REPORT_CREATED'})
        finally:
            server.shutdown()
    check_hash(before, STATE+'/busybox', DIGEST)
    check_hash(before, '/tmp/report.sh', digest(SCRIPT))
    snapshots = re.findall(rb'(?m)^([0-9a-f]{64})\s+/usr/glenda/compact-report/snapshot\r?$', before)
    if len(snapshots) != 1:
        raise ValueError('missing snapshot digest')
    commands = [f'sha1sum -2 256 {STATE}/busybox {STATE}/snapshot',
                f'/amd64/bin/compact-linux -j -R {STATE}/snapshot {STATE}/busybox cat /tmp/report >/tmp/report-read && echo REPORT_READ',
                'sha1sum -2 256 /tmp/report-read']
    after = session(image, commands, out, 'busybox-report-read', 150, required={1: 'REPORT_READ'})
    check_hash(after, STATE+'/busybox', DIGEST)
    check_hash(after, STATE+'/snapshot', snapshots[0].decode())
    check_hash(after, '/tmp/report-read', digest(expected))
    receipt = dict(source_commit=head, busybox_sha256=DIGEST, inputs=[a,b],
                   linux_report=expected.decode(), report_sha256=digest(expected),
                   snapshot_sha256=snapshots[0].decode(), reboot_verified=True)
    (out/'busybox-report.json').write_text(json.dumps(receipt, indent=2)+'\n')
    print(json.dumps(receipt))


if __name__ == '__main__':
    main(Path(sys.argv[1]))

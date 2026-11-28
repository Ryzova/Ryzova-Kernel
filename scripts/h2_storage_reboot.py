# SPDX-License-Identifier: GPL-3.0-only
"""Write and reread the same guest file on independent QEMU storage overlays."""
import hashlib
import json
from pathlib import Path
import secrets
import subprocess
import sys
import tempfile

from compact_windows_w6_native import session, standalone
from phase9_busybox_report import check_hash


def main(image):
    out = Path('artifacts/phase3').resolve()
    path = '/usr/glenda/h2-proof'
    payload = secrets.token_hex(24)
    expected = hashlib.sha256((payload + '\n').encode()).hexdigest()
    results = {}
    with tempfile.TemporaryDirectory() as work:
        for controller, unit in [('scsi', 'sd00'), ('block', 'sdF0')]:
            overlay = Path(work) / (controller + '.qcow2')
            subprocess.run(['qemu-img', 'create', '-f', 'qcow2', '-F', 'qcow2',
                            '-b', str(image.resolve()), str(overlay)], check=True)
            for stage in ['write', 'read']:
                commands = [f'cat /dev/{unit}/ctl']
                required = {}
                if stage == 'write':
                    commands.append(f'test ! -e {path} && echo {payload} > {path} && echo H2_CREATED')
                    required[1] = 'H2_CREATED'
                commands.append(f'sha1sum -2 256 {path}')
                if stage == 'write':
                    commands.append('echo sync >> /srv/hjfs.cmd && sleep 5 && echo H2_SYNC')
                    required[3] = 'H2_SYNC'
                log = session(overlay, commands, out, f'h2-{controller}-{stage}',
                              150, required=required, boot_controller=controller)
                if not standalone(log, f'hjfs: fs is /dev/{unit}/fs'):
                    raise ValueError(f'{controller}: unexpected root filesystem')
                if not any(standalone(log, f'binding {unit[:-1]} {driver}')
                           for driver in ('virtio', 'virtio10')):
                    raise ValueError(f'{controller}: missing bound driver')
                check_hash(log, path, expected)
            results[controller] = dict(unit=unit, reboot_sha256=expected)
    (out / 'h2-storage.json').write_text(json.dumps(results, indent=2) + '\n')


if __name__ == '__main__':
    main(Path(sys.argv[1]))

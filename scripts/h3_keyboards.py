# SPDX-License-Identifier: GPL-3.0-only
"""Type into guest ed using QEMU keyboard events and verify the saved bytes."""
import hashlib
import secrets
import sys
from pathlib import Path

from compact_windows_w6_native import session
from phase9_busybox_report import check_hash


def main(image):
    out = Path('artifacts/phase3').resolve()
    for keyboard in ('ps2', 'usb'):
        token = secrets.token_hex(8)
        path = '/tmp/h3-' + token
        # The serial command starts ed. Only the keyboard supplies its input.
        commands = [f'ed {path} </dev/cons && echo H3_EDITOR_EXIT',
                    f'sha1sum -2 256 {path}']
        keys = ['a', 'ret', *token, 'ret', 'dot', 'ret', 'w', 'ret', 'q', 'ret']
        log = session(image, commands, out, 'h3-keyboard-' + keyboard, 90,
                      keyboard=keyboard, key_stages={0: keys})
        check_hash(log, path, hashlib.sha256((token + '\n').encode()).hexdigest())


if __name__ == '__main__':
    main(Path(sys.argv[1]))

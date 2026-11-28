# H4 physical PC qualification

Use the same kernel revision on two identified amd64 PCs with different controllers. Record the commit, kernel digest, machine model, controller and driver, and how the console is connected. Use dedicated test media and spare storage with no needed data. Capture the boot transcript. Redact network and machine identifiers before sharing.

| Check | Procedure | Evidence to keep |
| --- | --- | --- |
| Storage | Run `ryz hw list` and `ryz hw info /dev/sdUNIT` for the test volume. Write a unique text file on that mounted volume, record its SHA-256, sync the filesystem, reboot, and hash the same file again. | Binding line, volume path, two matching digests and reboot boundary. |
| Network | Fetch a known file from a reachable test server through the identified wired interface. | Interface attachment, client exit status and digest matching the server copy. |
| Keyboard | At the local keyboard console, type a fresh challenge into a file using the editor, save and reread it. Repeat with a second identified keyboard. Disconnect remote and serial input during the test. | Keyboard models, input paths, challenge and saved text for each. |
| Recovery | Reboot from the dedicated test media and reopen the project. | Boot transcript and intact project digest. |

Record each result as passed, failed or untested. Keep physical results separate from QEMU. No physical PC result has been recorded by this change.

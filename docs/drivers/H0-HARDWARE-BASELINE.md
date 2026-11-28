# H0 hardware baseline — amd64 pc64

Source inventory at `f3bdf973ba11bf36b28ae4a35a2bf308a8e59230`. The separate runtime sample is the successful [native QEMU run 46095887169](https://github.com/Ryzova/Ryzova-Kernel/actions/runs/46095887169). Its source-provenance.txt records guest source `e8ee28391eccf1061898910f5b2004520b0ad3b3`. The observations below use fresh-boot-serial.log from that single run.

| Device | Discovery or attachment evidence | Observed operation |
| --- | --- | --- |
| QEMU disk on virtio-scsi-pci | Harness attaches scsi-hd. Guest identifies QEMU HARDDISK at /dev/sd00 and hjfs selects /dev/sd00/fs. The transcript does not name the bound PCI driver for this disk. | Guest reads the bootfile setting from /n/9fat/plan9.ini and emits RYZOVA_STORAGE_OK. A controller-specific write/reboot comparison remains open. |
| VirtIO Ethernet | Guest registers #l0 as virtio and configures /net/ether0. | HTTP fetch returns the expected host fixture and emits RYZOVA_NETWORK_OK. |
| QEMU xHCI, keyboard and mouse | Guest usbxhci reports vendor 1b36 and device 000d. Harness requests USB keyboard and mouse. | Interactive shell uses a serial UART. This sample establishes no keyboard or mouse input event. |
| Display | Harness specifies std VGA and headless output. | Guest reports no framebuffer and rio fails to open /dev/draw. Physical display support is unmeasured. |
| PCI candidate interface | Guest reads #P/drivercandidates and observes auto-bind=no. | RYZOVA_M0_PCI_OK establishes candidate enumeration only. |

## Reproduction

From the inventory revision, run:

```sh
python3 scripts/driver_inventory.py --output /tmp/pc64-inventory.json
python3 scripts/driver_release_matrix.py --output /tmp/driver-matrix.json --gate-output /tmp/driver-gate.json
```

The inventory has 143 configuration entries, 95 enabled and 48 disabled. The reviewed subset covers 15 drivers and 101 source probe records, including four PCI class selectors. The matrix records zero physically verified devices. The driver inventory, hardware evidence and release matrix unittest suites passed (18 tests).

## H1 handoff

Expose discovery, attachment and verified operation as separate fields. For storage, preserve the existing /dev/sd interface and capture the controller identity and driver-to-disk association on boot. Use VirtIO SCSI as the first H2 baseline and test a second controller with the same file write, reboot and checksum workload before claiming interchangeability.

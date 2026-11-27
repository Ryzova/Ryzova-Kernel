"""Build a single-source amd64 C CLI using the native compiler or Zig's cross compiler."""
import argparse
import platform
import shutil
import subprocess
from pathlib import Path

TRIPLES = {"linux": "x86_64-linux-musl", "windows": "x86_64-windows-gnu",
           "macos": "x86_64-macos"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", choices=TRIPLES)
    parser.add_argument("source", type=Path)
    parser.add_argument("--out-dir", type=Path, default=Path("build"))
    parser.add_argument("--win32-source", action="store_true",
                        help="enable the Phase 5C Win32 directory API subset")
    args = parser.parse_args()
    source = args.source.resolve()
    if not source.is_file() or source.suffix != ".c":
        parser.error("expected a readable .c source file")
    native = {"Darwin": "macos", "Windows": "windows", "Linux": "linux"}.get(platform.system())
    if args.target == native and (native == "macos" or platform.machine().lower() in ("amd64", "x86_64")):
        compiler = shutil.which("clang" if native == "windows" else "cc")
        if not compiler:
            parser.error("native C compiler unavailable")
        command = [compiler]
        if native == "macos":
            command.extend(["-arch", "x86_64"])
    else:
        zig = shutil.which("zig")
        if not zig:
            parser.error("cross compilation requires zig on PATH")
        command = [zig, "cc", "-target", TRIPLES[args.target]]
    if args.win32_source and args.target != "windows":
        include = Path(__file__).resolve().parents[1] / "ryzova/compat/win32-source"
        command.extend(["-I", str(include)])
    directory = args.out_dir / args.target
    directory.mkdir(parents=True, exist_ok=True)
    binary = directory / (source.stem + (".exe" if args.target == "windows" else ""))
    subprocess.run([*command, "-std=c11", "-O2", str(source), "-o", str(binary)], check=True)
    print(binary)


if __name__ == "__main__":
    main()

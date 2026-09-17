"""Write or verify a complete payload checksum manifest; excludes Git and exports."""
import argparse
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / 'metadata/checksums.sha256'


def inventory():
    return sorted(p for p in ROOT.rglob('*') if p.is_file() and p != MANIFEST
                  and not any(part in {'.git', '__pycache__', 'exports', '.venv'}
                              for part in p.relative_to(ROOT).parts))


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def write():
    MANIFEST.write_text(''.join(f'{sha(p)}  {p.relative_to(ROOT).as_posix()}\n' for p in inventory()))


def check():
    expected = dict(line.split('  ', 1)[::-1] for line in MANIFEST.read_text().splitlines())
    actual = {p.relative_to(ROOT).as_posix(): sha(p) for p in inventory()}
    if expected != actual:
        changed = sorted(k for k in expected.keys() | actual.keys() if expected.get(k) != actual.get(k))
        raise ValueError(f'Checksum mismatch: {changed[:20]}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write', action='store_true', help='Explicitly refresh hashes after intentional edits.')
    args = parser.parse_args()
    write() if args.write else check()
    print('Checksum manifest written.' if args.write else 'Checksums verified.')

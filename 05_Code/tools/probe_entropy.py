#!/usr/bin/env python3
"""Diagnose which NAND regions are plaintext and where FAT/FS signatures live."""
import math
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from nand import Nand, parse_gpt, LBA  # noqa: E402


def entropy(b):
    if not b:
        return 0.0
    from collections import Counter
    c = Counter(b)
    n = len(b)
    return -sum((v / n) * math.log2(v / n) for v in c.values())


def dump(b, base=0, n=0x80):
    for i in range(0, min(n, len(b)), 16):
        print("    %04X  %s  %s" % (base + i, b[i:i + 16].hex(' '),
                                    ''.join(chr(c) if 32 <= c < 127 else '.'
                                            for c in b[i:i + 16])))


def main():
    with Nand() as n:
        parts = parse_gpt(n)
        print("=== partition head: 32 bytes + entropy(4KB) ===")
        for p in sorted(parts, key=lambda x: x.first_lba):
            head = n.read(p.offset, 0x20)
            ent = entropy(n.read(p.offset, 4096))
            print("  %-26s off=%d ent=%.2f  %s | %s" % (
                p.name, p.offset, ent, head.hex(' '),
                ''.join(chr(c) if 32 <= c < 127 else '.' for c in head)))

        print("\n=== seek plaintext FS signatures in the first 1 GB ===")
        region = n.read(0, 1 << 30)
        for sig in (b"MSDOS5.0", b"FAT32   ", b"NTFS    ", b"PFS0",
                    b"NCA3", b"CAL0", b"Nintendo", b"NAND", b"exFAT   "):
            hits = []
            pos = region.find(sig)
            while pos != -1 and len(hits) < 6:
                hits.append(pos)
                pos = region.find(sig, pos + 1)
            print("  %-10s -> %s" % (sig.decode('latin1'),
                                     [hex(h) for h in hits] or "none"))

        print("\n=== SYSTEM partition first / last sectors ===")
        sp = [p for p in parts if p.name == "SYSTEM"][0]
        print("  first sector:")
        dump(n.read(sp.offset, 0x100))
        print("  last sector (backup boot sector):")
        dump(n.read(sp.offset + sp.size - LBA, 0x100))

        print("\n=== SAFE / USER heads ===")
        for nm in ("SAFE", "USER", "PRODINFO"):
            pp = [p for p in parts if p.name == nm][0]
            print("  %s off=%d:" % (nm, pp.offset))
            dump(n.read(pp.offset, 0x60))
    return 0


if __name__ == "__main__":
    sys.exit(main())

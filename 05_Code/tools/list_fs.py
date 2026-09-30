#!/usr/bin/env python3
"""Enumerate the file structure of a decrypted NCA section pair.

ExeFS is a PFS0 container -> parse it directly.
RomFS is not stored at section offset 0 (the IVFC hash levels come first), so
instead of reimplementing IVFC walking we locate the RomFS metadata by its
own signature: a romfs header followed by directory/file tables whose entries
carry the filenames.

Usage:
    python list_fs.py <section0.bin> [section1.bin]
"""
import os
import struct
import sys


def parse_pfs0(data, off):
    if data[off:off + 4] != b"PFS0":
        return None
    count, strsize, _ = struct.unpack_from("<III", data, off + 4)
    strtab = off + 0x10 + count * 0x18
    out = []
    for i in range(count):
        o, sz, nameoff = struct.unpack_from("<QQI", data, off + 0x10 + i * 0x18)
        end = data.index(b"\x00", strtab + nameoff)
        name = data[strtab + nameoff:end].decode("utf-8", "replace")
        out.append((name, strtab + strsize + o, sz))
    return out


def find_pfs0(data):
    pos = data.find(b"PFS0")
    if pos < 0:
        return None, -1
    return parse_pfs0(data, pos), pos


def scan_strings(data, minlen=4, limit=400):
    out, cur, start = [], bytearray(), 0
    for i, b in enumerate(data):
        if 32 <= b < 127:
            if not cur:
                start = i
            cur.append(b)
        else:
            if len(cur) >= minlen:
                out.append((start, cur.decode("ascii")))
            cur = bytearray()
    if len(cur) >= minlen:
        out.append((start, cur.decode("ascii")))
    return out[:limit]


def main():
    sec0 = sys.argv[1]
    sec1 = sys.argv[2] if len(sys.argv) > 2 else None

    d0 = open(sec0, "rb").read()
    files, pos = find_pfs0(d0)
    print("=== ExeFS (PFS0) ===  magic at 0x%X" % pos)
    if files:
        tot = 0
        for name, o, sz in sorted(files, key=lambda x: -x[2]):
            print("   %-24s %10d B   @0x%X" % (name, sz, o))
            tot += sz
        print("   %d files, %d bytes" % (len(files), tot))
    else:
        print("   no PFS0")

    if not sec1:
        return 0
    d1 = open(sec1, "rb").read()
    print("\n=== RomFS section: %d bytes ===" % len(d1))
    nz = [(i, b) for i, b in enumerate(d1) if b]
    print("   first non-zero offset: %s   last: %s   nonzero: %d (%.2f%%)" % (
        hex(nz[0][0]) if nz else "-", hex(nz[-1][0]) if nz else "-",
        len(nz), 100.0 * len(nz) / len(d1)))

    print("\n   --- notable strings (extensions / paths) ---")
    ss = scan_strings(d1, 4, 4000)
    ext_hits = [s for s in ss if any(s[1].lower().endswith(e) for e in
               (".shader", ".ttf", ".otf", ".dic", ".json", ".txt", ".cfg",
                ".png", ".jpg", ".bin", ".gdc", ".dat", ".res", ".tres",
                ".gd", ".txt", ".csv", ".xml", ".yaml", ".po", ".mo"))]
    for off, s in ext_hits[:60]:
        print("     %08X  %s" % (off, s))
    if not ext_hits:
        print("     (none with a known extension)")
        print("     first 40 strings with offsets:")
        for off, s in ss[:40]:
            print("       %08X  %s" % (off, s))
    return 0


if __name__ == "__main__":
    sys.exit(main())

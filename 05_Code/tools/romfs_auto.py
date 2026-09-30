#!/usr/bin/env python3
"""Auto-walk an NCA RomFS from the decrypted section dump.

Reads the IVFC level table out of the NCA's FS header, picks the level that
contains the RomFS superblock, then prints the whole file tree with sizes.

Usage:
    python romfs_auto.py <nca_file> <section1.bin>
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from index_fw import xts_decrypt_fast  # noqa: E402
from nca import HEADER_SIZE, SECTOR, load_keys  # noqa: E402

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def ivfc_levels(fs):
    """Return [(offset, size)] from the IVFC superblock at fs[0x8:]."""
    iv = fs[0x8:]
    levels = []
    for i in range(6):
        o = 0x10 + i * 0x18
        off = int.from_bytes(iv[o:o + 8], "little")
        sz = int.from_bytes(iv[o + 8:o + 16], "little")
        levels.append((off, sz))
    return levels


def find_romfs(data, levels):
    """Return romfs header offset, or None."""
    for off, sz in reversed(levels):
        if off + 0x60 > len(data):
            continue
        hsz = int.from_bytes(data[off:off + 8], "little")
        if hsz == 0x50:
            return off
    return None


def walk(data, hdr_off, prefix="", depth=0, out=None):
    if out is None:
        out = []
    if depth > 16 or hdr_off is None:
        return out
    h = struct.unpack_from("<10Q", data, hdr_off)
    dm = hdr_off + h[3]
    fm = hdr_off + h[7]
    fd = hdr_off + h[9]

    seen = set()

    def rec(entry, pre, dep):
        if dep > 16 or entry in seen:
            return
        seen.add(entry)
        p, sib, child, file = struct.unpack_from("<IIII", data, dm + entry)
        c = child
        while c != 0xFFFFFFFF:
            e = dm + c
            cp, csib, cchild, cfile = struct.unpack_from("<IIII", data, e)
            nlen = struct.unpack_from("<I", data, e + 0x14)[0]
            nm = data[e + 0x18:e + 0x18 + nlen].decode("utf-8", "replace")
            out.append(("DIR", pre + nm + "/", 0))
            rec(c, pre + nm + "/", dep + 1)
            c = csib
        f = file
        while f != 0xFFFFFFFF:
            e = fm + f
            fp, fsib, fofs, fsz, fhash = struct.unpack_from("<IIQQI", data, e)
            nlen = struct.unpack_from("<I", data, e + 0x1C)[0]
            nm = data[e + 0x20:e + 0x20 + nlen].decode("utf-8", "replace")
            tag = ""
            if fd + fofs + 4 <= len(data) and data[fd + fofs:fd + fofs + 4] == b"Yaz0":
                tag = " [Yaz0]"
            out.append(("FILE", pre + nm, fsz))
            f = fsib

    rec(0, prefix, depth)
    return out


def main():
    nca, sec1 = sys.argv[1], sys.argv[2]
    keys = load_keys(os.path.join(HERE, "prod.keys"))
    with open(nca, "rb") as fh:
        raw = fh.read(HEADER_SIZE)
    hdr = xts_decrypt_fast(keys["header_key"], raw, endian="big")
    pid = struct.unpack_from("<Q", hdr, 0x210)[0]
    fs = hdr[0x600:0x800]
    levels = ivfc_levels(fs)
    data = open(sec1, "rb").read()
    ro = find_romfs(data, levels)
    print("programId=%016X  section=%d bytes" % (pid, len(data)))
    print("IVFC levels:", [("0x%X" % o, "0x%X" % s) for o, s in levels])
    print("romfs header @", hex(ro) if ro is not None else "NOT FOUND")
    if ro is None:
        return 1
    entries = walk(data, ro)
    dirs = [e for e in entries if e[0] == "DIR"]
    files = [e for e in entries if e[0] == "FILE"]
    print("dirs=%d files=%d total=%d bytes" % (
        len(dirs), len(files), sum(f[2] for f in files)))
    print()
    for kind, name, size in entries:
        if kind == "DIR":
            print("  DIR  %s" % name)
        else:
            print("  FILE %-60s %10d" % (name, size))
    return 0


if __name__ == "__main__":
    sys.exit(main())

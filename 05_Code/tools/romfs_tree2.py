#!/usr/bin/env python3
"""Print the complete file tree of a decrypted NCA RomFS section.

Layout established for swkbd (section offset of RomFS header = 0x14000):
    romfs_hdr_t          @ 0x14000
    dir_hash_table       @ hdr + hdr.dir_hash_table_offset
    dir_meta             @ hdr + hdr.dir_meta_offset
    file_hash_table      @ hdr + hdr.file_hash_table_offset
    file_meta            @ hdr + hdr.file_meta_offset
    file data            @ hdr + hdr.file_data_offset      (= 0x14200)

Entry layouts (hactool romfs.h):
    dir  : u32 parent, u32 sibling, u32 child, u32 file, u32 hash, u32 name_len, name
    file : u32 parent, u32 sibling, u64 offset, u64 size, u32 hash, u32 name_len, name
Names are padded to 4 bytes. Offsets are relative to the file-data base.

Usage:
    python romfs_tree2.py <section1.bin> <hdr_off_hex>
"""
import os
import struct
import sys


def main():
    sec, hdr_off = sys.argv[1], int(sys.argv[2], 0)
    d = open(sec, "rb").read()
    h = struct.unpack_from("<10Q", d, hdr_off)
    (hsz, dht_o, dht_s, dm_o, dm_s, fht_o, fht_s, fm_o, fm_s, fd_o) = h
    print("romfs_hdr @0x%X  header_size=0x%X" % (hdr_off, hsz))
    print("  dir  hash @0x%X size=0x%X   dir  meta @0x%X size=0x%X" % (
        hdr_off + dht_o, dht_s, hdr_off + dm_o, dm_s))
    print("  file hash @0x%X size=0x%X   file meta @0x%X size=0x%X" % (
        hdr_off + fht_o, fht_s, hdr_off + fm_o, fm_s))
    print("  file data @0x%X" % (hdr_off + fd_o))

    dm_base = hdr_off + dm_o
    fm_base = hdr_off + fm_o
    data_base = hdr_off + fd_o

    files = []

    def dir_name(e):
        nlen = struct.unpack_from("<I", d, e + 0x14)[0]
        return d[e + 0x18:e + 0x18 + nlen].decode("utf-8", "replace")

    def file_name(e):
        nlen = struct.unpack_from("<I", d, e + 0x1C)[0]
        return d[e + 0x20:e + 0x20 + nlen].decode("utf-8", "replace")

    seen = set()

    def rec(entry, prefix, depth):
        if depth > 16:
            return
        key = entry
        if key in seen:
            return
        seen.add(key)
        p, sib, child, file = struct.unpack_from("<IIII", d, dm_base + entry)
        c = child
        while c != 0xFFFFFFFF:
            e = dm_base + c
            cp, csib, cchild, cfile = struct.unpack_from("<IIII", d, e)
            nm = dir_name(e)
            print("  DIR  %s%s/" % (prefix, nm))
            rec(c, prefix + nm + "/", depth + 1)
            c = csib
        f = file
        while f != 0xFFFFFFFF:
            e = fm_base + f
            fp, fsib, fofs, fsz, fhash = struct.unpack_from("<IIQQI", d, e)
            nm = file_name(e)
            full = prefix + nm
            comp = ""
            if data_base + fofs + 4 <= len(d):
                if d[data_base + fofs:data_base + fofs + 4] == b"Yaz0":
                    comp = " [Yaz0]"
            print("  FILE %-56s %9d B  off=0x%X%s" % (full, fsz, fofs, comp))
            files.append((full, fofs, fsz, comp))
            f = fsib

    print("\n=== RomFS tree ===")
    rec(0, "", 0)
    print("\n%d files total" % len(files))
    tot = sum(f[2] for f in files)
    print("total declared size: %d bytes" % tot)
    return 0


if __name__ == "__main__":
    sys.exit(main())

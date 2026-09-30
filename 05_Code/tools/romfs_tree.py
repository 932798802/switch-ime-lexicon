#!/usr/bin/env python3
"""List the real file tree of a decrypted NCA RomFS section.

The IVFC superblock (in the NCA FS header) locates the RomFS metadata level.
For swkbd that is level 4 at section offset 0x10000. The RomFS header and the
directory/file metadata tables there are NOT compressed, so the names are
readable directly.

Usage:
    python romfs_tree.py <section1.bin> <metadata_offset_hex>
"""
import os
import struct
import sys


def dump_section(d, base, n=0x60):
    for o in range(0, n, 16):
        r = d[base + o:base + o + 16]
        print("    %04X  %s  %s" % (o, r.hex(' '),
                                    ''.join(chr(c) if 32 <= c < 127 else '.' for c in r)))


def walk(d, meta_base, dir_meta_off, file_meta_off, data_base, limit=4000):
    """Walk RomFS dir/file metadata tables.

    Directory entry : u32 parent, u32 sibling, u32 child, u32 file, u32 hash,
                      u32 name_len, name (padded to 4)
    File entry      : u32 parent, u32 sibling, u64 offset, u64 size, u32 hash,
                      u32 name_len, name (padded to 4)
    """
    files = []
    dirs = {}

    def name_at(p):
        nlen = struct.unpack_from("<I", d, p)[0]
        return d[p + 4:p + 4 + nlen].decode("utf-8", "replace"), p + 4 + ((nlen + 3) & ~3)

    def walk_dir(entry):
        # entry -> (parent, sibling, child, file)
        p = entry
        parent, sibling, child, fchild = struct.unpack_from("<IIII", d, p)
        # children
        c = child
        while c != 0xFFFFFFFF and len(files) < limit:
            nm, nxt = name_at(c + 0x14)
            c = nxt
            dparent, dsib, dchild, dfchild = struct.unpack_from("<IIII", d, c)
            dirs_len = c
            walk_dir(c) if dchild != 0xFFFFFFFF else None
            c = dsib
        f = fchild
        while f != 0xFFFFFFFF and len(files) < limit:
            fm, nxt = name_at(f + 0x14 + 8 + 8)
            f = nxt
            fparent, fsib, foff, fsize, fhash = struct.unpack_from("<IIQQI", d, f)
            fm, nxt = name_at(f + 0x1C)
            files.append((fm, foff, fsize))
            f = fsib

    # The root dir entry is the first 0x18 bytes of dir_meta
    root = dir_meta_off

    def rec(entry, prefix, depth):
        if depth > 12 or len(files) > limit:
            return
        parent, sibling, child, fchild = struct.unpack_from("<IIII", d, meta_base + entry)
        c = child
        while c != 0xFFFFFFFF:
            e = meta_base + c
            dparent, dsib, dchild, dfchild = struct.unpack_from("<IIII", d, e)
            nlen = struct.unpack_from("<I", d, e + 0x10)[0]
            nm = d[e + 0x14:e + 0x14 + nlen].decode("utf-8", "replace")
            print("      DIR  %s%s/" % (prefix, nm))
            rec(c, prefix + nm + "/", depth + 1)
            c = dsib
        f = fchild
        while f != 0xFFFFFFFF:
            e = meta_base + f
            fparent, fsib, foff, fsize, fhash = struct.unpack_from("<IIQQI", d, e)
            nlen = struct.unpack_from("<I", d, e + 0x1C)[0]
            nm = d[e + 0x20:e + 0x20 + nlen].decode("utf-8", "replace")
            files.append((prefix + nm, foff, fsize))
            print("      FILE %-52s %9d B  off=0x%X" % (prefix + nm, fsize, foff))
            f = fsib

    rec(0, "", 0)
    return files


def main():
    sec = sys.argv[1]
    meta = int(sys.argv[2], 0)
    d = open(sec, "rb").read()
    print("section: %d bytes; romfs metadata at 0x%X" % (len(d), meta))
    print("\n--- presumed romfs_hdr_t ---")
    dump_section(d, meta, 0x60)
    vals = struct.unpack_from("<10Q", d, meta)
    names = ["header_size", "dir_hash_table_off", "dir_hash_table_size",
             "dir_meta_off", "dir_meta_size", "file_hash_table_off",
             "file_hash_table_size", "file_meta_off", "file_meta_size",
             "file_data_off"]
    for n, v in zip(names, vals):
        print("   %-22s = 0x%X (%d)" % (n, v, v))
    return 0


if __name__ == "__main__":
    sys.exit(main())

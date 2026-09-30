#!/usr/bin/env python3
"""Extract a decrypted RomFS section into real files.

The NCA RomFS section holds the whole IVFC image: hash levels + metadata + file
data. The RomFS header (0x50 bytes, no magic) sits at the start of the metadata
partition, and every other offset is relative to it. We locate it by its
fingerprint -- header_size == 0x50 followed immediately by
dir_hash_table_offset == 0x50.

RomFS header (all u64, little endian):
    0x00 header_size          0x08 dir_hash_off     0x10 dir_hash_size
    0x18 dir_meta_off         0x20 dir_meta_size    0x28 file_hash_off
    0x30 file_hash_size       0x38 file_meta_off    0x40 file_meta_size
    0x48 data_off

Directory entry (0x18 + name):
    0x00 parent  0x04 sibling  0x08 child  0x0C file  0x10 hash
    0x14 u32 name_size   0x18 name (UTF-8)
File entry (0x20 + name):
    0x00 parent  0x04 sibling  0x08 u64 data_offset  0x10 u64 data_size
    0x18 hash    0x1C u32 name_size   0x20 name (UTF-8)

Usage:
    python romfs_extract.py <section.bin> [outdir] [--list-only]
"""
import os
import struct
import sys


def find_romfs_header(d):
    """Return the offset of the RomFS header, or None."""
    needle = struct.pack("<QQ", 0x50, 0x50)
    p = d.find(needle)
    while p >= 0:
        # sanity: data_off must be inside the section and be the largest offset
        try:
            hdr = struct.unpack_from("<9Q", d, p)
        except struct.error:
            return None
        hsz, dho, dhs, dmo, dms, fho, fhs, fmo, fms = hdr
        data_off = struct.unpack_from("<Q", d, p + 0x48)[0]
        if (hsz == 0x50 and dho == 0x50 and dmo > 0 and fmo > 0
                and dmo + dms <= len(d) and fmo + fms <= len(d)
                and data_off < len(d)):
            return p
        p = d.find(needle, p + 1)
    return None


def parse(d):
    base = find_romfs_header(d)
    if base is None:
        return None, None
    (hsz, dho, dhs, dmo, dms, fho, fhs, fmo, fms) = struct.unpack_from(
        "<9Q", d, base)
    data_off = struct.unpack_from("<Q", d, base + 0x48)[0]
    info = dict(header=base, dir_hash=dho, dir_hash_size=dhs,
                dir_meta=dmo, dir_meta_size=dms, file_hash=fho,
                file_hash_size=fhs, file_meta=fmo, file_meta_size=fms,
                data=data_off)

    dirs = []      # (parent, sibling, child, file, name)
    p = base + dmo
    end = p + dms
    while p + 0x18 <= end:
        parent, sibling, child, fdir, h, nsz = struct.unpack_from(
            "<IIIIII", d, p)
        name = d[p + 0x18:p + 0x18 + nsz].decode("utf-8", "replace")
        if nsz == 0 or p + 0x18 + nsz > end:
            break
        dirs.append((parent, sibling, child, fdir, name))
        p += 0x18 + nsz
        p = (p + 3) & ~3

    files = []     # (parent, offset, size, name)
    p = base + fmo
    end = p + fms
    while p + 0x20 <= end:
        parent, sibling, foff, fsz, h, nsz = struct.unpack_from("<IIQQII", d, p)
        name = d[p + 0x20:p + 0x20 + nsz].decode("utf-8", "replace")
        if nsz == 0 or p + 0x20 + nsz > end:
            break
        files.append((parent, foff, fsz, name))
        p += 0x20 + nsz
        p = (p + 3) & ~3

    # rebuild paths: dir index 0 is the root
    child_of = {}
    for i, (par, sib, ch, fi, nm) in enumerate(dirs):
        child_of.setdefault(par, []).append(i)
    path = {0: ""}
    stack = [0]
    seen = set()
    while stack:
        i = stack.pop()
        if i in seen or i not in path:
            continue
        seen.add(i)
        for c in child_of.get(i, []):
            path[c] = path[i] + dirs[c][4] + "/"
            stack.append(c)
    files_of = {}
    for j, (par, off, sz, nm) in enumerate(files):
        files_of.setdefault(par, []).append(j)

    listing = []
    for j, (par, off, sz, nm) in enumerate(files):
        listing.append((path.get(par, "?/") + nm, off, sz))
    return info, listing


def main():
    path = sys.argv[1]
    outdir = sys.argv[2] if len(sys.argv) > 2 else \
        os.path.join(os.path.dirname(path), "romfs_files")
    list_only = "--list-only" in sys.argv
    d = open(path, "rb").read()
    info, listing = parse(d)
    if info is None:
        print("RomFS header not found in %s" % path)
        return 1
    print("section %d bytes (0x%X)" % (len(d), len(d)))
    print("romfs header @0x%X  dir_meta=0x%X(%d) file_meta=0x%X(%d) "
          "data=0x%X" % (info["header"], info["dir_meta"],
                         info["dir_meta_size"], info["file_meta"],
                         info["file_meta_size"], info["data"]))
    print("files: %d" % len(listing))
    total = 0
    for name, off, sz in sorted(listing, key=lambda x: -x[2]):
        print("  %-58s %10d  @0x%X" % (name, sz, info["data"] + off))
        total += sz
    print("  total file bytes: %d (%.2f MB)" % (total, total / 1048576))
    if list_only:
        return 0
    os.makedirs(outdir, exist_ok=True)
    for name, off, sz in listing:
        rel = name.replace("..", "_").lstrip("/")
        dst = os.path.join(outdir, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        with open(dst, "wb") as fh:
            fh.write(d[info["data"] + off:info["data"] + off + sz])
    print(">> extracted to %s" % outdir)
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Extract `main` from a decrypted ExeFS section and decompress the NSO0.

An NSO's segments are LZ4-compressed, so the on-disk 3.2 MB of swkbd's main
says nothing about the real code/rodata size -- the conversion dictionary (if
any) only becomes visible after decompression.

Header layout is taken verbatim from hactool's ref/nso.h:

    typedef struct { u32 file_off; u32 dst_off; u32 decomp_size;
                     u32 align_or_total_size; } nso0_segment_t;
    typedef struct {
        u32 magic;      // "NSO0"
        u32 _0x4;
        u32 _0x8;
        u32 flags;               // bit0 text, bit1 rodata, bit2 data compressed
        nso0_segment_t segments[3];   // @0x10
        u8  build_id[0x20];           // @0x40
        u32 compressed_sizes[3];      // @0x60
        u8  _0x6C[0x24];              // @0x6C
        u64 dynstr_extents;           // @0x90
        u64 dynsym_extents;           // @0x98
        u8  section_hashes[3][0x20];  // @0xA0
    } nso0_header_t;                  // sizeof == 0x100

and ref/nso.c decompresses each segment as ONE raw LZ4 block via
LZ4_decompress_safe(src, dst, compressed_sizes[i], decomp_size). There is no
per-64K block chain and no 8-byte dummy prefix -- do not add one.

Usage:
    python nso_dump.py <exefs_section0.bin> [outdir]
"""
import os
import struct
import sys

import lz4.block

MAGICS = (b"NSO0", b"META", b"PFS0", b"ROM0", b"IVFC", b"HFS0")
SEGS = ("text", "rodata", "data")


def parse_pfs0(data, off=0):
    """Try both known PFS0 entry layouts; return (files, layout_name).

    Firmware 20+ system titles use 0x18-byte entries with three u64 fields;
    the older hactool layout is 0x10-byte entries of four u32 fields. We
    disambiguate empirically: the correct layout must place entry 0 at offset 0
    and entry 1 exactly after entry 0.
    """
    if data[off:off + 4] != b"PFS0":
        return None, None
    count, strsz = struct.unpack_from("<II", data, off + 4)
    if not (0 < count < 4096):
        return None, None
    cands = []
    for name, ent_size, fmt in (("0x18/u64", 0x18, "<QQQ"),
                                ("0x10/u32", 0x10, "<IIII")):
        p0 = off + 0x10
        ents = [struct.unpack_from(fmt, data, p0 + i * ent_size)
                for i in range(count)]
        if not (ents[0][0] == 0 and (count == 1 or ents[1][0] == ents[0][1])):
            continue
        strtab_off = p0 + count * ent_size
        base = strtab_off + strsz
        hits = sum(1 for e in ents
                   if data[base + e[0]:base + e[0] + 4] in MAGICS)
        cands.append((hits, name, base, data[strtab_off:base], ents))
    if not cands:
        return None, None
    cands.sort(key=lambda c: -c[0])
    hits, name, base, estr, ents = cands[0]
    files = []
    for e in ents:
        no = e[2]
        end = estr.find(b"\0", no)
        nm = estr[no:end if end >= 0 else len(estr)].decode("utf-8", "replace")
        files.append((nm, base + e[0], e[1]))
    tag = name if hits == len(ents) else "%s (%d/%d valid)" % (
        name, hits, len(ents))
    return files, tag


def nso_info(blob):
    """Return (flags, segments, compressed_sizes, build_id, header_dict)."""
    if blob[:4] != b"NSO0":
        return None
    flags = struct.unpack_from("<I", blob, 0x0C)[0]
    segs = [struct.unpack_from("<IIII", blob, 0x10 + i * 0x10)
            for i in range(3)]
    csz = struct.unpack_from("<III", blob, 0x60)
    return flags, segs, csz, blob[0x40:0x60]


def main():
    path = sys.argv[1]
    outdir = sys.argv[2] if len(sys.argv) > 2 else \
        os.path.join(os.path.dirname(path), "nso")
    os.makedirs(outdir, exist_ok=True)
    d = open(path, "rb").read()
    print("exefs section: %d bytes (0x%X)" % (len(d), len(d)))

    pos = d.find(b"PFS0")
    files, layout = parse_pfs0(d, pos)
    print("PFS0 @0x%X   layout: %s" % (pos, layout))
    if not files:
        print("!! could not parse PFS0")
        return 1
    for nm, o, sz in files:
        print("  %-14s %10d B @0x%X  magic=%r" % (nm, sz, o, d[o:o + 4]))

    for nm, o, sz in files:
        if nm != "main":
            continue
        blob = d[o:o + sz]
        info = nso_info(blob)
        if info is None:
            print("main is not NSO0 (magic %r)" % blob[:4])
            return 1
        flags, segs, csz, bid = info
        print("\n=== NSO0 header ===")
        print("  flags=0x%X  build_id=%s" % (flags, bid.hex()))
        total = 0
        for i, (name, csize) in enumerate(zip(SEGS, csz)):
            fo, do, dsz, al = segs[i]
            print("  %-7s file_off=0x%-9X dst_off=0x%-9X decomp=%8d (0x%X)"
                  "  comp=%8d  align=%d" % (name, fo, do, dsz, dsz, csize, al))
        total_mem = segs[2][1] + segs[2][2]
        print("  linear span: %d bytes (%.2f MB)" % (total_mem,
                                                     total_mem / 1048576))
        for i, (name, csize) in enumerate(zip(SEGS, csz)):
            fo, do, dsz, al = segs[i]
            if dsz == 0:
                continue
            raw = blob[fo:fo + csize]
            compressed = bool(flags & (1 << i))
            if compressed:
                try:
                    out = lz4.block.decompress(raw, uncompressed_size=dsz)
                except Exception as exc:                       # noqa: BLE001
                    print("  !! %s LZ4 failed: %s" % (name, exc))
                    continue
            else:
                out = raw
            outp = os.path.join(outdir, "main.%s.bin" % name)
            with open(outp, "wb") as fh:
                fh.write(out)
            total += len(out)
            print("  -> %-7s %9d B (%s)  %s" % (
                name, len(out), "lz4" if compressed else "raw", outp))
        print("  total decompressed: %d bytes (%.2f MB)" % (
            total, total / 1048576))
    return 0


if __name__ == "__main__":
    sys.exit(main())

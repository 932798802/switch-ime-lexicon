#!/usr/bin/env python3
"""Unpack a decrypted NCA RomFS section: Yaz0 streams -> SARC archives -> names.

Nintendo system titles keep graphics/sound assets as Yaz0-compressed SARC
archives inside RomFS. Walking those archives yields the real file list, which
is what decides whether an asset (like a dictionary) is replaceable via
LayeredFS.

Yaz0 format (canonical, no EOF marker):
    u8  magic[4]  "Yaz0"
    u32 size      decompressed size (big endian)
    u8  reserved[8]
    then a bit stream starting at +0x10:
        code byte, MSB first
          bit = 1 -> literal byte
          bit = 0 -> two bytes b1 b2
                     dist = ((b1 & 0x0F) << 8) | b2
                     len  = (b1 >> 4) + 2      if (b1 >> 4) != 0
                          = next_byte + 0x12   if (b1 >> 4) == 0
                     copy from (out_len - dist - 1)
    The stream simply ends once `size` bytes have been produced. There is NO
    0x0000 terminator -- 0x0000 is a valid back-reference (dist 0 = repeat the
    previous byte 18 times), and mistaking it for EOF truncates any stream that
    contains zero runs (which SARC header padding guarantees).

Usage:
    python romfs_dump.py <section1.bin> [outdir]
"""
import os
import struct
import sys


def yaz0_decompress(d, off, strict=True):
    """Return (decompressed_bytes, bytes_consumed) or (None, reason_str)."""
    if d[off:off + 4] != b"Yaz0":
        return None, "no Yaz0 magic"
    size = int.from_bytes(d[off + 4:off + 8], "big")
    i = off + 0x10
    out = bytearray()
    n = len(d)
    while len(out) < size:
        if i >= n:
            msg = "ran off end of file at %d/%d bytes" % (len(out), size)
            return bytes(out), msg if not strict else msg
        code = d[i]
        i += 1
        for bit in range(7, -1, -1):
            if len(out) >= size:
                break
            if (code >> bit) & 1:
                if i >= n:
                    return bytes(out), "literal overrun"
                out.append(d[i])
                i += 1
            else:
                if i + 2 > n:
                    return bytes(out), "backref header overrun"
                b1, b2 = d[i], d[i + 1]
                i += 2
                dist = ((b1 & 0x0F) << 8) | b2
                if (b1 >> 4) == 0:
                    if i >= n:
                        return bytes(out), "long backref overrun"
                    ln = d[i] + 0x12
                    i += 1
                else:
                    ln = (b1 >> 4) + 2
                s = len(out) - dist - 1
                if s < 0:
                    return bytes(out), "backref before start (%d)" % s
                for k in range(ln):
                    if len(out) >= size:
                        break
                    out.append(out[s + k])
    return bytes(out), i - off


def parse_sarc(d):
    """Parse a SARC archive. Returns list of (name, abs_offset, size) or None."""
    if len(d) < 0x20 or d[:4] != b"SARC":
        return None
    file_size = struct.unpack_from("<I", d, 0x08)[0]
    data_off = struct.unpack_from("<I", d, 0x0C)[0]
    if d[0x14:0x18] != b"SFAT":
        return None
    node_count = struct.unpack_from("<H", d, 0x1A)[0]
    nodes = []
    p = 0x1C
    for _ in range(node_count):
        if p + 0x10 > len(d):
            break
        _h, attr, ds, de = struct.unpack_from("<IIII", d, p)
        nodes.append((attr, ds, de))
        p += 0x10
    if d[p:p + 4] != b"SFNT":
        return None
    strtab = p + 8
    files = []
    for attr, ds, de in nodes:
        noff = attr & 0xFFFFFF
        nlen = (attr >> 24) & 0xFF
        name = d[strtab + noff:strtab + noff + nlen].decode("utf-8", "replace")
        files.append((name, data_off + ds, de - ds))
    return files, file_size


def find_romfs_dir(data, base, size):
    """Best-effort: locate the RomFS file-metadata table inside raw file bytes
    (it may be a directory, or a file whose own content is a dir listing)."""
    return None


def main():
    path = sys.argv[1]
    outdir = sys.argv[2] if len(sys.argv) > 2 else \
        os.path.join(os.path.dirname(path), "romfs_unpacked")
    os.makedirs(outdir, exist_ok=True)
    d = open(path, "rb").read()
    print("romfs section: %d bytes (0x%X)" % (len(d), len(d)))

    offs = []
    p = d.find(b"Yaz0")
    while p >= 0:
        offs.append(p)
        p = d.find(b"Yaz0", p + 1)
    print("Yaz0 streams found: %d" % len(offs))

    allfiles = []
    nbad = 0
    for k, off in enumerate(offs):
        blob, used = yaz0_decompress(d, off)
        tag = "y%02d_%X" % (k, off)
        if blob is None:
            print("  [!] %s @0x%X: %s" % (tag, off, used))
            nbad += 1
            continue
        want = int.from_bytes(d[off + 4:off + 8], "big")
        ok = (len(blob) == want)
        if not ok:
            nbad += 1
        with open(os.path.join(outdir, tag + ".bin"), "wb") as fh:
            fh.write(blob)

        res = parse_sarc(blob)
        flag = "" if ok else "  <-- SHORT (wanted %d)" % want
        if res:
            files, declared = res
            print("\n--- %s @0x%X -> %d B  SARC, %d entries%s" % (
                tag, off, len(blob), len(files), flag))
            for name, o, sz in sorted(files, key=lambda x: -x[2]):
                print("      %-52s %9d B" % (name, sz))
            allfiles.append((tag, off, files))
            sub = os.path.join(outdir, tag + "_sarc")
            os.makedirs(sub, exist_ok=True)
            for name, o, sz in files:
                safe = name.replace("/", "_").replace("\\", "_")
                if not safe or sz <= 0:
                    continue
                with open(os.path.join(sub, safe), "wb") as fh:
                    fh.write(blob[o:o + sz])
        else:
            print("  %s @0x%X -> %d B%s  head=%r" % (
                tag, off, len(blob), flag, blob[:12]))

    txt = os.path.join(outdir, "all_names.txt")
    total = 0
    with open(txt, "w", encoding="utf-8") as fh:
        for tag, off, files in allfiles:
            for name, o, sz in files:
                fh.write("%s\t%s\t%d\n" % (tag, name, sz))
                total += 1
    print("\n>> %d SARC archives, %d files total, %d bad streams" % (
        len(allfiles), total, nbad))
    print(">> index: %s" % txt)
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Dump the strings inside a Switch MSBT (MsgStdBn) message file.

MSBT layout:
    header  : "MsgStdBn" + BOM + version + section_count + file_size + pad
    sections: "LBL1" labels, "TXT2" texts, "ATR1" attributes, "ATO1"
    TXT2    : u32 string_count, u32 offsets[], then UTF-16 strings

Usage:
    python msbt_dump.py <file.msbt> [--labels]
"""
import struct
import sys


def sections(d):
    """Section walk.

    Header: "MsgStdBn" + bom(0x08) + version(0x0A) + section_count(0x0E) + ...
    Section: magic[4] + size(u32, includes this 0x10 header) + reserved[8]
    """
    if d[:8] != b"MsgStdBn":
        return None
    n = struct.unpack_from("<H", d, 0x0E)[0]
    out = []
    p = 0x20
    for _ in range(n):
        magic = d[p:p + 4]
        size = struct.unpack_from("<I", d, p + 4)[0]
        out.append((magic.decode("latin1"), p + 0x10, size - 0x10))
        p += size
    return out


def read_labels(d, off, size):
    count = struct.unpack_from("<I", d, off)[0]
    labels = []
    p = off + 4
    for _ in range(count):
        blen = d[p]
        name = d[p + 1:p + 1 + blen].decode("ascii", "replace")
        nidx = struct.unpack_from("<I", d, p + 1 + blen)[0]
        p += 1 + blen + 4
        labels.append(name)
    return labels


def read_texts(d, off, size):
    count = struct.unpack_from("<I", d, off)[0]
    tbl = off + 4
    out = []
    for i in range(count):
        toff = struct.unpack_from("<I", d, tbl + i * 4)[0]
        p = off + toff
        end = p
        while end + 1 < len(d) and d[end:end + 2] != b"\x00\x00":
            end += 2
        out.append(d[p:end].decode("utf-16-le", "replace"))
    return out


def main():
    path = sys.argv[1]
    d = open(path, "rb").read()
    print("file: %s (%d bytes)" % (path, len(d)))
    secs = sections(d)
    if not secs:
        print("not an MSBT file; head:", d[:16])
        return 1
    print("sections:", [(s[0], s[2]) for s in secs])

    labels, texts = [], []
    for magic, off, size in secs:
        if magic == "LBL1":
            labels = read_labels(d, off, size)
        elif magic == "TXT2":
            texts = read_texts(d, off, size)

    print("\nlabels: %d   texts: %d" % (len(labels), len(texts)))
    print("\n--- all strings ---")
    for i, t in enumerate(texts):
        name = labels[i] if i < len(labels) else "#%d" % i
        print("  [%3d] %-28s %r" % (i, name, t))
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Sweep every system `Data` / `PublicData` title for IME-dictionary material.

These titles are all RomFS. RomFS stores its directory/file names as plain
UTF-16LE inside the metadata level, so a UTF-16LE string scan over the
decrypted section yields the full name list -- enough to tell whether a title
is a font pack, a dictionary, a timezone db, etc.

Usage:
    python scan_data.py [--kw] [--dump <title_id> <outdir>]
"""
import json
import os
import re
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from index_fw import xts_decrypt_fast  # noqa: E402
from nca import HEADER_SIZE, SECTOR, load_keys  # noqa: E402
from dump_nca import KAEK, build_iv, ctr_all, ecb_dec  # noqa: E402

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KEYS = os.path.join(HERE, "prod.keys")
FW = r"F:/NSbackup/20260927/AMS-22.5.0"
INDEX = os.path.join(HERE, "fw_index.json")

# terms that would indicate input-method dictionary / font material
IME_KW = (b"njbase", b"njtan", b"njexyomi", b"njcangjie", b"njcode",
          b"keisei", b"cangjie", b"pinyin", b"iWnn", b"bopomofo",
          b"dictionary", b"dict", b"hiragana", b"katakana", b"romaji",
          b"bffnt", b"bfarc", b"bfnt", b"kanji", b"converter", b"predict")


def utf16_strings(data, minlen=3, limit=400000):
    out = []
    cur = bytearray()
    i = 0
    n = len(data)
    while i + 1 < n:
        cp = data[i] | (data[i + 1] << 8)
        i += 2
        if 0x20 <= cp < 0x7F or 0x3000 <= cp <= 0x9FFF or 0xFF01 <= cp <= 0xFF60:
            cur += chr(cp).encode("utf-8")
        else:
            if len(cur) >= minlen:
                out.append(cur.decode("utf-8", "replace"))
                if len(out) >= limit:
                    return out
            cur = bytearray()
    if len(cur) >= minlen:
        out.append(cur.decode("utf-8", "replace"))
    return out


def decrypt_section(path, keys, sec=0):
    with open(path, "rb") as fh:
        raw = fh.read(HEADER_SIZE)
    hdr = xts_decrypt_fast(keys["header_key"], raw, endian="big")
    pid = struct.unpack_from("<Q", hdr, 0x210)[0]
    idx = max(hdr[0x206], hdr[0x220])
    if idx:
        idx -= 1
    kn = "key_area_key_%s_%02x" % (KAEK[hdr[0x207]], idx)
    if kn not in keys:
        return pid, None, kn
    datakey = ecb_dec(keys[kn], hdr[0x300:0x340])[0x20:0x30]
    h = hdr[0x400 + sec * 0x200:0x600 + sec * 0x200]
    s, e = struct.unpack_from("<II", hdr, 0x240 + sec * 0x10)
    if h[3] == 0:
        return pid, None, kn
    off = s * SECTOR
    length = min(e * SECTOR, os.path.getsize(path)) - off
    with open(path, "rb") as fh:
        fh.seek(off)
        data = fh.read(length)
    return pid, ctr_all(datakey, build_iv(h[0x140:0x148], off), data), kn


def main():
    keys = load_keys(KEYS)
    idx = json.load(open(INDEX))
    rows = [(v["program_id"], k, v) for k, v in idx.items()
            if v["content_type"] in ("Data", "PublicData") and v.get("program_id")]
    rows.sort()
    print("%-18s %10s  %s" % ("title_id", "size", "top utf-16 names / hits"))
    for pid, k, v in rows:
        path = os.path.join(FW, k)
        try:
            _pid, plain, kn = decrypt_section(path, keys)
        except Exception as exc:                                # noqa: BLE001
            print("%016X %10d  <%s>" % (pid, v["file_size"], exc))
            continue
        if plain is None:
            print("%016X %10d  <no data>" % (pid, v["file_size"]))
            continue
        names = utf16_strings(plain, 3, 40)
        hits = {kw.decode(): plain.count(kw) for kw in IME_KW
                if plain.count(kw)}
        print("%016X %10d  %s" % (pid, v["file_size"], ", ".join(names[:14])))
        if hits:
            print("      HITS: %s" % hits)
    return 0


if __name__ == "__main__":
    sys.exit(main())

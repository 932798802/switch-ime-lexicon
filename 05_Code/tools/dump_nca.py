#!/usr/bin/env python3
"""Fully decrypt an NCA's sections using hactool-verified parameters.

All parameters below are ports of hactool's nca.c (not guesses):

  key area : AES-ECB-Dec(key_area_key_<name>_<idx>, encrypted_keys[4][0x10])
             idx = max(header[0x206], header[0x220]) - 1
  data key : decrypted_key_area[2]                     (CRYPT_CTR)
  IV       : [ reverse(section_ctr[0:8]) | BE(offset>>4) ]
  offset   : media_start_offset * 0x200                (MEDIA_SIZE)
  cipher   : AES-128-CTR, big-endian counter

Note the section payload does NOT start with "PFS0"/"IVFC": hactool keeps the
FS superblock inside the FS header, so the payload begins with the IVFC level
table / hash data.

Usage:
    python dump_nca.py <nca_file> [outdir]
"""
import os
import struct
import sys
from collections import Counter as PyCounter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from index_fw import xts_decrypt_fast  # noqa: E402
from nca import HEADER_SIZE, SECTOR, load_keys  # noqa: E402
from Crypto.Cipher import AES  # noqa: E402
from Crypto.Util import Counter as AesCounter  # noqa: E402

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KEYS = os.path.join(HERE, "prod.keys")
KAEK = ("application", "ocean", "system")


def ecb_dec(k, d):
    return AES.new(k, AES.MODE_ECB).decrypt(d)


def ctr_all(key, iv, data):
    c = AesCounter.new(128, initial_value=int.from_bytes(iv, "big"),
                       allow_wraparound=True)
    return AES.new(key, AES.MODE_CTR, counter=c).decrypt(data)


def build_iv(section_ctr8, offset):
    ofs = offset >> 4
    ctr = bytearray(16)
    for j in range(8):
        ctr[j] = section_ctr8[8 - j - 1]
        ctr[0x10 - j - 1] = ofs & 0xFF
        ofs >>= 8
    return bytes(ctr)


def entropy(b):
    if not b:
        return 0.0
    n = len(b)
    return -sum((v / n) * __import__("math").log2(v / n)
                for v in PyCounter(b).values())


def strings(data, minlen=5, limit=80):
    out, cur = [], bytearray()
    for byte in data:
        if 32 <= byte < 127:
            cur.append(byte)
        else:
            if len(cur) >= minlen:
                out.append(cur.decode("ascii"))
            cur = bytearray()
    if len(cur) >= minlen:
        out.append(cur.decode("ascii"))
    return out[:limit]


def main():
    path = sys.argv[1]
    outdir = sys.argv[2] if len(sys.argv) > 2 else \
        os.path.join(HERE, "out", os.path.splitext(os.path.basename(path))[0])
    os.makedirs(outdir, exist_ok=True)
    keys = load_keys(KEYS)
    with open(path, "rb") as fh:
        raw = fh.read(HEADER_SIZE)
    hdr = xts_decrypt_fast(keys["header_key"], raw, endian="big")
    pid = struct.unpack_from("<Q", hdr, 0x210)[0]

    ct_field, ct2, kaek = hdr[0x206], hdr[0x220], hdr[0x207]
    idx = max(ct_field, ct2)
    if idx:
        idx -= 1
    print("programId    : %016X" % pid)
    print("0x206=%d 0x220=0x%02X  kaek=%d -> key index 0x%02X" % (ct_field, ct2, kaek, idx))

    kn = "key_area_key_%s_%02x" % (KAEK[kaek], idx)
    if kn not in keys:
        print("MISSING %s" % kn)
        return 1
    dka = ecb_dec(keys[kn], hdr[0x300:0x340])
    datakey = dka[2 * 0x10:3 * 0x10]
    print("using        : %s" % kn)
    print("data key     : %s" % datakey.hex())

    size = os.path.getsize(path)
    for i in range(4):
        h = hdr[0x400 + i * 0x200:0x600 + i * 0x200]
        s, e = struct.unpack_from("<II", hdr, 0x240 + i * 0x10)
        if h[3] == 0:
            continue
        off = s * SECTOR
        length = min(e * SECTOR, size) - off
        iv = build_iv(h[0x140:0x148], off)
        with open(path, "rb") as fh:
            fh.seek(off)
            data = fh.read(length)
        plain = ctr_all(datakey, iv, data)
        out = os.path.join(outdir, "section%d.bin" % i)
        with open(out, "wb") as fh:
            fh.write(plain)
        print("\n=== section %d  fs_type=%d  off=0x%X  len=%d ===" % (
            i, h[3], off, length))
        print("   IV        : %s" % iv.hex())
        print("   entropy   : %.2f  (8.0 = random)" % entropy(plain[:0x10000]))
        print("   head hex  : %s" % plain[:0x40].hex(' '))
        print("   head ascii: %r" % plain[:0x40])
        found = strings(plain, 5, 40)
        if found:
            print("   strings   : %s" % found[:25])
        else:
            print("   strings   : (none - likely still encrypted or pure hash)")
        print("   saved     : %s" % out)
    return 0


if __name__ == "__main__":
    sys.exit(main())

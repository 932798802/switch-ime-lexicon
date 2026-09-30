#!/usr/bin/env python3
"""Correct NCA section decryption, ported from hactool's nca.c.

Two details that are easy to get wrong and that no amount of guessing
recovers:

1) CTR initial value is a SPLIT construction:
       ctr[0:8]  = section_ctr bytes REVERSED   (i.e. read little-endian)
       ctr[8:16] = big-endian(section_file_offset >> 4)
   hactool:
       uint64_t ofs = offset >> 4;
       for (j = 0; j < 8; j++) {
           ctr[j]          = section_ctr[0x8 - j - 1];
           ctr[0x10-j-1]   = ofs & 0xFF;
           ofs >>= 8;
       }

2) The key area key index is (key generation - 1):
       crypto_type = max(header.crypto_type, header.crypto_type2);
       if (crypto_type) crypto_type--;
   so an NCA whose 0x220 byte reads 0x16 uses key_area_key_application_15.

The CTR data key is always decrypted_keys[2] for CRYPT_CTR.

Usage:
    python decrypt2.py <nca_file> [--sections 0,1]
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from index_fw import xts_decrypt_fast  # noqa: E402
from nca import HEADER_SIZE, SECTOR, load_keys  # noqa: E402
from Crypto.Cipher import AES  # noqa: E402

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KEYS = os.path.join(HERE, "prod.keys")
KAEK = ("application", "ocean", "system")
CRYPT = {0: "NONE", 1: "NONE?", 2: "XTS", 3: "CTR", 4: "BKTR"}
FS = {1: "?", 2: "PFS0", 3: "ROMFS", 4: "BKTR"}


def ecb_dec(k, d):
    return AES.new(k, AES.MODE_ECB).decrypt(d)


def ctr_crypt(key, iv, data):
    c = int.from_bytes(iv, "big")
    e = AES.new(key, AES.MODE_ECB)
    out = bytearray()
    for i in range(0, len(data), 16):
        ks = e.encrypt(c.to_bytes(16, "big"))
        out += bytes(x ^ y for x, y in zip(data[i:i + 16], ks))
        c = (c + 1) & ((1 << 128) - 1)
    return bytes(out)


def build_iv(section_ctr8, offset):
    """hactool's split CTR initial value."""
    ofs = offset >> 4
    ctr = bytearray(16)
    for j in range(8):
        ctr[j] = section_ctr8[8 - j - 1]
        ctr[0x10 - j - 1] = ofs & 0xFF
        ofs >>= 8
    return bytes(ctr)


def load(path):
    keys = load_keys(KEYS)
    with open(path, "rb") as fh:
        raw = fh.read(HEADER_SIZE)
    hdr = xts_decrypt_fast(keys["header_key"], raw, endian="big")
    return keys, hdr


def run(path, sections=(0, 1)):
    keys, hdr = load(path)
    if hdr[0x200:0x204] != b"NCA3":
        print("not NCA3"); return
    ct_field, ct_field2 = hdr[0x206], hdr[0x220]
    kaek = hdr[0x207]
    ctype = max(ct_field, ct_field2)
    if ctype:
        ctype -= 1
    print("programId    : %016X" % struct.unpack_from("<Q", hdr, 0x210)[0])
    print("0x206=%d  0x220=0x%02X  0x207(kaek)=%d" % (ct_field, ct_field2, kaek))
    print("key gen idx  : max(%d,0x%02X)-1 = 0x%02X" % (ct_field, ct_field2, ctype))

    keyname = "key_area_key_%s_%02x" % (KAEK[kaek], ctype)
    if keyname not in keys:
        print("MISSING KEY: %s" % keyname)
        alts = sorted(k for k in keys if k.startswith("key_area_key_%s_" % KAEK[kaek]))
        print("available:", alts[-4:])
        return
    kak = keys[keyname]
    print("using        : %s" % keyname)
    dka = ecb_dec(kak, hdr[0x300:0x340])
    datakey = dka[2 * 0x10:3 * 0x10]          # hactool: decrypted_keys[2]
    print("data key     : %s" % datakey.hex())

    for i in sections:
        h = hdr[0x400 + i * 0x200:0x600 + i * 0x200]
        s, e = struct.unpack_from("<II", hdr, 0x240 + i * 0x10)
        if h[3] == 0:
            print("\n[%d] empty section" % i); continue
        off = s * SECTOR
        sec_ctr = h[0x140:0x148]
        iv = build_iv(sec_ctr, off)
        print("\n[%d] fs_type=%d(%s) crypt=%d(%s)  entry=(%d..%d) off=0x%X" % (
            i, h[3], FS.get(h[3], "?"), h[4], CRYPT.get(h[4], "?"), s, e, off))
        print("     section_ctr = %s   IV = %s" % (sec_ctr.hex(), iv.hex()))
        with open(path, "rb") as fh:
            fh.seek(off)
            data = fh.read(min((e - s) * SECTOR, 0x100))
        plain = ctr_crypt(datakey, iv, data)
        print("     plain[0:0x40] = %s" % plain[:0x40].hex(' '))
        print("     ascii        = %r" % plain[:0x20])
    return


def main():
    if len(sys.argv) < 2:
        print(__doc__); return 1
    secs = (0, 1)
    if "--sections" in sys.argv:
        secs = tuple(int(x) for x in sys.argv[sys.argv.index("--sections") + 1].split(","))
    run(sys.argv[1], secs)
    return 0


if __name__ == "__main__":
    sys.exit(main())

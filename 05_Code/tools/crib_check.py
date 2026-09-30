#!/usr/bin/env python3
"""Verify the section data key WITHOUT knowing the CTR initial value.

Insight: for a ROMFS section, the first bytes of the encrypted section data
must decrypt to the very same IVFC header we already read in cleartext from
the FS header inside the 0xC00 header block. That gives a known-plaintext crib.

With crib plaintext P and ciphertext C, the keystream is KS = C xor P, and for
AES-CTR:
        KS[0:16]  = AES_enc(datakey, IV)
        KS[16:32] = AES_enc(datakey, IV+1)
so
        AES_dec(datakey, KS[0:16]) + 1 == AES_dec(datakey, KS[16:32])

The IV never needs to be known. If a data-key candidate satisfies that
relation, the candidate is correct - that is a 2^-128 coincidence otherwise.

Usage:
    python crib_check.py <nca_file> [--section 1] [--crib-off 0x8]
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
KAEK_NAMES = ("application", "ocean", "system")


def ecb_dec(key, data):
    return AES.new(key, AES.MODE_ECB).decrypt(data)


def xor(a, b):
    return bytes(x ^ y for x, y in zip(a, b))


def analyse(path, keys_path=KEYS, section=1, crib_off=0x8, crib_len=0x20):
    keys = load_keys(keys_path)
    with open(path, "rb") as fh:
        raw = fh.read(HEADER_SIZE)
    hdr = xts_decrypt_fast(keys["header_key"], raw, endian="big")
    if hdr[0x200:0x204] != b"NCA3":
        print("not NCA3, bailing")
        return

    kg = hdr[0x220]
    kaek_index = hdr[0x207]
    pid = struct.unpack_from("<Q", hdr, 0x210)[0]
    print("programId=%016X  kg=0x%02X  kaek=%d" % (pid, kg, kaek_index))

    h = hdr[0x400 + section * 0x200:0x600 + section * 0x200]
    s, e = struct.unpack_from("<II", hdr, 0x240 + section * 0x10)
    sec_off = s * SECTOR
    print("section %d: fs_type=%d crypt=%d  blocks %d..%d  -> offset 0x%X" % (
        section, h[3], h[4], s, e, sec_off))
    if h[3] != 3:
        print("  (warning: section %d is not ROMFS; crib may not apply)" % section)

    crib = h[crib_off:crib_off + crib_len]
    print("crib plaintext :", crib.hex(' '))
    with open(path, "rb") as fh:
        fh.seek(sec_off)
        ct = fh.read(crib_len)
    print("section cipher :", ct.hex(' '))
    ks = xor(ct, crib)
    print("keystream      :", ks.hex(' '))

    # Try every key_area_key variant we have for this generation: the section
    # key must come from the decrypted key area, so a wrong KAEK shows up here.
    print("\n--- testing data-key candidates ---")
    any_ok = False
    for name in KAEK_NAMES:
        kn = "key_area_key_%s_%02x" % (name, kg)
        if kn not in keys:
            print("  %-28s MISSING" % kn)
            continue
        dka = ecb_dec(keys[kn], hdr[0x300:0x340])
        for slot in range(4):
            dk = dka[slot * 0x10:(slot + 1) * 0x10]
            if dk == b"\x00" * 16:
                continue
            a = ecb_dec(dk, ks[0:16])
            b = ecb_dec(dk, ks[16:32])
            ai, bi = int.from_bytes(a, "big"), int.from_bytes(b, "big")
            for order, d in (("BE", bi - ai), ("LE", 
                              int.from_bytes(b, "little") - int.from_bytes(a, "little"))):
                if d == 1:
                    any_ok = True
                    print("  *** MATCH  %s slot %d  order=%s" % (kn, slot, order))
                    print("      IV =", a.hex())
                    print("      data key =", dk.hex())
                elif d == -1:
                    print("  *** MATCH(-1) %s slot %d order=%s  IV=%s" % (
                        kn, slot, order, b.hex()))
                    any_ok = True
            # also report how close, so we can see something is happening
            print("  %-34s slot %d  D(ks0)=%s  D(ks1)=%s  delta=%d" % (
                kn, slot, a.hex()[:16], b.hex()[:16], bi - ai))

    if not any_ok:
        print("\nNO candidate satisfied the CTR chain relation.")
        print("=> either the crib is wrong (section data does not start with the")
        print("   IVFC header) or the data key itself is wrong.")
    return any_ok


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    a = sys.argv
    sec = int(a[a.index("--section") + 1]) if "--section" in a else 1
    co = int(a[a.index("--crib-off") + 1], 0) if "--crib-off" in a else 0x8
    analyse(a[1], section=sec, crib_off=co)
    return 0


if __name__ == "__main__":
    sys.exit(main())

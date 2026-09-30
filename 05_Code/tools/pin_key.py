#!/usr/bin/env python3
"""Pin down the exact key_area_key index by brute force.

Structure, IV construction and cipher mode are now taken verbatim from
hactool:

    IV = reverse(section_ctr[0:8]) || big_endian(section_file_offset >> 4)
    data key = decrypted_key_area[2]      (CRYPT_CTR)
    key area = AES-ECB-Dec(key_area_key_<name>_<idx>, encrypted_keys)

The only remaining unknown is <idx>. hactool computes it as
max(0x206, 0x220) - 1, but that is cheap to verify exhaustively instead of
trusting it. A correct index must make the ExeFS section start with "PFS0".

Usage:
    python pin_key.py <nca_file>
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
    ofs = offset >> 4
    ctr = bytearray(16)
    for j in range(8):
        ctr[j] = section_ctr8[8 - j - 1]
        ctr[0x10 - j - 1] = ofs & 0xFF
        ofs >>= 8
    return bytes(ctr)


def main():
    path = sys.argv[1]
    keys = load_keys(KEYS)
    with open(path, "rb") as fh:
        raw = fh.read(HEADER_SIZE)
    hdr = xts_decrypt_fast(keys["header_key"], raw, endian="big")
    print("programId=%016X  0x206(crypto_type)=%d  0x220(crypto_type2)=0x%02X  kaek=%d"
          % (struct.unpack_from("<Q", hdr, 0x210)[0], hdr[0x206], hdr[0x220], hdr[0x207]))

    # targets: what the plaintext of each section must start with
    targets = {}
    for i in range(4):
        h = hdr[0x400 + i * 0x200:0x600 + i * 0x200]
        s, e = struct.unpack_from("<II", hdr, 0x240 + i * 0x10)
        if h[3] == 0:
            continue
        with open(path, "rb") as fh:
            fh.seek(s * SECTOR)
            ct = fh.read(0x20)
        targets[i] = {
            "h": h, "s": s, "e": e, "off": s * SECTOR, "ct": ct,
            "fs_type": h[3], "crypt": h[4],
            "fs_pref": h[:8],          # if data区 starts with a copy of the FS header
        }

    print("\n=== sweeping key_area_key index 0x00..0x1F x kaek x key-slot ===")
    hits = []
    for ki in range(0x20):
        for kk in range(3):
            kn = "key_area_key_%s_%02x" % (KAEK[kk], ki)
            if kn not in keys:
                continue
            dka = ecb_dec(keys[kn], hdr[0x300:0x340])
            for slot in range(4):
                dk = dka[slot * 0x10:(slot + 1) * 0x10]
                if dk == b"\x00" * 16:
                    continue
                for i, t in targets.items():
                    iv = build_iv(t["h"][0x140:0x148], t["off"])
                    plain = ctr_crypt(dk, iv, t["ct"])
                    tag = None
                    if plain[:4] == b"PFS0":
                        tag = "PFS0"
                    elif plain[:4] == b"IVFC":
                        tag = "IVFC"
                    elif plain[:8] == t["fs_pref"]:
                        tag = "FShdr-copy"
                    elif plain[:4] == b"HFS0":
                        tag = "HFS0"
                    if tag:
                        hits.append((ki, kk, slot, i, tag, plain.hex()))
    if hits:
        for h in hits:
            print("  *** HIT idx=0x%02X kaek=%s slot=%d sec=%d tag=%s\n      %s" % (
                h[0], KAEK[h[1]], h[2], h[3], h[4], h[5]))
    else:
        print("  no hit across 0x00..0x1F x 3 kaek x 4 slots")

    # Show what the hactool-computed index produces, for the record.
    ct_field, ct2 = hdr[0x206], hdr[0x220]
    idx = max(ct_field, ct2)
    if idx:
        idx -= 1
    print("\nhactool-computed index for reference: 0x%02X (kaek=%s)" % (idx, KAEK[hdr[0x207]]))
    kn = "key_area_key_%s_%02X" % (KAEK[hdr[0x207]], idx)
    if kn.lower() not in {k.lower() for k in keys}:
        print("  but that key is NOT present in the keyset")
    return 0


if __name__ == "__main__":
    sys.exit(main())

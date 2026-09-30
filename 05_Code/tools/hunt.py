#!/usr/bin/env python3
"""Exhaustive hunt for the correct NCA section decryption parameters.

Rather than guessing one combination at a time, enumerate everything that is
genuinely ambiguous and test a known-plaintext oracle:

    ExeFS section data must begin with "PFS0"
    RomFS section data must begin with "IVFC" (or a hash table)

Enumerated:
  * data-key derivation : ECB-DEC / ECB-ENC over each key_area_key name and
                          every slot, plus raw key-area slots
  * cipher              : AES-CTR / AES-ECB / AES-XTS
  * CTR initial value   : ~14 candidates, both IV placements, both endianness

Usage:
    python hunt.py <nca_file> [--section 0|1]
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from index_fw import xts_decrypt_fast  # noqa: E402
from nca import HEADER_SIZE, SECTOR, load_keys, _gf_mul_x  # noqa: E402
from Crypto.Cipher import AES  # noqa: E402

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KEYS = os.path.join(HERE, "prod.keys")
MAGICS = (b"PFS0", b"IVFC", b"HFS0", b"ROM0", b"NCA3", b"BKTR", b"FSH0")
KAEK = ("application", "ocean", "system")


def dec(k, d):
    return AES.new(k, AES.MODE_ECB).decrypt(d)


def enc(k, d):
    return AES.new(k, AES.MODE_ECB).encrypt(d)


def ctr(key, iv, data):
    c = int.from_bytes(iv, "big")
    e = AES.new(key, AES.MODE_ECB)
    out = bytearray()
    for i in range(0, len(data), 16):
        ks = e.encrypt(c.to_bytes(16, "big"))
        out += bytes(x ^ y for x, y in zip(data[i:i + 16], ks))
        c = (c + 1) & ((1 << 128) - 1)
    return bytes(out)


def ctr_le(key, iv, data):
    """Counter increments in little-endian order (non-standard)."""
    c = int.from_bytes(iv, "little")
    e = AES.new(key, AES.MODE_ECB)
    out = bytearray()
    for i in range(0, len(data), 16):
        ks = e.encrypt(c.to_bytes(16, "little"))
        out += bytes(x ^ y for x, y in zip(data[i:i + 16], ks))
        c = (c + 1) & ((1 << 128) - 1)
    return bytes(out)


def xts(key32, data, sector=0, endian="big"):
    e1 = AES.new(key32[:16], AES.MODE_ECB)
    e2 = AES.new(key32[16:], AES.MODE_ECB)
    out = bytearray()
    for s in range(len(data) // SECTOR):
        t = e2.encrypt((sector + s).to_bytes(16, endian))
        sec = data[s * SECTOR:(s + 1) * SECTOR]
        for b in range(SECTOR // 16):
            d = e1.decrypt(bytes(x ^ y for x, y in zip(sec[b * 16:(b + 1) * 16], t)))
            out += bytes(x ^ y for x, y in zip(d, t))
            t = _gf_mul_x(t)
    return bytes(out)


def main():
    path = sys.argv[1]
    keys = load_keys(KEYS)
    with open(path, "rb") as fh:
        raw = fh.read(HEADER_SIZE)
    hdr = xts_decrypt_fast(keys["header_key"], raw, endian="big")
    kg = hdr[0x220]
    kaek_index = hdr[0x207]

    print("kg=0x%02X  kaek_index=%d" % (kg, kaek_index))
    print("key area raw:", hdr[0x300:0x340].hex())

    # ---- build data key candidates
    dks = {}
    for name in KAEK:
        kn = "key_area_key_%s_%02x" % (name, kg)
        if kn not in keys:
            continue
        for slot in range(4):
            ct = hdr[0x300 + slot * 0x10:0x310 + slot * 0x10]
            dks["%s.s%d.DEC" % (name, slot)] = dec(keys[kn], ct)
            dks["%s.s%d.ENC" % (name, slot)] = enc(keys[kn], ct)
    # also raw slots
    for slot in range(4):
        dks["raw.s%d" % slot] = hdr[0x300 + slot * 0x10:0x310 + slot * 0x10]

    print("\ndata-key candidates: %d" % len(dks))

    # ---- per-section run
    for sec in (0, 1):
        h = hdr[0x400 + sec * 0x200:0x600 + sec * 0x200]
        s, e = struct.unpack_from("<II", hdr, 0x240 + sec * 0x10)
        if s == 0 and e == 0:
            continue
        off = s * SECTOR
        sec_ctr_8 = h[0x140:0x148]
        print("\n===== section %d  fs_type=%d crypt=%d  off=0x%X  len=0x%X" % (
            sec, h[3], h[4], off, (e - s) * SECTOR))
        print("   fs hdr 0x130-0x160:", h[0x130:0x160].hex(' '))
        with open(path, "rb") as fh:
            fh.seek(off)
            ct = fh.read(0x40)
        print("   cipher         :", ct.hex(' '))

        # IV candidates
        ivs = {
            "zero": b"\x00" * 16,
            "ctr||0": sec_ctr_8 + b"\x00" * 8,
            "0||ctr": b"\x00" * 8 + sec_ctr_8,
            "ctr_le||0": sec_ctr_8[::-1] + b"\x00" * 8,
            "off/16_be": (off // 16).to_bytes(16, "big"),
            "off/16_le": (off // 16).to_bytes(16, "little"),
            "block_be": s.to_bytes(16, "big"),
            "one": (1).to_bytes(16, "big"),
            "sec+1": (sec + 1).to_bytes(16, "big"),
        }
        found = []
        for dn, dk in dks.items():
            for ivn, iv in ivs.items():
                for scheme, plain in (("ctr", ctr(dk, iv, ct)),
                                      ("ctr_le", ctr_le(dk, iv, ct)),
                                      ("ecb", dec(dk, ct))):
                    for m in MAGICS:
                        if m in plain[:0x20]:
                            found.append((sec, dn, scheme, ivn, m,
                                          plain.find(m), off))
        # XTS with 32-byte keys built from the key area
        for dn, dk in dks.items():
            for k32name, k32 in (("dk*2", dk * 2), ("dk+0", dk + b"\x00" * 16)):
                for secno_name, secno in {"0": 0, "off/0x200": s}.items():
                    try:
                        plain = xts(k32, ct, sector=secno)
                    except Exception:
                        continue
                    for m in MAGICS:
                        if m in plain[:0x20]:
                            found.append((sec, dn + "+" + k32name, "xts",
                                          secno_name, m, plain.find(m), off))

        if found:
            for f in found:
                print("   *** HIT %s" % (f,))
        else:
            print("   no hit")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Decisive probe: can we decrypt an NCA section, and if not, why?

Runs a controlled experiment. A file whose key generation IS covered by
prod.keys must decrypt cleanly - that proves the header/FS parsing is right
and isolates any remaining failure to missing keys.

It enumerates the ambiguous parts instead of guessing:
  * section media offset   (block*0x200 vs 0xC00 + block*0x200)
  * FS header location     (inside the 0xC00 header block, NCA3 style)
  * data-key slot          (crypt_type vs crypt_type-1)
  * CTR initial value      (fs-header section_ctr, zero, sector number)

Usage:
    python decrypt_probe.py <nca_file> [--keys prod.keys]
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from index_fw import xts_decrypt_fast  # noqa: E402
from nca import HEADER_SIZE, SECTOR, load_keys, ct_crypt_fast  # noqa: E402
from Crypto.Cipher import AES  # noqa: E402

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KEYS = os.path.join(HERE, "prod.keys")
MAGICS = (b"PFS0", b"IVFC", b"HFS0", b"ROM0", b"NCA3", b"BKTR")


def ecb_dec(key, data):
    return AES.new(key, AES.MODE_ECB).decrypt(data)


def ctr_crypt(key, iv, data):
    ctr = int.from_bytes(iv, "big")
    ecb = AES.new(key, AES.MODE_ECB)
    out = bytearray()
    for i in range(0, len(data), 16):
        ks = ecb.encrypt(ctr.to_bytes(16, "big"))
        out += bytes(x ^ y for x, y in zip(data[i:i + 16], ks))
        ctr = (ctr + 1) & ((1 << 128) - 1)
    return bytes(out)


def probe(path, keys_path=KEYS):
    keys = load_keys(keys_path)
    size = os.path.getsize(path)
    with open(path, "rb") as fh:
        raw = fh.read(HEADER_SIZE)
    hdr = xts_decrypt_fast(keys["header_key"], raw, endian="big")

    magic = hdr[0x200:0x204]
    ct_id = hdr[0x205]
    kaek_index = hdr[0x207]
    program_id = struct.unpack_from("<Q", hdr, 0x210)[0]
    kg_old, kg_new = hdr[0x206], hdr[0x220]
    kg = kg_new if magic == b"NCA3" else kg_old

    print("file       :", os.path.basename(path), "(%d B)" % size)
    print("magic      : %s   content_type=%d  programId=%016X" % (
        magic.decode(), ct_id, program_id))
    print("key gen    : 0x206=0x%02X  0x220=0x%02X  -> using 0x%02X" % (
        kg_old, kg_new, kg))
    print("kaek_index : %d" % kaek_index)

    kaek_names = ("application", "ocean", "system")
    kaek_name = "key_area_key_%s_%02x" % (kaek_names[kaek_index], kg)
    if kaek_name not in keys:
        print("\n!! MISSING KEY: %s" % kaek_name)
        have = sorted(k for k in keys if k.startswith("key_area_key_%s_" % kaek_names[kaek_index]))
        print("   available:", have[-4:] if have else "none")
        print("\n=> verdict: key generation 0x%02X is NOT covered by this keyset" % kg)
        return False
    kaek = keys[kaek_name]
    print("kaek       : %s  (present)" % kaek_name)

    dec_key_area = ecb_dec(kaek, hdr[0x300:0x340])
    print("\ndecrypted key area (4 slots):")
    for i in range(4):
        k = dec_key_area[i * 0x10:(i + 1) * 0x10]
        print("   slot %d: %s%s" % (i, k.hex(), "   <- ALL ZERO" if k == b"\x00" * 16 else ""))

    # FS headers live inside the decrypted header block for NCA3
    print("\n--- FS headers at 0x400 + i*0x200 ---")
    for i in range(4):
        h = hdr[0x400 + i * 0x200:0x600 + i * 0x200]
        s, e = struct.unpack_from("<II", hdr, 0x240 + i * 0x10)
        print("  [%d] part=%d fs_type=%d crypt=%d  entry=(%d..%d) raw=%s" % (
            i, h[2], h[3], h[4], s, e, h[:0x10].hex()))
        if h[3] == 2:
            print("      -> PFS0 (ExeFS)")
        elif h[3] == 3:
            print("      -> ROMFS")
        elif h[3] == 4:
            print("      -> BKTR")

    print("\n--- FS header[1] full dump (looking for section_ctr) ---")
    h1 = hdr[0x600:0x800]
    for o in range(0, 0x200, 16):
        row = h1[o:o + 16]
        nz = any(row)
        print("   %03X  %s  %s" % (o, row.hex(' '),
                                   ''.join(chr(c) if 32 <= c < 127 else '.' for c in row)))

    found = []
    for i in range(4):
        h = hdr[0x400 + i * 0x200:0x600 + i * 0x200]
        fs_type, crypt = h[3], h[4]
        if fs_type == 0:
            continue
        s, e = struct.unpack_from("<II", hdr, 0x240 + i * 0x10)
        sec_ctr = h[0x140:0x148]
        for off_name, off in (("block*0x200", s * SECTOR),
                              ("0xC00+block*0x200", HEADER_SIZE + s * SECTOR)):
            if off >= size:
                continue
            take = min(e * SECTOR, size) - off
            if take <= 0:
                continue
            with open(path, "rb") as fh:
                fh.seek(off)
                data = fh.read(take)
            for slot in (crypt, crypt - 1):
                if not 0 <= slot <= 3:
                    continue
                dk = dec_key_area[slot * 0x10:(slot + 1) * 0x10]
                if dk == b"\x00" * 16:
                    continue
                ivs = {
                    "ctr||0": sec_ctr + b"\x00" * 8,
                    "0||ctr": b"\x00" * 8 + sec_ctr,
                    "off/16": (off // 16).to_bytes(16, "big"),
                    "s*0x200/16": (s * SECTOR // 16).to_bytes(16, "big"),
                    "zero": b"\x00" * 16,
                }
                for iv_name, iv in ivs.items():
                    plain = ctr_crypt(dk, iv, data[:0x2000])
                    for m in MAGICS:
                        if m in plain[:0x1000]:
                            pos = plain.find(m)
                            found.append((i, off_name, slot, iv_name, m, pos, off))
                            print("\n*** HIT sec=%d off=%s slot=%d iv=%s magic=%s at +0x%X"
                                  % (i, off_name, slot, iv_name, m.decode(), pos))
                            break
    if not found:
        print("\nno PFS0/IVFC magic recovered from any section combination")
        print("=> header parsed OK but section data not decryptable")
    return bool(found)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    kp = KEYS
    if "--keys" in sys.argv:
        kp = sys.argv[sys.argv.index("--keys") + 1]
    probe(args[0], kp)
    return 0


if __name__ == "__main__":
    sys.exit(main())

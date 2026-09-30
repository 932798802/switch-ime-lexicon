#!/usr/bin/env python3
"""Exhaustive attempt: can any (keygen, kaek, keyslot, IV variant) decrypt the
NCA section data of the given system title NCA?"""
import os
import struct
import sys

from Crypto.Cipher import AES

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from nca import Nca, key_area_key, load_keys  # noqa: E402

SCAN = 0x8000
TAGS = (b"PFS0", b"IVFC", b"FSH0", b"ROM0")


def iv_variants(sec_start):
    units = sec_start // 16
    return {
        "be_low":  units.to_bytes(16, "big"),                 # counter in low bytes, BE
        "be_high": units.to_bytes(16, "big")[0:8] + bytes(8),  # counter in high bytes
        "le_low":  units.to_bytes(16, "little"),
        "zero":    bytes(16),
        "abs_off": sec_start.to_bytes(16, "big"),
    }


def ctr(key, iv, data):
    return AES.new(key, AES.MODE_CTR, nonce=iv[:8],
                   initial_value=int.from_bytes(iv[8:], "big")).decrypt(data)


def run(d, prefix, keys_path):
    keys = load_keys(keys_path)
    name = [f for f in os.listdir(d) if f.startswith(prefix)][0]
    n = Nca(os.path.join(d, name), keys)
    h = n.hdr
    print("NCA %s | title %016X | kg=0x%02X kaek=%d" % (name, n.program_id, n.key_generation, n.kaek_index))

    secs = []
    for i in range(4):
        b, e = struct.unpack_from("<II", h, 0x240 + i * 0x10)
        secs.append((b * 0x200, e * 0x200))
    fh = open(n.path, "rb")

    def read(off, ln):
        fh.seek(off)
        return fh.read(ln)

    # plaintext first
    for si, (a, b) in enumerate(secs):
        if b <= a:
            continue
        pt = read(a, min(b - a, SCAN))
        for t in TAGS:
            if t in pt:
                print("  PLAINTEXT hit section %d %s" % (si, t))

    gens = sorted(int(k.rsplit("_", 1)[1], 16) for k in keys
                  if k.startswith("master_key_") and k.rsplit("_", 1)[1] != "source")
    hits = []
    tried = 0
    for gen in gens:
        for kaek in (0, 1, 2):
            try:
                kak = key_area_key(keys, kaek, gen)
            except KeyError:
                continue
            dk = AES.new(kak, AES.MODE_ECB).decrypt(n.enc_key_area)
            for slot in range(4):
                k = dk[slot * 16:slot * 16 + 16]
                if k == bytes(16):
                    continue
                for si, (a, b) in enumerate(secs):
                    if b <= a:
                        continue
                    data = read(a, min(b - a, SCAN))
                    for iname, iv in iv_variants(a).items():
                        tried += 1
                        pt = ctr(k, iv, data)
                        for t in TAGS:
                            if t in pt:
                                hits.append((gen, kaek, slot, si, iname, t.decode()))
    print("  tried %d combinations" % tried)
    for x in hits:
        print("  HIT gen=0x%02X kaek=%d slot=%d sec=%d iv=%s %s" % x)
    if not hits:
        print("  -> no combination works; section data is not decryptable with this keyset")
    return hits


if __name__ == "__main__":
    run(sys.argv[1], sys.argv[2], sys.argv[3])

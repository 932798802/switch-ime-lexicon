#!/usr/bin/env python3
"""Locate and decrypt the ExeFS / RomFS sections of a system NCA.

Brute-forces the key-area generation index because firmware NCA headers often
advertise a key_generation newer than the keyset you hold.
"""
import os
import struct
import sys

from Crypto.Cipher import AES

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from nca import Nca, ct_crypt_fast, key_area_key, load_keys  # noqa: E402

FILE_DIR = "F:/NSbackup/原文件/AMS-22.5.0"
KEYS = "F:/NSSW/prod.keys"


def main(nca_prefix):
    keys = load_keys(KEYS)
    name = [f for f in os.listdir(FILE_DIR) if f.startswith(nca_prefix)][0]
    n = Nca(os.path.join(FILE_DIR, name), keys)
    h = n.hdr
    print("NCA:", name, "| title %016X" % n.program_id, "|", n.content_type,
          "| kg=0x%02X kaek=%d kgold=%d" % (n.key_generation, n.kaek_index, n.key_gen_old), "| size", n.size)

    secs = []
    for i in range(4):
        b, e = struct.unpack_from("<II", h, 0x240 + i * 0x10)
        secs.append((b * 0x200, e * 0x200))
    print("sections (unbiased byte offsets):", secs)

    print("fs headers:")
    for i in range(4):
        o = 0x400 + i * 0x200
        print("  [%d] %s  ver=%d b1=%d b2=%d b3=%d mhash=%d"
              % (i, h[o:o + 0xC].hex(), h[o], h[o + 1], h[o + 2], h[o + 3], h[o + 4]))

    gens = sorted(int(k.rsplit("_", 1)[1], 16) for k in keys
                  if k.startswith("master_key_") and k.rsplit("_", 1)[1] != "source")
    print("keyset master_key gens:", ["%02x" % g for g in gens])
    print("NCA wants master_key_%02x" % n.key_generation)

    fh = open(n.path, "rb")

    def read(off, ln):
        fh.seek(off)
        return fh.read(ln)

    hits = []
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
                    data = read(a, min(b - a, 0x200000))
                    pt = ct_crypt_fast(k, a, data)
                    for tag in (b"PFS0", b"IVFC"):
                        j = pt.find(tag)
                        if j >= 0:
                            hits.append((gen, kaek, slot, si, tag.decode(), j))
    print()
    for gen, kaek, slot, si, tag, j in hits:
        print("HIT gen=0x%02X kaek=%d keyslot=%d section=%d  %s at +0x%X"
              % (gen, kaek, slot, si, tag, j))
    if not hits:
        print("no hit - section data could not be decrypted with the available keys")
    return hits


if __name__ == "__main__":
    if len(sys.argv) > 2:
        FILE_DIR = sys.argv[2]
        globals()["FILE_DIR"] = FILE_DIR
    main(sys.argv[1] if len(sys.argv) > 1 else "c65a992ef0d3")

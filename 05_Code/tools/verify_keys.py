#!/usr/bin/env python3
"""Self-consistency audit of prod.keys - no NCA needed.

If the keyset is internally consistent, every derivable key must reproduce
from its documented parents. This isolates "bad keyset" from "bad parsing"
before we blame the NCA code.

Nintendo derives DOWNWARD, i.e. the "*_source" constant is used as the
CIPHERTEXT:
    master_key_N   = AES-ECB-DEC(master_kek_N, master_key_source)
    titlekek_N     = AES-ECB-DEC(master_key_N, titlekek_source)
    key_area_key_X_N = AES-ECB-DEC(AES-ECB-DEC(master_key_N, aes_kek_generation_source),
                                   key_area_key_X_source)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from nca import load_keys  # noqa: E402
from Crypto.Cipher import AES  # noqa: E402

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KEYS = os.path.join(HERE, "prod.keys")


def dec(k, d):
    return AES.new(k, AES.MODE_ECB).decrypt(d)


def enc(k, d):
    return AES.new(k, AES.MODE_ECB).encrypt(d)


def main():
    keys = load_keys(sys.argv[1] if len(sys.argv) > 1 else KEYS)
    print("keyset entries:", len(keys))

    gens = []
    for i in range(0x20):
        if "master_key_%02x" % i in keys:
            gens.append(i)
    print("master_key generations:", ["0x%02X" % g for g in gens])
    print("highest generation present: 0x%02X" % max(gens))

    print("\n--- master_key_N == DEC(master_kek_N, master_key_source) ? ---")
    ok_all = True
    for g in gens:
        mk = keys.get("master_key_%02x" % g)
        kek = keys.get("master_kek_%02x" % g)
        src = keys["master_key_source"]
        if not mk or not kek:
            continue
        ap = dec(kek, src)
        good = ap == mk
        ok_all &= good
        if g >= 0x10 or not good:
            print("  gen 0x%02X: %s" % (g, "OK" if good else
                                       "MISMATCH expected=%s got=%s" % (mk.hex(), ap.hex())))
    print("  ->", "consistent" if ok_all else "INCONSISTENT")

    print("\n--- titlekek_N == DEC(master_key_N, titlekek_source) ? ---")
    ok_all = True
    for g in gens:
        if "titlekek_%02x" % g not in keys:
            continue
        ap = dec(keys["master_key_%02x" % g], keys["titlekek_source"])
        good = ap == keys["titlekek_%02x" % g]
        ok_all &= good
        if g >= 0x10 or not good:
            print("  gen 0x%02X: %s" % (g, "OK" if good else "MISMATCH"))
    print("  ->", "consistent" if ok_all else "INCONSISTENT")

    print("\n--- key_area_key_<x>_N derivation check ---")
    for name in ("application", "ocean", "system"):
        srcn = "key_area_key_%s_source" % name
        if srcn not in keys:
            print("  %s: source missing" % name)
            continue
        for g in gens:
            kn = "key_area_key_%s_%02x" % (name, g)
            if kn not in keys:
                continue
            k1 = dec(keys["master_key_%02x" % g], keys["aes_kek_generation_source"])
            if g == 0:
                ap = dec(k1, keys["aes_key_generation_source"])
            else:
                ap = dec(k1, keys[srcn])
            good = ap == keys[kn]
            if g >= 0x14 or not good:
                print("  %-34s gen 0x%02X: %s" % (kn, g, "OK" if good else
                      "MISMATCH  keyset=%s derived=%s" % (keys[kn].hex(), ap.hex())))
    print("\nNote: a MISMATCH here means the stored key disagrees with the")
    print("documented derivation - then the keyset, not the parser, is at fault.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

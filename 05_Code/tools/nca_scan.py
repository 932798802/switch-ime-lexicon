#!/usr/bin/env python3
"""NCA header scanner - find a system title NCA by program_id.

Only needs `header_key` from prod.keys (no key area / titlekey needed),
so it works without any Nintendo SDK or hactool.

Usage:
    python nca_scan.py <nca_dir> <prod.keys> [--find 0100000000001008]
"""
import os
import sys

from Crypto.Cipher import AES

NCA_HEADER_SIZE = 0xC00
ENC_OFFSET = 0x200  # header_key encrypted region starts here (AES-XTS, sector 0)
SECTOR = 0x200

CONTENT_TYPE = {
    0: "Program",
    1: "Meta",
    2: "Control",
    3: "Manual",
    4: "Data",
    5: "PublicData",
}
DIST_TYPE = {0: "Download", 1: "GameCard", 2: "GameCardCompat"}


def load_keys(path):
    keys = {}
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            try:
                keys[k.strip()] = bytes.fromhex(v.strip())
            except ValueError:
                pass
    return keys


def _gf_mul_x(b):
    """Multiply a 16-byte little-endian GF(2^128) element by x (XTS tweak step)."""
    carry = 0
    out = bytearray(16)
    for i in range(16):
        c = b[i]
        out[i] = ((c << 1) & 0xFF) | carry
        carry = (c >> 7) & 1
    if carry:
        out[0] ^= 0x87
    return bytes(out)


def xts_decrypt(key, data, sector_size=SECTOR, start_sector=0):
    """AES-128-XTS decrypt (pycryptodome ships without MODE_XTS, so do it by hand)."""
    k1, k2 = key[:16], key[16:]
    ecb_data = AES.new(k1, AES.MODE_ECB)
    ecb_tweak = AES.new(k2, AES.MODE_ECB)
    out = bytearray()
    for s in range(len(data) // sector_size):
        sector = data[s * sector_size:(s + 1) * sector_size]
        tweak = ecb_tweak.encrypt((start_sector + s).to_bytes(16, "little"))
        for b in range(sector_size // 16):
            blk = sector[b * 16:(b + 1) * 16]
            dec = ecb_data.decrypt(bytes(x ^ y for x, y in zip(blk, tweak)))
            out += bytes(x ^ y for x, y in zip(dec, tweak))
            tweak = _gf_mul_x(tweak)
    return bytes(out)


def decrypt_header(raw, header_key):
    """Return the decrypted header body (0xA00 bytes) or None."""
    if len(raw) < NCA_HEADER_SIZE:
        return None
    body = raw[ENC_OFFSET:NCA_HEADER_SIZE]
    # AES-128-XTS, sector index restarts at 0 for this region
    dec = xts_decrypt(header_key, body)
    if dec[:4] in (b"NCA3", b"NCA2", b"NCA0"):
        return dec
    return None


def parse_header(dec):
    import struct

    magic = dec[0:4].decode("ascii", "replace")
    version = struct.unpack_from("<I", dec, 0x04)[0]
    dist_type = dec[0x08]
    content_type = dec[0x09]
    crypto_type = dec[0x0A]
    kaek_index = dec[0x0B]
    size = struct.unpack_from("<Q", dec, 0x0C)[0]
    program_id = struct.unpack_from("<Q", dec, 0x14)[0]
    content_index = struct.unpack_from("<I", dec, 0x1C)[0]
    sdk_ver = struct.unpack_from("<I", dec, 0x20)[0]
    key_gen = dec[0x30]
    return {
        "magic": magic,
        "version": version,
        "dist": DIST_TYPE.get(dist_type, dist_type),
        "content_type": CONTENT_TYPE.get(content_type, content_type),
        "crypto_type": crypto_type,
        "kaek_index": kaek_index,
        "size": size,
        "program_id": program_id,
        "content_index": content_index,
        "sdk_ver": sdk_ver,
        "key_gen": key_gen,
    }


def main():
    d = sys.argv[1]
    keys_path = sys.argv[2]
    target = 0x0100000000001008
    if "--find" in sys.argv:
        target = int(sys.argv[sys.argv.index("--find") + 1], 16)

    keys = load_keys(keys_path)
    hk = keys.get("header_key")
    if hk is None or len(hk) != 32:
        print("ERROR: header_key missing or wrong size")
        return 1

    results = []
    files = sorted(f for f in os.listdir(d) if f.endswith(".nca"))
    fails = 0
    for name in files:
        p = os.path.join(d, name)
        try:
            with open(p, "rb") as fh:
                raw = fh.read(NCA_HEADER_SIZE)
        except OSError:
            fails += 1
            continue
        dec = decrypt_header(raw, hk)
        if dec is None:
            fails += 1
            continue
        info = parse_header(dec)
        info["file"] = name
        results.append(info)

    print("scanned %d NCA files, %d decrypted, %d skipped" % (len(files), len(results), fails))
    print()

    hit = [r for r in results if r["program_id"] == target]
    if hit:
        print("=== MATCH for %016X ===" % target)
        for h in hit:
            for k, v in h.items():
                if k == "program_id":
                    print("  %-14s 0x%016X" % (k, v))
                elif k == "size":
                    print("  %-14s %d (%.2f MB)" % (k, v, v / 1048576))
                else:
                    print("  %-14s %s" % (k, v))
        print()

    print("=== all system titles found (0100000000001008 = swkbd) ===")
    for r in sorted(results, key=lambda x: x["program_id"]):
        mark = "  <== swkbd" if r["program_id"] == 0x0100000000001008 else ""
        print(
            "%016X  %-13s idx=%-3d %9d B  %-6s kg=%s  %s%s"
            % (
                r["program_id"],
                r["content_type"],
                r["content_index"],
                r["size"],
                r["file"][:8],
                r["key_gen"],
                r["file"],
                mark,
            )
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())

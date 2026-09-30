#!/usr/bin/env python3
"""Index a LOCAL firmware package (all NCAs) and cross-check it against FTP.

The package `AMS-22.5.0/` is a flat dump of hash-named NCAs, exactly what
Daybreak/Awoo consume. Names carry no titleId, so we decrypt each NCA's
0xC00-byte header (header_key only) and read the identity out of it.

Usage:
    python index_fw.py <firmware_dir>
    python index_fw.py <firmware_dir> --verify-ftp    # byte-compare 3 NCAs
"""
import ftplib
import json
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from nca import HEADER_SIZE, SECTOR, _gf_mul_x, load_keys  # noqa: E402
from Crypto.Cipher import AES  # noqa: E402

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KEYS = os.path.join(HERE, "prod.keys")
INDEX = os.path.join(HERE, "fw_index.json")
FTP_HOST, FTP_PORT = "192.168.2.122", 5000
FTP_DIR = "/sdmc:/AMS-22.5.0"

CONTENT_TYPE = {0: "Program", 1: "Meta", 2: "Control", 3: "Manual",
                4: "Data", 5: "PublicData"}
# Enum values are from hactool ref/nca.h -- do NOT renumber:
#   section_fs_type_t   { FS_TYPE_PFS0 = 2, FS_TYPE_ROMFS = 3 }
#   section_crypt_type_t{ CRYPT_NONE = 1, CRYPT_XTS = 2, CRYPT_CTR = 3,
#                         CRYPT_BKTR = 4 }
# An earlier version of this file labelled 3 as "BKTR"; 3 is CTR. swkbd's
# sections really are plain CTR, which is why CTR decryption worked.
FS_TYPE = {2: "PFS0", 3: "ROMFS"}
CRYPT_TYPE = {1: "NONE", 2: "XTS", 3: "CTR", 4: "BKTR"}


def xts_decrypt_fast(key, data, endian="big", start_sector=0):
    """Batched AES-XTS. Identical result to nca.xts_decrypt, much faster.

    Two ECB passes per sector (all blocks at once) instead of per-block calls.
    """
    ecb_data = AES.new(key[:16], AES.MODE_ECB)
    ecb_tweak = AES.new(key[16:], AES.MODE_ECB)
    nsec = len(data) // SECTOR
    tweaks = bytearray()
    for s in range(nsec):
        t = ecb_tweak.encrypt((start_sector + s).to_bytes(16, endian))
        for _ in range(SECTOR // 16):
            tweaks += t
            t = _gf_mul_x(t)
    tmp = bytes(a ^ b for a, b in zip(data, tweaks))
    dec = ecb_data.decrypt(tmp)
    return bytes(a ^ b for a, b in zip(dec, tweaks))


def parse_header(raw, keys):
    hdr = xts_decrypt_fast(keys["header_key"], raw, endian="big")
    magic = hdr[0x200:0x204]
    if magic not in (b"NCA3", b"NCA2", b"NCA1", b"NCA0"):
        return None, hdr
    d = {
        "magic": magic.decode(),
        "distribution": hdr[0x204],
        "content_type": CONTENT_TYPE.get(hdr[0x205], hdr[0x205]),
        "ct_id": hdr[0x205],
        "kg_206": hdr[0x206],
        "kaek_index": hdr[0x207],
        "content_size": struct.unpack_from("<Q", hdr, 0x208)[0],
        "program_id": struct.unpack_from("<Q", hdr, 0x210)[0],
        "content_index": struct.unpack_from("<I", hdr, 0x218)[0],
        "sdk_addon": struct.unpack_from("<I", hdr, 0x21C)[0],
        "kg_220": hdr[0x220],
        "sections": [list(struct.unpack_from("<II", hdr, 0x240 + i * 0x10))
                     for i in range(4)],
    }
    # FS headers sit at 0x400 + i*0x200 inside the decrypted header block
    d["fs"] = []
    for i in range(4):
        h = hdr[0x400 + i * 0x200:0x600 + i * 0x200]
        d["fs"].append({
            "b0": h[0], "b1": h[1],
            "partition_type": h[2],
            "fs_type": FS_TYPE.get(h[3], h[3]),
            "crypt_type": CRYPT_TYPE.get(h[4], h[4]),
            "raw32": h[:0x20].hex(),
        })
    return d, hdr


def index(local_dir):
    keys = load_keys(KEYS)
    names = sorted(f for f in os.listdir(local_dir) if f.endswith(".nca"))
    out, fails = {}, []
    for i, name in enumerate(names, 1):
        p = os.path.join(local_dir, name)
        with open(p, "rb") as fh:
            raw = fh.read(HEADER_SIZE)
        try:
            d, _ = parse_header(raw, keys)
        except Exception as e:
            fails.append("%s: %s" % (name, e))
            continue
        if d is None:
            fails.append("%s: bad magic" % name)
            continue
        d["file"] = name
        d["file_size"] = os.path.getsize(p)
        out[name] = d
    with open(INDEX, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1)

    print("indexed %d/%d nca  (failed %d)" % (len(out), len(names), len(fails)))
    for x in fails[:10]:
        print("  FAIL", x)
    print("\nkey generation (0x206 / 0x220) distribution:")
    from collections import Counter
    c = Counter((d["kg_206"], d["kg_220"]) for d in out.values())
    for k, v in sorted(c.items()):
        print("   kg206=0x%02X kg220=0x%02X  x%d" % (k[0], k[1], v))
    print("\nkaek_index:", sorted({d["kaek_index"] for d in out.values()}))
    print("content types:", sorted({d["content_type"] for d in out.values()}))
    print("section fs types:", sorted({f["fs_type"] for d in out.values()
                                       for f in d["fs"] if f["fs_type"] != 0}))
    print("section crypt types:", sorted({f["crypt_type"] for d in out.values()
                                          for f in d["fs"] if f["crypt_type"] != 0}))

    print("\n=== programs by titleId (system applets first) ===")
    progs = [d for d in out.values() if d["ct_id"] == 0]
    for d in sorted(progs, key=lambda x: x["program_id"]):
        if d["program_id"] == 0x0100000000001008:
            mark = "  <== swkbd !!!"
        elif d["program_id"] & 0xFFFFFFFF00000000 == 0x0100000000000000 \
                and d["program_id"] < 0x0100000000002000:
            mark = "  <== system applet"
        else:
            mark = ""
        if mark:
            print("  %016X  idx=%d  %8d B  kg206=0x%02X kg220=0x%02X kaek=%d  %s%s" % (
                d["program_id"], d["content_index"], d["file_size"],
                d["kg_206"], d["kg_220"], d["kaek_index"], d["file"], mark))
    return out


def verify_ftp(out, n=3):
    """Byte-compare a few NCAs between local disk and the Switch over FTP."""
    f = ftplib.FTP()
    f.connect(FTP_HOST, FTP_PORT, timeout=25)
    f.login("", "")
    f.set_pasv(True)
    f.cwd(FTP_DIR)
    picks = sorted(out)[:n]
    ok = True
    for name in picks:
        local = os.path.join(os.path.dirname(INDEX), "fw2250", name)
        local2 = os.path.join(r"F:/NSbackup/20260927/AMS-22.5.0", name)
        with open(local2, "rb") as fh:
            lb = fh.read(HEADER_SIZE)
        buf = bytearray()
        conn = f.transfercmd("RETR " + name)
        while len(buf) < HEADER_SIZE:
            chunk = conn.recv(HEADER_SIZE - len(buf))
            if not chunk:
                break
            buf += chunk
        conn.close()
        f.voidresp()
        same = bytes(buf[:HEADER_SIZE]) == lb
        ok &= same
        print("  %s  local=%d ftp=%d  %s" % (name, len(lb), len(buf),
                                             "IDENTICAL" if same else "DIFFER!"))
    try:
        f.quit()
    except Exception:
        pass
    print("FTP cross-check:", "PASS - same source" if ok else "MISMATCH")
    return ok


def main():
    d = sys.argv[1] if len(sys.argv) > 1 else r"F:/NSbackup/20260927/AMS-22.5.0"
    out = index(d)
    if "--verify-ftp" in sys.argv:
        print("\n=== cross-check local vs FTP (first 3 NCAs) ===")
        verify_ftp(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Index a real-hardware firmware package over FTP without downloading it all.

An NCA's identity (titleId, content type, key generation, section layout)
lives entirely in its first 0xC00 bytes, and that block is decryptable with
just `header_key`. So we pull 3 KB per NCA instead of the whole package.

Usage:
    python ftp_fwhdr.py                     # index sdmc:/AMS-22.5.0
    python ftp_fwhdr.py <remote_dir>
    python ftp_fwhdr.py --show 0100000000001008
"""
import ftplib
import json
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from nca import HEADER_SIZE, xts_decrypt, load_keys  # noqa: E402

HOST, PORT, USER, PASS = "192.168.2.122", 5000, "", ""
FW_DIR = "sdmc:/AMS-22.5.0"
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(HERE, "cache")
KEYS = os.path.join(HERE, "prod.keys")
INDEX = os.path.join(HERE, "fw_index.json")

CONTENT_TYPE = {0: "Program", 1: "Meta", 2: "Control", 3: "Manual",
                4: "Data", 5: "PublicData"}


def connect():
    f = ftplib.FTP()
    f.connect(HOST, PORT, timeout=25)
    f.login(USER, PASS)
    f.set_pasv(True)
    return f


def read_partial(f, name, n, retries=3):
    """Read the first n bytes of a remote file, then drop the data socket.

    Faster than pulling 43 MB just to look at a header. If the server dislikes
    the early abort we retry with a full RETR capped by the callback.
    """
    for attempt in range(retries):
        try:
            conn = f.transfercmd("RETR " + name)
            buf = bytearray()
            while len(buf) < n:
                chunk = conn.recv(min(65536, n - len(buf)))
                if not chunk:
                    break
                buf += chunk
            conn.close()
            f.voidresp()
            if len(buf) >= n:
                return bytes(buf[:n])
        except Exception:
            try:
                conn.close()
            except Exception:
                pass
            try:
                f.close()
            except Exception:
                pass
            f = connect()
            try:
                f.cwd("/" + FW_DIR)
            except Exception:
                pass
    return None


def parse_header(raw, keys):
    hdr = xts_decrypt(keys["header_key"], raw, endian="big")
    magic = hdr[0x200:0x204]
    if magic not in (b"NCA3", b"NCA2", b"NCA1", b"NCA0"):
        return None
    d = {
        "magic": magic.decode(),
        "distribution": hdr[0x204],
        "content_type": CONTENT_TYPE.get(hdr[0x205], hdr[0x205]),
        "content_type_id": hdr[0x205],
        "kg_206": hdr[0x206],
        "kaek_index": hdr[0x207],
        "content_size": struct.unpack_from("<Q", hdr, 0x208)[0],
        "program_id": struct.unpack_from("<Q", hdr, 0x210)[0],
        "content_index": struct.unpack_from("<I", hdr, 0x218)[0],
        "sdk_addon": struct.unpack_from("<I", hdr, 0x21C)[0],
        "kg_220": hdr[0x220],
        "sections": [list(struct.unpack_from("<II", hdr, 0x240 + i * 0x10))
                     for i in range(4)],
        "fs_headers_hex": [hdr[0x400 + i * 0x200:0x400 + i * 0x200 + 0x20].hex()
                           for i in range(4)],
    }
    return d


def do_index(remote_dir):
    os.makedirs(CACHE, exist_ok=True)
    keys = load_keys(KEYS)
    f = connect()
    lines = []
    f.cwd(remote_dir)
    f.retrlines("LIST", lines.append)
    names = []
    for ln in lines:
        parts = ln.split(None, 8)
        if len(parts) >= 9 and parts[8].endswith(".nca"):
            names.append((parts[8], int(parts[4])))
    print("remote %s -> %d nca files" % (remote_dir, len(names)))

    out = {}
    fails = []
    for i, (name, size) in enumerate(sorted(names), 1):
        raw = read_partial(f, name, HEADER_SIZE)
        if raw is None:
            fails.append(name)
            continue
        with open(os.path.join(CACHE, name + ".hdr"), "wb") as fh:
            fh.write(raw)
        try:
            d = parse_header(raw, keys)
        except Exception as e:
            fails.append("%s (%s)" % (name, e))
            continue
        if d:
            d["file"] = name
            d["file_size"] = size
            out[name] = d
        else:
            fails.append("%s (bad magic)" % name)
        if i % 40 == 0:
            print("  %d/%d ..." % (i, len(names)))
    try:
        f.quit()
    except Exception:
        pass

    with open(INDEX, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1)

    print("\nparsed %d / %d, failed %d" % (len(out), len(names), len(fails)))
    for x in fails[:20]:
        print("   FAIL", x)

    kgs = sorted({(d["kg_206"], d["kg_220"]) for d in out.values()})
    print("key generation pairs (0x206, 0x220):", kgs)
    kaek = sorted({d["kaek_index"] for d in out.values()})
    print("kaek_index values:", kaek)
    ct = sorted({d["content_type_id"] for d in out.values()})
    print("content types:", ct)

    hit = [d for d in out.values() if d["program_id"] == 0x0100000000001008]
    print("\n=== swkbd (0100000000001008) ===")
    for d in hit:
        print("  file=%s size=%d idx=%d ct=%s kg206=0x%02X kg220=0x%02X kaek=%d" % (
            d["file"], d["file_size"], d["content_index"], d["content_type"],
            d["kg_206"], d["kg_220"], d["kaek_index"]))
        print("     content_size=%d sections=%s" % (d["content_size"], d["sections"]))
        for i, h in enumerate(d["fs_headers_hex"]):
            print("     fshdr[%d] = %s" % (i, h))
    return 0


def do_show(pid):
    with open(INDEX, encoding="utf-8") as fh:
        out = json.load(fh)
    want = int(pid, 16)
    for name, d in sorted(out.items(), key=lambda x: (x[1]["program_id"],
                                                      x[1]["content_index"])):
        if d["program_id"] != want:
            continue
        print("%s  idx=%d %-9s %9d B kg=(0x%02X,0x%02X) kaek=%d  %s" % (
            "0x%016X" % d["program_id"], d["content_index"], d["content_type"],
            d["file_size"], d["kg_206"], d["kg_220"], d["kaek_index"], d["file"]))
        print("   sections:", d["sections"])
        for i, h in enumerate(d["fs_headers_hex"]):
            print("   fshdr[%d] %s" % (i, h))
    return 0


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--show":
        return do_show(sys.argv[2])
    return do_index(sys.argv[1] if len(sys.argv) > 1 else FW_DIR)


if __name__ == "__main__":
    sys.exit(main())

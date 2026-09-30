#!/usr/bin/env python3
"""Identify every System Applet by reading its ExeFS `main.npdm` module name.

Authoritative: the NPDM header carries a fixed 0x50-byte module name at 0x24,
and `main.npdm` also embeds the program id inside its ACID/ACI0 section. This
is the only way to be sure which title id is swkbd -- title ids are not
self-describing.

Usage:
    python id_applets.py [--all]
"""
import json
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from index_fw import xts_decrypt_fast  # noqa: E402
from nca import HEADER_SIZE, SECTOR, load_keys  # noqa: E402
from dump_nca import KAEK, build_iv, ctr_all, ecb_dec  # noqa: E402

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KEYS = os.path.join(HERE, "prod.keys")
FW = r"F:/NSbackup/20260927/AMS-22.5.0"
INDEX = os.path.join(HERE, "fw_index.json")


def parse_pfs0(data, off=0):
    """PFS0 as used by firmware 22.x system applets:

        magic "PFS0"(4) | file_count(u32) | string_table_size(u32) | pad(u32)
        count x entry, 0x18 bytes, fields are u64:
            offset(u64) | size(u64) | string_table_offset(u64)
        string table (null-terminated names)
        file data (offsets are relative to the end of the string table)

    NOTE: this differs from the older hactool pfs0_file_entry_t (0x10 bytes of
    u32). Verified on 0100000000001010: entries land exactly on the string
    table ("main\\0main.npdm\\0") and main's data offset resolves to the NSO0
    magic at 0x160.
    """
    if data[off:off + 4] != b"PFS0":
        return None
    count, strsz = struct.unpack_from("<II", data, off + 4)
    p = off + 0x10
    ents = []
    for _ in range(count):
        o, sz, no = struct.unpack_from("<QQQ", data, p)
        p += 0x18
        ents.append((o, sz, no))
    strtab = data[p:p + strsz]
    p += strsz
    files = []
    for o, sz, no in ents:
        end = strtab.find(b"\0", no)
        name = strtab[no:end if end >= 0 else len(strtab)].decode(
            "utf-8", "replace")
        files.append((name, p + o, sz))
    return files


def npdm_name(blob):
    if blob[:4] != b"META":
        return None
    name = blob[0x24:0x24 + 0x50]
    return name.split(b"\0")[0].decode("utf-8", "replace")


def read_npdm_name(path, keys):
    with open(path, "rb") as fh:
        raw = fh.read(HEADER_SIZE)
    hdr = xts_decrypt_fast(keys["header_key"], raw, endian="big")
    pid = struct.unpack_from("<Q", hdr, 0x210)[0]
    idx = max(hdr[0x206], hdr[0x220])
    if idx:
        idx -= 1
    kn = "key_area_key_%s_%02x" % (KAEK[hdr[0x207]], idx)
    if kn not in keys:
        return pid, None
    datakey = ecb_dec(keys[kn], hdr[0x300:0x340])[0x20:0x30]
    size = os.path.getsize(path)
    for i in range(4):
        h = hdr[0x400 + i * 0x200:0x600 + i * 0x200]
        if h[3] != 2:                     # FS_TYPE_PFS0 only (ExeFS)
            continue
        s, e = struct.unpack_from("<II", hdr, 0x240 + i * 0x10)
        if s == 0 and e == 0:
            continue
        off = s * SECTOR
        length = min(e * SECTOR, size) - off
        with open(path, "rb") as fh:
            fh.seek(off)
            data = fh.read(length)
        plain = ctr_all(datakey, build_iv(h[0x140:0x148], off), data)
        # PFS0 is not necessarily at offset 0 -- locate it
        pos = plain.find(b"PFS0")
        if pos < 0:
            continue
        files = parse_pfs0(plain, pos)
        if not files:
            continue
        for name, o, sz in files:
            if name.endswith(".npdm"):
                blob = plain[o:o + sz]
                nm = npdm_name(blob) if blob[:4] == b"META" else None
                if nm is None:
                    q = plain.find(b"META", o, o + sz + 0x40)
                    if q >= 0:
                        nm = npdm_name(plain[q:q + 0x80])
                return pid, nm, [f[0] for f in files]
    return pid, None, []


def main():
    keys = load_keys(KEYS)
    idx = json.load(open(INDEX))
    want_all = "--all" in sys.argv
    rows = []
    for k, v in idx.items():
        pid = v.get("program_id")
        if pid is None or v["content_type"] != "Program":
            continue
        if not want_all and not (0x0100000000001000 <= pid <= 0x0100000000001FFF):
            continue
        rows.append((pid, k))
    rows.sort()
    print("%-18s %-22s %-34s %s" % ("title_id", "npdm name", "exefs files", "nca"))
    for pid, k in rows:
        path = os.path.join(FW, k)
        try:
            pid2, nm, fl = read_npdm_name(path, keys)
        except Exception as exc:            # noqa: BLE001
            nm, fl = "<%s: %s>" % (type(exc).__name__, exc), []
            pid2 = pid
        print("%016X %-22s %-34s %s" % (pid2, nm or "?", ",".join(fl), k))
    return 0


if __name__ == "__main__":
    sys.exit(main())

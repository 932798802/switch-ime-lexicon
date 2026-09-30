#!/usr/bin/env python3
"""NCA -> decrypted section -> IVFC -> RomFS listing / extraction.

Structures are taken verbatim from hactool's ref/ivfc.h:

    ivfc_hdr_t {                     /* size 0xE0 */
        u32 magic;                   /* "IVFC" */
        u32 id;
        u32 master_hash_size;
        u32 num_levels;
        ivfc_level_hdr_t level_headers[6];   /* @0x10, 0x18 each */
        u8  _0xA0[0x20];
        u8  master_hash[0x20];
    };
    ivfc_level_hdr_t { u64 logical_offset; u64 hash_data_size;
                       u32 block_size; u32 reserved; };

    romfs_hdr_t {                    /* size 0x50 */
        u64 header_size;             u64 dir_hash_table_offset;
        u64 dir_hash_table_size;     u64 dir_meta_table_offset;
        u64 dir_meta_table_size;     u64 file_hash_table_offset;
        u64 file_hash_table_size;    u64 file_meta_table_offset;
        u64 file_meta_table_size;    u64 data_offset;
    };

and ref/nca.c:nca_process_ivfc_section():

    romfs_offset = ivfc_header.level_headers[5].logical_offset;
    dir_meta  = section[romfs_offset + header.dir_meta_table_offset]
    file_meta = section[romfs_offset + header.file_meta_table_offset]
    file data = section[romfs_offset + header.data_offset + fentry.offset]

The IVFC header lives inside the NCA FS header at FS_header+0x08, so
level_headers[5] is at FS_header + 0x08 + 0x10 + 5*0x18 = FS_header + 0x90.

Usage:
    python nca_romfs.py <nca> [--section N] [--extract DIR] [--ivfc]
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from index_fw import xts_decrypt_fast  # noqa: E402
from nca import HEADER_SIZE, SECTOR, load_keys  # noqa: E402
from dump_nca import KAEK, build_iv, ctr_all, ecb_dec  # noqa: E402

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KEYS = os.path.join(HERE, "prod.keys")

FS_TYPE = {2: "PFS0", 3: "ROMFS"}
CRYPT_TYPE = {1: "NONE", 2: "XTS", 3: "CTR", 4: "BKTR"}


def load_section(nca_path, sec, keys):
    with open(nca_path, "rb") as fh:
        raw = fh.read(HEADER_SIZE)
    hdr = xts_decrypt_fast(keys["header_key"], raw, endian="big")
    pid = struct.unpack_from("<Q", hdr, 0x210)[0]
    idx = max(hdr[0x206], hdr[0x220])
    if idx:
        idx -= 1
    kn = "key_area_key_%s_%02x" % (KAEK[hdr[0x207]], idx)
    datakey = ecb_dec(keys[kn], hdr[0x300:0x340])[0x20:0x30]
    fsh = hdr[0x400 + sec * 0x200:0x600 + sec * 0x200]
    s, e = struct.unpack_from("<II", hdr, 0x240 + sec * 0x10)
    if fsh[3] == 0:
        return pid, kn, fsh, None
    off = s * SECTOR
    length = min(e * SECTOR, os.path.getsize(nca_path)) - off
    with open(nca_path, "rb") as fh:
        fh.seek(off)
        data = fh.read(length)
    plain = ctr_all(datakey, build_iv(fsh[0x140:0x148], off), data)
    return pid, kn, fsh, plain


def parse_ivfc(fsh):
    base = fsh[0x08:]
    if base[:4] != b"IVFC":
        return None
    mid, nlev = struct.unpack_from("<II", base, 0x04)
    levels = []
    for i in range(6):
        lo, hds, bs, rv = struct.unpack_from("<QQII", base, 0x10 + i * 0x18)
        levels.append(dict(logical_offset=lo, hash_data_size=hds,
                           block_size=1 << bs, reserved=rv))
    return dict(id=mid, num_levels=nlev, master_hash=base[0xC0:0xE0],
                levels=levels)


def parse_romfs(sec, romfs_off):
    hdr = struct.unpack_from("<10Q", sec, romfs_off)
    (hsz, dho, dhs, dmo, dms, fho, fhs, fmo, fms, dofs) = hdr
    if hsz != 0x50:
        return None, None

    dbase = romfs_off + dmo
    fbase = romfs_off + fmo

    def dirent(off):
        """off is relative to the directory meta table."""
        p = dbase + off
        if off + 0x18 > dms:
            return None
        par, sib, ch, fi, h, nsz = struct.unpack_from("<IIIIII", sec, p)
        if nsz > 0x300 or off + 0x18 + nsz > dms:
            return None
        name = sec[p + 0x18:p + 0x18 + nsz].decode("utf-8", "replace")
        return dict(off=off, parent=par, sibling=sib, child=ch, file=fi,
                    name=name)

    def fentry(off):
        p = fbase + off
        if off + 0x20 > fms:
            return None
        par, sib, fo, fsz, h, nsz = struct.unpack_from("<IIQQII", sec, p)
        if nsz > 0x300 or off + 0x20 + nsz > fms:
            return None
        name = sec[p + 0x20:p + 0x20 + nsz].decode("utf-8", "replace")
        return dict(off=off, parent=par, sibling=sib, data=fo, size=fsz,
                    name=name)

    listing = []
    guard = 0

    def walk(dir_off, prefix):
        nonlocal guard
        guard += 1
        if guard > 4096:
            return
        e = dirent(dir_off)
        if e is None:
            return
        # sub-directories: linked via child -> sibling
        ch = e["child"]
        while ch != 0xFFFFFFFF:
            c = dirent(ch)
            if c is None:
                break
            walk(ch, prefix + c["name"] + "/")
            ch = c["sibling"]
        # files in this directory
        fi = e["file"]
        while fi != 0xFFFFFFFF:
            f = fentry(fi)
            if f is None:
                break
            listing.append((prefix, f["data"], f["size"], f["name"]))
            fi = f["sibling"]

    walk(0, "")
    info = dict(header=romfs_off, dir_meta=dmo, dir_meta_size=dms,
                file_meta=fmo, file_meta_size=fms, data=dofs,
                dir_hash=dho, dir_hash_size=dhs,
                file_hash=fho, file_hash_size=fhs)
    return info, listing


def main():
    a = sys.argv[1:]
    nca = a[0]
    sec = 0
    extract = None
    show_ivfc = "--ivfc" in a
    for i, x in enumerate(a):
        if x == "--section":
            sec = int(a[i + 1])
        if x == "--extract":
            extract = a[i + 1]
    keys = load_keys(KEYS)
    pid, kn, fsh, plainn = load_section(nca, sec, keys)
    print("nca          : %s" % os.path.basename(nca))
    print("title_id     : %016X" % pid)
    print("key          : %s" % kn)
    print("fs header    : partition=%d fs_type=%s crypt=%s" % (
        fsh[2], FS_TYPE.get(fsh[3], fsh[3]),
        CRYPT_TYPE.get(fsh[4], fsh[4])))
    ivfc = parse_ivfc(fsh)
    if ivfc:
        print("ivfc         : id=0x%X num_levels=%d" % (ivfc["id"],
                                                        ivfc["num_levels"]))
        if show_ivfc:
            for i, lv in enumerate(ivfc["levels"]):
                print("   level %d  logical_offset=0x%-10X hash_data_size=%-10d"
                      " block_size=0x%X" % (i, lv["logical_offset"],
                                            lv["hash_data_size"],
                                            lv["block_size"]))
    if plainn is None:
        print("section %d empty" % sec)
        return 1
    print("section %d    : %d bytes decrypted" % (sec, len(plainn)))
    if not ivfc:
        return 1
    romfs_off = ivfc["levels"][5]["logical_offset"]
    print("romfs_offset : 0x%X" % romfs_off)
    info, listing = parse_romfs(plainn, romfs_off)
    if info is None:
        print("!! RomFS header not valid at 0x%X (first 8 bytes %s)" % (
            romfs_off, plainn[romfs_off:romfs_off + 8].hex(" ")))
        return 1
    print("romfs hdr    : dir_meta=0x%X(%d) file_meta=0x%X(%d) data=0x%X" % (
        info["dir_meta"], info["dir_meta_size"], info["file_meta"],
        info["file_meta_size"], info["data"]))
    print("files: %d" % len(listing))
    tot = 0
    for d, fo, fsz, nm in sorted(listing, key=lambda x: -x[2]):
        print("  %-56s %10d  @0x%X" % (d + nm, fsz,
                                       romfs_off + info["data"] + fo))
        tot += fsz
    print("  total %d bytes (%.2f MB)" % (tot, tot / 1048576))
    if extract:
        for d, fo, fsz, nm in listing:
            rel = (d + nm).lstrip("/")
            dst = os.path.join(extract, rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            base = romfs_off + info["data"] + fo
            with open(dst, "wb") as fh:
                fh.write(plainn[base:base + fsz])
        print(">> extracted to %s" % extract)
    return 0


if __name__ == "__main__":
    sys.exit(main())

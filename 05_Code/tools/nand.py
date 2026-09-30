#!/usr/bin/env python3
"""Minimal Nintendo Switch eMMC/NAND access layer - no hactool required.

A file-based emuMMC stores the raw NAND as a set of sequential chunk files
(`00`, `01`, ... plus BOOT0/BOOT1). Concatenated, they ARE the raw NAND image.
This module exposes that as a random-access block device, parses the GPT and
gives a tiny FAT32 reader so we can pull NCAs straight out of the SYSTEM
partition.

Usage:
    python nand.py info
    python nand.py ls SYSTEM /
    python nand.py ls SYSTEM /Contents/registered
    python nand.py get SYSTEM <path> <outfile>
    python nand.py find SYSTEM <substring>
    python nand.py cat SYSTEM <path> [nbytes]
"""
import os
import struct
import sys

NAND = r"F:/NSbackup/20260927/emuMMC/SD00/eMMC"
CHUNK = 4261412864          # 0xFE000000, size of chunk files 00..06
LBA = 0x200


# ------------------------------------------------------------------ block dev

class Nand:
    """Sequential chunk files presented as one flat block device."""

    def __init__(self, root=NAND):
        self.root = root
        chunks = []
        for n in range(8):
            p = os.path.join(root, n < 10 and "0%d" % n or "%d" % n)
            if n == 0:
                p = os.path.join(root, "00")
            if os.path.exists(p):
                chunks.append((p, os.path.getsize(p)))
        if not chunks:
            # fall back: any numeric file sorted
            for name in sorted(os.listdir(root)):
                if name.isdigit():
                    p = os.path.join(root, name)
                    chunks.append((p, os.path.getsize(p)))
        if not chunks:
            raise RuntimeError("no NAND chunk files in %s" % root)
        self.chunks = chunks
        self.size = sum(s for _, s in chunks)
        self._fds = {}
        # cumulative offsets
        self.offs = []
        acc = 0
        for _, s in chunks:
            self.offs.append(acc)
            acc += s

    def _fd(self, i):
        if i not in self._fds:
            self._fds[i] = open(self.chunks[i][0], "rb")
        return self._fds[i]

    def read(self, off, n):
        out = bytearray()
        if off >= self.size:
            return bytes(out)
        n = min(n, self.size - off)
        i = 0
        while i + 1 < len(self.chunks) and off >= self.offs[i + 1]:
            i += 1
        while len(out) < n and i < len(self.chunks):
            local = off - self.offs[i]
            avail = self.chunks[i][1] - local
            take = min(avail, n - len(out))
            fd = self._fd(i)
            fd.seek(local)
            out += fd.read(take)
            off += take
            i += 1
        return bytes(out)

    def __enter__(self):
        return self

    def __exit__(self, *a):
        for fd in self._fds.values():
            fd.close()


# ------------------------------------------------------------------ GPT

SWITCH_DATA_GUID = bytes.fromhex("e75ca6e7bc074fd1952d4e6e2ce12333")
SWITCH_TYPE_NAMES = {
    bytes.fromhex("e75ca6e7bc074fd1952d4e6e2ce12333"): "DATA",
}


def guid_le(b):
    """Format a mixed-endian GPT GUID."""
    d1, d2, d3 = struct.unpack("<IHH", b[:8])
    rest = b[8:]
    return "%08X-%04X-%04X-%s-%s" % (
        d1, d2, d3, rest[:2].hex().upper(), rest[2:].hex().upper())


class Partition:
    def __init__(self, name, type_guid, first_lba, last_lba):
        self.name = name
        self.type_guid = type_guid
        self.first_lba = first_lba
        self.last_lba = last_lba

    @property
    def offset(self):
        return self.first_lba * LBA

    @property
    def size(self):
        return (self.last_lba - self.first_lba + 1) * LBA

    def __repr__(self):
        return "<%s %d..%d %.1fMB>" % (self.name, self.first_lba, self.last_lba,
                                       self.size / 1e6)


def parse_gpt(nand):
    hdr = nand.read(LBA, 0x200)
    if hdr[:8] != b"EFI PART":
        raise RuntimeError("no GPT signature at LBA1: %r" % hdr[:8])
    ent_lba = struct.unpack_from("<Q", hdr, 0x48)[0]
    num = struct.unpack_from("<I", hdr, 0x50)[0]
    esz = struct.unpack_from("<I", hdr, 0x54)[0]
    if esz == 0 or esz > 0x1000:
        esz = 0x80
    raw = nand.read(ent_lba * LBA, num * esz)
    parts = []
    for i in range(num):
        e = raw[i * esz:(i + 1) * esz]
        if len(e) < 0x38:
            break
        if e[0x00:0x10] == b"\x00" * 16:
            continue
        first, last = struct.unpack_from("<QQ", e, 0x20)
        name = e[0x38:0x38 + 72].decode("utf-16-le", "replace").split("\x00")[0]
        parts.append(Partition(name, guid_le(e[0x00:0x10]), first, last))
    return parts


# ------------------------------------------------------------------ FAT32

class Fat32:
    """Read-only FAT32 reader good enough for the SYSTEM partition."""

    def __init__(self, nand, base, size):
        self.nand = nand
        self.base = base
        self.size = size
        bs = nand.read(base, 0x200)
        if bs[0x1FE:0x200] != b"\x55\xAA":
            raise RuntimeError("no FAT boot signature")
        self.bps = struct.unpack_from("<H", bs, 0x0B)[0]
        self.spc = bs[0x0D]
        self.reserved = struct.unpack_from("<H", bs, 0x0E)[0]
        self.nfats = bs[0x10]
        self.total_sectors = struct.unpack_from("<I", bs, 0x20)[0]
        self.fat_size = struct.unpack_from("<I", bs, 0x24)[0]
        self.root_cluster = struct.unpack_from("<I", bs, 0x2C)[0]
        if self.bps == 0:
            self.bps = 0x200
        self.cluster_bytes = self.bps * self.spc
        self.fat_off = base + self.reserved * self.bps
        self.data_off = base + (self.reserved + self.nfats * self.fat_size) * self.bps
        self.max_cluster = (self.total_sectors - self.reserved
                            - self.nfats * self.fat_size) // self.spc + 2
        self.label = bs[0x47:0x52].decode("ascii", "replace").strip()

    def _fat_entry(self, cluster):
        off = self.fat_off + cluster * 4
        v = struct.unpack("<I", self.nand.read(off, 4))[0] & 0x0FFFFFFF
        return v

    def _chain(self, cluster, limit=1 << 22):
        out = []
        while 2 <= cluster < 0x0FFFFFF8 and len(out) < limit:
            out.append(cluster)
            cluster = self._fat_entry(cluster)
        return out

    def cluster_off(self, cluster):
        return self.data_off + (cluster - 2) * self.cluster_bytes

    def read_cluster(self, cluster):
        return self.nand.read(self.cluster_off(cluster), self.cluster_bytes)

    def read_file(self, first_cluster, size):
        if size == 0:
            return b""
        data = bytearray()
        for c in self._chain(first_cluster):
            data += self.read_cluster(c)
            if len(data) >= size:
                break
        return bytes(data[:size])

    def listdir(self, path):
        """Return [(name, is_dir, size, first_cluster)] for a '/' path."""
        cluster = self.root_cluster
        parts = [p for p in path.split("/") if p]
        for part in parts:
            found = None
            for name, is_dir, size, fc in self._entries(cluster):
                if is_dir and name.lower() == part.lower():
                    found = fc
                    break
            if found is None:
                raise FileNotFoundError(path)
            cluster = found
        return self._entries(cluster)

    def _entries(self, cluster):
        out = []
        lfn = {}
        for c in self._chain(cluster):
            block = self.read_cluster(c)
            for i in range(0, len(block), 32):
                e = block[i:i + 32]
                if len(e) < 32 or e[0] == 0x00:
                    return out
                if e[0] == 0xE5:
                    lfn = {}
                    continue
                attr = e[0x0B]
                if attr == 0x0F:
                    seq = e[0] & 0x3F
                    chars = (e[1:11] + e[14:26] + e[28:32])
                    try:
                        lfn[seq] = chars.decode("utf-16-le", "replace")
                    except Exception:
                        pass
                    continue
                if attr & 0x08:
                    lfn = {}
                    continue
                if e[0] == 0x2E:      # '.' / '..'
                    lfn = {}
                    continue
                short = e[0:8].decode("ascii", "replace").strip()
                ext = e[8:11].decode("ascii", "replace").strip()
                if not lfn:
                    name = short + ("." + ext if ext else "")
                else:
                    name = "".join(lfn[k] for k in sorted(lfn)) 
                    name = name.split("\x00")[0].rstrip("\uffff")
                lfn = {}
                is_dir = bool(attr & 0x10)
                hi = struct.unpack_from("<H", e, 0x14)[0]
                lo = struct.unpack_from("<H", e, 0x1A)[0]
                fc = (hi << 16) | lo
                size = struct.unpack_from("<I", e, 0x1C)[0]
                out.append((name, is_dir, size, fc))
        return out


def find_partition(parts, name):
    for p in parts:
        if p.name.upper() == name.upper():
            return p
    for p in parts:
        if name.upper() in p.name.upper():
            return p
    raise KeyError(name)


def show_info():
    with Nand() as n:
        print("NAND chunks: %d, total %.2f GB" % (len(n.chunks), n.size / 1e9))
        for p, s in n.chunks:
            print("   %-60s %13d" % (p, s))
        print()
        parts = parse_gpt(n)
        print("GPT partitions: %d" % len(parts))
        print("%-28s %-14s %12s %12s %10s  %s" % (
            "name", "offset(bytes)", "first_lba", "last_lba", "size", "type"))
        for p in sorted(parts, key=lambda x: x.first_lba):
            print("%-28s %-14d %12d %12d %9.0fM  %s" % (
                p.name, p.offset, p.first_lba, p.last_lba, p.size / 1e6,
                p.type_guid[:8]))
    return 0


def open_part(name):
    n = Nand()
    parts = parse_gpt(n)
    p = find_partition(parts, name)
    return n, p, Fat32(n, p.offset, p.size)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    cmd = sys.argv[1]
    if cmd == "info":
        return show_info()

    n, p, fs = open_part(sys.argv[2])
    if cmd == "ls":
        path = sys.argv[3] if len(sys.argv) > 3 else "/"
        print("%s:%s  (label=%r, cluster=%d B)" % (p.name, path, fs.label,
                                                   fs.cluster_bytes))
        rows = fs.listdir(path)
        for name, is_dir, size, fc in sorted(rows, key=lambda r: (not r[1], r[0])):
            print("   %s %-52s %12d  c=%d" % ("d" if is_dir else "-", name, size, fc))
        print("   (%d entries)" % len(rows))
        return 0
    if cmd == "cat":
        path = sys.argv[3]
        nbytes = int(sys.argv[4]) if len(sys.argv) > 4 else 4096
        parent, _, base = path.rpartition("/")
        for name, is_dir, size, fc in fs.listdir(parent or "/"):
            if name.lower() == base.lower():
                print(fs.read_file(fc, min(size, nbytes))[:nbytes])
                return 0
        print("not found")
        return 1
    if cmd == "get":
        src, dst = sys.argv[3], sys.argv[4]
        parent, _, base = src.rpartition("/")
        for name, is_dir, size, fc in fs.listdir(parent or "/"):
            if name.lower() == base.lower():
                data = fs.read_file(fc, size)
                with open(dst, "wb") as fh:
                    fh.write(data)
                print("wrote %s (%d bytes)" % (dst, len(data)))
                return 0
        print("not found")
        return 1
    if cmd == "find":
        pat = sys.argv[3].lower()
        hits = []

        def walk(path, depth):
            if depth > 5:
                return
            try:
                rows = fs.listdir(path)
            except Exception:
                return
            for name, is_dir, size, fc in rows:
                full = path.rstrip("/") + "/" + name
                if pat in name.lower():
                    hits.append((full, is_dir, size))
                if is_dir:
                    walk(full, depth + 1)

        walk("/", 0)
        print("%d hits" % len(hits))
        for h in hits[:300]:
            print("   %s %s %d" % ("d" if h[1] else "-", h[0], h[2]))
        return 0

    print(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(main())

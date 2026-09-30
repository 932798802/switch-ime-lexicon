# -*- coding: utf-8 -*-
"""njdc_tailbrute.py —— 广谱暴力搜索尾部字节的生成函数。"""
import os
import sys
import zlib
import hashlib

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..",
                    "..", "01_Inputs", "firmware", "dat0805", "files", "Iwnn", "ZH", "CN", "pinyin", "GB18030")


def be(b, o, n):
    return int.from_bytes(b[o:o + n], "big")


def load(name):
    b = open(os.path.join(BASE, name), "rb").read()
    hs, rs, sst, tst, N = be(b, 0x10, 4), be(b, 0x20, 4), be(b, 0x24, 4), be(b, 0x28, 4), be(b, 0x50, 4)
    pool = b[sst:]
    ents = []
    for i in range(N):
        p = rs + i * 10
        rlen = int.from_bytes(b[p:p + 2], "little"); roff = be(b, p + 2, 2)
        tlen = int.from_bytes(b[p + 4:p + 6], "little"); toff = be(b, p + 6, 2)
        r = pool[roff:roff + rlen].decode("utf-16-be", "replace")
        w = pool[toff:toff + tlen].decode("utf-16-be", "replace")
        rec = b[p:p + 10]
        ents.append(dict(i=i, r=r, w=w, roff=roff, rlen=rlen, toff=toff, tlen=tlen, rec=rec))
    T = [be(b, tst + 2 * k, 2) >> 8 for k in range(N)]
    return b, N, ents, T


def fnv1a32(d):
    h = 0x811C9DC5
    for c in d:
        h ^= c
        h = (h * 0x01000193) & 0xFFFFFFFF
    return h


def fnv1_32(d):
    h = 0x811C9DC5
    for c in d:
        h = (h * 0x01000193) & 0xFFFFFFFF
        h ^= c
    return h


def djb2(d):
    h = 5381
    for c in d:
        h = ((h * 33) + c) & 0xFFFFFFFF
    return h


def sdbm(d):
    h = 0
    for c in d:
        h = (c + (h << 6) + (h << 16) - h) & 0xFFFFFFFF
    return h


def build(e):
    r, w = e["r"], e["w"]
    return {
        "R16": r.encode("utf-16-be"),
        "W16": w.encode("utf-16-be"),
        "W16le": w.encode("utf-16-le"),
        "RA": r.encode("ascii", "replace"),
        "R16+W16": r.encode("utf-16-be") + w.encode("utf-16-be"),
        "W16+R16": w.encode("utf-16-be") + r.encode("utf-16-be"),
        "REC": e["rec"],
        "RA+W16": r.encode("ascii", "replace") + w.encode("utf-16-be"),
    }


def funcs(srcs, e):
    out = {}
    for tag, d in srcs.items():
        _funcs_one(d, out, tag)
    return out


def _funcs_one(d, out, tag):
    if not d:
        return out
    out[tag + "/sum"] = sum(d)
    x = 0
    for c in d:
        x ^= c
    out[tag + "/xor"] = x
    out[tag + "/wsum"] = sum((i + 1) * c for i, c in enumerate(d))
    out[tag + "/fnv1a"] = fnv1a32(d)
    out[tag + "/fnv1"] = fnv1_32(d)
    out[tag + "/djb2"] = djb2(d)
    out[tag + "/sdbm"] = sdbm(d)
    out[tag + "/crc32"] = zlib.crc32(d) & 0xFFFFFFFF
    out[tag + "/adler"] = zlib.adler32(d) & 0xFFFFFFFF
    out[tag + "/md5b0"] = hashlib.md5(d).digest()[0]
    out[tag + "/sha1b0"] = hashlib.sha1(d).digest()[0]
    out[tag + "/crc8"] = zlib.crc32(d) & 0xFF
    if len(d) % 2 == 0:
        u16be = [int.from_bytes(d[i:i + 2], "big") for i in range(0, len(d), 2)]
        out[tag + "/sum16be"] = sum(u16be)
        xx = 0
        for v in u16be:
            xx ^= v
        out[tag + "/xor16be"] = xx
        u16le = [int.from_bytes(d[i:i + 2], "little") for i in range(0, len(d), 2)]
        out[tag + "/sum16le"] = sum(u16le)
        yy = 0
        for v in u16le:
            yy ^= v
        out[tag + "/xor16le"] = yy
    return out


def main(name="njubase1.a"):
    b, N, ents, T = load(name)
    print("=== %s N=%d ===" % (name, N))
    # 特征矩阵
    FE = [funcs(build(e), e) for e in ents]
    keys = set()
    for f in FE:
        keys |= set(f.keys())
    for k in list(keys):
        for f in FE:
            f.setdefault(k, 0)
    extra = {
        "i": lambda e: e["i"],
        "roff": lambda e: e["roff"],
        "toff": lambda e: e["toff"],
        "rlen": lambda e: e["rlen"],
        "tlen": lambda e: e["tlen"],
        "rc": lambda e: len(e["r"]),
        "wc": lambda e: len(e["w"]),
        "r0": lambda e: ord(e["r"][0]) if e["r"] else 0,
        "w0": lambda e: ord(e["w"][0]) if e["w"] else 0,
        "wlast": lambda e: ord(e["w"][-1]) if e["w"] else 0,
    }
    results = []
    for k in sorted(keys):
        vals = [f[k] for f in FE]
        for mod in (64, 128, 256, 32, 63, 127, 100, 96):
            for off in (0, 0x40):
                for op, fn in (("mod", lambda v: v % mod), ("and", lambda v: v & (mod - 1) if mod & (mod - 1) == 0 else v % mod)):
                    hit = sum(1 for i in range(N) if T[i] == fn(vals[i]) + off)
                    if hit > N * 0.5:
                        results.append((hit, "%s %s%d +0x%02x" % (k, op, mod, off)))
    for k, f in extra.items():
        vals = [f(e) for e in ents]
        for mod in (64, 128, 256):
            for off in (0, 0x40):
                hit = sum(1 for i in range(N) if T[i] == (vals[i] % mod) + off)
                if hit > N * 0.5:
                    results.append((hit, "%s %% %d +0x%02x" % (k, mod, off)))
    results.sort(reverse=True)
    if results:
        for h, d in results[:30]:
            print("  %d/%d  %s" % (h, N, d))
    else:
        print("  无任何候选 > 50%%")

    # 打印几个最可能的和值便于人工核对
    print("\n  i   读法         表记       v  | sumR  sumW  sumRW  sumRW&63  xorRW  xorRW&63")
    for i in range(30):
        e = ents[i]
        sR = sum(e["r"].encode("utf-16-be"))
        sW = sum(e["w"].encode("utf-16-be"))
        sRW = sR + sW
        x = 0
        for c in e["r"].encode("utf-16-be") + e["w"].encode("utf-16-be"):
            x ^= c
        print("  %-4d %-12s %-8s %3d | %5d %5d %6d %8d %6d %6d"
              % (i, e["r"], e["w"], T[i] - 0x40, sR, sW, sRW, sRW & 63, x, x & 63))


if __name__ == "__main__":
    main(*(sys.argv[1:] or ["njubase1.a"]))

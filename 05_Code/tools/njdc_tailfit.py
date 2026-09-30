# -*- coding: utf-8 -*-
"""njdc_tailfit.py —— 多编码 × 线性拟合搜索 v = (a*F1 + b*F2 + c) mod 64（高效版）。"""
import os
import sys
import itertools
import zlib

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..",
                    "..", "01_Inputs", "firmware", "dat0805", "files", "Iwnn", "ZH", "CN", "pinyin", "GB18030")

ENCS = ["utf-16-be", "utf-16-le", "utf-8", "gbk", "gb18030", "big5",
        "shift_jis", "euc_jp", "cp932", "euc_kr"]


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
        ents.append((i, r, w, roff, rlen, toff, tlen))
    T = [be(b, tst + 2 * k, 2) >> 8 for k in range(N)]
    return N, ents, T


def main(name):
    N, ents, T = load(name)
    V = [t - 0x40 for t in T]
    print("=== %s N=%d ===" % (name, N))

    F = {}
    for enc in ENCS:
        tag = enc.replace("-", "")
        sW, lW, xW, sR, lR, sRW = [], [], [], [], [], []
        for e in ents:
            _, r, w, _, _, _, _ = e
            try:
                wb = w.encode(enc); rb = r.encode(enc)
            except Exception:
                wb = b""; rb = b""
            sW.append(sum(wb)); lW.append(len(wb))
            x = 0
            for c in wb:
                x ^= c
            xW.append(x)
            sR.append(sum(rb)); lR.append(len(rb)); sRW.append(sum(wb) + sum(rb))
        F["sumW_" + tag] = sW
        F["lenW_" + tag] = lW
        F["xorW_" + tag] = xW
        F["sumR_" + tag] = sR
        F["lenR_" + tag] = lR
        F["sumRW_" + tag] = sRW
    F["sumcu"] = [sum(ord(c) for c in e[2]) for e in ents]
    F["lo"] = [sum(ord(c) & 0xFF for c in e[2]) for e in ents]
    F["hi"] = [sum(ord(c) >> 8 for c in e[2]) for e in ents]
    F["nw"] = [len(e[2]) for e in ents]
    F["toff"] = [e[5] for e in ents]
    F["roff"] = [e[3] for e in ents]
    keys = sorted(F)
    print("特征数=%d" % len(keys))

    sols = []
    # 单特征
    for k in keys:
        A = F[k]
        for a in range(1, 64):
            c = (V[0] - a * A[0]) % 64
            if (a * A[1] + c) % 64 != V[1] or (a * A[2] + c) % 64 != V[2]:
                continue
            hit = sum(1 for j in range(N) if (a * A[j] + c) % 64 == V[j])
            sols.append((hit, "v=(%d*%s+%d)%%64" % (a, k, c)))
    print("单特征候选: %d" % len(sols))

    # 双特征
    cnt = 0
    for k1, k2 in itertools.combinations(keys, 2):
        A = F[k1]; B = F[k2]
        for a in range(64):
            for b in range(64):
                c = (V[0] - a * A[0] - b * B[0]) % 64
                if (a * A[1] + b * B[1] + c) % 64 != V[1]:
                    continue
                if (a * A[2] + b * B[2] + c) % 64 != V[2]:
                    continue
                if (a * A[3] + b * B[3] + c) % 64 != V[3]:
                    continue
                hit = sum(1 for j in range(N) if (a * A[j] + b * B[j] + c) % 64 == V[j])
                cnt += 1
                if hit > N * 0.5:
                    sols.append((hit, "v=(%d*%s+%d*%s+%d)%%64" % (a, k1, b, k2, c)))
    print("通过前4条检验的双特征候选: %d" % cnt)
    sols.sort(reverse=True)
    if sols:
        for h, d in sols[:15]:
            print("  %d/%d  %s" % (h, N, d))
    else:
        print("  无候选")

    # 哈希
    print("\n--- zlib 哈希 &63 / %64 ---")
    for enc in ENCS:
        for src in ("w", "r", "rw"):
            ds = []
            for e in ents:
                _, r, w, _, _, _, _ = e
                try:
                    ds.append({"w": w.encode(enc), "r": r.encode(enc),
                               "rw": (r + w).encode(enc)}[src])
                except Exception:
                    ds.append(b"")
            for hn, hf in (("crc32&63", lambda d: zlib.crc32(d) & 63),
                           ("crc32%64", lambda d: zlib.crc32(d) % 64),
                           ("adler&63", lambda d: zlib.adler32(d) & 63)):
                hit = sum(1 for j in range(N) if hf(ds[j]) == V[j])
                if hit > N * 0.25:
                    print("  %d/%d  %s(%s:%s)" % (hit, N, hn, src, enc))


if __name__ == "__main__":
    main(*(sys.argv[1:] or ["njubase1.a"]))

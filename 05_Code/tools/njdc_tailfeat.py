# -*- coding: utf-8 -*-
"""njdc_tailfeat.py —— 尾部字节 vs 各种候选特征 并排对照 + 暴力搜索。"""
import os
from collections import Counter

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..",
                    "..", "01_Inputs", "firmware", "dat0805", "files", "Iwnn", "ZH", "CN", "pinyin", "GB18030")


def be(b, o, n):
    return int.from_bytes(b[o:o + n], "big")


def load_ents(name):
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
        ents.append((r, w, roff, rlen, toff, tlen))
    T = [be(b, tst + 2 * k, 2) >> 8 for k in range(N)]  # 取高字节（低字节相同）
    return b, hs, rs, sst, tst, N, ents, T


def main(name="njubase1.a"):
    b, hs, rs, sst, tst, N, ents, T = load_ents(name)
    print("=== %s  N=%d ===" % (name, N))
    hdr = ("  i    读法           表记    rc wc rb wb c0 cl w0 wl "
           "sum  xr  xw  roff toff | tail")
    print(hdr)
    for i in range(45):
        r, w, roff, rlen, toff, tlen = ents[i]
        rc, wc = len(r), len(w)
        rb, wb = rlen, tlen
        c0, cl = ord(r[0]), ord(r[-1])
        w0, wl = (ord(w[0]) if w else 0), (ord(w[-1]) if w else 0)
        s = sum(ord(c) for c in r)
        xr = 0
        for c in r:
            xr ^= ord(c)
        xw = 0
        for c in w:
            xw ^= ord(c)
        print("  %-4d %-15s %-6s %2d %2d %2d %2d %4d %4d %4d %4d %4d %4d %4d %5d %4d | 0x%02x (%3d)"
              % (i, r, w, rc, wc, rb, wb, c0, cl, w0, wl, s, xr, xw, roff, toff, T[i], T[i]))

    print("\n--- 暴力搜索：tail == F(...) ---")
    n = N
    res = []
    for i, (r, w, roff, rlen, toff, tlen) in enumerate(ents):
        pass

    def feats(i):
        r, w, roff, rlen, toff, tlen = ents[i]
        f = {}
        f["rc"] = len(r)
        f["wc"] = len(w)
        f["rb"] = rlen
        f["wb"] = tlen
        f["r0"] = ord(r[0]) if r else 0
        f["rlast"] = ord(r[-1]) if r else 0
        f["r1"] = ord(r[1]) if len(r) > 1 else 0
        f["w0"] = ord(w[0]) if w else 0
        f["wlast"] = ord(w[-1]) if w else 0
        f["w0lo"] = (ord(w[0]) & 0xFF) if w else 0
        f["w0hi"] = (ord(w[0]) >> 8) if w else 0
        f["wlastlo"] = (ord(w[-1]) & 0xFF) if w else 0
        f["sumr"] = sum(ord(c) for c in r)
        f["xorw"] = 0
        for c in w:
            f["xorw"] ^= ord(c)
        f["xorr"] = 0
        for c in r:
            f["xorr"] ^= ord(c)
        f["i"] = i
        f["roff"] = roff
        f["toff"] = toff
        return f

    F = [feats(i) for i in range(n)]
    keys = list(F[0].keys())
    best = []
    for k in keys:
        for mod in (256, 64, 128, 32, 48, 96, 16):
            for base in (0, 0x40, 0x61, 0x60, 0x41, 0x30):
                hit = sum(1 for i in range(n) if T[i] == (F[i][k] % mod) + base)
                if hit > n * 0.9:
                    best.append((hit, "%s %% %d + 0x%02x" % (k, mod, base)))
                hit2 = sum(1 for i in range(n) if T[i] == (F[i][k] & (mod - 1)) + base)
                if hit2 > n * 0.9:
                    best.append((hit2, "(%s & 0x%x) + 0x%02x" % (k, mod - 1, base)))
        # 直接相等
        hit = sum(1 for i in range(n) if T[i] == F[i][k])
        if hit > n * 0.5:
            best.append((hit, "== %s" % k))
    best.sort(reverse=True)
    if best:
        for h, d in best[:20]:
            print("  命中 %d/%d  %s" % (h, n, d))
    else:
        print("  无候选命中 > 90%%")

    # 检查 tail 是否是单调/分段/与 i 相关
    print("\n  tail 与 i 的关系: 段数=%d" % (1 + sum(1 for i in range(1, n) if T[i] != T[i - 1])))
    print("  tail 唯一值=%d  %s" % (len(set(T)), sorted(set(T))))
    print("  tail 值直方图: %s" % sorted(Counter(T).items()))


if __name__ == "__main__":
    import sys
    main(*(sys.argv[1:] or ["njubase1.a"]))

# -*- coding: utf-8 -*-
"""njdc_rec2.py —— 用真布局 u8+u24BE+u8+u24BE+pad 验证所有词典，并 dump njubase3 附加区。"""
import os
import sys
import math
from collections import Counter

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..",
                    "..", "01_Inputs", "firmware", "dat0805", "files", "Iwnn", "ZH", "CN", "pinyin", "GB18030")


def load(name):
    return open(os.path.join(BASE, name), "rb").read()


def be(b, o, n):
    return int.from_bytes(b[o:o + n], "big")


def decode_records(name, verbose=True):
    b = load(name)
    hs, rs, pool, tst, N = be(b, 0x10, 4), be(b, 0x20, 4), be(b, 0x24, 4), be(b, 0x28, 4), be(b, 0x50, 4)
    ents = []
    bad = 0
    for i in range(N):
        p = rs + i * 10
        rlen = b[p]
        roff = be(b, p + 1, 3)
        tlen = b[p + 4]
        toff = be(b, p + 5, 3)
        pad = be(b, p + 8, 2)
        if pad != 0:
            bad += 1
        a1, a2 = pool + roff, pool + toff
        r = w = None
        if rlen and a1 + rlen <= len(b):
            try:
                r = b[a1:a1 + rlen].decode("utf-16-be")
            except Exception:
                pass
        if tlen and a2 + tlen <= len(b):
            try:
                w = b[a2:a2 + tlen].decode("utf-16-be")
            except Exception:
                pass
        ents.append((rlen, roff, tlen, toff, r, w))
    letters = sum(1 for e in ents if e[4] and all('a' <= c <= 'z' for c in e[4]))
    cjk = sum(1 for e in ents if e[5] and all(0x2E80 <= ord(c) <= 0xA4CF or 0x4E00 <= ord(c) <= 0x9FFF
                                               or 0x20000 <= ord(c) <= 0x3FFFF or 0x3000 <= ord(c) <= 0x303F
                                               or 0xFF00 <= ord(c) <= 0xFFEF for c in e[5]))
    if verbose:
        print("=== %s N=%d pad!=0:%d  读法纯小写字母:%d/%d (%.1f%%)  表记纯CJK:%d/%d (%.1f%%)"
              % (name, N, bad, letters, N, 100.0 * letters / N, cjk, N, 100.0 * cjk / N))
        print("    首 6: %s" % [(e[4], e[5]) for e in ents[:6]])
        print("    末 3: %s" % [(e[4], e[5]) for e in ents[-3:]])
        reads = [e[4] for e in ents if e[4]]
        print("    读法升序: %s   max rlen=%d max tlen=%d" %
              (reads == sorted(reads), max(e[0] for e in ents), max(e[2] for e in ents)))
        # 失败样本
        fails = [i for i, e in enumerate(ents) if not (e[4] and all('a' <= c <= 'z' for c in e[4]))]
        print("    读法异常条数=%d 前 5 例: %s" % (len(fails), [(i, ents[i][4], ents[i][5]) for i in fails[:5]]))
    return b, hs, rs, pool, tst, N, ents


def main():
    for n in ["njubase1.a", "njubase2.a", "njcode.a", "njtan.a", "njubase3.a"]:
        decode_records(n)
        print()

    print("#" * 80)
    print("# njubase3 附加区 [0x2c, 0x24) 内容")
    print("#" * 80)
    b = load("njubase3.a")
    a, z = be(b, 0x2c, 4), be(b, 0x24, 4)
    print("  range 0x%x..0x%x  len=%d  /4=%s  /2=%s" % (a, z, z - a, (z - a) / 4, (z - a) / 2))
    print("  hex 前 128B:")
    for p in range(a, a + 128, 16):
        print("    %08x  %s" % (p, " ".join("%02x" % c for c in b[p:p + 16])))
    # 熵
    cnt = Counter(b[a:z])
    ent = -sum((v / (z - a)) * math.log2(v / (z - a)) for v in cnt.values())
    print("  熵 = %.3f bit/byte (均匀=8.0)" % ent)
    # 当成 u8 看分布前 10
    print("  字节分布前 10: %s" % cnt.most_common(10))
    # 与 pool 前段/b 他处比较
    print("  该区是否与别处重复: %s" % [hex(b.find(b[a:a + 64], a + 1))])
    # 读法池/表记池分界
    _, hs, rs, pool, tst, N, ents = decode_records("njubase3.a", verbose=False)
    maxr = max(e[1] + e[0] for e in ents)
    mint = min(e[3] for e in ents)
    print("  pool=0x%x..0x%x  最大读法末端=%d(0x%x)  最小表记偏移=%d(0x%x)"
          % (pool, tst, maxr, maxr, mint, mint))
    print("  pool 总长=%d  读法区约 %d  表记区约 %d" % (tst - pool, mint, tst - pool - mint))


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""njdc_poolmap.py —— 逐条列出记录与其在池中的精确区间，判定池的打包规则。"""
import os
import sys

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..",
                    "..", "01_Inputs", "firmware", "dat0805", "files", "Iwnn", "ZH", "CN", "pinyin", "GB18030")


def be(b, o, n):
    return int.from_bytes(b[o:o + n], "big")


def map_pool(name, lo=0, hi=40):
    b = open(os.path.join(BASE, name), "rb").read()
    rs, pool, tst, N = be(b, 0x20, 4), be(b, 0x24, 4), be(b, 0x28, 4), be(b, 0x50, 4)
    recs = []
    for i in range(N):
        p = rs + i * 10
        rl, ro, tl, to = b[p], be(b, p + 1, 3), b[p + 4], be(b, p + 5, 3)
        r = b[pool + ro:pool + ro + rl].decode("utf-16-be", "replace")
        w = b[pool + to:pool + to + tl].decode("utf-16-be", "replace")
        recs.append((r, ro, rl, w, to, tl))

    print("=" * 100)
    print("%s  N=%d  pool=%d..%d (len=%d)" % (name, N, pool, tst, tst - pool))
    print("=" * 100)
    print("%4s %-24s %6s %5s %-14s %6s %5s   %s" % ("i", "读法", "roff", "rlen", "表记", "toff", "tlen", "区间[roff,roff+rlen)"))
    for i in range(lo, min(hi, N)):
        r, ro, rl, w, to, tl = recs[i]
        print("%4d %-24s %6d %5d %-14s %6d %5d   [%d,%d)" % (i, r, ro, rl, w, to, tl, ro, ro + rl))

    # 用「最大串去重 + 升序」重建读法池，与观测比对
    reads = [r[0] for r in recs]
    uniq = sorted(set(reads))
    keep = [s for s in uniq if not any(t != s and s in t for t in uniq)]
    off = 0
    pred = {}
    for s in keep:
        pred[s] = off
        off += len(s) * 2
    print()
    print("  唯一读法 %d 个，去掉「是其它读法子串」后剩 %d 个，预测池长(读法区) %d" % (len(uniq), len(keep), off))
    maxr = max(r[1] + r[2] for r in recs)
    mint = min(r[4] for r in recs)
    print("  实测读法区 [0,%d)  表记区 [%d,%d)" % (maxr, mint, tst - pool))
    for i in range(lo, min(hi, N)):
        r, ro, rl, w, to, tl = recs[i]
        p = pred.get(r)
        print("   %4d %-24s 实测roff=%-6d 预测(独占)=%-6s %s" %
              (i, r, ro, p, "" if p == ro else ("<-- 共享: 落在某个更长串内部" if p is None else "<-- 不符")))
    return b, recs, pool, tst, rs, N


if __name__ == "__main__":
    args = sys.argv[1:] or ["njubase1.a"]
    name = args[0]
    lo = int(args[1]) if len(args) > 1 else 0
    hi = int(args[2]) if len(args) > 2 else 40
    map_pool(name, lo, hi)

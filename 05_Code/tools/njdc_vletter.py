# -*- coding: utf-8 -*-
"""njdc_vletter.py —— v 与首字母/读音桶的关系，判断 v 是「读音派生」还是「词条派生」。"""
import os
import sys
from collections import defaultdict, Counter

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
        ents.append((i, r, w, roff, rlen, toff, tlen))
    T = [be(b, tst + 2 * k, 2) >> 8 for k in range(N)]
    return N, ents, T


def main(name):
    N, ents, T = load(name)
    V = [t - 0x40 for t in T]
    print("=== %s N=%d ===" % (name, N))

    print("\n--- 按读法首字母 × v ---")
    for L in "abcdefghijklmnopqrstuvwxyz":
        idxs = [i for i in range(N) if ents[i][1].startswith(L)]
        if not idxs:
            continue
        c = Counter(V[i] for i in idxs)
        mn, mx = min(V[i] for i in idxs), max(V[i] for i in idxs)
        print("  %s  n=%-5d v∈[%2d,%2d] 众数=%-3d  分布前6=%s" %
              (L, len(idxs), mn, mx, c.most_common(1)[0][0], c.most_common(6)))

    print("\n--- 按读法前2字母 × v (样本) ---")
    by2 = defaultdict(list)
    for i in range(N):
        by2[ents[i][1][:2]].append(V[i])
    rows = sorted(by2.items(), key=lambda kv: -len(kv[1]))[:25]
    for k, vs in rows:
        print("  %-4s n=%-5d v∈[%2d,%2d] 众数=%-3d 均值=%.1f" %
              (k, len(vs), min(vs), max(vs), Counter(vs).most_common(1)[0][0],
               sum(vs) / len(vs)))

    print("\n--- 完整 'o' 桶 (ou*) ---")
    idxs = [i for i in range(N) if ents[i][1].startswith("o")]
    print("  共 %d 条" % len(idxs))
    for i in idxs:
        _, r, w, roff, rlen, toff, tlen = ents[i]
        print("    i=%-5d v=%-3d r=%-14s w=%-8s roff=%-6d toff=%-6d" %
              (i, V[i], r, w, roff, toff))

    print("\n--- 全库 v=0 的完整清单 ---")
    for i in range(N):
        if V[i] == 0:
            _, r, w, roff, rlen, toff, tlen = ents[i]
            print("    i=%-5d r=%-16s w=%-10s roff=%-6d toff=%-6d" % (i, r, w, roff, toff))

    print("\n--- 全库 v<=5 的清单 ---")
    for i in range(N):
        if V[i] <= 5:
            _, r, w, roff, rlen, toff, tlen = ents[i]
            print("    i=%-5d v=%-3d r=%-16s w=%-10s" % (i, V[i], r, w))


if __name__ == "__main__":
    main(*(sys.argv[1:] or ["njubase1.a"]))

# -*- coding: utf-8 -*-
"""njdc_vgroups.py —— 按 v 值分组看词条特征。"""
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
    print("=== %s N=%d ===" % (name, N))
    g = defaultdict(list)
    for i in range(N):
        g[T[i] - 0x40].append(i)

    for v in (0, 5, 63, 62, 61, 60, 56, 50):
        idxs = g.get(v, [])
        print("\n--- v=%d  共 %d 条 ---" % (v, len(idxs)))
        for i in idxs[:14]:
            _, r, w, roff, rlen, toff, tlen = ents[i]
            print("    i=%-5d r=%-14s w=%-6s rc=%2d wc=%2d roff=%-6d toff=%-6d"
                  % (i, r, w, len(r), len(w), roff, toff))

    # v=0 的 30 条共性
    print("\n--- v=0 的 30 条共性 ---")
    idxs = g[0]
    print("  末字: %s" % Counter(ents[i][2][-1] for i in idxs if ents[i][2]))
    print("  首字: %s" % Counter(ents[i][2][0] for i in idxs if ents[i][2]))
    print("  wc: %s   rc: %s" % (Counter(len(ents[i][2]) for i in idxs),
                                Counter(len(ents[i][1]) for i in idxs)))
    print("  读法: %s" % [ents[i][1] for i in idxs])
    print("  表记: %s" % [ents[i][2] for i in idxs])
    print("  w 的码点和: %s" % [sum(ord(c) for c in ents[i][2]) for i in idxs])
    print("  toff: %s" % [ents[i][5] for i in idxs])

    # v 与「同读法条目数」「同末字条目数」等对照
    print("\n--- 统计对照 ---")
    rc_count = Counter(len(e[1]) for e in ents)
    print("  读法长度分布: %s" % sorted(rc_count.items()))
    # 与「读法长度」的交叉表
    cross = defaultdict(Counter)
    for i in range(N):
        cross[len(ents[i][1])][T[i] - 0x40] += 1
    for L in sorted(cross):
        top = cross[L].most_common(4)
        print("  读法%2d字: n=%-5d v 分布前 4: %s" % (L, sum(cross[L].values()), top))

    # 检查 v 是否是「读法在该长度组内的序号」
    print("\n--- v 是否 = 读法在该长度组内的序号(或变体) ---")
    for L in sorted(cross)[:6]:
        idxs = [i for i in range(N) if len(ents[i][1]) == L]
        vv = [T[i] - 0x40 for i in idxs]
        print("  读法%2d字 组内 v 前 20: %s" % (L, vv[:20]))
        print("            组内序号 前 20: %s" % list(range(len(idxs)))[:20])


if __name__ == "__main__":
    main(*(sys.argv[1:] or ["njubase1.a"]))

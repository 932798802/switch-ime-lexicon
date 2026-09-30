# -*- coding: utf-8 -*-
"""njdc_pool.py —— 按偏移顺序 dump 字符串池，找出读法池/表记池的排布规律。"""
import os
import sys

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..",
                    "..", "01_Inputs", "firmware", "dat0805", "files", "Iwnn", "ZH", "CN", "pinyin", "GB18030")


def load(name):
    return open(os.path.join(BASE, name), "rb").read()


def be(b, o, n):
    return int.from_bytes(b[o:o + n], "big")


def main(name="njubase1.a"):
    b = load(name)
    hs, rs, pool, tst, N = be(b, 0x10, 4), be(b, 0x20, 4), be(b, 0x24, 4), be(b, 0x28, 4), be(b, 0x50, 4)
    ents = []
    for i in range(N):
        p = rs + i * 10
        ents.append((i, b[p], be(b, p + 1, 3), b[p + 4], be(b, p + 5, 3)))
    max_r = max(o + l for _, l, o, _, _ in ents)
    min_t = min(t for *_, t in ents)
    print("=== %s N=%d pool=0x%x..0x%x  读法区=<0,%d)  表记区=[%d,%d)"
          % (name, N, pool, tst, max_r, min_t, tst - pool))
    print("  读法区大小=%d  表记区大小=%d" % (max_r, tst - pool - min_t))

    # 读法区: 收集 (roff, rlen, reading) 唯一，按 roff 排序
    seen = {}
    for i, rl, ro, tl, to in ents:
        if ro < max_r:
            seen.setdefault(ro, (rl, i))
    roffs = sorted(seen)
    print("\n--- 读法池按偏移顺序（前 40）---")
    prev_end = 0
    for k, ro in enumerate(roffs[:40]):
        rl, owner = seen[ro]
        s = b[pool + ro:pool + ro + rl].decode("utf-16-be", "replace")
        gap = ro - prev_end
        print("  %5d : len=%-3d owner_i=%-5d gap=%-4d %s" % (ro, rl, owner, gap, s))
        prev_end = ro + rl
    # 空隙统计
    gaps = []
    prev = 0
    for ro in roffs:
        gaps.append(ro - prev)
        prev = ro + seen[ro][0]
    from collections import Counter
    print("  读法区 相邻空隙分布: %s" % Counter(gaps).most_common(8))
    print("  读法区 唯一读法数=%d  覆盖字节=%d/%d" % (len(roffs), sum(v[0] for v in seen.values()), max_r))

    # 表记区
    seenw = {}
    for i, rl, ro, tl, to in ents:
        if to >= min_t:
            seenw.setdefault(to, (tl, i))
    toffs = sorted(seenw)
    print("\n--- 表记池按偏移顺序（前 40）---")
    prev_end = min_t
    for k, to in enumerate(toffs[:40]):
        tl, owner = seenw[to]
        s = b[pool + to:pool + to + tl].decode("utf-16-be", "replace")
        print("  %5d : len=%-3d owner_i=%-5d gap=%-4d %s" % (to, tl, owner, to - prev_end, s))
        prev_end = to + tl
    gaps = []
    prev = min_t
    for to in toffs:
        gaps.append(to - prev)
        prev = to + seenw[to][0]
    print("  表记区 相邻空隙分布: %s" % Counter(gaps).most_common(8))
    print("  表记区 唯一串数=%d  覆盖字节=%d/%d" % (len(toffs), sum(v[0] for v in seenw.values()),
                                            tst - pool - min_t))

    # 表记是否按「长度降序/前缀共享」排列：看是否每个串都能在已写串里找到前缀
    print("\n--- 表记前缀共享检验（前 300 个唯一串）---")
    written = []  # (start, text)
    shared = 0
    for k, to in enumerate(toffs[:300]):
        tl, owner = seenw[to]
        s = b[pool + to:pool + to + tl].decode("utf-16-be", "replace")
        hit = None
        for st, txt in written:
            if txt.startswith(s):
                hit = (st, txt)
                break
        if hit:
            shared += 1
        if k < 20:
            print("  %-6d len=%-3d owner=%-5d %s   共享于=%s" % (to, tl, owner, s, hit))
        written.append((to, s))
    print("  前 300 个唯一串中，能被已写串包含为前缀的: %d" % shared)


if __name__ == "__main__":
    main(*(sys.argv[1:] or ["njubase1.a"]))

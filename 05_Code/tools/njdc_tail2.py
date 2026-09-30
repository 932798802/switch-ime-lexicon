# -*- coding: utf-8 -*-
"""njdc_tail2.py —— 尾部表语义：与词条逐条对齐，找规律。"""
import os
import sys
from collections import Counter, defaultdict

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..",
                    "..", "01_Inputs", "firmware", "dat0805", "files", "Iwnn", "ZH", "CN", "pinyin", "GB18030")


def be(b, o, n):
    return int.from_bytes(b[o:o + n], "big")


def load(name):
    return open(os.path.join(BASE, name), "rb").read()


def main(name="njubase1.a"):
    b = load(name)
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
    T = [be(b, tst + 2 * k, 2) for k in range(N)]
    print("%s  N=%d  tail bytes=%d" % (name, N, len(b) - tst))
    hi_lo_equal = sum(1 for k in range(N) if (T[k] >> 8) == (T[k] & 0xFF))
    print("  尾部值 hi==lo 数量: %d / %d" % (hi_lo_equal, N))
    print("  尾部值域: min=0x%x max=0x%x  唯一值=%d" % (min(T), max(T), len(set(T))))
    print("  值分布: %s" % sorted(Counter(T).items())[:40])

    print("\n  i     读法              表记        读法B 表记B | tail  tail&0xff  -0x64")
    for i in range(40):
        r, w, roff, rlen, toff, tlen = ents[i]
        print("  %-5d %-16s %-8s %4d %5d | 0x%04x %5d %6d"
              % (i, r, w, rlen, tlen, T[i], T[i] & 0xFF, (T[i] & 0xFF) - 0x64))

    # 假设检验: tail - 0x64 是否等于「读法字符数」/「表记字符数」/「公共前缀」等
    print("\n--- 假设检验（用全部 N 条）---")
    cands = {
        "读法字符数": lambda r, w, rl, tl: len(r),
        "表记字符数": lambda r, w, rl, tl: len(w),
        "读法字节数": lambda r, w, rl, tl: rl,
        "表记字节数": lambda r, w, rl, tl: tl,
        "读法字节数/2": lambda r, w, rl, tl: rl // 2,
        "首字符ord": lambda r, w, rl, tl: ord(r[0]) if r else 0,
        "读法首字符+末字符": lambda r, w, rl, tl: (ord(r[0]) + ord(r[-1])) if r else 0,
    }
    for name_, f in cands.items():
        for base in (0, 0x64, 0x60, 0x40):
            hit = sum(1 for i, (r, w, roff, rl, toff, tl) in enumerate(ents) if T[i] == f(r, w, rl, tl) + base)
            if hit > N * 0.5:
                print("  %-16s + 0x%02x : 命中 %d / %d" % (name_, base, hit, N))

    # 与「下一条读法的公共前缀」比对
    def lcp(a, bb):
        n = 0
        for x, y in zip(a, bb):
            if x != y:
                break
            n += 1
        return n
    for base in (0, 0x64, 0x60, 0x40, 0x61):
        hit = 0
        for i in range(N - 1):
            v = lcp(ents[i][0], ents[i + 1][0])
            if T[i] == v + base:
                hit += 1
        print("  与下条公共前缀 + 0x%02x : 命中 %d / %d" % (base, hit, N - 1))

    # 与「上一条读法的公共前缀」比对
    for base in (0, 0x64, 0x60, 0x40):
        hit = sum(1 for i in range(1, N) if T[i] == lcp(ents[i - 1][0], ents[i][0]) + base)
        print("  与上条公共前缀 + 0x%02x : 命中 %d / %d" % (base, hit, N - 1))

    # 尾部到底哪里开始变成常量
    print("\n--- tail 从第几条开始恒定 ---")
    last = T[-1]
    k = N - 1
    while k > 0 and T[k - 1] == last:
        k -= 1
    print("  最后一个恒定值 0x%04x，从 i=%d 起恒定，共 %d 条" % (last, k, N - k))
    # 各值的连续段
    segs = []
    s = 0
    cur = T[0]
    for i in range(1, N):
        if T[i] != cur:
            segs.append((s, i - 1, cur))
            s = i
            cur = T[i]
    segs.append((s, N - 1, cur))
    print("  连续段数=%d  前 30 段: %s" % (len(segs), [(a, b_, hex(v)) for a, b_, v in segs[:30]]))


if __name__ == "__main__":
    main(*(sys.argv[1:] or ["njubase1.a"]))

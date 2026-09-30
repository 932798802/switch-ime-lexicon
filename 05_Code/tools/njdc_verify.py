# -*- coding: utf-8 -*-
"""njdc_verify.py —— 验证索引表 T[b] = 1 + count(读法首字节 <= b)，并全量解码各词典。"""
import os
import sys
from collections import Counter

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..",
                    "..", "01_Inputs", "firmware", "dat0805", "files", "Iwnn", "ZH", "CN", "pinyin", "GB18030")


def be(b, o, n):
    return int.from_bytes(b[o:o + n], "big")


def analyze(name):
    b = open(os.path.join(BASE, name), "rb").read()
    hs, rs, sst, tst, N = be(b, 0x10, 4), be(b, 0x20, 4), be(b, 0x24, 4), be(b, 0x28, 4), be(b, 0x50, 4)
    pool = b[sst:]
    print("=" * 84)
    print("%s  size=%d hs=0x%x rs=0x%x pool=0x%x tail=0x%x N=%d  idxlen=%d"
          % (name, len(b), hs, rs, sst, tst, N, rs - hs))
    print("  0x20 + 10N = %d   vs 0x24 = %d   %s" % (rs + 10 * N, sst, "OK" if rs + 10 * N == sst else "MISMATCH"))
    print("=" * 84)

    # 前缀
    pre = [be(b, hs + 4 * k, 4) for k in range(min(9, (rs - hs) // 4))]
    print("  9×u32 前缀: %s" % pre)

    # T 表验证
    n_u32 = (rs - hs - 2) // 4
    T = [be(b, hs + 4 * k, 4) for k in range(n_u32)]
    print("  u32 表实际长度(扣掉末尾 2B) = %d" % n_u32)

    # 解码全部词条
    ents = []
    bad = 0
    for i in range(N):
        p = rs + i * 10
        rlen = int.from_bytes(b[p:p + 2], "little"); roff = be(b, p + 2, 2)
        tlen = int.from_bytes(b[p + 4:p + 6], "little"); toff = be(b, p + 6, 2)
        if roff + rlen > len(pool) or toff + tlen > len(pool):
            bad += 1
            ents.append(None)
            continue
        try:
            r = pool[roff:roff + rlen].decode("utf-16-be")
            w = pool[toff:toff + tlen].decode("utf-16-be")
        except Exception:
            r, w = "", ""
            bad += 1
        ents.append((r, w))
    print("  解码越界/异常: %d / %d" % (bad, N))

    reads = [e[0] for e in ents if e]
    c = Counter(r.encode("utf-16-be")[:1][0] if r else 0 for r in reads)
    run = 0
    calcT = []
    for bb in range(256):
        run += c.get(bb, 0)
        calcT.append(run + 1)
    # 与文件中的 256 表比较
    if n_u32 >= 9 + 256:
        fileT = T[9:9 + 256]
        diff = [(k, fileT[k], calcT[k]) for k in range(256) if fileT[k] != calcT[k]]
        print("  T[b] 假设检验: 不符 %d / 256" % len(diff))
        if diff:
            print("    前 20 处不符: %s" % diff[:20])
        else:
            print("    *** T[b] = 1 + count(首字节 <= b) 完全成立 ***")
    # 剩余部分
    rest = T[9 + 256:]
    if rest:
        print("  9+256 之后剩余 u32: %d 个  min=%d max=%d 唯一=%d" % (len(rest), min(rest), max(rest), len(set(rest))))
        print("    前 20: %s" % rest[:20])

    # 排序 / 样例
    print("  读法升序: %s" % (reads == sorted(reads)))
    print("  首 3: %s" % [(e[0], e[1]) for e in ents[:3]])
    print("  末 3: %s" % [(e[0], e[1]) for e in ents[-3:]])
    # 首字节分布
    print("  首字节分布(前 12): %s" % sorted(c.items())[:12])
    return b, hs, rs, sst, tst, N, T, ents


if __name__ == "__main__":
    for n in (sys.argv[1:] or ["njubase1.a", "njubase2.a", "njcode.a", "njtan.a", "njubase3.a"]):
        analyze(n)
        print()

# -*- coding: utf-8 -*-
"""njdc_tail.py —— 解码记录表 + 验证「字母分桶」假设 + dump 尾部表/页脚。"""
import os
import sys

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..",
                    "..", "01_Inputs", "firmware", "dat0805", "files", "Iwnn", "ZH", "CN", "pinyin", "GB18030")


def be(b, o, n):
    return int.from_bytes(b[o:o + n], "big")


def le(b, o, n):
    return int.from_bytes(b[o:o + n], "little")


def load(name):
    return open(os.path.join(BASE, name), "rb").read()


def decode(name):
    b = load(name)
    hs, rs, sst, tst, N = be(b, 0x10, 4), be(b, 0x20, 4), be(b, 0x24, 4), be(b, 0x28, 4), be(b, 0x50, 4)
    pool = b[sst:]
    ents = []
    for i in range(N):
        p = rs + i * 10
        rlen = int.from_bytes(b[p:p + 2], "little")
        roff = be(b, p + 2, 2)
        tlen = int.from_bytes(b[p + 4:p + 6], "little")
        toff = be(b, p + 6, 2)
        try:
            r = pool[roff:roff + rlen].decode("utf-16-be")
            w = pool[toff:toff + tlen].decode("utf-16-be")
        except Exception:
            r, w = "?", "?"
        ents.append((i, roff, rlen, r, toff, tlen, w))
    return b, hs, rs, sst, tst, N, ents


def main():
    for name in (sys.argv[1:] or ["njubase1.a", "njcode.a", "njtan.a"]):
        b, hs, rs, sst, tst, N, ents = decode(name)
        fs = len(b)
        m14, m18 = be(b, 0x14, 4), be(b, 0x18, 4)
        print("=" * 82)
        print("%s  size=%d N=%d hs=0x%x rs=0x%x pool=0x%x tail=0x%x  0x14=%d 0x18=%d"
              % (name, fs, N, hs, rs, sst, tst, m14, m18))
        print("=" * 82)
        # 实际最大长度
        print("  实际 max 读法字节=%d  max 表记字节=%d  ->  0x14 匹配=%s  0x18 匹配=%s"
              % (max(e[2] for e in ents), max(e[5] for e in ents),
                 max(e[2] for e in ents) == m14, max(e[5] for e in ents) == m18))
        # 排序？
        reads = [e[3] for e in ents]
        print("  按读法升序: %s" % (reads == sorted(reads)))
        bad = [(a, c) for a, c in zip(reads, reads[1:]) if a > c]
        print("  逆序对数量: %d  首 5 例: %s" % (len(bad), bad[:5]))
        print("  首 5 条: %s" % [(e[3], e[6]) for e in ents[:5]])
        print("  末 5 条: %s" % [(e[3], e[6]) for e in ents[-5:]])

        # 26 桶验证
        idx = [be(b, hs + 4 * k, 4) for k in range((rs - hs) // 4)]
        tail2 = b[hs + 4 * ((rs - hs) // 4):rs]
        print("  u32 表长度=%d  末尾 2B=%s" % (len(idx), tail2.hex()))
        # 找第一个非 0/1 的位置
        start = next(k for k, v in enumerate(idx) if v > 1)
        print("  首个 >1 元素 idx=%d" % start)
        cum = idx[start:start + 26]
        print("  26 桶累积: %s" % cum)
        # 用读法首字母分组
        from collections import Counter
        c = Counter(r[0] for r in reads if r)
        letters = "abcdefghijklmnopqrstuvwxyz"
        run = 0
        calc = []
        for L in letters:
            run += c.get(L, 0)
            calc.append(run)
        print("  按首字母累积: %s" % calc)
        print("  >>> 匹配: %s" % (calc == cum))
        if calc != cum:
            diff = [(letters[i] if i < 26 else "?", cum[i] - calc[i]) for i in range(min(26, len(cum)))]
            print("      差异: %s" % diff)

        # 尾部表
        print("\n  尾部区 [0x%x, EOF) = %d B" % (tst, fs - tst))
        print("    = 2*(N+2)=%d ? %s   2*(N-54)=%d ? %s"
              % (2 * (N + 2), fs - tst == 2 * (N + 2),
                 2 * (N - 54), fs - tst == 2 * (N - 54)))
        print("  尾部前 48B: %s" % b[tst:tst + 48].hex(" "))
        print("  尾部末 112B: %s" % b[fs - 112:fs].hex(" "))
        # 页脚跨文件是否一致
        print("  FOOTER112 md5=%s" % __import__("hashlib").md5(b[fs - 112:fs]).hexdigest())
        # 0x30 / 0x0C
        print("  0x30(trailer)=%d  0x0c=%d  0x0c+0x30=%d" % (be(b, 0x30, 4), be(b, 0x0c, 4), be(b, 0x0c, 4) + be(b, 0x30, 4)))
        # 尾部当 u16 BE 前 24
        print("  尾部 u16BE 前 24: %s" % [be(b, tst + 2 * k, 2) for k in range(24)])
        print("  尾部 u16BE 后 24: %s" % [be(b, fs - 112 + 2 * k, 2) for k in range(56)][:56][-24:])


if __name__ == "__main__":
    main()

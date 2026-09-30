# -*- coding: utf-8 -*-
"""njdc_ixcmp.py —— 对比多个 NJDC 的索引区 [hs, 0x20)，判断是否为固定表。"""
import os
import glob
import hashlib

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..",
                    "..", "01_Inputs", "firmware", "dat0805", "files", "Iwnn", "ZH", "CN", "pinyin", "GB18030")


def be(b, o, n):
    return int.from_bytes(b[o:o + n], "big")


def load(name):
    b = open(os.path.join(BASE, name), "rb").read()
    hs = be(b, 0x10, 4)
    rs = be(b, 0x20, 4)
    return b, hs, rs


def main():
    names = ["njcode.a", "njubase1.a", "njubase2.a", "njexyomi.a"]
    print("--- 索引区 [hs, 0x20) 指纹 ---")
    for n in names:
        b, hs, rs = load(n)
        reg = b[hs:rs]
        print("%-14s hs=0x%-5x rs=0x%-8x len=%-7d md5=%s" %
              (n, hs, rs, len(reg), hashlib.md5(reg).hexdigest()))
        print("              首 32B: %s" % " ".join("%02x" % c for c in reg[:32]))
        print("              末 32B: %s" % " ".join("%02x" % c for c in reg[-32:]))

    # 逐字节比较 njcode / njubase1 / njubase2
    print("\n--- 逐字节差异 (njcode vs njubase1, 前 0x54..0x47A 公共区间) ---")
    b1, hs1, rs1 = load("njcode.a")
    b2, hs2, rs2 = load("njubase1.a")
    b3, hs3, rs3 = load("njubase2.a")
    print("hs1=0x%x rs1=0x%x  hs2=0x%x rs2=0x%x  hs3=0x%x rs3=0x%x" % (hs1, rs1, hs2, rs2, hs3, rs3))
    L = min(rs1, rs2, rs3) - max(hs1, hs2, hs3)
    d12 = [(i, b1[hs1 + i], b2[hs2 + i]) for i in range(L) if b1[hs1 + i] != b2[hs2 + i]]
    d23 = [(i, b2[hs2 + i], b3[hs3 + i]) for i in range(L) if b2[hs2 + i] != b3[hs3 + i]]
    print("njcode vs njubase1 不同字节数=%d / %d" % (len(d12), L))
    print("  前 60 个差异: %s" % d12[:60])
    print("njubase1 vs njubase2 不同字节数=%d / %d" % (len(d23), L))
    print("  前 60 个差异: %s" % d23[:60])

    # 把索引区当 u32 BE 数组看
    print("\n--- 索引区当 u32 BE ---")
    for n in names:
        b, hs, rs = load(n)
        a = [be(b, p, 4) for p in range(hs, rs - 3, 4)]
        print("%-14s 元素数=%d  min=%d max=%d 唯一=%d" %
              (n, len(a), min(a), max(a), len(set(a))))
        print("              前 24: %s" % a[:24])

    # njubase1: 0x1F8 起 u32 数组细节
    print("\n--- njubase1.a 0x1F8 起 u32 BE 数组 ---")
    b, hs, rs = load("njubase1.a")
    a = [(p, be(b, p, 4)) for p in range(0x1F8, rs - 3, 4)]
    print("元素数=%d" % len(a))
    print("前 24: %s" % [(hex(p), v) for p, v in a[:24]])
    print("后 12: %s" % [(hex(p), v) for p, v in a[-12:]])
    vals = [v for _, v in a]
    print("单调不减=%s" % all(vals[i] <= vals[i + 1] for i in range(len(vals) - 1)))
    print("全部落在 [0x20,0x24)=[%d,%d): %s" % (rs, be(b, 0x24, 4),
          all(rs <= v < be(b, 0x24, 4) for v in vals)))
    d = [vals[i + 1] - vals[i] for i in range(len(vals) - 1)]
    print("相邻差 前 40: %s" % d[:40])
    print("相邻差 唯一值: %s" % sorted(set(d))[:40])

    # 0x1F8 之前当 u8 看
    print("\n--- njubase1.a [0x54,0x1F8) 非零字节 ---")
    nz = [(i, b[i]) for i in range(0x54, 0x1F8) if b[i]]
    print("非零=%d  %s" % (len(nz), nz[:80]))


if __name__ == "__main__":
    main()

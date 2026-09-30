# -*- coding: utf-8 -*-
"""njdc_ix.py —— 干净 dump NJDC 索引区：按不同端序/步长解释，找规律。"""
import os
import sys

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..",
                    "..", "01_Inputs", "firmware", "dat0805", "files", "Iwnn", "ZH", "CN", "pinyin", "GB18030")


def be(b, o, n):
    return int.from_bytes(b[o:o + n], "big")


def le(b, o, n):
    return int.from_bytes(b[o:o + n], "little")


def hexdump(b, s, e, per=16):
    for p in range(s, e, per):
        print("%08x  %s" % (p, " ".join("%02x" % c for c in b[p:p + per])))


def main(name):
    b = open(os.path.join(BASE, name), "rb").read()
    hs = be(b, 0x10, 4)
    rs = be(b, 0x20, 4)
    N = be(b, 0x50, 4)
    print("=" * 80)
    print("%s  size=%d  hs=0x%x rs=0x%x  N=%d  idx_len=%d" % (name, len(b), hs, rs, N, rs - hs))
    print("=" * 80)

    print("\n[raw hex 0x%x .. 0x%x]" % (hs, min(hs + 0x120, rs)))
    hexdump(b, hs, min(hs + 0x120, rs))

    print("\n[u32 BE @ hs+4k]")
    a = [be(b, p, 4) for p in range(hs, rs - 3, 4)]
    print("n=%d" % len(a))
    for i in range(0, len(a), 16):
        print("  %4d: %s" % (i, " ".join("%6d" % v for v in a[i:i + 16])))
    print("[u16 BE @ hs+2k] 前 64 + 后 40")
    a2 = [be(b, p, 2) for p in range(hs, rs - 1, 2)]
    print("n=%d" % len(a2))
    for i in range(0, min(len(a2), 64), 16):
        print("  %4d: %s" % (i, " ".join("%6d" % v for v in a2[i:i + 16])))
    print("  ...")
    for i in range(max(0, len(a2) - 40) // 16 * 16, len(a2), 16):
        print("  %4d: %s" % (i, " ".join("%6d" % v for v in a2[i:i + 16])))

    # 0x1F8 起单独看
    if rs > 0x1F8:
        print("\n[0x1F8 .. 0x%x raw hex]" % rs)
        hexdump(b, 0x1F8, min(0x1F8 + 0x80, rs))
        print("\n[0x1F8 .. 0x%x 当 u32 BE]" % rs)
        a3 = [(p, be(b, p, 4)) for p in range(0x1F8, rs - 3, 4)]
        print("n=%d" % len(a3))
        for i in range(0, len(a3), 16):
            print("  %4d: %s" % (i, " ".join("%6d" % v for _, v in a3[i:i + 16])))
        vals = [v for _, v in a3]
        if vals:
            print("min=%d max=%d 单调不减=%s 落[rs,str)=%s" %
                  (min(vals), max(vals),
                   all(vals[i] <= vals[i + 1] for i in range(len(vals) - 1)),
                   all(rs <= v < be(b, 0x24, 4) for v in vals)))


if __name__ == "__main__":
    for n in (sys.argv[1:] or ["njubase1.a"]):
        main(n)

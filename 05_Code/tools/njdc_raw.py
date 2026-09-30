# -*- coding: utf-8 -*-
"""njdc_raw.py —— 逐字节 dump 头部 0x00..0x54 与各区间边界，作为生成器的字面依据。"""
import os
import sys

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..",
                    "..", "01_Inputs", "firmware", "dat0805", "files", "Iwnn", "ZH", "CN", "pinyin", "GB18030")


def be(b, o, n):
    return int.from_bytes(b[o:o + n], "big")


def hexline(b, s, e, per=16):
    for p in range(s, e, per):
        print("    %08x  %-47s  |%s|" % (p, " ".join("%02x" % c for c in b[p:p + per]),
                                        "".join(chr(c) if 32 <= c < 127 else "." for c in b[p:p + per])))


def dump(name):
    b = open(os.path.join(BASE, name), "rb").read()
    hs, rs, pool, tst, N = be(b, 0x10, 4), be(b, 0x20, 4), be(b, 0x24, 4), be(b, 0x28, 4), be(b, 0x50, 4)
    print("=" * 100)
    print("%s  size=%d  hs=%d rs=%d pool=%d tail=%d N=%d  0x0c=%d 0x30=%d" %
          (name, len(b), hs, rs, pool, tst, N, be(b, 0x0c, 4), be(b, 0x30, 4)))
    print("=" * 100)
    print("  头部 0x00..0x54:")
    hexline(b, 0, hs)
    print("  索引区前半（前缀 9×u32）:")
    hexline(b, hs, hs + 36)
    print("  T 表尾 + 索引区末尾到 records 之间:")
    hexline(b, hs + 36 + 1024 - 16, min(rs + 16, len(b)))
    if rs > hs + 36 + 1024 + 16:
        print("  ...（rhythm 中间 %d 字节省略）" % (rs - (hs + 1060 + 16)))
    print("  记录表首 2 条:")
    hexline(b, rs, rs + 20)
    print("  记录表尾 2 条:")
    hexline(b, rs + 10 * N - 20, rs + 10 * N)
    print("  pool 起点:")
    hexline(b, pool, pool + 16)
    print("  tail 表首 32B:")
    hexline(b, tst, tst + 32)
    print("  tail 表尾 32B + 文件末尾 128B:")
    hexline(b, tst + 2 * (N + 2) - 32, tst + 2 * (N + 2))
    hexline(b, len(b) - 112, len(b))
    print("  一致性: 0x0c+0x30=%d  filesize=%d   2*(N+2)=%d  tail..0x0c=%d"
          % (be(b, 0x0c, 4) + be(b, 0x30, 4), len(b), 2 * (N + 2), be(b, 0x0c, 4) - tst))
    print()


if __name__ == "__main__":
    for n in (sys.argv[1:] or ["njubase1.a", "njtan.a", "njcode.a", "njubase3.a"]):
        dump(n)

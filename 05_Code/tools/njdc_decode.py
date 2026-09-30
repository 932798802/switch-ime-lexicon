#!/usr/bin/env python3
"""验证 NJDC 记录表字段假设：解码全部词条。

假设（由列特征推出）：
  @0 u16 LE = 读法长度(B)
  @2 u16 BE = 读法偏移（相对字符串池首）
  @4 u16 LE = 表记长度(B)
  @6 u16 BE = 表记偏移（相对字符串池首）
如果假设正确，解出的读法应几乎全是 ASCII 字母，表记应几乎全是 CJK 汉字。
"""
import os
import re
import sys

BASE = r"D:/proj/WorkBuddy/game mod/ns-ime/01_Inputs/firmware/dat0805/files/Iwnn"
TARGETS = [
    "ZH/CN/pinyin/GB18030/njubase1.a",
    "ZH/CN/pinyin/GB18030/njubase2.a",
    "ZH/CN/pinyin/GB18030/njubase3.a",
    "ZH/CN/pinyin/GB18030/njtan.a",
    "ZH/CN/pinyin/GB18030/njexyomi.a",
    "ZH/CN/pinyin/GB18030/njubase1.ad1",
    "KO/njubase1.a",
    "ZH/TW/bopomofo/njubase1.a",
]

CJK = re.compile(r"[\u3400-\u9fff\uf900-\ufaff]")
LAT = re.compile(r"^[A-Za-z'\-\u0100-\u024f ]*$")


def be(buf, o, w):
    return int.from_bytes(buf[o:o + w], "big")


def run(path, show=25):
    buf = open(path, "rb").read()
    magic = buf[:4]
    base = 0
    if magic == b"NJAD":
        base = buf.find(b"NJDC")
        print(f"  [NJAD 容器，内嵌 NJDC @0x{base:x}]")
    n = be(buf, base + 0x50, 4)
    rec_start = be(buf, base + 0x20, 4) + base
    str_start = be(buf, base + 0x24, 4) + base
    tail_start = be(buf, base + 0x28, 4) + base
    footer = buf.rfind(b"NJDC", base)
    pool = buf[str_start:tail_start]

    print(f"  N={n}  记录区 0x{rec_start:x}  池 0x{str_start:x}..0x{tail_start:x} "
          f"({len(pool)} B)")
    if rec_start + n * 10 > len(buf):
        print("  !! 记录区越界，参数不符")
        return

    ok_r = ok_t = bad = 0
    samples = []
    for i in range(n):
        p = rec_start + i * 10
        rlen = int.from_bytes(buf[p:p + 2], "little")
        roff = be(buf, p + 2, 2)
        tlen = int.from_bytes(buf[p + 4:p + 6], "little")
        toff = be(buf, p + 6, 2)
        if roff + rlen > len(pool) or toff + tlen > len(pool) or rlen == 0 or tlen == 0:
            bad += 1
            continue
        read = pool[roff:roff + rlen].decode("utf-16-be", errors="replace")
        word = pool[toff:toff + tlen].decode("utf-16-be", errors="replace")
        if LAT.match(read):
            ok_r += 1
        if word and all(CJK.match(c) for c in word):
            ok_t += 1
        if len(samples) < show:
            samples.append((i, roff, rlen, read, toff, tlen, word))

    print(f"  越界/异常 {bad} 条")
    print(f"  读法是纯拉丁字母 * {ok_r}/{n}（{ok_r / n * 100:.1f}%）")
    print(f"  表记全是 CJK 汉字 * {ok_t}/{n}（{ok_t / n * 100:.1f}%）")
    print("  样本:")
    for i, ro, rl, rd, to, tl, wd in samples:
        print(f"    #{i:<5} 读法@0x{ro:05x}+{rl:<3} {rd:<22} 表记@0x{to:05x}+{tl:<3} {wd}")


def main():
    for rel in TARGETS:
        p = os.path.join(BASE, rel)
        if not os.path.exists(p):
            print(f"!! 缺失 {rel}")
            continue
        print("=" * 84)
        print(rel, f"{os.path.getsize(p):,} B")
        run(p)
    return 0


if __name__ == "__main__":
    sys.exit(main())

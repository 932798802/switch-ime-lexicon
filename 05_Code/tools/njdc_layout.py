#!/usr/bin/env python3
"""dump NJDC 的关键区域，判断索引表结构（能否重建词典）。"""
import os
import sys

BASE = r"D:/proj/WorkBuddy/game mod/ns-ime/01_Inputs/firmware/dat0805/files/Iwnn"

PLAN = {
    "ZH/CN/pinyin/GB18030/njubase1.a": [
        (0x00, 0x60), (0x40, 0x100), (0x110, 0x100),
        (0x470, 0x60), (0x8750, 0xC0), (0x112D0, 0x60),
    ],
    "ZH/CN/pinyin/GB18030/njubase1.ad1": [
        (0x00, 0x60), (0x28, 0x60), (0x90, 0x120),
        (0x4E00, 0x60), (0x4E80, 0x60), (0x7700, 0x80),
    ],
}


def dump(buf, off, n):
    lines = []
    for i in range(off, min(off + n, len(buf)), 16):
        chunk = buf[i:i + 16]
        hx = " ".join(f"{c:02x}" for c in chunk)
        asc = "".join(chr(c) if 32 <= c < 127 else "." for c in chunk)
        lines.append(f"    {i:06x}  {hx:<47}  {asc}")
    return "\n".join(lines)


def main():
    for rel, regions in PLAN.items():
        p = os.path.join(BASE, rel)
        if not os.path.exists(p):
            print(f"!! 缺失 {rel}")
            continue
        buf = open(p, "rb").read()
        print("=" * 84)
        print(f"{rel}   size={len(buf):,}")
        # 头部字段速览（大端 u32）
        head0 = 0x28 if buf[:4] == b"NJAD" else 0x00
        print("  头字段:", " ".join(
            f"{o:02x}={int.from_bytes(buf[head0 + o:head0 + o + 4], 'big')}"
            for o in range(0x10, 0x54, 4) if head0 + o + 4 <= len(buf)))
        for off, n in regions:
            print(f"  --- {off:#x}..{off + n:#x} ---")
            print(dump(buf, off, n))


if __name__ == "__main__":
    sys.exit(main())

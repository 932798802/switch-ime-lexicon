#!/usr/bin/env python3
"""把 NJDC 记录表排成表格，用「列特征」定位偏移列 / 长度列 /
   并检验尾部 2 字节表。"""
import os
import sys

BASE = r"D:/proj/WorkBuddy/game mod/ns-ime/01_Inputs/firmware/dat0805/files/Iwnn"
PATH = os.path.join(BASE, "ZH/CN/pinyin/GB18030/njubase1.a")

REC = 10
SHOW = 40


def be(buf, o, w):
    return int.from_bytes(buf[o:o + w], "big")


def main():
    buf = open(PATH, "rb").read()
    n = be(buf, 0x50, 4)
    rec_start = be(buf, 0x20, 4)
    str_start = be(buf, 0x24, 4)
    tail_start = be(buf, 0x28, 4)
    footer = buf.rfind(b"NJDC")

    recs = [buf[rec_start + i * REC: rec_start + (i + 1) * REC] for i in range(n)]
    print(f"N={n}  记录区 {rec_start:#x}  池 {str_start:#x}  尾表 {tail_start:#x}  footer {footer:#x}")

    print("\n=== 前 %d 条记录，逐字节（大端解释）===" % SHOW)
    print("  #   " + "  ".join(f"{i:>4}" for i in range(REC)) + "   | u16BE 逐个")
    for i in range(SHOW):
        r = recs[i]
        xs = " ".join(f"{b:02x}" for b in r)
        u16 = " ".join(f"{int.from_bytes(r[j:j+2],'big'):5d}" for j in range(0, REC, 2))
        print(f"  {i:<3} {xs}   | {u16}")

    print("\n=== 各字节列的特征 ===")
    print(f"{'pos':>4} {'min':>7} {'max':>7} {'zeros':>6} {'even%':>7} {'单调递增':>9}")
    for pos in range(REC):
        col = [r[pos] for r in recs]
        mono = all(col[i] <= col[i + 1] for i in range(len(col) - 1))
        even = sum(1 for v in col if v % 2 == 0) / len(col) * 100
        print(f"{pos:>4} {min(col):>7} {max(col):>7} {col.count(0):>6} {even:>6.1f}% {str(mono):>9}")

    print("\n=== 所有 (pos,width,endian) 组合的特征 ===")
    print("（只列出「全为偶数」「单调」或「值域像偏移」的列）")
    stats = []
    for pos in range(REC):
        for w in (1, 2, 3, 4):
            if pos + w > REC:
                continue
            for endian in ("big", "little"):
                vals = [int.from_bytes(r[pos:pos + w], endian) for r in recs]
                mn, mx = min(vals), max(vals)
                mono = all(vals[i] <= vals[i + 1] for i in range(len(vals) - 1))
                all_even = all(v % 2 == 0 for v in vals)
                stats.append((pos, w, endian, mn, mx, mono, all_even, sum(vals)))
    for pos, w, endian, mn, mx, mono, all_even, s in stats:
        interesting = mono or (all_even and mx < 5000) or (49000 < s < 49200) or (35600 < s < 35900) \
                      or (13200 < s < 13400) or (6600 < s < 6700) or (17800 < s < 18000)
        if interesting:
            print(f"  [{pos}]w{w} {endian:>6}  min={mn:>6} max={mx:>6} sum={s:>7}  "
                  f"单调={'Y' if mono else 'n'} 全偶={'Y' if all_even else 'n'}")

    # 尾部表
    tail_n = (footer - tail_start) // 2
    tail = [int.from_bytes(buf[tail_start + i * 2: tail_start + i * 2 + 2], "big") for i in range(tail_n)]
    print(f"\n=== 尾部表（{tail_n} 项 × 2 B）===")
    print("  前 60 项(BE):", tail[:60])
    print(f"  min={min(tail)} max={max(tail)} sum={sum(tail)}")
    tail_le = [int.from_bytes(buf[tail_start + i * 2: tail_start + i * 2 + 2], "little") for i in range(tail_n)]
    print(f"  LE 解释: min={min(tail_le)} max={max(tail_le)} sum={sum(tail_le)}")
    print(f"  目标参考: 读法池 35718 / 表记池 13322 / 池总 49040")
    return 0


if __name__ == "__main__":
    sys.exit(main())

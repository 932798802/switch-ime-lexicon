#!/usr/bin/env python3
"""反向求解 NJDC 的 10 字节记录表字段布局。

核心思路（可判定）：
  如果记录表某列存的是「字符串长度」，那么 3351 条的长度之和
  必须精确等于字符串池的字节数（或字符数）。
  这给了我们一个极强的约束，可以穷举出正确字段位置。

已知（实测）：
  njubase1.a  N=3351（由 header[0x50] 给出，且被两个独立区间同时印证）
  header[0x20]=0x47A  记录表起始
  header[0x24]=0x8760  字符串池起始
  header[0x28]=0x146F0 尾部表起始
  记录区 = 0x8760-0x47A = 33510 = N*10        -> 每项 10 字节
  字符串池 = 0x146F0-0x8760 = 49040
  尾部表 = 0x1611E-0x146F0 = 6702 = N*2        -> 每项 2 字节
  观察：读法池(ASCII) 结束于 0x112E6，表记池(汉字) 从那里开始
          -> 读法池字节数 35718 (=2*17859)，表记池字节数 13322 (=2*6661)
"""
import os
import sys

BASE = r"D:/proj/WorkBuddy/game mod/ns-ime/01_Inputs/firmware/dat0805/files/Iwnn"
FILES = [
    "ZH/CN/pinyin/GB18030/njubase1.a",
    "ZH/CN/pinyin/GB18030/njubase2.a",
]

REC = 10


def be(buf, o, w):
    return int.from_bytes(buf[o:o + w], "big")


def analyze(path):
    buf = open(path, "rb").read()
    n = be(buf, 0x50, 4)
    rec_start = be(buf, 0x20, 4)
    str_start = be(buf, 0x24, 4)
    tail_start = be(buf, 0x28, 4)
    footer = buf.rfind(b"NJDC")

    print("=" * 78)
    print(f"{os.path.basename(path)}   size={len(buf):,}")
    print(f"  header: N={n}  rec={rec_start:#x}  str={str_start:#x}  tail={tail_start:#x}  footer={footer:#x}")

    rec_size = str_start - rec_start
    pool_size = tail_start - str_start
    tail_size = footer - tail_start
    print(f"  记录区 {rec_size} B  -> {rec_size / n:.4f} B/条")
    print(f"  字符串池 {pool_size} B")
    print(f"  尾部表 {tail_size} B -> {tail_size / n:.4f} B/条")

    if rec_size != n * REC:
        print("  !! 记录区不是 N*10，结论不适用本题")
        return

    recs = [buf[rec_start + i * REC: rec_start + (i + 1) * REC] for i in range(n)]

    # --- 强约束 1：找「长度列」---
    # 目标：读法池 35718/17859、表记池 13322/6661、合计 49040
    targets = {49040: "池总字节", 24520: "池总字符",
               35718: "读法池字节", 17859: "读法池字符",
               13322: "表记池字节", 6661: "表记池字符"}
    print("\n  --- 穷举「长度列」候选（某列之和 == 某个池尺寸）---")
    hits = []
    for pos in range(REC):
        for w in (1, 2, 3, 4):
            if pos + w > REC:
                continue
            for endian in ("big", "little"):
                vals = [int.from_bytes(r[pos:pos + w], endian) for r in recs]
                s = sum(vals)
                if s in targets:
                    hits.append((pos, w, endian, s, targets[s]))
                    print(f"    命中! 列@[{pos}] 宽{w} {endian:>6}  求和={s}  == {targets[s]}")
    if not hits:
        print("    （无命中——长度字段可能不是定宽整数，或需先做变换）")

    # --- 强约束 2：找「偏移列」---
    # 若长度列已知，则偏移列排序后应等于其前缀和
    print("\n  --- 对每个命中的长度列，搜「偏移列」---")
    for pos, w, endian, s, label in hits:
        lens = [int.from_bytes(r[pos:pos + w], endian) for r in recs]
        # 候选偏移列
        for opos in range(REC):
            for ow in (2, 3, 4):
                if opos + ow > REC or (opos < pos + w and pos < opos + ow):
                    continue
                for oend in ("big", "little"):
                    offs = [int.from_bytes(r[opos:opos + ow], oend) for r in recs]
                    pair = sorted(zip(offs, lens))
                    # 完美划分检验：offsets 必须是 lengths 的前缀和
                    cur = 0
                    ok = True
                    for o, l in pair:
                        if o != cur:
                            ok = False
                            break
                        cur += l
                    if ok and cur == s:
                        print(f"    完美划分! 长度=[{pos}]w{w}{endian} 偏移=[{opos}]w{ow}{oend}  ({label})")
    return n, recs


def main():
    for f in FILES:
        p = os.path.join(BASE, f)
        if os.path.exists(p):
            analyze(p)
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""探测 iWnn 的 NJDC 词典文件：头部字段、字符串池、词条可读性。

用来回答「第三方词库能不能塞进去」——关键是判断这些文件是
    (a) 纯词表（词 → 读法）结构（可重建）
    (b) 带 trie / 哈希索引的编译产物（难重建）
"""
import os
import re
import sys

BASE = r"D:/proj/WorkBuddy/game mod/ns-ime/01_Inputs/firmware/dat0805/files/Iwnn"

TARGETS = [
    "ZH/CN/pinyin/GB18030/njubase1.a",
    "ZH/CN/pinyin/GB18030/njubase1.ad1",
    "ZH/CN/pinyin/GB18030/njubase2.a",
    "ZH/CN/pinyin/GB18030/njubase3.a",
    "ZH/CN/pinyin/GB18030/njtan.a",
    "ZH/CN/pinyin/GB18030/njexyomi.a",
    "ZH/CN/pinyin/GB18030/njcode.a",
    "ZH/CN/njcon.a",
    "KO/njubase1.a",
    "ZH/TW/bopomofo/njubase1.a",
]


def hexdump(buf, n=80):
    lines = []
    for i in range(0, min(n, len(buf)), 16):
        chunk = buf[i:i + 16]
        hx = " ".join(f"{c:02x}" for c in chunk)
        asc = "".join(chr(c) if 32 <= c < 127 else "." for c in chunk)
        lines.append(f"    {i:04x}  {hx:<47}  {asc}")
    return "\n".join(lines)


RUN_RE = re.compile(r"[\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af\u3100-\u312f"
                    r"A-Za-z0-9\u00c0-\u024f]{2,}")


def utf16_runs(buf, endian, minlen=2):
    """按指定端序解码后找连续「可读」串，返回 (字节偏移, 串)。"""
    txt = buf.decode(f"utf-16-{endian}", errors="replace")
    out = []
    for m in RUN_RE.finditer(txt):
        if len(m.group()) >= minlen:
            out.append((m.start() * 2, m.group()))
    return out


def probe(rel):
    path = os.path.join(BASE, rel)
    if not os.path.exists(path):
        print(f"  !! 缺失 {rel}")
        return
    buf = open(path, "rb").read()
    print("=" * 80)
    print(f"{rel}    size = {len(buf):,} B")
    print("  头部:")
    print(hexdump(buf, 64))

    # NJDC magic 位置
    positions = [m.start() for m in re.finditer(rb"NJDC", buf)]
    print(f"  'NJDC' 出现位置: {[hex(p) for p in positions[:10]]}"
          f"{f' (共 {len(positions)} 处)' if len(positions) > 10 else ''}")

    # 头部关键字段（GBATEK 口径，大端）
    if len(buf) >= 0x14:
        be = lambda o, n: int.from_bytes(buf[o:o + n], "big")
        le = lambda o, n: int.from_bytes(buf[o:o + n], "little")
        print(f"  字段(大端): 0x04={be(4,2)} 0x06={be(6,2)} 0x08={be(8,2)} "
              f"0x0A={be(10,2)} 0x0C={be(12,4)} (文件长={len(buf)}) 0x10={be(16,4)}")
        print(f"  字段(小端): 0x04={le(4,2)} 0x06={le(6,2)} 0x08={le(8,2)} "
              f"0x0A={le(10,2)} 0x0C={le(12,4)} 0x10={le(16,4)}")

    for endian in ("le", "be"):
        runs = utf16_runs(buf, endian, 2)
        if not runs:
            print(f"  UTF-16-{endian.upper()} 可读串: 0")
            continue
        # 只统计 CJK 为主的串
        cjk = [(o, s) for o, s in runs
               if sum(1 for c in s if '\u4e00' <= c <= '\u9fff' or
                      '\u3040' <= c <= '\u30ff' or
                      '\uac00' <= c <= '\ud7af') >= 2]
        print(f"  UTF-16-{endian.upper()}: 可读串 {len(runs)} 个，"
              f"其中 CJK 串 {len(cjk)} 个；"
              f"位置范围 0x{runs[0][0]:x}–0x{runs[-1][0]:x}")
        for o, s in runs[:25]:
            print(f"      [0x{o:06x}] {s[:60]}")
        if cjk:
            print("    --- CJK 样本（前 25 条）---")
            for o, s in cjk[:25]:
                print(f"      [0x{o:06x}] {s[:60]}")


def main():
    for rel in TARGETS:
        probe(rel)
    return 0


if __name__ == "__main__":
    sys.exit(main())

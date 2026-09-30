#!/usr/bin/env python3
"""按 GBATEK 的 NJDC 描述解析词条表，验证词典内容是否可读、可重建。

GBATEK（3DS NJDC）关键线索：
  - 全部大端
  - 10-byte Table 每项: [1B 字符串长度(偶数)] [3B 字符串偏移(相对字符串表)] [6B 零填充]
      -> 「后 6 字节全 0」是很强的指纹，可以用来定位词条表
  - 字符串是无结尾零的 UTF-16
本脚本用该指纹在文件里搜词条表，再据此把词条抽出来。
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
    "ZH/CN/pinyin/GB18030/njcode.a",
    "ZH/CN/pinyin/GB18030/njubase1.ad1",
    "ZH/CN/njcon.a",
    "ZH/TW/bopomofo/njubase1.a",
    "KO/njubase1.a",
]

# 10 字节项：长度(1, 偶数) + 偏移(3) + 6 个零；要求连续 >= 8 项
ENTRY_PAT = re.compile(rb"(?:[\x02-\xfe][\x00-\x0f][\x00-\xff][\x00-\xff]\x00{6}){8,}")


def be32(b, o):
    return int.from_bytes(b[o:o + 4], "big")


def norm_endian(x):
    """小端字节序文件也兼容：若 >= 文件长则尝试反转。"""
    return x


def header_fields(buf, limit=0x54):
    out = []
    for o in range(0x04, limit, 4):
        out.append((o, be32(buf, o)))
    return out


def decode_str(buf, off, byte_len, endian="be"):
    raw = buf[off:off + byte_len]
    try:
        if endian == "be":
            return raw.decode("utf-16-be", errors="replace")
        return raw.decode("utf-16-le", errors="replace")
    except Exception:
        return "?"


def scan_entry_tables(buf):
    """返回 [(表起始偏移, 项数, 项模式字节数)]"""
    res = []
    for m in ENTRY_PAT.finditer(buf):
        # 尽量向右延伸
        start = m.start()
        n = len(m.group()) // 10
        res.append((start, n))
    return res


def probe(rel):
    path = os.path.join(BASE, rel)
    if not os.path.exists(path):
        print(f"  !! 缺失 {rel}")
        return
    buf = open(path, "rb").read()
    print("=" * 84)
    print(f"{rel}    size = {len(buf):,} B")

    magic = buf[:4]
    print(f"  magic = {magic!r}   "
          f"{'（NJDC 主词典）' if magic == b'NJDC' else '（NJAD 追加词典容器）' if magic == b'NJAD' else '（未知）'}")

    base = 0
    if magic == b"NJAD":
        print("  --- NJAD 容器头 ---")
        for o in range(0x04, 0x28, 4):
            print(f"      0x{o:02x} = {be32(buf, o)}  (0x{be32(buf, o):x})")
        njdc_at = buf.find(b"NJDC")
        print(f"  内嵌 NJDC 位于 0x{njdc_at:x}")
        base = njdc_at

    print("  --- NJDC 头字段（大端 u32，0x10 起） ---")
    offs = []
    for o, v in header_fields(buf, 0x54):
        if base and o < 0x10:
            continue
        mark = ""
        if o > base and v < len(buf) and v > 0x40:
            mark = "  <- 像是偏移/长度"
            offs.append((o, v))
        print(f"      0x{o:02x} = {v:>10}  (0x{v:x}){mark}")

    print("  --- 10 字节词条表候选（连续 >= 8 项） ---")
    tables = scan_entry_tables(buf)
    if not tables:
        print("      无")
    for start, n in tables[:8]:
        print(f"      @0x{start:x}  项数≈{n}  覆盖 0x{start:x}–0x{start + n * 10:x}")

    # 用最大的表抽词条
    if tables:
        start, n = max(tables, key=lambda t: t[1])
        # 字符串表基址：取 header 里那个最像的（0x24）
        strbase = be32(buf, 0x24) if base == 0 else be32(buf, base + 0x24)
        print(f"  --- 试着用字符串表基址 0x{strbase:x} 抽词条（前者 {min(n, 40)} 条） ---")
        ok = 0
        for i in range(min(n, 40)):
            p = start + i * 10
            slen = buf[p]
            soff = int.from_bytes(buf[p + 1:p + 4], "big")
            if slen == 0:
                continue
            for endian in ("be", "le"):
                s = decode_str(buf, strbase + soff, slen, endian)
                if s and any('\u4e00' <= c <= '\u9fff' or
                             '\u3040' <= c <= '\u30ff' or
                             '\uac00' <= c <= '\ud7af' or
                             c.isalnum() for c in s):
                    print(f"      #{i:<4} len={slen:<4} off=0x{soff:06x} [{endian}] {s[:50]}")
                    ok += 1
                    break
        print(f"      可解出 {ok} 条")

    # 直接找 UTF-16BE 汉字串（若字符串表混装读法与表记）
    print("  --- 直接扫 UTF-16BE 汉字串（前 20） ---")
    text = buf.decode("utf-16-be", errors="replace")
    cnt = 0
    for m in re.finditer(r"[\u4e00-\u9fff]{2,}", text):
        cnt += 1
        if cnt <= 20:
            print(f"      [0x{m.start()*2:06x}] {m.group()[:50]}")
    print(f"      UTF-16BE 汉字串合计 {cnt} 条")


def main():
    for rel in TARGETS:
        probe(rel)
    return 0


if __name__ == "__main__":
    sys.exit(main())

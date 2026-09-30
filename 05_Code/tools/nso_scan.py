#!/usr/bin/env python3
"""扫 swkbd main 的三个段，找词典 / fs API / title id 证据。

用来判定 swkbd 打开 iWnn 词典走的是哪条 fs 路径：
  - 走 OpenDataStorageByDataId  -> Atmosphere LayeredFS（atmosphere/contents/<id>/romfs）可覆盖
  - 走 OpenFileSystemWithId     -> fs.mitm 只处理 manual html，romfs 覆盖不生效
"""
import os
import re
import sys

ROOT = r"D:/proj/WorkBuddy/ns-ime/out/c65a992ef0d3b7c3e5fd1daecb63c6b0/nso"
FILES = ["main.text.bin", "main.rodata.bin", "main.data.bin"]

# 严格关键词：避免 "fs" / "Data" 这类泛词刷屏
KW = [
    "dic://", "Iwnn", "iwnn", "IWN", "njx", "NJDC", "njdc",
    "fsp-srv", "fsp:", "MountRom", "OpenDataStorage", "OpenFileSystem",
    "romfs", "RomFs", "Romfs", "ncm", "DataId", "dataId",
    "bopomofo", "pinyin", "cangjie", "jyutping",
]

TITLE_IDS = {
    "swkbd 0100000000001008 (自身)": 0x0100000000001008,
    "Data  0100000000000805 (ZH/KO)": 0x0100000000000805,
    "Data  0100000000000808 (JA/EU)": 0x0100000000000808,
    "Data  0100000000000809": 0x0100000000000809,
    "Data  010000000000080A": 0x010000000000080A,
}


def ascii_strings(buf, minlen=4):
    for m in re.finditer(rb"[\x20-\x7e]{%d,}" % minlen, buf):
        yield m.start(), m.group().decode("ascii", "replace")


def utf16_strings(buf, minlen=4):
    for m in re.finditer(rb"(?:[\x20-\x7e]\x00){%d,}" % minlen, buf):
        yield m.start(), m.group().decode("utf-16-le", "replace")


def main():
    kw_lower = [k.lower() for k in KW]
    for fn in FILES:
        path = os.path.join(ROOT, fn)
        if not os.path.exists(path):
            print(f"!! 缺失 {path}")
            continue
        buf = open(path, "rb").read()
        print("=" * 78)
        print(f"{fn}   size = {len(buf):,} B")

        print("--- title id 字节序列（找硬编码的词典 title） ---")
        for name, tid in TITLE_IDS.items():
            le = tid.to_bytes(8, "little")
            be = tid.to_bytes(8, "big")
            le_hits = [m.start() for m in re.finditer(re.escape(le), buf)]
            be_hits = [m.start() for m in re.finditer(re.escape(be), buf)]
            flag = "  <<<" if (le_hits or be_hits) else ""
            print(f"  {name:34s} LE={len(le_hits):3d} {[hex(x) for x in le_hits[:6]]}"
                  f"  BE={len(be_hits):3d} {[hex(x) for x in be_hits[:6]]}{flag}")

        print("--- 关键词字符串 ---")
        seen = set()
        n = 0
        for kind, gen in (("A", ascii_strings(buf)), ("U", utf16_strings(buf))):
            for off, s in gen:
                low = s.lower()
                if not any(k in low for k in kw_lower):
                    continue
                key = (kind, s)
                if key in seen:
                    continue
                seen.add(key)
                n += 1
                if n <= 120:
                    print(f"  [{kind}] 0x{off:08x}  {s[:140]}")
        if n > 120:
            print(f"  ... 共 {n} 条，已截断")
        if n == 0:
            print("  （无命中）")


if __name__ == "__main__":
    sys.exit(main())

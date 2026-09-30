#!/usr/bin/env python3
"""在 swkbd 的 NSO 段里搜指定关键词，判断 iWnn 是否要读「外部词典文件」。

用法:
    python nso_kw.py [关键词 ...]
不给关键词则用内置的「词典体系」关键词表。
"""
import os
import re
import sys

ROOT = r"D:/proj/WorkBuddy/ns-ime/out/c65a992ef0d3b7c3e5fd1daecb63c6b0/nso"
FILES = ["main.text.bin", "main.rodata.bin", "main.data.bin"]

DEFAULT_KW = [
    # 用户词典 / 学习词典
    "njuser", "njusr", "usrdic", "userdic", "user_dict", "userdict", "UserDict",
    "learning", "Learning", "ujisyo", "ujisyuu",
    # 追加 / 外部词典
    "njaddon", "addon", "add_dic", "adddic", "additional", "addition", "njadd",
    "wdic", ".dic", ".dtd", "njexyomi", "njubase", "njtan", "njcon", "njcode",
    "njstroke", "njcangjie", "njtrans",
    # iWnn API 前缀 / 引擎内部
    "njx_", "njx", "nj_lib", "njlib", "NJ_LIB",
    # 词典种类关键词（对照 Programming Manual 的 8 类）
    "ancillary", "customized", "integration", "integrated",
    # 挂载 / 路径
    "dic://", "dic2://", "dic3://", "Iwnn",
]


def ascii_strings(buf, minlen=3):
    for m in re.finditer(rb"[\x20-\x7e]{%d,}" % minlen, buf):
        yield m.start(), m.group().decode("ascii", "replace")


def utf16_strings(buf, minlen=3):
    for m in re.finditer(rb"(?:[\x20-\x7e]\x00){%d,}" % minlen, buf):
        yield m.start(), m.group().decode("utf-16-le", "replace")


def main():
    kws = sys.argv[1:] or DEFAULT_KW
    kws_l = [k.lower() for k in kws]
    for fn in FILES:
        path = os.path.join(ROOT, fn)
        if not os.path.exists(path):
            continue
        buf = open(path, "rb").read()
        print("=" * 78)
        print(f"{fn}   ({len(buf):,} B)   关键词: {len(kws)} 个")
        seen = set()
        n = 0
        for kind, gen in (("A", ascii_strings(buf)), ("U", utf16_strings(buf))):
            for off, s in gen:
                low = s.lower()
                hit = [k for k in kws_l if k in low]
                if not hit:
                    continue
                key = (kind, s)
                if key in seen:
                    continue
                seen.add(key)
                n += 1
                if n <= 150:
                    print(f"  [{kind}] 0x{off:08x}  {s[:130]}    <- {','.join(hit[:3])}")
        if n == 0:
            print("  （无命中）")
        elif n > 150:
            print(f"  ... 共 {n} 条（已截断）")


if __name__ == "__main__":
    sys.exit(main())

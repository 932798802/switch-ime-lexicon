# -*- coding: utf-8 -*-
"""patch_ad1.py —— 把新 .a 的头部同步进配套 .ad1 内嵌的头副本。

NJAD(.ad1) 头部 0x28 起存放一份与配套 .a 逐字节相同的 NJDC 头部（0x54 字节）。
替换 .a 后，若引擎用这份副本做一致性校验，就会看到过期数值。
本脚本把新 .a 的头部复制进去，其余字节原样保留。

用法:  python patch_ad1.py <新 njubase3.a> <原 njubase3.ad1> <输出 njubase3.ad1>
注意:  这是**推测性**修补 —— .ad1 的其余语义尚未解出。默认部署方案并不覆盖 .ad1。
"""
import sys

HEAD = 0x54
EMB = 0x28


def main():
    a_new, ad1_in, ad1_out = sys.argv[1], sys.argv[2], sys.argv[3]
    new = open(a_new, "rb").read()
    old = bytearray(open(ad1_in, "rb").read())
    assert old[:4] == b"NJAD", "输入不是 NJAD"
    assert old[EMB:EMB + 4] == b"NJDC", "0x28 处没有内嵌 NJDC 头"
    before = bytes(old[EMB:EMB + HEAD])
    after = new[:HEAD]
    old[EMB:EMB + HEAD] = after
    open(ad1_out, "wb").write(bytes(old))
    diff = sum(1 for x, y in zip(before, after) if x != y)
    print("  .ad1 内嵌头: 同步 %d 字节（差异 %d 字节）→ %s" % (HEAD, diff, ad1_out))
    print("     新 0x0c=%d  0x20=%d  0x24=%d  0x28=%d  0x50=%d"
          % (int.from_bytes(after[0x0c:0x10], "big"), int.from_bytes(after[0x20:0x24], "big"),
             int.from_bytes(after[0x24:0x28], "big"), int.from_bytes(after[0x28:0x2c], "big"),
             int.from_bytes(after[0x50:0x54], "big")))


if __name__ == "__main__":
    main()

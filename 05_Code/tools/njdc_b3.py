# -*- coding: utf-8 -*-
"""njdc_b3.py —— 暴力搜索 njubase3 的记录布局（用「读法必须是 ASCII / 表记必须是 CJK」做评分）。"""
import os
import struct
from itertools import product

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..",
                    "..", "01_Inputs", "firmware", "dat0805", "files", "Iwnn", "ZH", "CN", "pinyin", "GB18030")

NAME = "njubase3.a"
b = open(os.path.join(BASE, NAME), "rb").read()


def be(o, n):
    return int.from_bytes(b[o:o + n], "big")


def le(o, n):
    return int.from_bytes(b[o:o + n], "little")


RS = be(0x20, 4)
POOL = be(0x24, 4)
N = be(0x50, 4)
POOL_LEN = be(0x28, 4) - POOL
print("rs=0x%x pool=0x%x pool_len=%d N=%d" % (RS, POOL, POOL_LEN, N))


def is_ascii_letters(s):
    return len(s) > 0 and all(('a' <= c <= 'z') or ('A' <= c <= 'Z') for c in s)


def is_cjk(s):
    return len(s) > 0 and all(0x2E80 <= ord(c) <= 0x9FFF or 0xF900 <= ord(c) <= 0xFAFF
                              or 0xFF00 <= ord(c) <= 0xFFEF or 0x3000 <= ord(c) <= 0x303F
                              or 0x4E00 <= ord(c) <= 0x9FFF or 0x20000 <= ord(c) <= 0x3FFFF
                              for c in s)


def get(off, length, base):
    a = base + off
    if length <= 0 or length > 200 or off < 0 or a + length > len(b):
        return None
    raw = b[a:a + length]
    if length % 2:
        return None
    try:
        return raw.decode("utf-16-be")
    except Exception:
        return None


def score(layout, base):
    """layout: list of (name, offset, size, endian)"""
    good_r = good_w = 0
    tot = 0
    for i in range(0, min(N, 400)):
        p = RS + i * 10
        vals = {}
        ok = True
        for (nm, off, size, end) in layout:
            v = b[p + off:p + off + size]
            if len(v) < size:
                ok = False; break
            vals[nm] = int.from_bytes(v, end)
        if not ok:
            continue
        tot += 1
        r = get(vals["roff"], vals["rlen"], base)
        w = get(vals["toff"], vals["tlen"], base)
        if r and is_ascii_letters(r):
            good_r += 1
        if w and is_cjk(w):
            good_w += 1
    if tot == 0:
        return 0, 0, 0
    return good_r / tot, good_w / tot, tot


def main():
    cands = []
    # 常见 2+2+2+2 排列
    for order in product([("rlen", 0), ("roff", 2), ("tlen", 4), ("toff", 6)], repeat=1):
        pass
    # 枚举: rlen/roff/tlen/toff 放在 4 个 2 字节槽 [0,2,4,6]，各自选端序
    import itertools
    slots = [0, 2, 4, 6]
    base_opts = [POOL]
    for perm in itertools.permutations(slots):
        names = ["rlen", "roff", "tlen", "toff"]
        for ends in product(["big", "little"], repeat=4):
            layout = list(zip(names, perm, [2, 2, 2, 2], ends))
            for base in base_opts:
                gr, gw, tot = score(layout, base)
                cands.append((gr + gw, gr, gw, layout, base))
    # u8 tlen + u24 toff
    for toff_end in ("big", "little"):
        for tlen_at in (4,):
            layout = [("rlen", 0, 2, "little"), ("roff", 2, 2, "big"),
                      ("tlen", 4, 1, "little"), ("toff", 5, 3, toff_end)]
            gr, gw, tot = score(layout, POOL)
            cands.append((gr + gw, gr, gw, layout, POOL))
    # roff u24 @2, tlen u8 @5, toff u16 @6
    for rend in ("big", "little"):
        layout = [("rlen", 0, 2, "little"), ("roff", 2, 3, rend),
                  ("tlen", 5, 1, "little"), ("toff", 6, 2, "big")]
        gr, gw, tot = score(layout, POOL)
        cands.append((gr + gw, gr, gw, layout, POOL))

    cands.sort(reverse=True)
    seen = set()
    for s, gr, gw, layout, base in cands[:400]:
        key = str(layout) + str(base)
        if key in seen:
            continue
        seen.add(key)
        print("得分=%.3f  读法OK=%.3f 表记OK=%.3f  base=0x%x  %s"
              % (s, gr, gw, base, [(n, o, sz, e) for n, o, sz, e in layout]))
        if s > 1.5:
            break


if __name__ == "__main__":
    main()

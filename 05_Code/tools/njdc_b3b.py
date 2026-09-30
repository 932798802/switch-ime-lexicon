# -*- coding: utf-8 -*-
"""njdc_b3b.py —— 更广的 njubase3 记录布局搜索（含 u24/u32 变体）。"""
import os
import itertools

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..",
                    "..", "01_Inputs", "firmware", "dat0805", "files", "Iwnn", "ZH", "CN", "pinyin", "GB18030")
b = open(os.path.join(BASE, "njubase3.a"), "rb").read()


def be(o, n):
    return int.from_bytes(b[o:o + n], "big")


RS = be(0x20, 4); POOL = be(0x24, 4); N = be(0x50, 4)
POOL_LEN = be(0x28, 4) - POOL
TEST = 3000
print("rs=0x%x pool=0x%x pool_len=%d N=%d" % (RS, POOL, POOL_LEN, N))


def is_letters(s):
    return len(s) > 0 and all('a' <= c <= 'z' for c in s)


def is_cjk(s):
    return len(s) > 0 and all(0x2E80 <= ord(c) <= 0xA4CF or 0xFF00 <= ord(c) <= 0xFFEF
                              or 0x4E00 <= ord(c) <= 0x9FFF or 0x20000 <= ord(c) <= 0x3FFFF
                              or 0x3000 <= ord(c) <= 0x303F or 0xFE30 <= ord(c) <= 0xFE4F
                              for c in s)


def dec(off, length, base):
    a = base + off
    if length <= 0 or length > 300 or off < 0 or a + length > len(b) or length % 2:
        return None
    try:
        return b[a:a + length].decode("utf-16-be")
    except Exception:
        return None


def score(layout, base):
    gr = gw = tot = 0
    for i in range(TEST):
        p = RS + i * 10
        try:
            v = {}
            for (nm, off, size, end) in layout:
                v[nm] = int.from_bytes(b[p + off:p + off + size], end)
        except Exception:
            continue
        tot += 1
        r = dec(v["roff"], v["rlen"], base)
        w = dec(v["toff"], v["tlen"], base)
        if r and is_letters(r):
            gr += 1
        if w and is_cjk(w):
            gw += 1
    return (gr / tot, gw / tot, tot) if tot else (0, 0, 0)


def main():
    res = []
    # 布局模板: 名称顺序固定 rlen,roff,tlen,toff（可含 pad），枚举起点与宽度
    width_opts = {"rlen": [2], "roff": [2, 3, 4], "tlen": [1, 2], "toff": [2, 3, 4]}
    names = ["rlen", "roff", "tlen", "toff"]
    for ws in itertools.product(*[width_opts[n] for n in names]):
        total_w = sum(ws)
        if total_w > 10:
            continue
        pad_pos = [10 - total_w]  # 尾随 pad
        # 构造偏移
        offs = []
        cur = 0
        for w in ws:
            offs.append((cur, w))
            cur += w
        for ends in itertools.product(["big", "little"], repeat=4):
            layout = [(names[k], offs[k][0], offs[k][1], ends[k]) for k in range(4)]
            gr, gw, tot = score(layout, POOL)
            res.append((gr + gw, gr, gw, layout, POOL))
    # 也试「roff/toff 相对 rs 或文件头」
    for base in (0, POOL, RS):
        pass
    res.sort(reverse=True)
    seen = set()
    shown = 0
    for s, gr, gw, layout, base in res:
        key = str(layout)
        if key in seen:
            continue
        seen.add(key)
        print("得分=%.4f 读法=%.4f 表记=%.4f base=0x%x  %s" % (s, gr, gw, base, layout))
        shown += 1
        if shown >= 10:
            break

    # 用最优布局看几个样本
    best = res[0][3]
    base = res[0][4]
    print("\n--- 最优布局样本 ---")
    for i in range(30):
        p = RS + i * 10
        v = {nm: int.from_bytes(b[p + off:p + off + sz], end) for (nm, off, sz, end) in best}
        r = dec(v["roff"], v["rlen"], base)
        w = dec(v["toff"], v["tlen"], base)
        print("  i=%-4d rlen=%-4d roff=%-7d tlen=%-3d toff=%-7d | %-14s %s"
              % (i, v["rlen"], v["roff"], v["tlen"], v["toff"], r, w))
    # 统计失败原因
    bad = 0
    for i in range(TEST):
        p = RS + i * 10
        v = {nm: int.from_bytes(b[p + off:p + off + sz], end) for (nm, off, sz, end) in best}
        r = dec(v["roff"], v["rlen"], base)
        if not (r and is_letters(r)):
            bad += 1
    print("\n  读法失败 %d / %d" % (bad, TEST))


if __name__ == "__main__":
    main()

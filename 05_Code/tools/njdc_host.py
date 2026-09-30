# -*- coding: utf-8 -*-
"""njdc_host.py —— 对给定池偏移，dump 其周边字节并标出宿主串，判定共享规则。"""
import os
import sys

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..",
                    "..", "01_Inputs", "firmware", "dat0805", "files", "Iwnn", "ZH", "CN", "pinyin", "GB18030")


def be(b, o, n):
    return int.from_bytes(b[o:o + n], "big")


def load(name):
    b = open(os.path.join(BASE, name), "rb").read()
    rs, pool, tst, N = be(b, 0x20, 4), be(b, 0x24, 4), be(b, 0x28, 4), be(b, 0x50, 4)
    recs = []
    for i in range(N):
        p = rs + i * 10
        rl, ro, tl, to = b[p], be(b, p + 1, 3), b[p + 4], be(b, p + 5, 3)
        recs.append((b[pool + ro:pool + ro + rl].decode("utf-16-be", "replace"), ro, rl,
                     b[pool + to:pool + to + tl].decode("utf-16-be", "replace"), to, tl))
    return b, recs, pool, tst, rs, N


def show(name, offs, back=48, fwd=64):
    b, recs, pool, tst, rs, N = load(name)
    print("=" * 96)
    print("%s  pool=%d..%d" % (name, pool, tst))
    print("=" * 96)
    for o in offs:
        s = max(0, o - back)
        seg = b[pool + s:pool + o + fwd]
        try:
            txt = seg.decode("utf-16-be", "replace")
        except Exception:
            txt = seg.hex()
        print("\n  偏移 %d （前 %d 字节起于 %d）" % (o, s, pool + s))
        print("    ascii-view(去零): %s" % txt.replace("\x00", ""))
        print("    host window     : %r" % txt)
        print("            ^ 目标位于窗口字符位 %d" % ((o - s) // 2))
    print()


def batch(name="njubase1.a"):
    b, recs, pool, tst, rs, N = load(name)
    # 找出所有「落在其它串内部」的 roff：即存在 roff < o < roff+rlen 的更大区间
    ivals = []
    for r in recs:
        ivals.append((r[1], r[1] + r[2], r[0]))
    ivals.sort()
    # 合并成不重叠的「宿主区间」（记录中出现的最大跨度）
    # 用所有起点排序后，用贪心：若 o 落在 [start,end) 且 o!=start 则共享
    starts = {}
    for s, e, r in ivals:
        if s not in starts or e > starts[s][0]:
            starts[s] = (e, r)
    shared = []
    for r in recs:
        o = r[1]
        if o in starts and o == starts[o][0] - r[2]:
            continue
        # 找到包含 o 的宿主（start < o < end）
        host = None
        for s, e, _r in ivals:
            if s < o < e:
                host = (s, e, _r)
                break
        shared.append((r[0], o, r[2], host))
    print("%s: 共 %d 条，其中 %d 条 roff 落在别的串内部（前缀/后缀共享）" %
          (name, N, len(shared)))
    for r, o, l, h in shared[:25]:
        print("   %-22s roff=%-6d len=%-3d 宿主=[%d,%d) '%s'" %
              (r, o, l, h[0], h[1], h[2]) if h else "   %-22s roff=%d 无宿主" % (r, o))
    print()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "batch":
        batch(sys.argv[2] if len(sys.argv) > 2 else "njubase1.a")
    else:
        name = sys.argv[1] if len(sys.argv) > 1 else "njubase1.a"
        offs = [int(x) for x in sys.argv[2:]] or [10268, 8680, 4456, 2488, 106, 30738, 20968]
        show(name, offs)

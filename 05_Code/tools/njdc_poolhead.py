# -*- coding: utf-8 -*-
"""njdc_poolhead.py —— dump 字符串池头部内容，用以判定池的排序/共享规则。"""
import os
import sys

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..",
                    "..", "01_Inputs", "firmware", "dat0805", "files", "Iwnn", "ZH", "CN", "pinyin", "GB18030")


def be(b, o, n):
    return int.from_bytes(b[o:o + n], "big")


def decode(name, head=1400):
    b = open(os.path.join(BASE, name), "rb").read()
    rs, pool, tst, N = be(b, 0x20, 4), be(b, 0x24, 4), be(b, 0x28, 4), be(b, 0x50, 4)
    recs = []
    for i in range(N):
        p = rs + i * 10
        recs.append((b[p], be(b, p + 1, 3), b[p + 4], be(b, p + 5, 3)))

    offs = sorted(set([r[1] for r in recs] + [r[3] for r in recs]))
    print("=" * 90)
    print("%s  N=%d  pool=[0x%x,0x%x) len=%d  tail=0x%x" % (name, N, pool, tst, tst - pool, tst))
    print("=" * 90)

    # 池头按「可能的串边界」切分：把所有出现过的偏移排序，逐段解码
    segs = [o for o in offs if o < head]
    print("  池头 %d 字节内出现的偏移数=%d，前 40 个: %s" % (head, len(segs), segs[:40]))
    print()
    prev = None
    for o in segs[:50]:
        # 该偏移处开始的串（取到下一个偏移）
        nxt = None
        for o2 in offs:
            if o2 > o:
                nxt = o2
                break
        end = nxt if nxt is not None else o + 40
        raw = b[pool + o:pool + min(end, len(b) - pool)]
        try:
            s = raw.decode("utf-16-be")
        except Exception:
            s = raw.hex()
        n = (end - o) // 2
        # 也看看这一段的原始十六进制
        print("  off=%-6d len=%-4d %-28r  hex=%s" %
              (o, end - o, s, b[pool + o:pool + min(o + 24, end)].hex(" ")))
    print()
    print("  池最前 64 字节 hex: %s" % b[pool:pool + 64].hex(" "))
    try:
        print("  池最前 64 字节 utf16be: %r" % b[pool:pool + 64].decode("utf-16-be"))
    except Exception as e:
        print("  解码失败: %s" % e)
    print("  第一条记录: rlen=%d roff=%d tlen=%d toff=%d" % recs[0])
    print("  最后一条记录: rlen=%d roff=%d tlen=%d toff=%d" % recs[-1])
    maxr = max(r[1] + r[0] for r in recs)
    mint = min(r[3] for r in recs)
    print("  读法区假设 [0,%d)  表记区假设 [%d,%d)" % (maxr, mint, tst - pool))
    # 读法池内前 20 个偏移处的串
    print()
    print("  读法池前 20 个偏移:")
    seen = []
    for r in recs:
        if r[1] not in seen:
            seen.append(r[1])
        if len(seen) >= 20:
            break
    for o in seen:
        s = b[pool + o:pool + o + 40].decode("utf-16-be", "replace")
        # 截到遇到下一个已知偏移
        print("    %-6d %r" % (o, s[:20]))
    return b, recs, pool, tst, N


if __name__ == "__main__":
    for n in (sys.argv[1:] or ["njubase1.a"]):
        decode(n)
        print()

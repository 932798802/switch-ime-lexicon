# -*- coding: utf-8 -*-
"""njdc_locate.py —— 用「T 表内容可计算」这一点，在文件里搜索 T 表位置，反推前缀长度。
   同时 dump njubase3 的记录表与附加表。"""
import os
import sys

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..",
                    "..", "01_Inputs", "firmware", "dat0805", "files", "Iwnn", "ZH", "CN", "pinyin", "GB18030")


def be(b, o, n):
    return int.from_bytes(b[o:o + n], "big")


def hexdump(b, s, e, per=16, limit=32):
    for i, p in enumerate(range(s, e, per)):
        if i >= limit:
            print("        ...")
            return
        print("  %08x  %s" % (p, " ".join("%02x" % c for c in b[p:p + per])))


def decode(name):
    b = open(os.path.join(BASE, name), "rb").read()
    hs, rs, sst, tst, N = be(b, 0x10, 4), be(b, 0x20, 4), be(b, 0x24, 4), be(b, 0x28, 4), be(b, 0x50, 4)
    pool = b[sst:]
    ents = []
    for i in range(N):
        p = rs + i * 10
        rlen = int.from_bytes(b[p:p + 2], "little"); roff = be(b, p + 2, 2)
        tlen = int.from_bytes(b[p + 4:p + 6], "little"); toff = be(b, p + 6, 2)
        if roff + rlen > len(pool) or toff + tlen > len(pool):
            ents.append(None); continue
        try:
            r = pool[roff:roff + rlen].decode("utf-16-be")
            w = pool[toff:toff + tlen].decode("utf-16-be")
        except Exception:
            r, w = None, None
        ents.append((r, w))
    return b, hs, rs, sst, tst, N, ents


def main(names):
    for name in names:
        b, hs, rs, sst, tst, N, ents = decode(name)
        print("=" * 84)
        print("%s  N=%d hs=0x%x rs=0x%x pool=0x%x tail=0x%x" % (name, N, hs, rs, sst, tst))
        print("=" * 84)
        # 计算 T 表
        cnt = [0] * 256
        ok = 0
        for e in ents:
            if e and e[0]:
                cnt[e[0].encode("utf-16-be")[1]] += 1
                ok += 1
        print("  可解码词条 %d/%d" % (ok, N))
        run = 0
        T = []
        for bb in range(256):
            run += cnt[bb]
            T.append(run + 1)
        tb = b"".join(int(v).to_bytes(4, "big") for v in T)
        pos = b.find(tb)
        print("  T 表字节串在文件中位置: %s   -> 前缀长度 = %s"
              % (hex(pos) if pos >= 0 else "未找到",
                 (pos - hs) if pos >= 0 else "-"))
        if pos >= 0:
            print("  前缀内容 raw:")
            hexdump(b, hs, pos, limit=8)
            pre = [be(b, hs + 4 * k, 4) for k in range((pos - hs) // 4)]
            print("  前缀 9/u32: %s" % pre[:12])
            print("  T 表后到 rs 的剩余字节数: %d" % (rs - (pos + 1024)))
            if rs - (pos + 1024) > 0:
                print("  剩余 raw:")
                hexdump(b, pos + 1024, rs, limit=8)
        # 头部字段
        print("  头部: 0x14=%d 0x18=%d 0x1c=%d 0x20=%d 0x24=%d 0x28=%d 0x2c=%d 0x30=%d "
              "0x34=%d 0x38=%d 0x3c=%d 0x40=%d 0x44=%d 0x48=%d 0x4c=%d 0x50=%d 0x54=%d 0x58=%d 0x5c=%d"
              % tuple(be(b, o, 4) for o in (0x14, 0x18, 0x1c, 0x20, 0x24, 0x28, 0x2c, 0x30,
                                            0x34, 0x38, 0x3c, 0x40, 0x44, 0x48, 0x4c, 0x50, 0x54, 0x58, 0x5c)))

    # njubase3 专项
    print("\n" + "#" * 84)
    print("# njubase3.a 专项")
    print("#" * 84)
    b = open(os.path.join(BASE, "njubase3.a"), "rb").read()
    hs, rs, sst, tst, N = be(b, 0x10, 4), be(b, 0x20, 4), be(b, 0x24, 4), be(b, 0x28, 4), be(b, 0x50, 4)
    print("  records=[0x%x,0x%x) len=%d  stride=%s" % (rs, be(b, 0x2c, 4), be(b, 0x2c, 4) - rs,
                                                      (be(b, 0x2c, 4) - rs) / N))
    print("  记录表前 24 条 (10B each):")
    hexdump(b, rs, rs + 240, per=10, limit=24)
    print("  附加表 [0x%x, 0x%x) 前 48 u32:" % (be(b, 0x2c, 4), sst))
    extra = be(b, 0x2c, 4)
    print("   " + " ".join("%d" % be(b, extra + 4 * k, 4) for k in range(40)))
    print("   " + " ".join("%d" % be(b, extra + 4 * k, 4) for k in range(40, 80)))
    # 该表是否递增
    vals = [be(b, extra + 4 * k, 4) for k in range(2000)]
    print("  前 2000 项 单调不减=%s  min=%d max=%d" %
          (all(vals[i] <= vals[i + 1] for i in range(len(vals) - 1)), min(vals), max(vals)))
    # 池起始
    print("  pool 起始 0x%x 处: %s" % (sst, b[sst:sst + 32].hex(" ")))
    end = be(b, 0x2c, 4)
    print("  记录表末尾 0x%x 处: %s" % (end - 20, b[end - 20:end].hex(" ")))


if __name__ == "__main__":
    main(sys.argv[1:] or ["njubase1.a", "njubase2.a", "njcode.a", "njtan.a"])

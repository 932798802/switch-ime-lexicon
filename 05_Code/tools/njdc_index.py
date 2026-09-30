# -*- coding: utf-8 -*-
"""
njdc_index.py —— 解析 NJDC 头部之后的索引/bucket 区（0x54 .. 记录表起始）

目标：搞清 0x54-0x47A 这段到底怎么构成，特别是 0x1F8 起那个递增 u32 偏移数组。
"""
import os
import struct
import sys

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..",
                    "..", "01_Inputs", "firmware", "dat0805", "files", "Iwnn", "ZH", "CN", "pinyin", "GB18030")


def be(b, off, n):
    return int.from_bytes(b[off:off + n], "big")


def le(b, off, n):
    return int.from_bytes(b[off:off + n], "little")


def header(buf):
    h = {}
    h["magic"] = buf[0:4].decode("ascii", "replace")
    h["size"] = len(buf)
    for off in (0x04, 0x08, 0x0C, 0x10, 0x14, 0x18, 0x1C, 0x20, 0x24, 0x28,
                0x2C, 0x30, 0x34, 0x38, 0x3C, 0x40, 0x44, 0x48, 0x4C, 0x50):
        h["%02x" % off] = be(buf, off, 4)
    return h


def dump_hex(buf, start, end, per=16):
    out = []
    for p in range(start, end, per):
        chunk = buf[p:p + per]
        hexs = " ".join("%02x" % c for c in chunk)
        out.append("%08x  %-47s" % (p, hexs))
    return "\n".join(out)


def main(path):
    name = os.path.basename(path)
    with open(path, "rb") as f:
        buf = f.read()
    h = header(buf)
    print("=" * 78)
    print("%s  %d B" % (name, h["size"]))
    print("=" * 78)
    print("header:")
    for k in ("magic", "04", "08", "0c", "10", "14", "18", "1c", "20", "24",
              "28", "2c", "30", "34", "38", "3c", "40", "44", "48", "4c", "50"):
        v = h[k] if k == "magic" else h[k]
        print("  @0x%-3s = %-12d  0x%x" % (k, h[k], h[k]) if k != "magic"
              else "  @0x%-3s = %s" % (k, v))

    hdr_size = h["10"]
    rec_start = h["20"]
    str_start = h["24"]
    tail_start = h["28"]
    N = h["50"]
    print("\n  header_size=0x%x  records=0x%x  strpool=0x%x  tail=0x%x  N=%d"
          % (hdr_size, rec_start, str_start, tail_start, N))
    print("  index region = [0x%x, 0x%x)  size=%d"
          % (hdr_size, rec_start, rec_start - hdr_size))

    # --- 0x54 起 dump ---
    print("\n--- dump 0x54..0x%x (前 320 字节) ---" % (min(hdr_size + 320, rec_start)))
    print(dump_hex(buf, hdr_size, min(hdr_size + 320, rec_start)))

    # --- 逐字节特征扫 0x54..rec_start ---
    print("\n--- 逐 u8 列特征 [0x%x, 0x%x) ---" % (hdr_size, rec_start))
    reg = buf[hdr_size:rec_start]
    print("  len=%d" % len(reg))
    nz = [(i, v) for i, v in enumerate(reg) if v != 0]
    print("  非零字节数=%d  占比=%.1f%%" % (len(nz), 100.0 * len(nz) / len(reg)))
    if nz:
        print("  首个非零 @%d(0x%x) = 0x%02x" % (nz[0][0], nz[0][0], nz[0][1]))
        # 连续非零段
        segs = []
        s = nz[0][0]
        p = s
        for i, v in nz[1:]:
            if i == p + 1:
                p = i
            else:
                segs.append((s, p))
                s = i
                p = i
        segs.append((s, p))
        print("  非零段（相对 0x54，绝对偏移）:")
        for a, b in segs[:40]:
            print("    rel %5d..%5d (abs 0x%x..0x%x)  len=%d" % (a, b, a + hdr_size, b + hdr_size, b - a + 1))
        if len(segs) > 40:
            print("    ... 共 %d 段" % len(segs))

    # --- 从 0x1F8 起读递增 u32 数组 ---
    print("\n--- 0x1F8 起 u32 数组（相对 0x54 的偏移 = 0x1A4）---")
    arr = []
    p = 0x1F8
    while p + 4 <= rec_start:
        v = be(buf, p, 4)
        arr.append((p, v))
        p += 4
    print("  元素数=%d  (0x1F8..0x%x)" % (len(arr), rec_start))
    inc = all(arr[i][1] <= arr[i + 1][1] for i in range(len(arr) - 1))
    print("  单调不减: %s" % inc)
    print("  前 20 个:")
    for off, v in arr[:20]:
        print("    @0x%x = %d (0x%x)" % (off, v, v))
    print("  后 10 个:")
    for off, v in arr[-10:]:
        print("    @0x%x = %d (0x%x)" % (off, v, v))

    # 这些值看起来像绝对偏移还是相对？
    vals = [v for _, v in arr]
    print("  min=%d max=%d  是否都落在 [records, strpool)=[0x%x,0x%x): %s"
          % (min(vals), max(vals), rec_start, str_start,
             all(rec_start <= v < str_start for v in vals)))
    # 看看是否等距
    d = [vals[i + 1] - vals[i] for i in range(len(vals) - 1)]
    print("  相邻差: min=%d max=%d 唯一值数=%d" % (min(d), max(d), len(set(d))))
    print("  差的前 30 个: %s" % d[:30])

    # --- 0x54..0x1F8 这段（在数组之前）---
    print("\n--- 0x54..0x1F8 段（数组之前，len=%d）---" % (0x1F8 - hdr_size))
    print(dump_hex(buf, hdr_size, 0x1F8, per=16))

    # 试着当成 u16 BE 数组
    print("\n--- 0x54..0x1F8 当 u16 BE 数组 ---")
    a16 = [be(buf, p, 2) for p in range(hdr_size, 0x1F8, 2)]
    print("  个数=%d" % len(a16))
    print("  前 64: %s" % a16[:64])
    print("  非零个数=%d" % sum(1 for v in a16 if v))
    nzu = [(i, v) for i, v in enumerate(a16) if v]
    print("  非零项: %s" % nzu[:80])

    # 试着当 u32 BE
    print("\n--- 0x54..0x1F8 当 u32 BE 数组 ---")
    a32 = [be(buf, p, 4) for p in range(hdr_size, 0x1F8, 4)]
    print("  个数=%d" % len(a32))
    print("  %s" % a32)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        targets = sys.argv[1:]
    else:
        targets = ["njexyomi.a", "njubase1.a", "njubase3.a"]
    for t in targets:
        p = t if os.path.exists(t) else os.path.join(BASE, t)
        if os.path.exists(p):
            main(p)

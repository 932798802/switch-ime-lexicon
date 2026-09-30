# -*- coding: utf-8 -*-
"""njdc_lib.py —— NJDC 词典的读/写库（大端）。

已解出的格式（依据 0805 title 内 5 个 pinyin 词典实测，全部字节级比对）:

  头部 (0x54 = 84 字节, 21×u32):
    0x00 "NJDC"
    0x04 0x00020000       常量
    0x08 0x00050000       常量
    0x0c 文件大小 - 0x30   （即尾部 trailer 之前的长度）
    0x10 84               头部长度
    0x14 读法最大字节数
    0x18 表记最大字节数
    0x1c 0
    0x20 记录表偏移   = 84 + 36 + 1024 + 2
    0x24 字符串池偏移 = 0x20 + 10N
    0x28 尾部表偏移   = 0x24 + 池长
    0x2c 0                 （njubase3 另有一段附加区时非 0）
    0x30 112              trailer（尾随块）长度
    0x34..0x40 0
    0x44 索引区结束偏移 = 1144
    0x48 0x00010101       常量
    0x4c 0x00010101       常量（njtan 为 0x000e0104）
    0x50 记录条数 N
  索引区 (0x54 起):
    9×u32 前缀 [0,1,0,0,0,0,0,0,1]
    256×u32 T 表: T[b] = 1 + #{记录: 读法第 1 个字符的编码 <= b}
  间隙 2 字节: 08 06
  记录表: N × 10 字节
    0 u8   读法长度(字节)
    1 u24BE 读法偏移(相对池首)
    4 u8   表记长度(字节)
    5 u24BE 表记偏移(相对池首)
    8 u16  保留 0
  字符串池: concat(升序「最大读法」) + concat(升序「最大表记」)
    「最大」= 该串不是同一池内任何其它串的子串
  尾部表: N×u16 = 0x4040 | ((v<<8)|v)，v = 6bit 优先级（njubase1/2/njtan 口径）
  文件尾: 4 字节 "NJDC"；文件大小 = 尾部表偏移 + 2N + 4；0x0c = 大小 - 112
"""
import bisect

MAGIC = b"NJDC"
FOOTER_RESERVE = 112                      # 0x30 / 0x0c 的口径：末尾 112 字节为保留区
END_MAGIC = b"NJDC"                       # 文件最后 4 字节
HEADER_SIZE = 0x54
GAP = b"\x08\x06"                      # 标准词典（含 njubase3）固定这 2 字节
PREFIX = [0, 1, 0, 0, 0, 0, 0, 0, 1]


def be(b, o, n):
    return int.from_bytes(b[o:o + n], "big")


def u32(v):
    return int(v).to_bytes(4, "big")


# ---------------------------------------------------------------- 保留字判定
def _prefix_range_multi(S, s):
    """S 为已排序的字符串列表；判定是否存在元素 x != s 且 s 是 x 的前缀。"""
    lo = bisect.bisect_left(S, s)
    up = s[:-1] + chr(ord(s[-1]) + 1)
    hi = bisect.bisect_left(S, up)
    return (hi - lo) > 1


def maximal_strings(uniq):
    """返回 uniq 中「不是其它串子串」的串（按 UTF-16BE 字节升序）。"""
    sufs = sorted({s[i:] for s in uniq for i in range(len(s))})
    rev = sorted({s[::-1] for s in uniq})
    rsufs = sorted({r[i:] for r in rev for i in range(len(r))})
    out = []
    for s in uniq:
        # s 是别的串的子串 ⟺ 存在更长的后缀以 s 为前缀(前缀型)
        #                    或 s 是别的串的真后缀(后缀型 → 反转后成前缀型)
        if _prefix_range_multi(sufs, s):
            continue
        if _prefix_range_multi(rsufs, s[::-1]):
            continue
        out.append(s)
    return out


def build_pool(readings, writings):
    """构造字符串池，返回 (池字节, 读法偏移表, 表记偏移表, 读法最大/表记最大字节数)。"""
    uR = sorted(set(readings), key=lambda s: s.encode("utf-16-be"))
    uW = sorted(set(writings), key=lambda s: s.encode("utf-16-be"))
    kr = maximal_strings(uR)
    kw = maximal_strings(uW)

    rb = "".join(kr).encode("utf-16-be")
    wb = "".join(kw).encode("utf-16-be")
    pool = rb + wb

    def offsets(uniq, base):
        """每个串 -> 池内偏移；取首次出现（语义等价于厂商文件）。"""
        d = {}
        for s in uniq:
            e = s.encode("utf-16-be")
            p = pool.find(e, base)
            if p < 0:
                p = pool.find(e)
            d[s] = p
        return d

    ro = offsets(uR, 0)
    wo = offsets(uW, len(rb))
    maxr = max((len(s.encode("utf-16-be")) for s in readings), default=0)
    maxw = max((len(s.encode("utf-16-be")) for s in writings), default=0)
    return pool, ro, wo, maxr, maxw


def build_njdc(entries, tail_values=None, gap=GAP, prefix=PREFIX, const48=0x010101, const4c=0x010101,
               sort=True):
    """entries: [(reading, writing)]。
       tail_values: 与 entries 等长的 0..63 列表；None 则全部用 63。
       sort: 按读法 UTF-16BE 字节序稳定排序（同读法保持传入顺序）。"""
    if sort:
        order = sorted(range(len(entries)), key=lambda i: entries[i][0].encode("utf-16-be"))
        entries = [entries[i] for i in order]
        if tail_values is not None:
            tail_values = [tail_values[i] for i in order]
    readings = [e[0] for e in entries]
    writings = [e[1] for e in entries]
    N = len(entries)
    pool, ro, wo, maxr, maxw = build_pool(readings, writings)

    rs = HEADER_SIZE + 36 + 1024 + len(gap)
    ps = rs + 10 * N
    ts = ps + len(pool)

    # T 表
    cnt = [0] * 256
    for r in readings:
        if r:
            cnt[r[0].encode("utf-16-be")[1]] += 1
    run = 0
    T = []
    for b in range(256):
        run += cnt[b]
        T.append(run + 1)

    body = bytearray()
    body += MAGIC + u32(0x00020000) + u32(0x00050000)
    body += u32(ts + 2 * N + 4 - FOOTER_RESERVE)     # 0x0c: 文件大小 - 112
    body += u32(HEADER_SIZE) + u32(maxr) + u32(maxw) + u32(0)
    body += u32(rs) + u32(ps) + u32(ts) + u32(0)
    body += u32(FOOTER_RESERVE) + u32(0) + u32(0) + u32(0) + u32(0)
    body += u32(HEADER_SIZE + 36 + 1024)             # 0x44: 索引区结束
    body += u32(const48) + u32(const4c) + u32(N)

    body += b"".join(u32(v) for v in prefix)
    body += b"".join(u32(v) for v in T)
    body += gap

    for (r, w) in entries:
        rb = r.encode("utf-16-be")
        wb = w.encode("utf-16-be")
        body += bytes([len(rb) & 0xff]) + (ro[r] & 0xffffff).to_bytes(3, "big")
        body += bytes([len(wb) & 0xff]) + (wo[w] & 0xffffff).to_bytes(3, "big")
        body += b"\x00\x00"
    body += pool

    # 尾部表：N 个 u16 = 0x4040 | ((v<<8)|v)；随后 4 字节 "NJDC"
    tl = bytearray()
    for i in range(N):
        v = 63 if tail_values is None else (int(tail_values[i]) & 0x3f)
        c = 0x40 | v
        tl += bytes([c, c])
    body += tl
    body += END_MAGIC
    return bytes(body)


# ---------------------------------------------------------------- 解析/校验
def parse_njdc(b):
    assert b[:4] == MAGIC, "不是 NJDC"
    rs, ps, ts, N = be(b, 0x20, 4), be(b, 0x24, 4), be(b, 0x28, 4), be(b, 0x50, 4)
    ent = []
    for i in range(N):
        p = rs + i * 10
        rl, ro, wl, w2 = b[p], be(b, p + 1, 3), b[p + 4], be(b, p + 5, 3)
        ent.append((b[ps + ro:ps + ro + rl].decode("utf-16-be"),
                    b[ps + w2:ps + w2 + wl].decode("utf-16-be")))
    return {
        "N": N, "rs": rs, "ps": ps, "ts": ts,
        "maxr": be(b, 0x14, 4), "maxw": be(b, 0x18, 4),
        "tail": [be(b, ts + 2 * i, 2) for i in range(N)],
        "entries": ent,
    }


def verify_roundtrip(path, verbose=True):
    raw = open(path, "rb").read()
    d = parse_njdc(raw)
    rebuilt = build_njdc(d["entries"], tail_values=[v & 0x3f for v in d["tail"]])
    same = rebuilt == raw
    if verbose:
        n = min(len(rebuilt), len(raw))
        diff = [i for i in range(n) if rebuilt[i] != raw[i]]
        print("  %-16s N=%-6d 原=%-9d 重建=%-9d 字节全等=%s  差异字节数=%d"
              % (path.split("/")[-1] if "/" in path else path.split("\\")[-1],
                 d["N"], len(raw), len(rebuilt), same, len(diff)))
        if diff:
            # 只看记录表区域的差异（偏移字段）
            rs = d["rs"]
            inrec = [i for i in diff if rs <= i < rs + 10 * d["N"]]
            print("     差异集中在记录表:%d 字节  其它区:%d 字节  首处=0x%x"
                  % (len(inrec), len(diff) - len(inrec), diff[0]))
        # 语义一致性
        d2 = parse_njdc(rebuilt)
        print("     语义一致(条目完全相同)=%s  尾部值一致=%s"
              % (d2["entries"] == d["entries"], d2["tail"] == d["tail"]))
    return same, d, rebuilt


if __name__ == "__main__":
    import os
    import sys
    BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..",
                        "01_Inputs", "firmware",
                        "dat0805", "files", "Iwnn", "ZH", "CN", "pinyin", "GB18030")
    names = sys.argv[1:] or ["njubase1.a", "njubase2.a", "njcode.a", "njtan.a", "njubase3.a"]
    for nm in names:
        verify_roundtrip(os.path.join(BASE, nm))

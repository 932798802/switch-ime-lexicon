# -*- coding: utf-8 -*-
"""verify_njdc.py —— NJDC 词典的结构校验 + 功能抽查。

判据分两层（与 nro/source/njdc_check.h 保持一致）:
  Tier 1  通用不变量 —— 任何符合 NJDC 的文件都应满足。
  Tier 2  「干净版式」特征值 —— 仅当 (头部长度 == 0x54 且 记录表偏移 == 1146) 时检查。

⚠️ 教训（务必不要再犯）: 早期版本把这三条当成「通用判据」——
      0x20 == 1146 、0x44 == 1144 、0x0c == 文件大小 - 112
   结果把原版词典误判为坏文件:
      njubase3.a（extra 版式）  0x20=81726  0x44=81724
      njtan.a   （自有索引区）  0x20=57895  0x44=57880
      njexyomi.a（头长 60）     0x0c = 大小 - 88，不是 -112
   真相: 它们只是「干净版式」那一类文件（njubase1/2、njcode）的特征值。
   通用关系只有一条: **0x0c = 文件大小 − 28 − 头部长度**。

用法:
  python verify_njdc.py <要校验的 .a 文件> [参考的原始 .a 文件]
"""
import os
import sys
import hashlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import njdc_lib as L

PROBES = [
    ("shalujianta", "杀戮尖塔"), ("jianta", "尖塔"), ("luoshi", "落实"),
    ("lvxing", "旅行"), ("nvhai", "女孩"), ("yuanzhoulv", "圆周率"),
    ("aierdengfahuan", "艾尔登法环"), ("heishenhuawukong", "黑神话悟空"),
    ("baokemeng", "宝可梦"), ("saierda", "塞尔达"), ("sipuladun", "斯普拉遁"),
    ("jisuanjishu", "计算技术"), ("jisuanji", "计算机"),
    ("youxi", "游戏"), ("lianji", "联机"), ("cundang", "存档"),
    ("beijingdaxue", "北京大学"), ("nianqingren", "年轻人"), ("zhaoxiangji", "照相机"),
]
# 简拼抽查（只在含简拼条目的包里才会命中）
ABBR_PROBES = [
    ("sljt", "杀戮尖塔"), ("aedfh", "艾尔登法环"), ("hshwk", "黑神话悟空"),
    ("bkm", "宝可梦"), ("cd", "存档"), ("zm", "周目"),
]

HEADER_SIZE_CLEAN = 0x54    # 84
HEADER_SIZE_NJEXYOMI = 0x3C  # 60
REC_OFF_CLEAN = 1146
IDX_END_CLEAN = 1144
TRAILER_CONST = 28


def be(b, o, n):
    return int.from_bytes(b[o:o + n], "big")


def check(path, ref=None):
    raw = open(path, "rb").read()
    ok = True
    print("=" * 84)
    print("校验 %s   大小=%d  sha256=%s" % (path, len(raw), hashlib.sha256(raw).hexdigest()[:16]))
    print("=" * 84)

    def ck(name, cond, extra=""):
        nonlocal ok
        ok = ok and bool(cond)
        print("  [%s] %-42s %s" % ("OK " if cond else "FAIL", name, extra))

    def skip(name, extra=""):
        print("  [ -- ] %-42s %s" % (name, extra))

    hs = be(raw, 0x10, 4)
    rs = be(raw, 0x20, 4)
    ps = be(raw, 0x24, 4)
    ts = be(raw, 0x28, 4)
    N = be(raw, 0x50, 4)
    clean = (hs == HEADER_SIZE_CLEAN and rs == REC_OFF_CLEAN)

    print("  ---- Tier 1：通用不变量 ----")
    ck("魔数 NJDC", raw[:4] == b"NJDC")
    ck("头部长度为已知取值 (84 或 60)",
       hs in (HEADER_SIZE_CLEAN, HEADER_SIZE_NJEXYOMI), "0x10=%d" % hs)
    ck("0x0c = 文件大小 - 28 - 头部长度",
       be(raw, 0x0c, 4) == len(raw) - TRAILER_CONST - hs,
       "%d vs %d" % (be(raw, 0x0c, 4), len(raw) - TRAILER_CONST - hs))
    ck("文件末 4 字节 = NJDC", raw[-4:] == b"NJDC", raw[-4:].hex(" "))

    if N == 0:
        skip("记录型词典（N > 0）", "N=0 —— 非记录型文件，以下结构项不适用")
        print("\n  结论: %s\n" % ("文件头合法；N=0，按设计跳过记录结构检查" if ok
                                 else "存在失败项，请检查上面 FAIL 行"))
        return ok

    ck("记录表偏移 >= 头部长度", rs >= hs, "0x20=%d" % rs)
    ck("池偏移 >= 记录表 + 10N", ps >= rs + 10 * N, "%d vs %d" % (ps, rs + 10 * N))
    ck("尾部表偏移 >= 池偏移", ts >= ps, "%d vs %d" % (ts, ps))
    ck("文件大小 = 尾部表 + 2N + 4", len(raw) == ts + 2 * N + 4,
       "%d vs %d" % (len(raw), ts + 2 * N + 4))

    d = L.parse_njdc(raw)
    ent = d["entries"]
    R = [e[0] for e in ent]
    W = [e[1] for e in ent]
    ck("0x50 记录数 == 实际解出条数", N == len(ent), "N=%d" % N)

    bad = 0
    for i in range(N):
        p = rs + i * 10
        rl, ro, wl, wo = raw[p], be(raw, p + 1, 3), raw[p + 4], be(raw, p + 5, 3)
        if (ps + ro + rl > ts or ps + wo + wl > ts or rl == 0 or wl == 0
                or (wl % 2) or (rl % 2)):
            bad += 1
    ck("所有记录偏移/长度合法", bad == 0, "异常 %d 条" % bad)

    if clean:
        print("  ---- Tier 2：干净版式特征值（0x10=84 且 0x20=1146）----")
        ck("0x20 记录表偏移 = 1146", rs == REC_OFF_CLEAN, "0x20=%d" % rs)
        ck("池偏移 = 记录表 + 10N", ps == rs + 10 * N, "%d vs %d" % (ps, rs + 10 * N))
        ck("0x30 = 112", be(raw, 0x30, 4) == 112)
        ck("0x44 = 1144（索引区结束）", be(raw, 0x44, 4) == IDX_END_CLEAN,
           "0x44=%d" % be(raw, 0x44, 4))
        ck("0x2c/0x38/0x54 = 0（无附加区）",
           be(raw, 0x2c, 4) == 0 and be(raw, 0x38, 4) == 0 and be(raw, 0x54, 4) == 0)
        ck("间隙 = 08 06", raw[IDX_END_CLEAN:REC_OFF_CLEAN] == b"\x08\x06",
           raw[IDX_END_CLEAN:REC_OFF_CLEAN].hex(" "))
        ck("索引前缀 = [0,1,0,0,0,0,0,0,1]",
           [be(raw, 0x54 + 4 * i, 4) for i in range(9)] == [0, 1, 0, 0, 0, 0, 0, 0, 1])
        ck("记录保留字段为 0",
           all(raw[rs + i * 10 + 8] == 0 and raw[rs + i * 10 + 9] == 0 for i in range(N)))
        ck("读法按 UTF-16BE 升序（非递减）",
           all(R[i].encode("utf-16-be") <= R[i + 1].encode("utf-16-be") for i in range(N - 1)))

        mr = max(len(r.encode("utf-16-be")) for r in R)
        mw = max(len(w.encode("utf-16-be")) for w in W)
        ck("0x14 = 读法最大字节数", be(raw, 0x14, 4) == mr, "%d vs %d" % (be(raw, 0x14, 4), mr))
        ck("0x18 = 表记最大字节数", be(raw, 0x18, 4) == mw, "%d vs %d" % (be(raw, 0x18, 4), mw))

        tv = [raw[ts + 2 * i] for i in range(N)]
        ck("尾部表首字节都在 0x40..0x7f", all(0x40 <= x <= 0x7f for x in tv))

        # 以下两项是「**本工程产物**的写法约定」，不是干净版式的通用不变量——
        # 原版 njcode（记号/小键盘词典）的读法本就含非字母字符，尾部表也不是
        # 成对相同（它用 0x4000 变体）。因此只报告实测比例，不判 FAIL。
        # 本工程的产物应恒为 100%（否则说明生成器出问题），一眼可辨。
        n_az = sum(1 for r in R if r.isascii() and r.isalpha() and r.islower())
        n_pair = sum(1 for i in range(N) if raw[ts + 2 * i] == raw[ts + 2 * i + 1])
        print("  [info] %-42s %d/%d 条%s" % (
            "读法字符集（本工程约定 = 全 a-z）", n_az, N,
            "" if n_az == N else "  ← 非 a-z %d 条" % (N - n_az)))
        print("  [info] %-42s %d/%d 条%s" % (
            "尾部表高低字节成对相同（本工程约定）", n_pair, N,
            "" if n_pair == N else "  ← 不成对 %d 条" % (N - n_pair)))

        # T 表复算（索引区 0x78 起 256 个 u32）
        cnt = [0] * 256
        for r in R:
            cnt[r[0].encode("utf-16-be")[1]] += 1
        run, T = 0, []
        for b in range(256):
            run += cnt[b]
            T.append(run + 1)
        Tf = [be(raw, 0x78 + 4 * i, 4) for i in range(256)]
        ck("T 表可复算", Tf == T, "T[0]=%d T[255]=%d (N+1=%d)" % (T[0], T[255], N + 1))
    else:
        print("  ---- Tier 2 跳过：本文件不是「干净版式」----")
        skip("干净版式特征值", "0x10=%d 0x20=%d（原版词典常见，属正常）" % (hs, rs))

    # ---- 功能抽查 ----
    idx = {}
    for r, w in ent:
        idx.setdefault(r, []).append(w)
    print("  ---- 输入法命中抽查 ----")
    for rd, want in PROBES:
        cands = idx.get(rd, [])
        hit = want in cands
        print("    %-16s -> %-10s 候选 %d 个  首选=%-8s %s"
              % (rd, want, len(cands), cands[0] if cands else "-",
                 "命中" if hit else ("未收录" if not cands else "在候选中")))

    if any(rd in idx for rd, _ in ABBR_PROBES):
        print("  ---- 简拼（首字母）抽查 ----")
        for rd, want in ABBR_PROBES:
            cands = idx.get(rd, [])
            hit = want in cands
            print("    %-16s -> %-10s 候选 %d 个  首选=%-8s %s"
                  % (rd, want, len(cands), cands[0] if cands else "-",
                     "命中" if hit else ("未收录" if not cands else "在候选中")))

    if ref:
        dr = L.parse_njdc(open(ref, "rb").read())
        sr = {(r, w) for r, w in dr["entries"]}
        sn = {(r, w) for r, w in ent}
        print("  ---- 与原版对比 (%s) ----" % os.path.basename(ref))
        print("    原版 %d 条 / %d 字节      新版 %d 条 / %d 字节"
              % (dr["N"], os.path.getsize(ref), N, len(raw)))
        print("    新增条目 %d 条   原版有而新版无 %d 条" % (len(sn - sr), len(sr - sn)))
        print("    唯一表记：原版 %d -> 新版 %d" % (len({w for _, w in sr}), len({w for _, w in sn})))
        print("    重复条目（同一 读法+表记 出现多次）: %d" % (N - len(sn)))
        miss = sorted(sr - sn)[:8]
        print("    未覆盖样例（前 8）: %s" % (miss,))

    print("\n  结论: %s\n" % ("全部结构检查通过" if ok else "存在失败项，请检查上面 FAIL 行"))
    return ok


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(1)
    sys.exit(0 if check(args[0], args[1] if len(args) > 1 else None) else 1)

# -*- coding: utf-8 -*-
"""njdc_poolrule2.py —— 精确判定字符串池的打包规则。
   假设 H1: 发射流 = 「非其它串子串」的唯一串按升序拼接。
   假设 H2: 其余串的偏移 = 该串在发射流中的 首次/末次 出现位置。
"""
import os
import sys

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..",
                    "..", "01_Inputs", "firmware", "dat0805", "files", "Iwnn", "ZH", "CN", "pinyin", "GB18030")


def be(b, o, n):
    return int.from_bytes(b[o:o + n], "big")


def all_occ(buf, s):
    """s 在 buf 中所有出现位置（允许重叠）。"""
    out = []
    i = buf.find(s)
    while i >= 0:
        out.append(i)
        i = buf.find(s, i + 2)          # 步进 2 字节（UTF-16 对齐）
    return out


def analyze(name):
    b = open(os.path.join(BASE, name), "rb").read()
    rs, pool, tst, N = be(b, 0x20, 4), be(b, 0x24, 4), be(b, 0x28, 4), be(b, 0x50, 4)
    recs = []
    for i in range(N):
        p = rs + i * 10
        rl, ro, tl, to = b[p], be(b, p + 1, 3), b[p + 4], be(b, p + 5, 3)
        recs.append((rl, ro, tl, to))
    R = [b[pool + ro:pool + ro + rl].decode("utf-16-be", "replace") for rl, ro, _, _ in recs]
    W = [b[pool + to:pool + to + tl].decode("utf-16-be", "replace") for _, _, tl, to in recs]

    print("=" * 100)
    print("%s  N=%d  pool=[%d,%d) len=%d" % (name, N, pool, tst, tst - pool))
    print("=" * 100)

    # ---- 读法池 ----
    maxr = max(ro + rl for rl, ro, _, _ in recs)
    mint = min(to for _, _, _, to in recs)
    print("  读法区实测 [0,%d)   表记区实测 [%d,%d)" % (maxr, mint, tst - pool))

    for tag, strings, region_end, base_field in (("读法", R, maxr, 1), ("表记", W, tst - pool - mint, 3)):
        uniq = sorted(set(strings))
        keep = [s for s in uniq if not any(t != s and s in t for t in uniq)]
        stream = "".join(keep)
        beg = 0 if tag == "读法" else mint
        actual = b[pool + beg:pool + region_end].decode("utf-16-be", "replace")
        print()
        print("  [%s] 唯一 %d，去子串后 %d，拼接长度 %d 字节；实测区长度 %d 字节" %
              (tag, len(uniq), len(keep), len(stream) * 2, region_end - beg))
        print("        发射流与实测区字节完全相同: %s" % (stream == actual))
        if stream != actual:
            # 找第一处差异
            n = min(len(stream), len(actual))
            d = next((i for i in range(n) if stream[i] != actual[i]), n)
            print("        首个差异在字符 %d: 预测 …%r  实测 …%r" %
                  (d, stream[max(0, d - 30):d + 30], actual[max(0, d - 30):d + 30]))
        # 偏移选择规则（用观测到的第一条记录）
        first = {}
        for s, o in zip(strings, [r[base_field] for r in recs]):
            first.setdefault(s, o)
        for mode in ("首次", "末次"):
            hit = 0
            for s, o in first.items():
                occ = all_occ(stream, s)
                if not occ:
                    continue
                want = occ[0] if mode == "首次" else occ[-1]
                if want * 2 == o:
                    hit += 1
            print("        %s出现 命中 %d/%d" % (mode, hit, len(first)))
        # 共享条目样本
        sh = [(s, o) for s, o in first.items()
              if not any(t != s and s in t for t in uniq)]
        print("        独占串样本: %s" % [(s, o) for s, o in sh[:3]])
    print()


if __name__ == "__main__":
    for n in (sys.argv[1:] or ["njubase1.a"]):
        analyze(n)

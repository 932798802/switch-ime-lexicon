# -*- coding: utf-8 -*-
"""njdc_poolrule.py —— 验证池规则：升序排序 + 丢弃「是其它串子串」的项，偏移=累计长度。"""
import os
import sys

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..",
                    "..", "01_Inputs", "firmware", "dat0805", "files", "Iwnn", "ZH", "CN", "pinyin", "GB18030")


def be(b, o, n):
    return int.from_bytes(b[o:o + n], "big")


def test(name, verbose=True):
    b = open(os.path.join(BASE, name), "rb").read()
    hs, rs, pool, tst, N = be(b, 0x10, 4), be(b, 0x20, 4), be(b, 0x24, 4), be(b, 0x28, 4), be(b, 0x50, 4)
    ents = []
    for i in range(N):
        p = rs + i * 10
        ents.append((b[p], be(b, p + 1, 3), b[p + 4], be(b, p + 5, 3)))
    max_r = max(o + l for l, o, _, _ in ents)
    min_t = min(t for *_, t in ents)

    def get(off, ln):
        return b[pool + off:pool + off + ln].decode("utf-16-be", "replace")

    reads = sorted({get(o, l) for l, o, _, _ in ents})
    words = sorted({get(t, tl) for _, _, tl, t in ents})

    def predict(strings, mode):
        """mode: 'nosub' 丢子串 / 'nosuffix' 丢后缀 / 'noprefix' 丢前缀 / 'all' 全保留"""
        keep = []
        for s in strings:
            drop = False
            for t in strings:
                if t == s:
                    continue
                if mode == "nosub" and s in t:
                    drop = True
                elif mode == "nosuffix" and t.endswith(s):
                    drop = True
                elif mode == "noprefix" and t.startswith(s):
                    drop = True
                if drop:
                    break
            if mode == "all":
                drop = False
            if not drop:
                keep.append(s)
        off = 0
        out = []
        for s in keep:
            out.append((off, s))
            off += len(s) * 2
        return out, off

    # 观测: 真实写入串的偏移
    obs_r = {}
    for l, o, _, _ in ents:
        obs_r.setdefault(o, None)
    # 只在读法区内
    obs_r = sorted(o for o in obs_r if o < max_r)

    print("=== %s ===" % name)
    for mode in ("all", "nosub", "nosuffix", "noprefix"):
        pr, size = predict(reads, mode)
        pset = {o for o, s in pr}
        hit = len(pset & set(obs_r))
        print("  读法池 mode=%-9s 预测串数=%-6d 预测区大小=%-7d 与观测起始偏移交集=%d/%d"
              % (mode, len(pr), size, hit, len(obs_r)))
        print("      大小匹配=%s" % (size == max_r))
    print("  观测: 读法区大小=%d 唯一起始偏移=%d" % (max_r, len(obs_r)))

    obs_t = sorted({t for *_, t in ents if t >= min_t})
    wsize = tst - pool - min_t
    for mode in ("all", "nosub", "nosuffix", "noprefix"):
        pw, size = predict(words, mode)
        pset = {min_t + o for o, s in pw}
        hit = len(pset & set(obs_t))
        print("  表记池 mode=%-9s 预测串数=%-6d 预测区大小=%-7d 与观测交集=%d/%d  大小匹配=%s"
              % (mode, len(pw), size, hit, len(obs_t), size == wsize))
    print("  观测: 表记区大小=%d 唯一起始偏移=%d" % (wsize, len(obs_t)))

    if verbose:
        # 用最优 mode 对比前 20 个
        pr, _ = predict(reads, "nosub")
        print("\n  读法池预测前 20: %s" % [(o, s) for o, s in pr[:20]])
        # 观测前 20 个起始偏移对应的串
        seen = set()
        ob = []
        for o in obs_r:
            L = max(l for l, oo, _, _ in ents if oo == o)
            ob.append((o, get(o, L)))
        print("  读法池观测前 20: %s" % ob[:20])
    return


if __name__ == "__main__":
    for n in (sys.argv[1:] or ["njubase1.a", "njubase2.a", "njcode.a"]):
        test(n)
        print()

# -*- coding: utf-8 -*-
"""njdc_poolprobe.py —— 确认池的排序规则与后缀共享规则。"""
import os
import sys

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..",
                    "..", "01_Inputs", "firmware", "dat0805", "files", "Iwnn", "ZH", "CN", "pinyin", "GB18030")


def be(b, o, n):
    return int.from_bytes(b[o:o + n], "big")


def main(name="njubase1.a"):
    b = open(os.path.join(BASE, name), "rb").read()
    hs, rs, pool, tst, N = be(b, 0x10, 4), be(b, 0x20, 4), be(b, 0x24, 4), be(b, 0x28, 4), be(b, 0x50, 4)
    ents = []
    for i in range(N):
        p = rs + i * 10
        ents.append((i, b[p], be(b, p + 1, 3), b[p + 4], be(b, p + 5, 3)))
    max_r = max(o + l for _, l, o, _, _ in ents)
    min_t = min(t for *_, t in ents)

    # 收集唯一串（按起始偏移）
    def collect(filter_fn):
        m = {}
        for i, rl, ro, tl, to in ents:
            if filter_fn(ro, to):
                key = ro
                if key not in m:
                    m[key] = (ents[i][1 if filter_fn(ro, to) == "r" else 3], i)
        return m

    # 读法区
    rmap = {}
    for i, rl, ro, tl, to in ents:
        if ro < max_r:
            rmap.setdefault(ro, []).append(i)
    order = sorted(rmap)
    print("=== %s  读法区 [0,%d) 唯一起始偏移 %d 个 ===" % (name, max_r, len(order)))
    # 每个偏移对应的串（取该偏移处最长的解释？先按第一个 owner 的 rlen）
    entries = []
    for o in order:
        # 取所有 owner 中最长的 rlen
        L = max(b[rs + i * 10] for i in rmap[o])
        entries.append((o, L, b[pool + o:pool + o + L].decode("utf-16-be", "replace")))
    # 单调性检查
    bad = [k for k in range(len(entries) - 1) if entries[k][2] > entries[k + 1][2]]
    print("  按偏移顺序，读法升序违例数=%d" % len(bad))
    if bad:
        for k in bad[:12]:
            print("    %5d: %s   ->  %5d: %s" % (entries[k][0], entries[k][2],
                                                 entries[k + 1][0], entries[k + 1][2]))
    # 覆盖/空洞
    gaps = [(entries[k][0] + entries[k][1], entries[k + 1][0])
            for k in range(len(entries) - 1) if entries[k][0] + entries[k][1] != entries[k + 1][0]]
    print("  不连续处 %d 个（负值=后缀共享）前 12: %s"
          % (len(gaps), [(a, b_, b_ - a) for a, b_ in gaps[:12]]))
    # 后缀共享统计
    sh = sum(1 for a, b_ in gaps if b_ < a)
    print("  其中后缀共享 %d 处" % sh)

    # 表记区
    wmap = {}
    for i, rl, ro, tl, to in ents:
        if to >= min_t:
            wmap.setdefault(to, []).append(i)
    worder = sorted(wmap)
    wentries = []
    for o in worder:
        L = max(b[rs + i * 10 + 4] for i in wmap[o])
        wentries.append((o, L, b[pool + o:pool + o + L].decode("utf-16-be", "replace")))
    print("\n=== 表记区 [%d,%d) 唯一起始偏移 %d 个 ===" % (min_t, tst - pool, len(worder)))
    bad = [k for k in range(len(wentries) - 1) if wentries[k][2] > wentries[k + 1][2]]
    print("  按偏移顺序，表记升序违例数=%d" % len(bad))
    for k in bad[:6]:
        print("    %5d: %s  ->  %5d: %s" % (wentries[k][0], wentries[k][2],
                                            wentries[k + 1][0], wentries[k + 1][2]))
    gaps = [(wentries[k][0] + wentries[k][1], wentries[k + 1][0])
            for k in range(len(wentries) - 1) if wentries[k][0] + wentries[k][1] != wentries[k + 1][0]]
    print("  不连续处 %d 个 前 12: %s" % (len(gaps), [(a, b_, b_ - a) for a, b_ in gaps[:12]]))
    print("  其中后缀共享: %d" % sum(1 for a, b_ in gaps if b_ < a))
    print("  表记区前 3 / 后 3: %s ... %s" % ([e[2] for e in wentries[:3]], [e[2] for e in wentries[-3:]]))

    # 读法区最后几个
    print("  读法区最后 5: %s" % [(e[0], e[2]) for e in entries[-5:]])
    print("  读法区 878 附近: %s" % [(e[0], e[2]) for e in entries if 840 <= e[0] <= 900][:10])


if __name__ == "__main__":
    main(*(sys.argv[1:] or ["njubase1.a"]))

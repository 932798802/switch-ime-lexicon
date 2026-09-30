# -*- coding: utf-8 -*-
"""njdc_keydet.py —— 判定性检验：v 是否由某键唯一决定。"""
import os
import sys
from collections import defaultdict

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..",
                    "..", "01_Inputs", "firmware", "dat0805", "files", "Iwnn", "ZH", "CN", "pinyin", "GB18030")


def be(b, o, n):
    return int.from_bytes(b[o:o + n], "big")


def load(name):
    b = open(os.path.join(BASE, name), "rb").read()
    hs, rs, sst, tst, N = be(b, 0x10, 4), be(b, 0x20, 4), be(b, 0x24, 4), be(b, 0x28, 4), be(b, 0x50, 4)
    pool = b[sst:]
    ents = []
    for i in range(N):
        p = rs + i * 10
        rlen = int.from_bytes(b[p:p + 2], "little"); roff = be(b, p + 2, 2)
        tlen = int.from_bytes(b[p + 4:p + 6], "little"); toff = be(b, p + 6, 2)
        r = pool[roff:roff + rlen].decode("utf-16-be", "replace")
        w = pool[toff:toff + tlen].decode("utf-16-be", "replace")
        ents.append((r, w))
    T = [be(b, tst + 2 * k, 2) >> 8 for k in range(N)]
    return N, ents, T


def test(name, N, ents, T, keyfn, label):
    m = defaultdict(set)
    for i in range(N):
        m[keyfn(ents[i])].add(T[i])
    multi = {k: v for k, v in m.items() if len(v) > 1}
    print("  %-28s 键数=%-6d 冲突键=%-6d  决定度=%.1f%%"
          % (label, len(m), len(multi), 100.0 * (1 - len(multi) / max(1, len(m)))))
    if multi and len(multi) < 5:
        print("      冲突样例: %s" % list(multi.items())[:5])
    return 1 - len(multi) / max(1, len(m))


def main(name):
    N, ents, T = load(name)
    print("=== %s N=%d ===" % (name, N))
    tests = [
        ("字面(w)", lambda e: e[1]),
        ("读法(r)", lambda e: e[0]),
        ("(r,w)", lambda e: (e[0], e[1])),
        ("w 末字", lambda e: e[1][-1] if e[1] else ""),
        ("w 首字", lambda e: e[1][0] if e[1] else ""),
        ("w 首2字", lambda e: e[1][:2]),
        ("w 末2字", lambda e: e[1][-2:]),
        ("w 首字+末字", lambda e: (e[1][0], e[1][-1]) if e[1] else ""),
        ("w 长度", lambda e: len(e[1])),
        ("(w 首字,w 长度)", lambda e: (e[1][0], len(e[1])) if e[1] else ""),
        ("(w 末字,w 长度)", lambda e: (e[1][-1], len(e[1])) if e[1] else ""),
        ("(w 首字,末字,长度)", lambda e: (e[1][0], e[1][-1], len(e[1])) if e[1] else ""),
        ("r 末字", lambda e: e[0][-1] if e[0] else ""),
        ("(r 首3字)", lambda e: e[0][:3]),
        ("(r 前2字,w 首字)", lambda e: (e[0][:2], e[1][:1])),
        ("(w 首字,r 长度)", lambda e: (e[1][:1], len(e[0]))),
    ]
    scores = []
    for label, fn in tests:
        scores.append((label, test(name, N, ents, T, fn, label)))

    # 值分布
    from collections import Counter
    c = Counter(T)
    print("\n  v 分布: %s" % sorted((k - 0x40, v) for k, v in c.items()))

    # 如果 w 末字决定 v，看看是不是数值函数
    print("\n--- 若由 w 末字决定，检验数值关系 ---")
    m = defaultdict(set)
    for i in range(N):
        m[ents[i][1][-1]].add(T[i])
    ok = sum(1 for k, v in m.items() if len(v) == 1)
    print("  末字决定: %d/%d 个不同末字可唯一确定 v" % (ok, len(m)))
    # 看末字码点与 v 的关系
    pairs = sorted((ord(k), list(v)[0] - 0x40) for k, v in m.items() if k)
    print("  前 30 个 (末字码点, v): %s" % pairs[:30])
    print("  后 10 个: %s" % pairs[-10:])


if __name__ == "__main__":
    main(*(sys.argv[1:] or ["njubase1.a"]))

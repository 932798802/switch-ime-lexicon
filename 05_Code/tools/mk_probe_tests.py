# -*- coding: utf-8 -*-
"""mk_probe_tests.py —— 生成一组「判别测试包」，回答一个问题：

    大小上限到底是「单本」还是「三本总量」？

背景（见根 README.md 的「技术侦察报告」节 §21）
--------------------------------------
工程原以为「每本词典有独立的大小预算」，但该结论**缺实验支撑**：
§15 的全部阈值实验只动过 `njubase3` 一本，所以观测到的「失败点」既可解读为
「单本上限」（4.87 ✅ / 5.16 ❌ MB），也可解读为「**三本总量上限**」
（5.31 ✅ / 5.61 ❌ MB）—— 两种假设**数学等价**，至今未区分。

本脚本按「三本共享总大小」猜想造一组测试例：**每本都远小于单本上限，
但总量超过总量阈值**。若引擎仍能出词，则「总量假设」被否证。

每本都带独有探针
----------------
    njubase1.a  →  打 ``nbp1``  →  「探针一」
    njubase2.a  →  打 ``nbp2``  →  「探针二」
    njubase3.a  →  打 ``nbp3``  →  「探针三」

这样不仅知道「装成功了没有」，还知道「**哪一本被读取了**」。
（引擎对读法形态零校验，``0000``/``zzzz`` 都能命中 —— 见 FINDINGS §5.2。）

产出
----
    04_Outputs/tests/<用例>/atmosphere/contents/0100000000000805/romfs/
        Iwnn/ZH/CN/pinyin/{GB18030,GB2312}/njubase{1,2,3}.a

判读说明**不另外生成文件** —— 工程约定只有一个说明文档：见根目录 `README.md`
的「判别测试包」一节。本脚本跑完也会把用例一览打到终端。

用法
----
    python 05_Code/tools/mk_probe_tests.py           # 全部用例
    python 05_Code/tools/mk_probe_tests.py --only t1 # 只做某一个
"""
import argparse
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from build_from_lexicon import (ROOT, LEX, ORIG, ATMO_BASE, ENCODINGS,
                                load_tsv, take_by_budget, write_dict,
                                build_base3_entries)
from mkdict import is_cjk_word

TESTS = os.path.join(ROOT, "04_Outputs", "tests")
CACHE = os.path.join(TESTS, "_cache")

# 每本注入的探针：(读法, 表记)
PROBES = {1: ("nbp1", "探针一"),
          2: ("nbp2", "探针二"),
          3: ("nbp3", "探针三")}

# ---------------------------------------------------------------------------
# 测试用例：(ID, base3 目标MB, base1 目标MB, base2 目标MB, base3 是否加简拼, 说明)
#   目标 0 表示「只放该本原版条目 + 探针」（体积约 = 原版）
#
#   注意：目标值是**近似**的。take_by_budget 的成本模型刻意保守（估算 ≥ 实际），
#   所以产出的文件会比目标小 10~40%。以下数值已按实测校准过一次。
# ---------------------------------------------------------------------------
CASES = [
    ("t0-baseline",   4.5, 0.0,  0.0,  True,
     "基线：只有 base3 大（≈ §15 已知可用的配置），base1/base2 仅原版+探针"),
    ("t1-b1-2m",      4.5, 2.0,  0.0,  True,
     "★关键判别：base3 一个字节没动，只把 base1 加到 ~2 MB（仍远低于单本上限 4.6）"),
    ("t2-three-3m",   3.0, 3.0,  3.0,  False,
     "三本都只有 ~2.5 MB（远低于单本上限 4.6），但总量 ≈ 8 MB"),
    ("t3-full",       4.5, 4.28, 4.42, True,
     "当前交付配置的三本（总量 ≈ 13 MB）"),
]

# 并入原版条目后的「基础体积」(MB)。
# base1/base2 原版本就是干净版式；base3 原版带 662 KB 附加区，
# 换成干净版式后会变小 —— 实测 57,954 条 ≈ 1.30 MB。
BASE_MB = {1: 0.09, 2: 0.09, 3: 1.30}


def orig_size(n):
    """该本原版词典的字节数（用于把目标文件大小换算成新词片预算）。"""
    return os.path.getsize(os.path.join(ORIG, "njubase%d.a" % n))


def case_dirs(tag):
    root = os.path.join(TESTS, tag)
    return [os.path.join(root, *ATMO_BASE, enc) for enc in ENCODINGS]


def patch_paths(n, dirs):
    return [os.path.join(d, "njubase%d.a" % n) for d in dirs]


def build_case(tag, mb3, mb1, mb2, abbrev3, keep):
    """生成一个用例。返回 {本号: (条数, 字节数)}。"""
    dirs = case_dirs(tag)
    stats = {}
    pos = 0

    # ---------------- base3 ----------------
    if abbrev3:
        # 与 build_from_lexicon.py 同款配置：130,000 词 + 简拼（**已去重**，
        # 否则重复条目会让引擎拒绝加载整个词典 —— FINDINGS §15.4）
        ents, n_abbr, n_drop = build_base3_entries(keep, 130000, 60000, verbose=False)
        ents = ents + [PROBES[3]]
        pos += 130000
        note = "（130,000 词 + %d 条简拼，丢弃撞车 %d）" % (n_abbr, n_drop)
    else:
        budget3 = max(0.3, mb3 - BASE_MB[3])
        chunk3 = take_by_budget(keep, pos, budget3)
        pos += len(chunk3)
        ents = [(r[0], r[2]) for r in chunk3] + [PROBES[3]]
        note = "（纯全拼，无简拼）"
    sz, n, _ = write_dict(ents, os.path.join(ORIG, "njubase3.a"),
                          patch_paths(3, dirs), 32)
    stats[3] = (n, sz)
    print("      base3 %s %d 条" % (note, n))

    # ---------------- base1 / base2 ----------------
    for idx, mb in ((1, mb1), (2, mb2)):
        if mb > 0:
            budget = max(0.05, mb - BASE_MB[idx])
            chunk = take_by_budget(keep, pos, budget)
            pos += len(chunk)
            entries = [(r[0], r[2]) for r in chunk]
        else:
            entries = []
        entries.append(PROBES[idx])
        sz, n, _ = write_dict(entries, os.path.join(ORIG, "njubase%d.a" % idx),
                              patch_paths(idx, dirs), 32)
        stats[idx] = (n, sz)

    return stats


def total_visible(stats):
    """引擎可见总量 = 三本 + 未动的 njtan/njcode/njexyomi。"""
    untouched = sum(os.path.getsize(os.path.join(ORIG, f))
                    for f in ("njtan.a", "njcode.a", "njexyomi.a"))
    return sum(s for _, s in stats.values()) + untouched


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default=None, help="只生成指定用例（如 t1）")
    a = ap.parse_args()

    tsv = os.path.join(LEX, "ALL.tsv")
    if not os.path.isfile(tsv):
        sys.exit("找不到 %s —— 先跑 mk_lexicon.py" % tsv)

    print("=== 读主词库 ===")
    rows = load_tsv(tsv)
    keep = [r for r in rows if is_cjk_word(r[2])
            and r[0].isascii() and r[0].isalpha()]
    print("  保留 %d 条\n" % len(keep))

    os.makedirs(TESTS, exist_ok=True)
    table = []
    for tag, mb3, mb1, mb2, ab3, desc in CASES:
        if a.only and a.only not in tag:
            continue
        print("=" * 78)
        print("用例 %s —— %s" % (tag, desc))
        print("  目标：base3=%.2f  base1=%.2f  base2=%.2f MB" % (mb3, mb1, mb2))
        print("=" * 78)
        st = build_case(tag, mb3, mb1, mb2, ab3, keep)
        tot = total_visible(st)
        got = tuple(st[i][1] / 1048576.0 for i in (3, 1, 2))
        print("  实际：base3=%.2f  base1=%.2f  base2=%.2f MB"
              "   引擎可见总量=%.2f MB\n"
              % (got[0], got[1], got[2], tot / 1048576.0))
        table.append((tag, desc, mb3, mb1, mb2, got, tot / 1048576.0))

    if table:
        print_table(table)
        print("完成。测试包在 %s" % TESTS)
        print("判读说明见根目录 README.md 的「判别测试包」一节。")
    return 0


def print_table(table):
    """把用例一览打印到终端。

    **不写文件** —— 工程约定只有一个说明文档（根目录 `README.md`），
    判读说明在它的「判别测试包」一节。
    """
    print()
    print("=" * 78)
    print("用例一览（%d 个）" % len(table))
    print("=" * 78)
    print("  %-14s %9s %9s %9s %11s" % ("用例", "base3", "base1", "base2", "引擎可见总量"))
    for tag, desc, mb3, mb1, mb2, got, tot in table:
        print("  %-14s %6.2f MB %6.2f MB %6.2f MB %8.2f MB"
              % (tag, got[0], got[1], got[2], tot))
    print()
    print("  探针：njubase1 -> nbp1「探针一」 / njubase2 -> nbp2「探针二」 / njubase3 -> nbp3「探针三」")
    print()
    print("  判读：")
    print("    0) 先装 t0-baseline —— 必须出词；不出说明装法/路径有问题。")
    print("    1) 再装 t1-b1-2m —— 它与 t0 只差 base1 从 0.09 -> 1.79 MB")
    print("       （远低于单本上限 4.6），所以：")
    print("         不出词 => 总量是限制，「每本独立预算」被否证，三本方案作废")
    print("         出词   => 单本假设成立")
    print()
    print("  完整判读说明见根目录 README.md 的「判别测试包」一节。")


if __name__ == "__main__":
    sys.exit(main())

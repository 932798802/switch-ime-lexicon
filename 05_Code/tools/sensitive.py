# -*- coding: utf-8 -*-
"""sensitive.py —— 敏感词过滤（词条级删除）

为什么不用「全库直接匹配」
--------------------------
`01_Inputs/sensitive/` 下的公开词库（Konsheng/Sensitive-lexicon，MIT）
是给**句子级上下文过滤**用的 —— 命中即打星号。而本工程做的是
**词条级删除**：删掉之后用户就打不出这个词了。两者语义完全不同。

实测反例（直接用全库精确匹配会删掉这些正常词）：
    制度 / 改革 / 政府 / 网络 / 系统 / 一个 / 土豆 / 几何 / 地址 / 镜子
    / 限量 / 阿拉伯 / 自拍 / 小学 / 病毒 / 饮水 / 蘑菇 / 丝袜 / 邮件

所以本模块采用两条约束把误伤压到最低：

  ① **只用核心库** —— 色情 / 暴恐 / 涉枪涉爆 / 反动。
     排除「零时-Tencent」「网易前端过滤」「GFW补充」「政治类型」「民生」
     「广告类型」等大杂烩库（它们把「客服」「招聘」「淘宝」也标成敏感）。
  ② **交叉验证** —— 一个词必须被至少 `MIN_LIBS` 个不同库标记才算数。
     单库标记的多是误伤（「几何」只被 1 个库标记）。

白名单
------
`01_Inputs/sensitive/whitelist.txt`（每行一个词，# 开头为注释）里的词
**永不删除**。用于豁免交叉验证也没能滤掉的偶发误伤。

用法
----
    from sensitive import SensitiveFilter
    sf = SensitiveFilter()
    if sf.is_bad(word): ...
"""
import os

# ---------------------------------------------------------------------------
# 核心库：词本身即违规（该词没有正常用法）
# ---------------------------------------------------------------------------
CORE_LIBS = (
    "色情类型.txt",
    "色情词库.txt",
    "暴恐词库.txt",
    "涉枪涉爆.txt",
    "反动词库.txt",
)

# 至少被几个库同时标记才算敏感
MIN_LIBS = 3

# 单字不删（2026-09-30 我定：单字是廉价填充物，且高频字会被误标）
MIN_LEN = 2

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
SENS_DIR = os.path.join(ROOT, "01_Inputs", "sensitive")
WHITELIST = os.path.join(SENS_DIR, "whitelist.txt")


def _read_words(path):
    out = set()
    if not os.path.isfile(path):
        return out
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            w = line.strip()
            if w and not w.startswith("#"):
                out.add(w)
    return out


class SensitiveFilter:
    """敏感词判定器。词库缺失时自动退化为「不过滤」，并在 verbose 下提示。"""

    def __init__(self, enabled=True, verbose=True, min_libs=MIN_LIBS,
                 min_len=MIN_LEN, ids_only=None):
        self.enabled = enabled
        self.min_len = min_len
        self.libs = {}                      # 库名 -> 词集合
        self.bad = set()                    # 最终敏感词集合
        self.whitelist = _read_words(WHITELIST)
        self.ids_only = set(ids_only) if ids_only else None   # 只统计指定来源

        if not enabled:
            if verbose:
                print("  [敏感词] 已停用（--no-sensitive）")
            return

        # 加载**全部**库：核心库决定「谁有资格被删」，全部库参与「交叉投票」。
        # 只加载核心库会导致交叉验证无票可投（5 个库里同时出现 ≥3 次的词极少）。
        for fn in sorted(os.listdir(SENS_DIR)) if os.path.isdir(SENS_DIR) else []:
            if not fn.endswith(".txt") or fn in ("LICENSE.txt", "whitelist.txt"):
                continue
            ws = _read_words(os.path.join(SENS_DIR, fn))
            if ws:
                self.libs[fn] = ws

        core = set()
        for name in CORE_LIBS:
            core |= self.libs.get(name, set())
        if not core:
            if verbose:
                print("  [敏感词] 核心库为空 —— 跳过过滤")
            return

        # 交叉投票：一个词被多少个库标记
        cnt = {}
        for ws in self.libs.values():
            for w in ws:
                cnt[w] = cnt.get(w, 0) + 1

        # 入选条件：① 出现在核心库（词本身违规）② 被 ≥min_libs 个库标记
        # ③ 不是单字 ④ 不在白名单
        self.bad = {w for w in core
                    if cnt.get(w, 0) >= min_libs
                    and len(w) >= min_len
                    and w not in self.whitelist}
        self._all_hits = core
        self.hit_count = {w: cnt.get(w, 0) for w in self.bad}

        if verbose:
            print("  [敏感词] 入库 %d 个 / 核心库候选 %d 条；"
                  "交叉验证(≥%d库) 后 %d 条，白名单豁免 %d 条"
                  % (len(self.libs), len(core), min_libs,
                     len(self.bad), len(self.whitelist)))

    # ------------------------------------------------------------------
    def is_bad(self, word):
        if not self.enabled or not word:
            return False
        if len(word) < self.min_len:
            return False
        return word in self.bad

    def n_libs(self, word):
        """该词被几个库标记（用于生成审核清单）。"""
        return sum(1 for ws in self.libs.values() if word in ws)

    @property
    def all_hits(self):
        """所有被任一核心库命中的词（含被交叉验证滤掉的），供审核。"""
        return getattr(self, "_all_hits", set())


def filter_rows(rows, sf, verbose=True):
    """从 rows 里剔除敏感词条。rows: [(full, abbr, word, weight, src)]。

    返回 (保留列表, 被删列表)。被删的用于生成审核清单。
    """
    if not sf.enabled or not sf.bad:
        return list(rows), []
    keep, drop = [], []
    for r in rows:
        if sf.is_bad(r[2]):
            drop.append(r)
        else:
            keep.append(r)
    if verbose and drop:
        print("  [敏感词] 从词源剔除 %d 条" % len(drop))
    return keep, drop


def write_removed_report(drop, path, sf=None, verbose=True):
    """写删除清单（供人工审核）：词<TAB>全拼<TAB>来源<TAB>库数"""
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("# 敏感词删除清单（自动生成，供审核）\n")
        f.write("# 判定：核心库（色情/暴恐/涉枪涉爆/反动）中 ≥%d 个库交叉标记\n" % MIN_LIBS)
        f.write("# 列：中文<TAB>全拼<TAB>来源<TAB>标记库数\n")
        f.write("# 若认为某条是误伤，把它加进 01_Inputs/sensitive/whitelist.txt\n")
        for r in sorted(drop, key=lambda x: x[2]):
            n = sf.n_libs(r[2]) if sf else 0
            f.write("%s\t%s\t%s\t%d\n" % (r[2], r[0], r[4] if len(r) > 4 else "", n))
    if verbose:
        print("  删除清单 -> %s  (%d 条)" % (os.path.relpath(path, ROOT), len(drop)))

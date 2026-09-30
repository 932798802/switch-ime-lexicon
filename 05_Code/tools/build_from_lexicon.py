# -*- coding: utf-8 -*-
"""build_from_lexicon.py —— 以 `01_Inputs/lex/ALL.tsv` 为**唯一输入**生成 NS 词典（NJDC）。

闭环的另一半
------------
    01_Inputs/lex/*.yaml (rime-ice)  ─┐
    01_Inputs/lex/game.txt (游戏词)   ─┴─>  mk_lexicon.py  ─>  01_Inputs/lex/ALL.tsv
                                                                     │
                                                   本脚本  ──────────┘
                                                     └─> 04_Outputs/<v版本>/atmosphere/
                                                            contents/0100000000000805/romfs/
                                                            Iwnn/ZH/CN/pinyin/{GB18030,GB2312}/
                                                                njubase1.a   njubase2.a   njubase3.a

**以后加词、改拼音、调优先级，只编辑 ALL.tsv 再跑本脚本即可**，不必再动 yaml。
（ALL.tsv 是纯文本，手工编辑没问题 —— 它只是纯文本。）

分片策略（为什么是三本）
------------------------
实测确认：单本上限约 4.6 MB 文件字节数，但**每本有各自独立的预算**
（探针 `nbprobe` 能被打出来，见根 README.md 的「技术侦察报告」节 §18）。所以把词分散到
base1/2/3 三本，总容量约为三倍。

  * base3（主词库）：权重最高的 N 个词 **+ 它们的简拼**（既有的可用配置）
  * base1 / base2  ：继续按权重往下取，各自按「目标字节数」切（不是按条数 ——
                      同样条数下，词更长的那批文件会大很多，按条数切会撞上限）

用法
----
    python 05_Code/tools/build_from_lexicon.py
    python 05_Code/tools/build_from_lexicon.py --base3-words 130000 --mb1 4.28 --mb2 4.42

产出布局（版本号取自根目录 `VERSION`）::

    04_Outputs/v0.1/atmosphere/contents/0100000000000805/romfs/Iwnn/ZH/CN/pinyin/
        GB18030/njubase1.a   njubase2.a   njubase3.a
        GB2312/njubase1.a    njubase2.a   njubase3.a

把 `04_Outputs/v0.1/atmosphere/` 整个拷到 SD 卡根目录即可（与卡上已有的
atmosphere 合并/覆盖）。回滚 = 删掉卡上的 `contents/0100000000000805/`，
固件原版立即恢复（全程不动 NAND）。
"""
import argparse
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))     # ns-ime/
LEX = os.path.join(ROOT, "01_Inputs", "lex")
OUTPUTS = os.path.join(ROOT, "04_Outputs")
sys.path.insert(0, HERE)

import njdc_lib as L
from mkdict import is_cjk_word

# 原版固件词典（与新版合并，保证不丢原覆盖）。
# 2026-09-30 目录重组后位于 01_Inputs/firmware/ 下。
ORIG = os.path.join(ROOT, "01_Inputs", "firmware", "dat0805", "files", "Iwnn",
                    "ZH", "CN", "pinyin", "GB18030")

# ---------------------------------------------------------------------------
# 产物布局：直接铺成 SD 卡上的样子，整个 <版本> 目录拷过去就能用
#
#   <OUTPUTS>/<v版本>/atmosphere/contents/0100000000000805/romfs/Iwnn/ZH/CN/pinyin/
#       GB18030/njubase{1,2,3}.a
#       GB2312/njubase{1,2,3}.a
#
# GB18030 与 GB2312 是系统里并列的两套编码目录（§9.5），两套都放一份，
# 无论设备走哪套都能命中 —— 代价只是多占一份空间。
# ---------------------------------------------------------------------------
ATMO_BASE = ("atmosphere", "contents", "0100000000000805", "romfs",
             "Iwnn", "ZH", "CN", "pinyin")
ENCODINGS = ("GB18030", "GB2312")


def version_tag():
    """读根目录 VERSION（内容形如 `0.1`）-> 目录名 `v0.1`。"""
    p = os.path.join(ROOT, "VERSION")
    v = open(p, encoding="utf-8").read().strip() if os.path.isfile(p) else "0"
    return "v" + (v or "0")


def out_dirs():
    """要写出的编码目录列表（每个编码目录一份）。"""
    root = os.path.join(OUTPUTS, version_tag())
    return [os.path.join(root, *ATMO_BASE, enc) for enc in ENCODINGS]


def load_tsv(path, verbose=True):
    """读 ALL.tsv -> [(全拼, 简拼, 中文, 权重)]，按权重降序。"""
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line or line.startswith("#"):
                continue
            p = line.split("\t")
            if len(p) < 4:
                continue
            full, abbr, word = p[0].strip(), p[1].strip(), p[2].strip()
            try:
                w = float(p[3])
            except ValueError:
                w = 1.0
            if not full or not word:
                continue
            rows.append((full, abbr, word, w))

    rows.sort(key=lambda r: -r[3])
    if verbose:
        print("  读入 %-30s %d 条" % (os.path.basename(path), len(rows)))
    return rows


def take_by_budget(pool, start, mb_target, verbose_tag=""):
    """按「文件大小预算」从 pool[start:] 顺序取词。

    成本模型（保守，故意略高估）：
        每条 = 12（记录表 10 + 尾表 2）
             + 2*len(读法)  若该读法首次出现
             + 2*len(表记)  若该表记首次出现
    忽略「极大串共享」（子串不重复存），所以估算 >= 实际 —— 切出来偏小、偏安全。
    """
    budget = int(mb_target * 1048576)
    left = budget - (1146 + 4 + 8192)          # 头/索引/magic + 余量
    seen_r, seen_w = set(), set()
    out = []
    for full, abbr, word, w in pool[start:]:
        c = 12
        if full not in seen_r:
            c += 2 * len(full)
        if word not in seen_w:
            c += 2 * len(word)
        if c > left:
            break
        left -= c
        seen_r.add(full)
        seen_w.add(word)
        out.append((full, abbr, word, w))
    return out


def write_dict(entries, merge_path, out_paths, tail_v, verbose=True):
    """entries: [(读法, 表记)]；并入 merge_path 的原版条目后写出 NJDC。

    out_paths: 输出路径列表 —— 同一份内容写到每个路径
               （用于「GB18030 / GB2312 双编码目录各放一份」）。
    """
    if isinstance(out_paths, str):
        out_paths = [out_paths]
    have = set(entries)
    ents = list(entries)
    n_orig = 0
    if merge_path and os.path.isfile(merge_path):
        o = L.parse_njdc(open(merge_path, "rb").read())
        for e in o["entries"]:
            if e not in have:
                ents.append(e)
                have.add(e)
                n_orig += 1
        if verbose:
            print("        并入原版 %-14s %d 条（新增 %d）"
                  % (os.path.basename(merge_path), o["N"], n_orig))
    ents.sort(key=lambda e: e[0].encode("utf-16-be"))
    out = L.build_njdc(ents, tail_values=[tail_v] * len(ents))
    for p in out_paths:
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "wb") as f:
            f.write(out)

    d = L.parse_njdc(out)
    assert d["N"] == len(ents)
    if verbose:
        rel = os.path.relpath(out_paths[0], ROOT).replace("\\", "/")
        print("      %6d 条  %9d B (%.2f MB)  ->  %s%s"
              % (len(ents), len(out), len(out) / 1048576.0, rel,
                 "" if len(out_paths) == 1 else "  （共 %d 个编码目录各一份）" % len(out_paths)))
    return len(out), len(ents), n_orig


def build_base3_entries(keep, n_words, n_abbr, allow_dup=False, verbose=True):
    """base3 的条目 = 前 n_words 个词（全拼）+ **去重后**的简拼。

    简拼必须去重（对齐 mkdict.py 的 `have` / `collides`）：
      ① 同一词的**多个读法**可能算出**同一个简拼**（「不了」buliao/bule 都 → `bl`）；
      ② 简拼串可能是同词其它读法的前缀。
    两类都会产生「同一 `(读法, 表记)` 出现两次」的重复条目，而实测已证明
    **重复条目会让引擎拒绝加载整个词典**（FINDINGS §15.4）。

    返回 `(entries, n_abbr, n_dropped)`。
    """
    b3 = keep[:n_words]
    ents = [(r[0], r[2]) for r in b3]
    have = set(ents)
    byword = {}
    for full, _ab, word, _w in b3:
        byword.setdefault(word, []).append(full)

    def collides(ab, word):
        return any(r.startswith(ab) for r in byword.get(word, []) if r != ab)

    n_drop = 0
    for full, abbr, word, w in b3[:n_abbr]:
        if not abbr or abbr == "-" or abbr == full:
            continue
        k = (abbr, word)
        if k in have:
            continue
        if not allow_dup and collides(abbr, word):
            n_drop += 1
            continue
        have.add(k)
        byword.setdefault(word, []).append(abbr)
        ents.append(k)
    if verbose:
        print("      %d 个词 + %d 条简拼（丢弃同词撞车 %d 条）"
              % (len(b3), len(ents) - len(b3), n_drop))
    return ents, len(ents) - len(b3), n_drop


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tsv", default=None, help="主词库（默认 lex/ALL.tsv）")
    ap.add_argument("--base3-words", type=int, default=130000,
                    help="base3 取多少个权重最高的词（默认 130000：实测 150000 会让"
                         "合并原版条目后的文件涨到 5.06 MB，超过约 4.92 MB 的失败点）")
    ap.add_argument("--abbrev-limit", type=int, default=60000,
                    help="base3 里生成多少条简拼")
    ap.add_argument("--abbrev-allow-dup", action="store_true",
                    help="不过滤「与同词其它读法撞车」的简拼（默认过滤，见 build 内注释）")
    ap.add_argument("--mb1", type=float, default=4.28, help="base1 目标大小(MB)")
    ap.add_argument("--mb2", type=float, default=4.42, help="base2 目标大小(MB)")
    ap.add_argument("--tail-word", type=int, default=32, help="新词尾表值 0..63")
    ap.add_argument("--tail-abbr", type=int, default=58, help="简拼尾表值 0..63")
    a = ap.parse_args()

    tsv = a.tsv or os.path.join(LEX, "ALL.tsv")
    if not os.path.isfile(tsv):
        sys.exit("找不到主词库 %s —— 先跑 tools/mk_lexicon.py" % tsv)

    print("=== 产物版本 %s ===" % version_tag())
    print("    输出：04_Outputs/%s/atmosphere/contents/0100000000000805/romfs/"
          "Iwnn/ZH/CN/pinyin/{GB18030,GB2312}/" % version_tag())
    print()
    print("=== 1. 读主词库 ===")
    rows = load_tsv(tsv)

    # 过滤（与 mk_lexicon.py 保持一致）
    print("=== 2. 过滤 ===")
    keep = [r for r in rows if is_cjk_word(r[2])
            and r[0].isascii() and r[0].isalpha()]
    print("  保留 %d 条" % len(keep))

    # ---------------- base3：前 N 词 + 简拼 ----------------
    print("=== 3. base3（主词库 + 简拼） ===")
    b3_entries, n_abbr, n_collide = build_base3_entries(
        keep, a.base3_words, a.abbrev_limit, a.abbrev_allow_dup)

    dirs = out_dirs()

    def paths(name):
        return [os.path.join(d, name) for d in dirs]

    sz3, n3, _merged3 = write_dict(b3_entries,
                                   os.path.join(ORIG, "njubase3.a"),
                                   paths("njubase3.a"), a.tail_word)

    # ---------------- base1 / base2：按字节预算继续取 ----------------
    pos = a.base3_words
    print("=== 4. base1（目标 %.2f MB） ===" % a.mb1)
    chunk1 = take_by_budget(keep, pos, a.mb1)
    pos += len(chunk1)
    print("      %d 条" % len(chunk1))
    sz1, n1, _m1 = write_dict([(r[0], r[2]) for r in chunk1],
                              os.path.join(ORIG, "njubase1.a"),
                              paths("njubase1.a"), a.tail_word)

    print("=== 5. base2（目标 %.2f MB） ===" % a.mb2)
    chunk2 = take_by_budget(keep, pos, a.mb2)
    pos += len(chunk2)
    print("      %d 条" % len(chunk2))
    sz2, n2, _m2 = write_dict([(r[0], r[2]) for r in chunk2],
                              os.path.join(ORIG, "njubase2.a"),
                              paths("njubase2.a"), a.tail_word)

    # 汇总（产物即 04_Outputs/<版本>/atmosphere/... 下的三本 .a）
    print()
    print("三本合计 %d 条（base3 %d + base1 %d + base2 %d）"
          % (len(b3_entries) + len(chunk1) + len(chunk2),
             len(b3_entries), len(chunk1), len(chunk2)))
    print("词库剩余未用 %d 条" % max(0, len(keep) - pos))
    return 0


if __name__ == "__main__":
    sys.exit(main())

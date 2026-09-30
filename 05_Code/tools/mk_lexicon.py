# -*- coding: utf-8 -*-
"""mk_lexicon.py -- 把所有词源**汇总成一个主词库文件**，供后续生成 NS 词典使用。

输出格式（TSV，可用 Excel / 文本编辑器打开编辑）
----------------------------------------------
    全拼<TAB>简拼<TAB>中文<TAB>权重<TAB>来源

    shalujianta	sljt	杀戮尖塔	100000	game

  * **全拼**：音节连写，设备口径（ü → v），字母小写。
  * **简拼**：每个音节的首字母；单音节词（一个字）不生成简拼，写 `-`。
  * **中文**：要输出的候选词。
  * **权重**：越大越优先被选中（分词片时按此排序）。
  * **来源**：`ice_8105` / `ice_base` / `ice_ext` / `game`。

**用途**：这是「人可读、可改」的中间层 ——
想加词、改拼音、调优先级，直接编辑这一个文件即可，不必再动各个 yaml。
之后由生成器读它产出 NJDC 词典。

为什么要单独生成它，而不是沿用 parse_rime
-----------------------------------------
`mkdict.parse_rime()` 会把音节空格去掉变成连写（`sha lu jian ta` → `shalujianta`），
**音节边界就丢了**，之后没法再算「首字母简拼」。
所以本脚本自己解析 Rime yaml，**保留音节**再分别导出全拼与简拼。
"""
import argparse
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))     # ns-ime/
LEX = os.path.join(ROOT, "01_Inputs", "lex")
sys.path.insert(0, HERE)

from mkdict import is_cjk_word
from sensitive import SensitiveFilter, filter_rows, write_removed_report

# 设备口径：ü → v（与 mkdict / 设备一致）
TRANS = str.maketrans({"ü": "v", "ǖ": "v", "ǘ": "v", "ǚ": "v", "ǜ": "v"})


def norm_syllables(syl):
    """'shā lu jian ta' -> ['sha','lu','jian','ta']（去掉声调符号、ü→v）"""
    out = []
    for s in syl.replace("-", " ").split():
        s = s.strip().lower()
        if not s:
            continue
        # 去掉拼音声调符号（带声调的字母）
        s = "".join(ch for ch in s if ch.isascii() and ch.isalpha())
        if s:
            out.append(s.translate(TRANS))
    return out


def load_rime(path, source, verbose=True):
    """读 Rime 词库 yaml，保留音节。返回 [(中文, 音节list, 权重)]。"""
    out = []
    started = False
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not started:
                if line.strip() == "...":
                    started = True
                continue
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) < 2:
                continue
            word = parts[0].strip()
            syl = norm_syllables(parts[1])
            if not word or not syl:
                continue
            w = 1.0
            if len(parts) >= 3:
                try:
                    w = float(parts[2])
                except ValueError:
                    w = 1.0
            out.append((word, syl, w))
    if verbose:
        print("  %-34s %7d 条  [%s]" % (os.path.basename(path), len(out), source))
    return [(w_, s_, wt, source) for (w_, s_, wt) in out]


def load_game(path, weight, verbose=True):
    """读游戏词表（中文 + 分音节拼音）。返回 [(中文, 音节list, 权重)]。"""
    out = []
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        word = parts[0]
        syl = norm_syllables(" ".join(parts[1:]))
        if not word or not syl:
            continue
        out.append((word, syl, weight, "game"))
    if verbose:
        print("  %-34s %7d 条  [game]" % (os.path.basename(path), len(out)))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lex", action="append", default=[], help="Rime 词库 yaml")
    ap.add_argument("--game", default=None, help="游戏词表（中文 + 分音节拼音）")
    ap.add_argument("--game-weight", type=float, default=100000.0,
                    help="游戏词条的权重（默认 100000，保证优先入选）")
    ap.add_argument("--out", default=None)
    ap.add_argument("--maxwlen", type=int, default=6,
                    help="词长上限（字）。默认 6 —— 删掉 7 字及以上的超长词"
                         "（2026-09-30 我要求；此前为 11）")
    ap.add_argument("--maxrlen", type=int, default=36)
    ap.add_argument("--no-sensitive", action="store_true",
                    help="停用敏感词过滤")
    ap.add_argument("--removed-report",
                    default="10_Other/sensitive-removed-lexicon.txt",
                    help="被敏感词过滤剔除的清单（供人工审核）")
    a = ap.parse_args()

    lex = a.lex or [os.path.join(LEX, f)
                    for f in ("ice_8105.yaml", "ice_base.yaml", "ice_ext.yaml")]
    game = a.game or os.path.join(LEX, "game.txt")
    out_path = a.out or os.path.join(LEX, "ALL.tsv")

    src_map = {"ice_8105.yaml": "ice_8105", "ice_base.yaml": "ice_base",
               "ice_ext.yaml": "ice_ext"}

    print("=== 读取词源 ===")
    rows = []                       # (中文, 音节list, 权重, 来源)
    for p in lex:
        tag = src_map.get(os.path.basename(p), os.path.basename(p))
        rows += load_rime(p, tag)
    if game and os.path.exists(game):
        rows += load_game(game, a.game_weight)

    print("  原始合计 %d 条" % len(rows))

    print("=== 过滤与去重 ===")
    # 注意：游戏词条可能与 rime 词库重复（同 全拼+中文）。
    # 这种情况下**以游戏词表为准**：把权重提到 --game-weight 并把来源改成 game，
    # 否则游戏词会带着 rime 的低权重（常见 100）沉到 88 万条的最后，
    # 后续按权重取词时会被漏掉。
    best = {}
    n_long = 0
    for word, syl, w, src in rows:
        if not is_cjk_word(word):
            continue
        full = "".join(syl)
        if not full or not full.isascii() or not full.isalpha():
            continue
        if len(word) > a.maxwlen or len(full) > a.maxrlen:
            if len(word) > a.maxwlen:
                n_long += 1
            continue
        # 简拼：多音节才生成（单音节 = 单字，简拼等于全拼，没意义）
        abbr = "".join(s[0] for s in syl) if len(syl) >= 2 else "-"
        key = (full, word)
        if key in best:
            if src == "game":
                best[key] = (abbr, max(best[key][1], a.game_weight), "game")
            continue
        best[key] = (abbr, w if src != "game" else a.game_weight, src)

    keep = [(k[0], v[0], k[1], v[1], v[2]) for k, v in best.items()]
    keep.sort(key=lambda r: -r[3])
    print("  超长词（>%d 字）剔除 %d 条" % (a.maxwlen, n_long))

    print("=== 敏感词过滤 ===")
    sf = SensitiveFilter(enabled=not a.no_sensitive)
    keep, drop = filter_rows(keep, sf)
    if drop:
        rp = (a.removed_report if os.path.isabs(a.removed_report)
              else os.path.join(ROOT, a.removed_report))
        os.makedirs(os.path.dirname(rp), exist_ok=True)
        write_removed_report(drop, rp, sf)

    n_game = sum(1 for r in keep if r[4] == "game")
    print("  保留 %d 条（其中标记为 game 的 %d 条）" % (len(keep), n_game))

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8", newline="\n") as f:
        f.write("# NS 输入法主词库（汇总）\n")
        f.write("# 列：全拼<TAB>简拼<TAB>中文<TAB>权重<TAB>来源\n")
        f.write("# 简拼 = 多音节词各音节首字母；单音节词写 -\n")
        f.write("# 词源：rime-ice（8105/base/ext）+ game（游戏词条）\n")
        f.write("# 权重大者优先入选；游戏词条默认权重 100000\n")
        for full, abbr, word, w, src in keep:
            f.write("%s\t%s\t%s\t%g\t%s\n" % (full, abbr, word, w, src))
    print("写出 %s  %d 行" % (out_path, len(keep)))

    # 抽查
    game_rows = [r for r in keep if r[4] == "game"]
    print("其中游戏词条 %d 条，示例：" % len(game_rows))
    for full, abbr, word, w, src in game_rows[:6]:
        print("   %-14s %-6s %s" % (full, abbr, word))


if __name__ == "__main__":
    main()

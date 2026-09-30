# -*- coding: utf-8 -*-
"""mk_game.py —— 把 `game-words.txt`（纯词）自动注音后并入 `game.txt`

`game.txt` 的格式是「词 + 空格分隔的音节」，手工维护 1000+ 条太容易出错，
所以扩充词表用纯词写（`game-words.txt`），由本脚本用 pypinyin 注音后合并。

特性
----
* **不覆盖已有条目** —— `game.txt` 里手工写的读音优先保留（pypinyin 对
  多音字未必准，例如「重制」的「重」应为 chong）。
* 自动跳过 **超过 --maxwlen 字** 或 **含非汉字** 的词，并报告。
* 幂等：重复运行不会产生重复行。

用法
----
    python 05_Code/tools/mk_game.py            # 并入
    python 05_Code/tools/mk_game.py --dry-run  # 只看会加什么
"""
import argparse
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
LEX = os.path.join(ROOT, "01_Inputs", "lex")
sys.path.insert(0, HERE)

from mkdict import is_cjk_word          # noqa: E402

SRC = os.path.join(LEX, "game-words.txt")
DST = os.path.join(LEX, "game.txt")

# 多音字手工修正（pypinyin 默认读音在游戏词里会读错的）
OVERRIDE = {
    "重制": ["chong", "zhi"],
    "重置": ["chong", "zhi"],
    "传说": ["chuan", "shuo"],
    "无双": ["wu", "shuang"],
    "单机": ["dan", "ji"],
    "上传": ["shang", "chuan"],
    "长按": ["chang", "an"],
}


def read_existing(path):
    """读 game.txt -> {词: [音节...]}（保留原有条目与读音）"""
    out = {}
    if not os.path.isfile(path):
        return out
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            p = line.split()
            if len(p) >= 2:
                out[p[0]] = p[1:]
    return out


def read_words(path):
    """读纯词表 -> [词]（去重、保序）"""
    seen, out = set(), []
    with open(path, encoding="utf-8") as f:
        for line in f:
            w = line.strip()
            if not w or w.startswith("#"):
                continue
            if w not in seen:
                seen.add(w)
                out.append(w)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--maxwlen", type=int, default=6)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    if not os.path.isfile(SRC):
        sys.exit("找不到 %s" % SRC)
    try:
        from pypinyin import lazy_pinyin
    except ImportError:
        sys.exit("需要 pypinyin：python -m pip install pypinyin")

    existing = read_existing(DST)
    words = read_words(SRC)
    print("现有 game.txt: %d 条；词表 %s: %d 个词" % (len(existing), os.path.basename(SRC), len(words)))

    added, skip_len, skip_nonhanzi, dup = [], [], [], 0
    for w in words:
        if w in existing:
            dup += 1
            continue
        if len(w) > a.maxwlen:
            skip_len.append(w)
            continue
        if not is_cjk_word(w):
            skip_nonhanzi.append(w)
            continue
        syl = OVERRIDE.get(w) or lazy_pinyin(w)
        if not syl or not "".join(syl).isascii() or not "".join(syl).isalpha():
            skip_nonhanzi.append(w)
            continue
        added.append((w, syl))

    print()
    print("重复(已存在)  : %4d" % dup)
    print("新增          : %4d" % len(added))
    print("跳过·超长     : %4d %s" % (len(skip_len), skip_len[:6]))
    print("跳过·非汉字   : %4d %s" % (len(skip_nonhanzi), skip_nonhanzi[:6]))
    print()
    print("新增样例:")
    for w, syl in added[:12]:
        print("   %-14s %s" % (w, " ".join(syl)))
    if added[12:]:
        print("   ... 共 %d 条" % len(added))

    if a.dry_run:
        print("\n（--dry-run，未写入）")
        return 0

    # 合并写回：原有条目保持原样，新词追加
    lines = []
    if os.path.isfile(DST):
        with open(DST, encoding="utf-8") as f:
            body = [l.rstrip("\n") for l in f]
    else:
        body = []
    for l in body:
        lines.append(l)
    if lines and lines[-1].strip():
        lines.append("")
    lines.append("# ---- 以下由 mk_game.py 自动注音并入（源自 game-words.txt）----")
    for w, syl in added:
        lines.append("%s %s" % (w, " ".join(syl)))

    with open(DST, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    print("\n写出 %s  共 %d 条" % (DST, len(existing) + len(added)))
    return 0


if __name__ == "__main__":
    sys.exit(main())

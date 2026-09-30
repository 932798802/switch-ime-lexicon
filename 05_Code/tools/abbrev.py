# -*- coding: utf-8 -*-
"""abbrev.py —— 首字母缩写（简拼）支持。

【目的】
让「打首字母出词」成为可能：`sljt` → 杀戮尖塔、`aedfh` → 艾尔登法环。
做法是**给多字词额外追加一条「首字母读法」条目**，而不是改引擎。

【为什么字→拼音表要从设备里取，而不是自己写】
拼音首字母必须与设备口径**逐字一致**，否则缩写对不上。设备自己的单字词典
`njtan.a`（title `0100000000000805`）里就有权威映射：12,503 个汉字、704 个多音字，
且天然满足设备口径（ü 写作 v：律=lü→`lv`；谁=`shei`/`shui`；血=`xie`/`xue`；
钥=`yao`/`yue`；壳=`ke`/`qiao`…）。自己拍一份音节表反而容易错。

【重要前提：这是未经验证的行为】
实测原版 `njubase3.a` 的全部 57,954 条读法，用设备自带的 415 个合法音节去切分
**100% 都能切开、零例外** —— 说明读法字段被当作「音节序列」看待，词典里
**没有任何一条纯辅音缩写先例**。
所以「加一条 `sljt` 读法引擎就能匹配到」是**假设，不是事实**：
若引擎在匹配前做音节切分／合法性校验，辅音串会被丢弃，简拼就不会生效。
**必须先出一个只含少量简拼条目的冒烟包，实机打 `sljt` 验证。**

失败也不会破坏任何东西：那些条目只是永远匹配不到而已。
"""

import itertools

# 汉字区间（与 mkdict.is_cjk_word 保持一致）
CJK = [(0x3400, 0x4DBF), (0x4E00, 0x9FFF), (0xF900, 0xFAFF), (0x20000, 0x3FFFF)]


def is_cjk_char(c):
    o = ord(c)
    return any(a <= o <= b for a, b in CJK)


def load_char_pinyin(njtan_path):
    """从设备单字词典 njtan.a 建立 {汉字: [拼音, ...]}（已去重、按字母序）。

    多音字会有多个拼音（如 行 → hang/xing），因此缩写可能有多解。
    """
    import os
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import njdc_lib as L

    d = L.parse_njdc(open(njtan_path, "rb").read())
    m = {}
    for reading, writing in d["entries"]:
        if len(writing) != 1 or not is_cjk_char(writing):
            continue
        if not reading or not reading.isascii() or not reading.isalpha():
            continue
        m.setdefault(writing, set()).add(reading)
    return {k: sorted(v) for k, v in m.items()}


def abbrev_variants(word, charmap, max_combos=4):
    """返回该词的首字母缩写候选（可能多个，来自多音字）。

    - 逐字取拼音首字母，例如 杀戮尖塔 → s l j t → "sljt"
    - 长度 < 2 的缩写不生成（等于没缩写）
    - 多音字组合数用 max_combos 截断，避免组合爆炸
    - 任何一字不在表里（生僻字/非汉字）→ 放弃，返回 []
    """
    if len(word) < 2 or not all(is_cjk_char(c) for c in word):
        return []

    opts = []
    for ch in word:
        ps = charmap.get(ch)
        if not ps:
            return []
        letters = sorted({p[0] for p in ps if p})
        if not letters:
            return []
        opts.append(letters)

    out = []
    for combo in itertools.product(*opts):
        s = "".join(combo)
        if len(s) < 2:
            continue
        if s not in out:
            out.append(s)
        if len(out) >= max_combos:
            break
    return out


if __name__ == "__main__":
    import os
    import sys
    HERE = os.path.dirname(os.path.abspath(__file__))
    DEFAULT = os.path.join(HERE, "..", "..", "01_Inputs", "firmware",
                           "dat0805", "files", "Iwnn", "ZH", "CN",
                           "pinyin", "GB18030", "njtan.a")
    path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT
    cm = load_char_pinyin(path)
    print("字→拼音表：%d 个汉字（其中多音字 %d 个）"
          % (len(cm), sum(1 for v in cm.values() if len(v) > 1)))
    for w in ["杀戮尖塔", "艾尔登法环", "黑神话悟空", "宝可梦", "存档", "联机", "爆率",
              "周目", "北京大学", "年轻人", "照相机", "圆周率"]:
        print("   %-8s -> %s" % (w, abbrev_variants(w, cm)))
    print("   多音字样例 行/谁/血/钥/壳/重:")
    for w in ["行动", "谁知", "血液", "钥匙", "贝壳", "重庆"]:
        print("      %-6s -> %s" % (w, abbrev_variants(w, cm)))
    print("   生僻/非汉字 犇玊/abc ->", abbrev_variants("犇玊", cm), abbrev_variants("abc", cm))

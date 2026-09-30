# -*- coding: utf-8 -*-
"""mkdict.py —— 由 Rime 词库 + 游戏词表编译出可替换 njubase3.a 的 NJDC 词典。

用法:
  python mkdict.py --lex base.dict.yaml [--lex ext.dict.yaml] [--limit 120000]
                   --out ../dist/njubase3.a [--no-game]
                   [--abbrev none|games|all] [--abbrev-ref njtan.a] [--abbrev-v N]

词库行格式:  词 <TAB> 拼音音节(空格分隔) <TAB> 权重
输出的读法 = 拼音音节去掉空格（全小写 a-z，与设备口径一致：ü 用 v）

--abbrev 追加「首字母缩写」条目，让打首字母能出词（`sljt` → 杀戮尖塔）。
   none  = 不生成（默认）
   games = 只对游戏词表生成 —— **冒烟判定用**，增量极小
   all   = 对全部入选词生成 —— 完整体验（条目数大约翻倍）
  注意：这是**未经验证的行为**，详见 tools/abbrev.py 顶部说明。必须实机冒烟。
"""
import argparse
import math
import os
import sys
import hashlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import njdc_lib as L
import abbrev as AB

DEFAULT_NJTAN = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..",
                             "01_Inputs", "firmware",
                             "dat0805", "files", "Iwnn", "ZH", "CN", "pinyin",
                             "GB18030", "njtan.a")

# ---------------------------------------------------------------- 游戏词表
# 直接针对「没有游戏词库」这一痛点。拼音按设备口径（ü → v）。
GAME_WORDS = """
杀戮尖塔 sha lu jian ta
杀戮之塔 sha lu zhi ta
尖塔 jian ta
爬塔 pa ta
肉鸽 rou ge
类肉鸽 lei rou ge
独立游戏 du li you xi
主机游戏 zhu ji you xi
掌机 zhang ji
单机游戏 dan ji you xi
联机游戏 lian ji you xi
网络游戏 wang luo you xi
手游 shou you
端游 duan you
回合制 hui he zhi
即时战略 ji shi zhan lve
角色扮演 jue se ban yan
动作冒险 dong zuo mao xian
开放世界 kai fang shi jie
沙盒 sha he
模拟经营 mo ni jing ying
战棋 zhan qi
无双 wu shuang
割草 ge cao
魂系 hun xi
类魂 lei hun
刷子游戏 shua zi you xi
存档 cun dang
读档 du dang
云存档 yun cun dang
周目 zhou mu
二周目 er zhou mu
速通 su tong
无伤 wu shang
开荒 kai huang
毕业 bi ye
毕业装 bi ye zhuang
面板 mian ban
词条 ci tiao
天赋 tian fu
技能点 ji neng dian
装备 zhuang bei
副本 fu ben
刷怪 shua guai
爆率 bao lv
掉落 diao luo
氪金 ke jin
抽卡 chou ka
十连 shi lian
保底 bao di
歪了 wai le
欧皇 ou huang
非酋 fei qiu
皮肤 pi fu
时装 shi zhuang
血条 xue tiao
蓝条 lan tiao
暴击 bao ji
闪避 shan bi
格挡 ge dang
反弹 fan tan
减伤 jian shang
治疗 zhi liao
辅助 fu zhu
坦克 tan ke
输出 shu chu
打野 da ye
上单 shang dan
中单 zhong dan
射手 she shou
打团 da tuan
团战 tuan zhan
大招 da zhao
被动 bei dong
冷却 leng que
走位 zou wei
手感 shou gan
帧数 zhen shu
掉帧 diao zhen
画质 hua zhi
优化 you hua
独占 du zhan
第三方 di san fang
第一方 di yi fang
移植 yi zhi
复刻 fu ke
重制 chong zhi
高清重制 gao qing chong zhi
资料片 zi liao pian
季票 ji piao
内购 nei gou
付费下载 fu fei xia zai
试玩版 shi wan ban
体验版 ti yan ban
正式版 zheng shi ban
国行版 guo hang ban
港版 gang ban
限定版 xian ding ban
特典 te dian
典藏版 dian cang ban
塞尔达传说 sai er da chuan shuo
塞尔达 sai er da
宝可梦 bao ke meng
口袋妖怪 kou dai yao guai
精灵宝可梦 jing ling bao ke meng
超级马力欧 chao ji ma li ou
超级马里奥 chao ji ma li ao
马力欧 ma li ou
马里奥 ma li ao
马力欧赛车 ma li ou sai che
斯普拉遁 si pu la dun
喷射战士 pen she zhan shi
动物森友会 dong wu sen you hui
异度神剑 yi du shen jian
火焰纹章 huo yan wen zhang
火焰之纹章 huo yan zhi wen zhang
星之卡比 xing zhi ka bi
大金刚 da jin gang
密特罗德 mi te luo de
银河战士 yin he zhan shi
皮克敏 pi ke min
路易吉 lu yi ji
鬼屋 gui wu
三角战略 san jiao zhan lve
牧场物语 mu chang wu yu
星露谷物语 xing lu gu wu yu
符文工房 fu wen gong fang
歧路旅人 qi lu lv ren
八方旅人 ba fang lv ren
勇者斗恶龙 yong zhe dou e long
最终幻想 zui zhong huan xiang
炼金工房 lian jin gong fang
真女神转生 zhen nv shen zhuan sheng
女神异闻录 nv shen yi wen lu
皇家骑士团 huang jia qi shi tuan
战场女武神 zhan chang nv wu shen
魔界战记 mo jie zhan ji
逆转裁判 ni zhuan cai pan
洛克人 luo ke ren
恶魔城 e mo cheng
怪物猎人 guai wu lie ren
生化危机 sheng hua wei ji
鬼泣 gui qi
怪物弹珠 guai wu dan zhu
黑神话悟空 hei shen hua wu kong
黑神话 hei shen hua
悟空 wu kong
明末渊虚之羽 ming mo yuan xu zhi yu
影之刃零 ying zhi ren ling
失落之魂 shi luo zhi hun
卧龙苍天陨落 wo long cang tian yun luo
匹诺曹的谎言 pi nuo cao de huang yan
星刃 xing ren
剑星 jian xing
怪物猎人物语 guai wu lie ren wu yu
异度之刃 yi du zhi ren
原神 yuan shen
崩坏 beng huai
王者荣耀 wang zhe rong yao
英雄联盟 ying xiong lian meng
绝地求生 jue di qiu sheng
和平精英 he ping jing ying
我的世界 wo de shi jie
星际争霸 xing ji zheng ba
魔兽世界 mo shou shi jie
暗黑破坏神 an hei po huai shen
暗黑 an hei
巫师 wu shi
上古卷轴 shang gu juan zhou
辐射 fu she
刺客信条 ci ke xin tiao
神秘海域 shen mi hai yu
战神 zhan shen
最后生还者 zui hou sheng huan zhe
死亡搁浅 si wang ge qian
只狼 zhi lang
艾尔登法环 ai er deng fa huan
黑暗之魂 hei an zhi hun
血源诅咒 xue yuan zu zhou
仁王 ren wang
对马岛之魂 dui ma dao zhi hun
地平线 di ping xian
赛博朋克 sai bo peng ke
尼尔机械纪元 ni er ji xie ji yuan
空洞骑士 kong dong qi shi
哈迪斯 ha di si
死亡细胞 si wang xi bao
泰拉瑞亚 tai la rui ya
以撒的结合 yi sa de jie he
霓虹深渊 ni hong shen yuan
弹丸论破 dan wan lun po
主播女孩重度依赖 zhu bo nv hai zhong du yi lai
帝国时代 di guo shi dai
文明 wen ming
全面战争 quan mian zhan zheng
三国志 san guo zhi
真三国无双 zhen san guo wu shuang
信长之野望 xin zhang zhi ye wang
孤岛惊魂 gu dao jing hun
孤岛危机 gu dao wei ji
看门狗 kan men gou
全境封锁 quan jing feng suo
彩虹六号 cai hong liu hao
使命召唤 shi ming zhao huan
战地 zhan di
泰坦陨落 tai tan yun luo
光环 guang huan
极限竞速 ji xian jing su
尘埃 chen ai
足球经理 zu qiu jing li
实况足球 shi kuang zu qiu
fifa
逃生 tao sheng
寂静岭 ji jing ling
零 ling
如龙 ru long
审判之眼 shen pan zhi yan
女神异闻录5
异界锁链 yi jie suo lian
猎天使魔女 lie tian shi mo nv
忍者龙剑传 ren zhe long jian zhuan
死或生 si huo sheng
铁拳 tie quan
街霸 jie ba
拳皇 quan huang
真人快打 zhen ren kuai da
苍翼默示录 cang yi mo shi lu
罪恶装备 zui e zhuang bei
少女前线 shao nv qian xian
明日方舟 ming ri fang zhou
碧蓝航线 bi lan hang xian
命运冠位指定 ming yun guan wei zhi ding
fate
阴阳师 yin yang shi
第五人格 di wu ren ge
蛋仔派对 dan zai pai dui
元梦之星 yuan meng zhi xing
星空 xing kong
无人深空 wu ren shen kong
戴森球计划 dai sen qiu ji hua
鬼谷八荒 gui gu ba huang
太吾绘卷 tai wu hui juan
了不起的修仙模拟器 liao bu qi de xiu xian mo ni qi
波西亚时光 bo xi ya shi guang
沙石镇时光 sha shi zhen shi guang
双人成行 shuang ren cheng xing
胡闹厨房 hu nao chu fang
人类一败涂地 ren lei yi bai tu di
糖豆人 tang dou ren
鹅鸭杀 e ya sha
在我们之中 zai wo men zhi zhong
太空狼人杀 tai kong lang ren sha
孤岛求生 gu dao qiu sheng
歧路 qi lu
异度之刃 yi du zhi ren
纸片马力欧 zhi pian ma li ou
异界锁链2
""".strip()


def parse_rime(path):
    """解析 Rime 词库，返回 [(word, reading, weight)]。"""
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
            syl = parts[1].strip()
            w = 1.0
            if len(parts) >= 3:
                try:
                    w = float(parts[2])
                except ValueError:
                    w = 1.0
            if not word or not syl:
                continue
            reading = syl.replace(" ", "").replace("-", "").lower()
            out.append((word, reading, w))
    return out


def parse_game(text):
    out = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        word = parts[0]
        reading = "".join(parts[1:]).lower()
        out.append((word, reading, 1.0))
    return out


CJK = [(0x3400, 0x4DBF), (0x4E00, 0x9FFF), (0xF900, 0xFAFF), (0x20000, 0x3FFFF)]


def is_cjk_word(s):
    return s and all(any(a <= ord(c) <= b for a, b in CJK) for c in s)


def compile_dict(lex_paths, limit, out_path, with_game=True, maxwlen=11, maxrlen=36,
                 merge_path=None, verbose=True,
                 abbrev_mode="none", abbrev_ref=None, abbrev_v=None,
                 abbrev_min_len=2, abbrev_max_combos=4, abbrev_limit=0,
                 abbrev_allow_dup=False):
    raw = []
    for p in lex_paths:
        got = parse_rime(p)
        if verbose:
            print("  读入 %-28s %d 条" % (os.path.basename(p), len(got)))
        raw += got
    game = parse_game(GAME_WORDS) if with_game else []
    if verbose:
        print("  游戏词表 %d 条" % len(game))

    # 过滤 + 去重
    seen = set()
    singles, words = {}, {}
    for word, reading, w in raw:
        if not is_cjk_word(word):
            continue
        if not reading or not reading.isascii() or not reading.isalpha():
            continue
        if len(word) > maxwlen or len(reading) > maxrlen:
            continue
        k = (reading, word)
        if k in seen:
            continue
        seen.add(k)
        (singles if len(word) == 1 else words)[k] = w

    gamed = {}
    for word, reading, w in game:
        if not is_cjk_word(word) or len(reading) > maxrlen or len(word) > maxwlen:
            continue
        gamed[(reading, word)] = w

    # 并入原版条目，保证「不丢覆盖」
    merged, merged_v = {}, {}
    if merge_path:
        o = L.parse_njdc(open(merge_path, "rb").read())
        for (r, w), v in zip(o["entries"], [x & 0x3f for x in o["tail"]]):
            merged_v[(r, w)] = v
            merged[(r, w)] = 10 ** (6.0 * v / 63.0)
        if verbose:
            print("  并入原版 %-20s %d 条" % (os.path.basename(merge_path), len(merged)))

    # 组成：单字 → 游戏词 → 原版条目 → 其余按权重降序
    pick = []                                   # [(reading, word), weight, forced_v]
    pos = set()

    def add(k, w, v=None):
        # 跨组去重（先前漏了这一步）：单字表与原版并入表、游戏词与原版并入表
        # 会有大量重叠（如 啊/阿/爱 既是单字又在原版词典里），重复会让
        # 候选列表出现同一个词两次。**首次出现者胜**（保持原有的组间优先序）。
        if k in pos:
            return
        pos.add(k)
        pick.append((k, w, v))

    for k, w in singles.items():
        add(k, w)
    for k, w in gamed.items():
        add(k, w, 58)
    for k, w in merged.items():
        add(k, w, merged_v[k])
    # 统计跨组去重了多少条。**必须在并入 rest 之前算**：rest 会把 pick 填到
    # limit，之后再算就是「三组之和 − 上限」，恒为负、被 max(0,·) 抹成 0，
    # 打印出「跨组去重 -0」的假象（这个 bug 曾让人误以为去重没生效）。
    dedup_drop = len(singles) + len(gamed) + len(merged) - len(pick)

    taken = pos
    rest = sorted(((k, v) for k, v in words.items() if k not in taken),
                  key=lambda kv: -kv[1])
    # rest 里最多补 (limit − 已选) 条；注意「已选」是去重后的真实条数，
    # 所以被去重省下来的额度会自动被常用词补上，不浪费额度。
    budget = max(0, limit - len(pick))
    n_rest = min(budget, len(rest))
    for k, v in rest[:budget]:
        add(k, v)

    if verbose:
        print("  单字 %d + 游戏 %d + 原版 %d + 补常用 %d = %d 条"
              "（上限 %d，跨组去重 -%d）"
              % (len(singles), len(gamed), len(merged), n_rest,
                 len(pick), limit, dedup_drop))

    # ---------------------------------------------------------- 首字母缩写（简拼）
    # 给多字词**额外追加**一条「首字母读法」条目：sljt → 杀戮尖塔。
    # 原理：引擎按读法做前缀查找，所以多一条读法 = 多一个入口。
    # 但这是**未经验证的行为**（原版词典里零先例），必须先冒烟，见 tools/abbrev.py。
    if abbrev_mode and abbrev_mode != "none":
        ref = abbrev_ref or DEFAULT_NJTAN
        if not os.path.isfile(ref):
            raise SystemExit("找不到字→拼音表来源 njtan.a：%s\n"
                             "用 --abbrev-ref 指定，或先解包词典 title。" % ref)
        cmap = AB.load_char_pinyin(ref)
        if verbose:
            print("  字→拼音表 %s：%d 汉字 / 多音字 %d"
                  % (os.path.basename(ref), len(cmap),
                     sum(1 for v in cmap.values() if len(v) > 1)))

        have = {k for k, _, _ in pick}
        if abbrev_mode == "games":
            src = [(k, w0, v0) for (k, w0, v0) in pick if k in gamed]
        else:
            src = list(pick);
            # all 模式下必须显式排序：pick 里「原版并入」那一段是按读法字母序排的，
            # 直接截断会偏向 a/b/c 开头的词。这里按「有效优先级」降序，
            # 并给游戏词一个巨额加成，保证它们一定进得来。
            def eff(t):
                (k, w0, v0) = t
                base = (10 ** (6.0 * v0 / 63.0)) if v0 is not None else w0
                return -(base + (10 ** 9 if k in gamed else 0))
            src.sort(key=eff)

        # 截断按 src 的顺序（games 模式 = pick 原序；all 模式 = 上面的有效优先级）
        #
        # 【为什么必须丢掉「与同词其它读法撞车」的简拼】
        # 典型：阿呆 = adai，简拼 = ad。打 ad 时——全拼前缀 adai 命中一次，
        # 简拼条目 ad 又命中一次 → 候选列表里「阿呆」出现两次。
        # 这类简拼**本来就是冗余的**（入口已经存在），丢掉是零功能损失。
        # 实机统计：full 包 60,000 条简拼里有 295 条属于此类（0.5%），
        # 几乎全是「首字零声母」的词（阿X / 按X / 沙盒 shahe），
        # 因为首字拼音只有 a/e/o 一个字母时，简拼前两位正好是全拼的前两位。
        byword = {}
        for (reading, word), _w, _v in pick:
            byword.setdefault(word, []).append(reading)

        def collides(ab, word):
            # 打 ab 时，若该词的**其他读法**也以 ab 开头 → 同一个词被命中两次
            return any(r.startswith(ab) for r in byword.get(word, []) if r != ab)

        cand = []
        n_collide = 0
        for (reading, word), w0, v0 in src:
            if abbrev_limit and len(cand) >= abbrev_limit:
                break
            if len(word) < abbrev_min_len:
                continue
            for ab in AB.abbrev_variants(word, cmap, abbrev_max_combos):
                if ab == reading:
                    continue
                k = (ab, word)
                if k in have:
                    continue
                if not abbrev_allow_dup and collides(ab, word):
                    n_collide += 1
                    continue
                have.add(k)
                # 记进 byword：同一词的后续变体也要能看到它
                byword.setdefault(word, []).append(ab)
                cand.append((k, w0, v0 if abbrev_v is None else abbrev_v))
                if abbrev_limit and len(cand) >= abbrev_limit:
                    break

        # 追加在末尾：build_njdc 按读法稳定排序，同读法下**基础条目排在简拼之前**
        pick.extend(cand)

        if verbose:
            print("  简拼追加 %d 条（模式 %s，%s；因与同词全拼撞车丢掉 %d 条）"
                  % (len(cand), abbrev_mode,
                     "继承原优先级" if abbrev_v is None else "统一 v=%d" % abbrev_v,
                     n_collide))
            for (ab, wd), _, _ in cand[:10]:
                print("      %-12s -> %s" % (ab, wd))

    # 权重 → 6bit 优先级 v
    ws = [w for _, w, _ in pick if w > 0] or [1.0]
    lmin, lmax = math.log10(1.0), math.log10(max(ws))
    span = (lmax - lmin) or 1.0
    entries, tails = [], []
    for (reading, word), w, v0 in pick:
        if v0 is not None:
            v = v0
        else:
            v = int(round(63 * (math.log10(max(w, 1.0)) - lmin) / span))
        entries.append((reading, word))
        tails.append(max(0, min(63, v)))

    data = L.build_njdc(entries, tail_values=tails)
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "wb") as f:
        f.write(data)
    if verbose:
        print("  写出 %s  %d 字节  sha256=%s"
              % (out_path, len(data), hashlib.sha256(data).hexdigest()[:16]))
    return data, entries


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lex", action="append", default=[], help="Rime 词库 yaml")
    ap.add_argument("--limit", type=int, default=120000)
    ap.add_argument("--out", required=True)
    ap.add_argument("--merge", default=None, help="原版 njubase3.a，其条目全部并入")
    ap.add_argument("--no-game", action="store_true")
    ap.add_argument("--abbrev", choices=["none", "games", "all"], default="none",
                    help="追加首字母缩写条目：none/games/all（见文件头说明）")
    ap.add_argument("--abbrev-ref", default=None, help="njtan.a 路径（字→拼音表来源）")
    ap.add_argument("--abbrev-v", type=int, default=None,
                    help="简拼条目的优先级 v；不给则继承原条目（推荐）")
    ap.add_argument("--abbrev-min-len", type=int, default=2, help="只对至少这么长的词生成（默认 2）")
    ap.add_argument("--abbrev-max-combos", type=int, default=4, help="多音字组合上限（默认 4）")
    ap.add_argument("--abbrev-limit", type=int, default=0, help="简拼条数上限，按权重取前 N（0=不限）")
    ap.add_argument("--abbrev-allow-dup", action="store_true",
                    help="不过滤「与同词全拼撞车」的简拼（默认过滤，见 compile_dict 内注释）")
    a = ap.parse_args()
    lex = a.lex or ["/tmp/ice_base.yaml"]
    compile_dict(lex, a.limit, a.out, with_game=not a.no_game, merge_path=a.merge,
                 abbrev_mode=a.abbrev, abbrev_ref=a.abbrev_ref, abbrev_v=a.abbrev_v,
                 abbrev_min_len=a.abbrev_min_len, abbrev_max_combos=a.abbrev_max_combos,
                 abbrev_limit=a.abbrev_limit, abbrev_allow_dup=a.abbrev_allow_dup)


if __name__ == "__main__":
    main()

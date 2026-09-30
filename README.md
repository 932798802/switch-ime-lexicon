# ns-ime —— Nintendo Switch 中文输入法大词库

给 Switch 系统输入法（swkbd / OMRON iWnn）换词典。走 **Atmosphere LayeredFS**
覆盖，只写 SD 卡、不动 NAND；卸载即删目录，原版立即恢复。

> **本工程只有这一个说明文档。** 原先散落在各目录的 `README.md`，以及 FINDINGS、
> 大词库说明，已全部并入本文件（见文末两个附录）。文件较大，导航如下：

| 段落 | 内容 |
|---|---|
| **正文**（下方 → 附录 A 前） | 工程入口：目录结构、生成流程、部署、硬约束、版本管理 |
| **附录 A** —— 各目录说明 | `firmware`（原版词典来源）· `04_Outputs`（产物布局）· 判别测试包 · `nro` 插件工程 |
| **附录 B** —— 技术档案 | FINDINGS v15（23 节，完整侦察过程）· 大词库成果与验证 · 证据链审查 · 早期报告 v1 |

> 附录中的节号（如 §21）沿用原文；所有交叉引用都指向本文件内的对应段落。

## 工程目录

| 目录 | 内容 |
|---|---|
| `01_Inputs/` | `lex/`（词源 + ALL.tsv）、`firmware/`（原版词典）、`prod.keys` |
| `02_References/` | `hactool/`、`atmosphere/` 参考源码 |
| `03_Documents/` | 早期 HTML 报告（`report.html`、`reports/`） |
| `04_Outputs/` | **产物**：`<版本>/atmosphere/…`（已铺成 SD 卡结构）＋ `tests/`（判别测试包） |
| `05_Code/` | `tools/`（Python）、`nro/`（主机端插件工程） |
| `10_Other/` | 缓存、备份、归档 |

## 生成（两条命令）

```bat
python 05_Code/tools/mk_lexicon.py           :: 词源    -> 01_Inputs/lex/ALL.tsv
python 05_Code/tools/build_from_lexicon.py   :: ALL.tsv -> 04_Outputs/<版本>/atmosphere/...
```

**加词、改拼音、调优先级 → 只编辑 `ALL.tsv`，再跑第二条命令。**

自检：`python 05_Code/tools/verify_njdc.py <产物路径>`
（预期输出「全部结构检查通过」，且 `重复条目 = 0`）

## 部署

把 `04_Outputs/v0.1/atmosphere/` **整个复制到 SD 卡根目录**（卡上已有 `atmosphere`
则选「合并/覆盖」，不要整个替换掉它）：

```
<SD>:\atmosphere\contents\0100000000000805\romfs\Iwnn\ZH\CN\pinyin\
    GB18030\njubase{1,2,3}.a
    GB2312\njubase{1,2,3}.a
```

- 装完**关掉屏幕键盘再打开**；不行就重启。
- ⚠️ **开机别按住 L** —— 那是 Atmosphere 的覆盖键，按住反而**关掉** LayeredFS。
- 卸载：删掉卡上 `contents\0100000000000805\` 整个文件夹。
- 验证：打 `shalujianta` → 出「杀戮尖塔」；打 `sljt` → 同样出（简拼）。

## ⚠️ 三条硬约束

1. **单本上限 ≈ 4.64~4.92 MB**（实测）。但**「多本分担可扩容」尚未验证** ——
   现有实验只动过 `njubase3` 一本，因此「单本上限」与「**三本总量上限**」两种解读
   **至今未区分**（详见 本文档的「技术侦察报告」节 §21）。
   → **上机前先看 `04_Outputs/tests/` 里的判别测试包。**
2. **重复条目会让引擎拒绝加载整个词典**（实测）。生成器已对简拼去重，
   校验器会报告重复条目数。
3. **三本方案验证通过前，实机可用交付以单本 `njubase3.a`（4.53 MB）为准** ——
   部署时只放这一个文件，不要放 base1 / base2。

`HexDict.nro` 需重编译（系统重装清空了 devkitPro / Qt / CMake）—— 见 本文档的「05_Code/nro」节。

## 版本管理与入库范围

git 管理，当前 **v0.1**（`VERSION` 文件 + 标签 `v0.1`）。

**不入库**：主机密钥（`prod.keys`）、原版固件词典（`01_Inputs/firmware/dat08xx/`）、
含原版条目的产物（`04_Outputs/**/*.a`）、nro 编译产物、`10_Other/`。
克隆后跑生成流程前，须自备 `01_Inputs/firmware/dat0805/`。

**第三方**：`lex/ice_*.yaml` 来自 [rime-ice](https://github.com/iDvel/rime-ice)（MIT）；
`game.txt` 为本工程原创；`02_References/` 下代码的版权见各文件头。


---

# 附录 A：各目录说明

> 以下四节原本是各自目录下的 `README.md`，已合并到本文件。


---

## 01_Inputs/firmware —— 原版固件词典（不入库）

生成新词典时需要**并入原版条目**（保证不丢原有覆盖），所以这里要放从主机备份
解包出来的原版词典。

### 目录

| 目录 | 来源 | 用途 |
|---|---|---|
| `dat0805/` | title `0100000000000805`（中日韩词典数据） | **必需** —— `build_from_lexicon.py` 从 `dat0805/files/Iwnn/ZH/CN/pinyin/GB18030/` 读原版 `njubase1/2/3.a` 作为合并基底 |
| `dat0808/` | title `0100000000000808`（日文 + 欧美） | 侦察参考，生成链当前不用 |

### ⚠️ 为什么不入库

这是**任天堂的版权内容**，已在 `.gitignore` 中屏蔽：

```gitignore
01_Inputs/firmware/dat0805/
01_Inputs/firmware/dat0808/
```

请用**自己的**主机备份自行解包，不要从本仓库获取。

### 怎么重新解包

数据源：SD 卡的**全量备份**（含固件 NCA 包 + `prod.keys`），
工具在 `05_Code/tools/`：

| 脚本 | 作用 |
|---|---|
| `index_fw.py` | 建立固件 NCA 索引（从备份目录扫描 + 解密头部） |
| `nca.py` / `dump_nca.py` | NCA 解密与分区导出 |
| `nca_romfs.py` / `romfs_dump.py` | RomFS 解包 |
| `id_applets.py` | 识别各 title 的 program_id |

解包后按上述结构摆进 `dat0805/`、`dat0808/` 即可。

> 侦察脚本里部分路径写成相对 `HERE/../../01_Inputs/firmware/dat0805`，
> 部分（如 `nso_kw.py`）仍指向已删除的旧中间产物，需要时按脚本内注释调整。


---

## 04_Outputs —— 最终产物（可直接拷进 SD 卡）

### 布局

```
04_Outputs/
└─ v0.1/                               ← 版本号取自根目录 VERSION
   └─ atmosphere/                      ← ★ 整个文件夹拷到 <SD>:\ 即可
      └─ contents/0100000000000805/romfs/Iwnn/ZH/CN/pinyin/
         ├─ GB18030/njubase{1,2,3}.a
         └─ GB2312/njubase{1,2,3}.a    （与 GB18030 内容完全相同）
```

两套编码目录都放一份，设备走哪套都能命中。

- **部署**：`v0.1/atmosphere/` 整个拷到 SD 卡根目录（卡上已有 `atmosphere` 则选「合并/覆盖」）。
- **回滚**：删掉卡上 `atmosphere\contents\0100000000000805\`，固件原版立即恢复。
- ⚠️ **开机别按住 L** —— 那是覆盖键，按住会**关掉** LayeredFS，看起来像没生效。

### ⚠️ 三本方案尚未验证

**验证通过前，实机可用交付以单本 `njubase3.a`（4.53 MB）为准** —— 只放这一个文件。

工程原以为「每本有独立的大小预算」，但见 `../本文档的「技术侦察报告」节 **§21**：
全部阈值实验**只动过 `njubase3` 一本**，所以「单本上限」与「**三本总量上限**」
两种解读至今未区分。当前三本引擎可见总量 ≈ 13.46 MB，是已知可用最大值（≈5.31 MB）
的 2.5 倍 —— 若真限总量则**必然失败（候选为空）**。

**判别测试包见 `tests/`** —— 每本都带独有探针，实机可判定「哪一本被读取」。

### 不入版本库

产物**内含并入的原版固件条目**（仅 `njubase3` 就并入 57,954 条），含任天堂版权内容 →
已被 `.gitignore` 屏蔽（规则 `04_Outputs/**/*.a`）。需要时自己跑：

```bat
python 05_Code/tools/mk_lexicon.py            :: 词源    -> 01_Inputs/lex/ALL.tsv
python 05_Code/tools/build_from_lexicon.py    :: ALL.tsv -> 04_Outputs/<版本>/atmosphere/...
```

前置：`01_Inputs/firmware/dat0805/` 下要有从**自己主机备份**解包的原版词典。

### 版本号

目录名取自 `VERSION`（当前 `0.1` → `v0.1`）。发新版：改 `VERSION` → 重跑生成器，
**旧版本目录保留**，互不覆盖。


---

## 判别测试包 —— 大小上限是「单本」还是「三本总量」？

> 由 `05_Code/tools/mk_probe_tests.py` 生成。背景见 本文档的「技术侦察报告」节 §21。

### 怎么用

每个用例都是一个**完整的 atmosphere 目录**。任选一个，把它整个拷到 SD 卡根目录
（覆盖同名文件；**换用例前先把卡上 `contents/0100000000000805/` 删干净**，
否则会残留上一次的文件），然后进输入法依次打这三个词：

| 输入 | 若出现 | 说明 |
|---|---|---|
| `nbp3` | 「探针三」 | `njubase3.a` **被读取** |
| `nbp1` | 「探针一」 | `njubase1.a` 被读取 |
| `nbp2` | 「探针二」 | `njubase2.a` 被读取 |

**判据**：只要**有一个探针出词**，就说明词典加载成功；**三个都不出**，即为加载失败。

### 用例一览

| 用例 | base3 | base1 | base2 | 引擎可见总量 | 说明 |
|---|---|---|---|---|---|
| `t0-baseline` | 4.53 MB | 0.09 MB | 0.09 MB | **4.96 MB** | 基线：只有 base3 大（≈ §15 已知可用的配置），base1/base2 仅原版+探针 |
| `t1-b1-2m` | 4.53 MB | 1.79 MB | 0.09 MB | **6.66 MB** | ★关键判别：base3 一个字节没动，只把 base1 加到 ~2 MB（仍远低于单本上限 4.6） |
| `t2-three-3m` | 2.06 MB | 2.65 MB | 2.69 MB | **7.65 MB** | 三本都只有 ~2.5 MB（远低于单本上限 4.6），但总量 ≈ 8 MB |
| `t3-full` | 4.53 MB | 3.81 MB | 4.09 MB | **12.68 MB** | 当前交付配置的三本（总量 ≈ 13 MB） |

### 判读

**第 0 步：装 `t0-baseline`**（≈ 已知可用配置）。它**必须出词** ——
若连它都不出，说明装法/路径有问题（先解决那个，别急着看下面的结论）。

#### 关键一步：`t1-b1-2m`

`t1` 与 `t0` 的**唯一差别**：`njubase1.a` 从原版（≈0.09 MB）加大到 ≈1.8 MB。
**1.8 MB 远低于单本上限 4.6 MB**，所以：

| `t1-b1-2m` 结果 | 推论 |
|---|---|
| ❌ 三个探针都不出 | **总量是限制** —— base3 一个字节没动、新加的 base1 才 1.8 MB，唯一变量就是总量。**「每本独立预算」被否证，三本方案作废。** |
| ✅ 出词 | 总量不是限制 → 「单本假设」成立。继续用 `t2` / `t3` 确认。 |

#### 辅助用例

- **`t2-three-3m`**：三本都只有 2.1~2.7 MB（每本都远低于 4.6），但总量 7.65 MB。
  若它 ❌ 而 `t0` ✅ → 同样指向「总量」。
- **`t3-full`**：当前交付配置（总量 12.68 MB）—— 这是最终要用的那个。

#### 探针预期

每个用例的**三本都塞了探针**，所以正常情况下 `nbp1` / `nbp2` / `nbp3` 都该出词。
**哪个不出，就说明哪一本没被引擎读到** —— 这比「能不能出词」信息量更大。

### 注意

- 每次换用例**务必先清空**卡上的 `contents/0100000000000805/`，否则会残留上一次的文件。
- 装完要**关掉屏幕键盘再打开**（或重启）。**开机不要按住 L**。
- 本包两套编码目录都放；若想顺带测「只放 GB18030」，删掉卡上的 `GB2312/` 即可。


---

## HexDict —— Switch 中文输入法词典管理器（.nro）

把本工程生成的 NJDC 大词库，做成**一个 .nro 程序**：在 hbmenu 里点几下就能
安装 / 切换 / 卸载，不用再插读卡器、开电脑、拖文件。

对应三个真实痛点里的 **②联想差** 与 **③没有游戏词库**。

---

### 1. 它解决了什么（以及为什么值得做）

原来的 overlay 方案（见 `../../本文档的「大词库成果与验证」节）已经**在实机验证通过**，但它有一个软肋：

> 出问题时必须**拔卡、插读卡器、插电脑**才能把文件删掉救回来。

HexDict 把这件事变成 **hbmenu 里按一个键**：

| | 手工 overlay | HexDict.nro |
|---|---|---|
| 安装 | 读卡器 + 电脑 + 拖文件 | hbmenu 里按 A |
| 切换到轻量版 | 重新拷文件 | 按 X |
| 出问题还原 | 拔卡 + 电脑 + 删目录 | 按 Y |
| 装前自检 | 电脑上跑 Python | 程序内建 NJDC 结构校验 |
| 出错风险 | 「装了个坏文件」只能靠电脑查 | 装完自动回读 + CRC32 比对 |

---

### 2. 它能做什么 / 不能做什么（先把边界讲清楚）

#### 能做

- **安装**：把内嵌的一个「词典包」写到
  `sdmc:/atmosphere/contents/0100000000000805/romfs/Iwnn/ZH/CN/pinyin/{GB18030,GB2312}/njubase{1,2,3}.a`
  —— 一个包可能含 **1~3 个文件**（多本分担，见 §5）
- **卸载**：删掉 overlay 子树 → 固件原版词典立即恢复（**永远安全，NAND 从未被改动**）
- **切换**：MULTI（约 411,000 词，三本）/ ABBR 完整版（150,000 词 + 简拼）/ 轻量版（80,000 条）/ SD 上的自定义词典
- **自检**：写入前验 NJDC 结构，写入后回读校验大小与 CRC32
- **一键重启**：走 Atmosphere 的 `spsm` mitm（`spsmShutdown(true)`）

#### 不能做（重要，别期待）

1. **不能「热生效」**。
   词典的加载是 `fs.mitm`（sysmodule）在做；swkbd 一旦打开词典，romfs 索引就建在内存里。
   `.nro` 只能**写文件**，改不了已建好的索引。所以装完仍然需要
   **让键盘重新打开词典**（关掉键盘再开）；保守做法是**重启主机**。

   > 源码依据（`refs/ams/fsmitm_layered_romfs_storage.cpp`）：
   > - `HasSdRomfsContent()`（`amsmitm_fs_utils.cpp:187`）是**实时**查 SD，无缓存
   >   —— 所以**理论上不需要重启主机**，只要旧的 storage 句柄被释放；
   > - layered storage 按 `program_id` 缓存在 `g_storage_set`，但引用计数归零后
   >   由 finalizer 线程（每 500 ms 扫一次 + 一次 second chance）**在约 1 秒内回收**；
   > - 因此「关掉键盘再打开」有机会直接生效，值得实测一次（见 §5）。
   >   如果 swkbd 是常驻 applet（句柄不释放），那就必须重启。

2. **不能改「按键位置」**（痛点 ①）。那是 swkbd 本体布局的事，词典层面无解。

3. **不覆盖 NAND**。只写 SD 卡 —— 而这正是 LayeredFS 需要的形态，够用。

4. **界面是英文 ASCII**。libnx 内置点阵字体**不含 CJK 字形**，写中文会变乱码。
   要中文界面得自带字体资源，本版没做。

---

### 3. 前置条件

| 项 | 要求 |
|---|---|
| 主机 | 已装 Atmosphere（CFW）+ emuMMC 或 sysMMC |
| hbmenu | `sdmc:/hbmenu.nro` 存在。通常在相册里**按住 R 键**进入 |
| 构建 | **devkitPro + libnx**（https://devkitpro.org/wiki/Getting_Started），默认装在 `C:/devkitPro` |
| 构建 | Python 3（`gen_embed.py` 用；本工程已在 `../../01_Inputs/lex` 附带词库，无需联网） |

> ## ⚠️ 2026-09-30 状态：工具链缺失，`.nro` 需重编译
>
> 系统重装把 `C:\devkitPro`、Qt（`mingw32-make`）、CMake **一并清空**。
> 本目录的 `HexDict.nro` 是 **09-27 编译的旧产物**，而 `assets/` 已在同日更新为
> 修复后的词典（`d9b9c226`）—— **两者已不匹配，必须重新编译**。
>
> 重建三件套：
> 1. **devkitPro**：`python ../tools/install_devkitpro.py`
>    （7 个 pacman 包已在 `../../10_Other/dkp-cache` 缓存，`download()` 会直接复用，**可离线装**）；
> 2. **`devkitA64/base_rules`**：不在任何 pacman 包里，来自 GitHub 仓库
>    `devkitPro/devkitA64-rules`（`codeload.github.com` 可达）；
> 3. **一个 make**：原先借 Qt 的 `mingw32-make`，现在也没了，需另装 MinGW-w64 / MSYS2。
>
> 不需要 devkitPro 也能跑的那一半仍然可用：`check-pc.bat`（但需先装 MinGW 提供 `g++`）、
> `python tools/gen_embed.py`（纯 Python，已验证通过）。

---

### 4. 构建

```bat
build.bat
```

三步：① `python tools\gen_embed.py` 把 `assets/*.a` 内嵌成 `source/embed.s`；
② `make`；③ 产出 `HexDict.nro`。

产物：约 **5.6 MB**（内嵌完整版 3.9 MB + 轻量版 1.8 MB）。

拷到 SD 卡根目录或 `sdmc:/switch/`，从 hbmenu 启动。

#### 目录结构

```
nro/
├─ Makefile              devkitPro/libnx 标准工程
├─ build.bat             一键构建 .nro（需要 devkitPro；ASCII 脚本）
├─ check-pc.bat          ★ 一键 PC 侧自检（不需要 devkitPro，现在就能跑）
├─ assets/               要内嵌的词典（由 ../../04_Outputs/ 拷来）
│   ├─ multi-njubase1.a  MULTI 包 -> njubase1.a   4.28 MB
│   ├─ multi-njubase2.a  MULTI 包 -> njubase2.a   4.42 MB
│   ├─ multi-njubase3.a  MULTI 包 -> njubase3.a   4.64 MB
│   ├─ njubase3.a        ABBR 包  -> njubase3.a   4.64 MB（150,000 词 + 简拼）
│   └─ njubase3-lite.a   LITE 包  -> njubase3.a   1.83 MB（80,000 条）
├─ source/
│   ├─ main.cpp          界面 + 安装/卸载/重启逻辑
│   ├─ njdc_check.h      NJDC 结构校验（平台无关，PC 侧有回归测试）
│   ├─ embed.s           ← 自动生成（.incbin 内嵌词典）
│   └─ embed_meta.h      ← 自动生成（sha256 / 大小 / 生成时间）
└─ tools/
    ├─ gen_embed.py      生成 embed.s / embed_meta.h
    ├─ host_test.cpp     在 PC 上回归 NJDC 校验器（见 §5.1）
    ├─ stub/switch.h     仅用于语法自检的最小 libnx 桩（**不是** libnx 替代品）
    └─ host_test.exe     ← 编译产物
```

---

### 5. 验证

#### 5.1 PC 侧（不需要主机，现在就能跑）

```bat
check-pc.bat
```

两步：① 用 `tools/stub/switch.h` 对 `source/main.cpp` 做 **语法自检**
（`g++ -fsyntax-only -Wall -Wextra`，当前零告警）；② 编译并运行 **NJDC 校验器回归**。

校验器回归的关键点：`.nro` 里的结构校验如果写错，后果是「装进一个坏词典」或
「误拒一个好词典」。所以把校验逻辑抽成平台无关的 `source/njdc_check.h`，
用**真实固件词典**跑：

- 本工程两版词典 → `[OK] clean`
- 原版 `njubase1/2`、`njcode`、`njtan`、`njubase3` → `[OK]`
  （分别是 clean / clean / clean / other / extra 四种版式）
- 三个负例（破坏魔数 / 截断 4 字节 / 把 N 改大）→ **全部被正确拒绝**
- `njexyomi.a`（N=0 的纯预测型小文件）→ `[EXPECTED]` 按设计排除

当前结果 **ALL PASSED**，完整输出存于 `../../03_Documents/reports/njdc_checker_regression.txt`。

> **这次回归抓到了两个真 bug**，见 `njdc_check.h` 顶部注释：
> ① `0x20 == 1146` / `0x44 == 1144` 不是 NJDC 通用不变量（原版 `njubase3` 是 81726/81724，
>    `njtan` 是 57895/57880），写死会把**原版文件误判成坏的**；
> ② `0x0c = size − 112` 也只是巧合，正确通式是 **`0x0c = size − 28 − 头部长度`**
>    （`njexyomi` 头部 60 → 减 88，不是 112）。
>
> 顺带得到一个重要事实：我们把原版 `njubase3`（带 662 KB 附加区）整个换成 clean 版式，
> **实机照常工作** → 引擎完全按文件自身头部字段寻址，**不要求同槽位文件版式一致**。

#### 5.2 主机侧：冒烟测试（最终判据）

1. **基线**：先不装任何词典，进任意输入框打 `shalujianta` → 应**打不出「杀戮尖塔」**。
2. 启动 HexDict.nro → 状态应显示 `NOT INSTALLED`。
3. 按 **A** 装 MULTI（三本）→ 状态应变为
   `INSTALLED - MULTI (3 dictionaries, ~411,000 words)`，且 `base1 / base2 / GB18030 / GB2312`
   四行都有大小（base1/base2 只在多本方案下出现）。
   若想只装单本，按 **B**（ABBR 完整版 → `INSTALLED - FULL build`）或 **X**（LITE）。
4. **先别重启**，直接退出去打 `shalujianta`：
   - 能出「杀戮尖塔」→ 说明 LayeredFS 是**每次打开实时判定**的，§2-1 的推论成立（省一次重启）；
   - 打不出 → 重启后再试（**开机时不要按住 L**）。
5. 按 **Y** 卸载 → 状态回到 `NOT INSTALLED`，词典应回到原版。

> ⚠️ **开机按住 L 会关闭 LayeredFS 覆盖**：Atmosphere 默认覆盖键是 `L` 且
> `override_by_default = true`，判定式 `IsOverrideMatch = override_by_default ^ keys_triggered`
> → 按住 L 反而是「关闭」。这是最容易误判成「方案失败」的坑。

---

### 6. 现在缺什么

见 §3 顶部的「2026-09-30 状态」：缺 **devkitPro + `devkitA64/base_rules` + 一个 make** 三样。
本目录的 `HexDict.nro` 是 09-27 的旧产物，而 `assets/` 已在 09-30 换成修复版词典
（`njubase3` 的简拼重复条目 bug 已修，见 `../../本文档的「大词库成果与验证」节 顶部），
**两者不匹配，必须重新编译**。`build.bat` 本身无需改动。

### 7. 已知限制

- 只覆盖**简体中文拼音**（`ZH/CN/pinyin`）。繁体 `ZH/TW`、粤拼 / 仓颉 / 笔画未做。
- **不处理 `.ad1`**（`njubase3.ad1` 的 NJAD 容器语义仍未解）。
  实机已证明**只覆盖 `.a` 就够用**，所以本工具不碰 `.ad1`。
- 候选词**排序**不保证优于原版（原版条目沿用原优先级，新词按词频映射）。
- `njexyomi.a`（联想词典，中文版仅 1,528 B 近乎空壳）**本工具不管** ——
  它是 N=0 的另一种版式，要改得单独解，见 `../../本文档的「技术侦察报告」节 §12.6。


---
---

# 附录 B：技术档案

> 以下是完整的历史记录，保留原节号与原始路径（`dist/` 等是 2026-09-30 重组前的结构）。


---

## swkbd / iWnn 输入法技术侦察报告（v15）

- 日期：2026-09-27（v5 增补：**实机验证通过** ＋ 原版 6 本词典版式对照 ＋ `.nro` 打包，见 §13；
  v6 增补：**重复条目 bug 修复** ＋ **简拼（首字母联想）方案** ＋ **校验器统一**，见 §14；
  v7 增补：**规模上限诊断** —— 大词典「键盘能弹但不出词」的正交实验设计，见 §15；
  v8 增补：**清理失败产物** ＋ **扩容路线转向「逐档加词」**，见 §16；
  v9 增补：**规模上限定论（= 文件字节数）** ＋ **判据纠错** ＋ **多本分担新方向**，见 §17；
  v10 增补：**★ 多本分担扩容打通** —— 探针证实引擎读 njubase1，三本合计 41 万词，见 §18；
  v11 增补（2026-09-30）：**简拼重复条目 bug 回归修复** ＋ **部署包脚本化** ＋ **目录整理**，见 §19；
  v12 增补（2026-09-30）：**移除部署与校验** ＋ **目录按 01/02/03/04/05/10 分类重组**，见 §20；
  v13 增补（2026-09-30）：**⚠️ 证据链复审** —— 「每本独立预算」缺证据，见 §21；
  v14 增补（2026-09-30）：**产物改为「版本化 + SD 卡结构」布局**（`04_Outputs/v0.1/atmosphere/…`），见 §22；
  v15 增补（2026-09-30）：**判别测试包**（三本各带探针 + 总量/单本对照），见 §23）
  单本还是总量尚未区分，见 §21）
- 目标机：Switch 固件 **22.5.0** ＋ Atmosphere 1.11.2 ＋ emuMMC（file-based，SD00）
- 数据源：**实机 SD 卡全量备份** `F:/NSbackup/20260927/`（固件包 `AMS-22.5.0/` 238 个 NCA ＋ `switch/prod.keys`）
  ＋ Atmosphere 官方源码（`github.com/Atmosphere-NX/Atmosphere`，存档于 `refs/ams/`）
- 方式：纯离线解析固件 NCA + 源码比对，不动主机、不联网
- 口径：标「已验证」的项均有本次实测证据；v2 推翻了 v1 的 3 处核心结论（§8），v3 追加路线可行性论证（§9），
  v4 追加 NJDC 完整规范与生成器产出（§12），v5 追加实机验证与 .nro 打包（§13），
  v6 追加去重修复、简拼方案与校验器统一（§14），v7 追加规模上限诊断（§15）

---

### 0. 一句话结论

Switch 的输入法**不是 swkbd**，而是「**swkbd（界面/宿主）＋ OMRON iWnn 1.16.2（引擎）＋ 独立词典 title（数据）**」的三段式结构。

**关键纠正**：词库**不在** swkbd 里，而在**独立的系统数据 title**：
`0100000000000805`（中日韩，17.25 MB）与 `0100000000000808`（日文＋欧美，18.67 MB）。
它们是**普通 RomFS 文件**（`NJDC` 格式），因此「**加游戏词库**」的落点是**真实存在**的——这是 v1 判错的最重要一条。

同时纠正：**swkbd 22.5.0 确实支持中文输入**（简体拼音 / 繁体注音·仓颉·速成·粤拼·笔画）。

**v3 追加（最重要的一条可行性结论）**：LayeredFS 覆盖词典 title **在 Atmosphere 源码层面成立**（见 §9）。
swkbd 取词典走的是 `nn::fs` 的 `OpenDataStorageByDataId`，而这正是 `fs.mitm` 会套 LayeredFS 的两条路径之一。
实机落点：

```
sd:/atmosphere/contents/0100000000000805/romfs/Iwnn/ZH/CN/pinyin/GB18030/<词典文件>
```

→ 「②联想差」与「③没有游戏词库」两个痛点，**都有可落地的技术路径**；
真正未解的是 **NJDC 私有格式能否正确构造**（§7 第 2 项），而非「能不能覆盖」。

---

### 1. 三段式架构（已验证）

```
                 ┌─────────────────────────────────────────┐
游戏调用 swkbd ──▶│ swkbd  0100000000001008                 │
KeyboardConfig   │ ├ ExeFS 3.22 MB  main (NSO0, LZ4)        │
                 │ │   └ 解压后 text 3.99 + rodata 1.10      │
                 │ │       + data 0.41 ≈ 5.50 MB            │
                 │ │   └ 内含: iWnn 1.16.2 引擎 / nn::atk UI │
                 │ │            nn::font / KeyboardPredict    │
                 │ └ RomFS 629 KB（47 文件，542,852 B）      │
                 │     ├ lyt/*.szs      键盘布局（Yaz0+SARC）│
                 │     ├ message/<18语言>/*.msbt   UI 文本   │
                 │     ├ common/agl|shader|sead   渲染资源   │
                 │     └ sound/swkbd.bfsar        音效       │
                 └──────────────┬──────────────────────────┘
                                │ 挂载 URI（已验证字符串）
                    dic://Iwnn  │  dic2://Iwnn
                                ▼
       ┌────────────────────────────────────────────────────┐
       │ 0100000000000805 (Data/RomFS, 17.25 MB)  ZH + KO   │
       │   Iwnn/ZH/CN/pinyin/GB{2312,18030}/nj*.a|.ad1      │
       │   Iwnn/ZH/CN/stroke/…  Iwnn/ZH/TW/{pinyin,bopomofo,│
       │   cangjie[,quick],stroke}/…  Iwnn/ZH/HK/{jyutping, │
       │   cangjie[,quick],stroke}/…  Iwnn/KO/…            │
       ├────────────────────────────────────────────────────┤
       │ 0100000000000808 (Data/RomFS, 18.67 MB)  JA + 欧美 │
       │   Iwnn/JA/32/  Iwnn/JA_small/32/  Iwnn/DE|EN|ES|FR│
       │   |IT|NL|PT|RU （large / regular 两档）            │
       └────────────────────────────────────────────────────┘
```

#### 1.1 引擎身份（硬证据）

swkbd `main.rodata` 结尾处的 SDK 字符串（偏移 `0x10D625`）：

```
SDK MW+OmronSoftware+iWnn-1_16_2
SDK MW+Nintendo+NintendoWare_Atk-22_1_15-Release
SDK MW+Nintendo+NintendoWare_Font-22_1_15-Release
```

并将其词典组件名与挂载点写在 rodata：

```
iWnn   dic2://Iwnn   dic://Iwnn   KeyboardPredict   dic2
njtan.a  njexyomi.a  njcangjie.a  njcode.a  njubase1.ad1  njubase1br.a
keisei/njubase1.ad1   cangjie/quick
```

> `keisei`（形成）与 `cangjie/quick` 这两个**路径片段**，与 0805 RomFS 里的
> `Iwnn/ZH/TW/pinyin/keisei/` 与 `Iwnn/ZH/TW/cangjie/quick/` **逐字对应** —— 闭环成立。

#### 1.2 swkbd 支持的语言（硬证据）

`message/CNzh/swkbd.msbt` 的「选择键盘」列表末尾原文：

```
简体中文 / 繁體中文 / 한국어
日本語　ローマ字入力 / 日本語　50音（横並び）（左から）（右から）
English(US/UK) / Français / Español / Deutsch / Italiano / Nederlands / Português / Русский
```

且 **18 种语言的 `swkbd.msbt` 全部**都含 `SwkbdAddKeytop_ZHSimplifiedChinese`、
`SwkbdAddKeytop_ZHTraditionalChinese`、`SwkbdFooter_KanaRotate` 等标签。

布局资源侧：`lyt/50on.szs` → `SwkbdBaseKeytop50on`；`lyt/Qwerty.szs` →
`SwkbdBaseKeytopQwerty` / `SwkbdBaseKeytopQwerty_ChangeInputMode`。

---

### 2. 已验证：NCA 解密链路（工具链基石）

全部参数移植自 hactool 源码（`ref/nca.c` / `nca.h` / `ivfc.h` / `utils.h` / `aes.c`）：

| 项 | 正确做法 |
| --- | --- |
| 头部解密 | 前 `0xC00` 整体 AES-XTS，tweak = BE(sector)，sector 从 0 起 |
| `media_to_real` | `0x200 * block`，**不加 0xC00** |
| **key index** | `max(0x206, 0x220) - 1` ← 最初解不开的主因 |
| key area | `AES-ECB-Dec(key_area_key_<name>_<idx>, encrypted_keys[4][0x10])` |
| data key | **固定 `decrypted_key_area[2]`**（CTR） |
| CTR IV | `reverse(section_ctr[0:8]) ∥ BE(offset>>4)`（**双段拼接**） |
| **FS header** | `0x400 + i*0x200`，section 数据区**不含** FS header |
| **IVFC 头** | 在 FS header `+0x08`，`level_headers[i]` 位于 `+0x10 + i*0x18` |
| **RomFS 定位** | `romfs_offset = ivfc.level_headers[5].logical_offset` |
| NSO 分段 | **单块原始 LZ4**（`LZ4_decompress_safe` 全段），**无** 64K 分块链、**无** 8 字节前缀 |

**枚举纠错**（v1 标错过）：`CRYPT_NONE=1 / XTS=2 / **CTR=3** / BKTR=4`。
v1 把 3 标成 BKTR；实际 swkbd 的 section 就是 plain **CTR** —— 这也解释了为什么 CTR 解密一直是对的。

**NSO 头布局**（`nso.h`，v1 用错了字段）：`segments[3]` 从 `0x10` 起、每项
`{file_off, dst_off, decomp_size, align}` 各 4 字节；`0x1C` 是 **text 的 align**，不是 mod0 偏移。

---

### 3. 已验证：RomFS 解析要点

| 项 | 结论 |
| --- | --- |
| `.szs` | Yaz0 压缩的 **SARC**（magic `SARC`/`SFAT`/`SFNT`），BOM `ff fe` = LE |
| SARC 节点 | 从 `SFAT + header_size(0x0C)` 开始，**不是** `+8`；attr 高字节 = 名字长度 |
| `_DIC` | swkbd data 段含 **243 个 `_DIC` 控制块**（iWnn 词典句柄表，约 5 KB），**无词条体** |
| RomFS 引用 | `parent/child/sibling/file` 是**字节偏移**而非索引 |
| RomFS 区域顺序 | 不必是 header→meta→data；本固件 0805 实际是 `header(0x50) → data(0x200) → …meta` |
| `FSAR` | `sound/swkbd.bfsar`（**sound** archive，不是字体！"STRG" 是其字符串表） |

**Yaz0 关键坑**：**没有结束标记**。`00 00` 是合法回引用（dist=1，重复上一字节 18 次）；
误判为 EOF 会把 41 条流截断到几十字节（v1 的 `romfs_dump.py` 就栽在这里，本版已修）。

---

### 4. 已验证：两个词典 title 的完整清单

#### 0100000000000805 — 亚洲（ZH + KO），76 文件 / 17.25 MB

| 目录 | 文件 | 字节 |
| --- | --- | --- |
| `Iwnn/ZH/CN/pinyin/GB18030/` | 11 | 2,807,207 |
| `Iwnn/ZH/CN/pinyin/GB2312/` | 10 | 2,639,488 |
| `Iwnn/ZH/CN/stroke/GB18030/` | 1 | 1,021,518 |
| `Iwnn/ZH/CN/stroke/GB2312/` | 1 | 202,700 |
| `Iwnn/ZH/TW/pinyin/` | 4 | 1,868,612 |
| `Iwnn/ZH/TW/pinyin/keisei/` ＋ `no_keisei/` | 4+4 | 506,940 ＋ 505,236 |
| `Iwnn/ZH/TW/bopomofo/` | 4 | 1,764,104 |
| `Iwnn/ZH/TW/bopomofo/keisei/` ＋ `no_keisei/` | 4+4 | 456,576 ＋ 455,492 |
| `Iwnn/ZH/TW/cangjie/` ＋ `quick/` | 2+4 | 308,274 ＋ 396,727 |
| `Iwnn/ZH/TW/stroke/` | 1 | 441,698 |
| `Iwnn/ZH/HK/jyutping/` | 8 | 2,645,342 |
| `Iwnn/ZH/HK/cangjie/` ＋ `quick/` | 2+4 | 288,526 ＋ 370,684 |
| `Iwnn/ZH/HK/stroke/` | 1 | 441,698 |
| `Iwnn/KO/` | 4 | 965,434 |

#### 0100000000000808 — 日文＋欧美，77 文件 / 18.67 MB

| 目录 | 文件 | 字节 |
| --- | --- | --- |
| `Iwnn/JA/32/` | 7 | **4,889,008** |
| `Iwnn/JA_small/32/` | 7 | 2,100,485 |
| `Iwnn/DE/large/` ＋ `regular/` | 4+4 | 1,440,540 ＋ 951,428 |
| `Iwnn/FR/FR/{large,regular}/`、`FR/CA/regular/` | 4+4+4 | 1,090,026 ＋ 980,108 ＋ 873,485 |
| `Iwnn/ES/ES/`、`IT/IT/`、`NL/NL/` | 4×3 | 1,035,150 / 959,248 / 1,002,826 |
| `Iwnn/RU/{large,regular}/` | 4+4 | 1,151,770 ＋ 727,713 |
| `Iwnn/EN/`（US/GB ＋ 公共） | 1+1+5 | 10,864 ＋ 11,882 ＋ 1,022,844 |
| `Iwnn/PT/…` | 8 | 1,294,039 |

> **中日词典体量对比**：日文主词典 `JA/32` = **4.89 MB**；中文拼音 `CN/pinyin/GB18030` = **2.81 MB**（含 base1/2/3）。
> 而**中文的预测/联想词典 `njexyomi.a` 只有 1,528 B**，日文 `njexyomi*.a` 也只是 94 KB 级
> —— 这就是「联想功能不行」的量化解释。

#### 词典文件格式（已验证）

全部 `nj*.a` / `nj*.ad1` 以魔数 **`NJDC`** 开头，**大端序**：

```
0x00 "NJDC"          0x04 u16 version(1 或 2)
0x08 u32 (0x00040000/0x00050000)   0x0C u32 ≈ 数据长度
0x10 u32 header_size（base 类 0x54，exyomi 类 0x3C）
0x14 / 0x18 / 0x1C  u32 各段计数
```

---

### 5. 已验证：三痛点的真实成因

| 痛点 | 成因（已定位） | 证据 |
| --- | --- | --- |
| ① 按键位置不好 | 布局是 **bflyt 二进制资源**，只在 4 种基础键帽间切换（`SwkbdBaseKeytop50on/Qwerty` 等）；键位坐标写死在 bflyt 里，不能通过配置调整 | `lyt/*.szs` 内 40–131 个 `.bflan`/`.bflyt` 条目 |
| ② 联想功能不行 | 中文预测词典 `njexyomi.a` = **1.5 KB**（近空壳）；预测逻辑在 `main` 的 `KeyboardPredict` 模块内，无统计语言模型 | 0805 清单；swkbd rodata |
| ③ 没有游戏词库 | 词库是独立 title 的独立文件，**但 iWnn 只认 `NJDC` 格式**，不存在「随手丢个 txt 就生效」的入口；且系统无用户词典注册 UI/持久化 | 0805/0808 清单；swkbd 无 `userdict`/`learning` 相关串 |

---

### 6. 三条路线的落点与成本（修正版）

| 路线 | 落点 | 判定 | 主要成本 / 风险 |
| --- | --- | --- | --- |
| **A. 扩充词库** | LayeredFS 覆盖 `0100000000000805` 的 `Iwnn/ZH/CN/pinyin/GB18030/njtan.a`、`njubase*.a` | **落点最准，但需 NJDC 编解码器** | 需逆向/复刻 iWnn `NJDC` 索引结构（trie ＋ 记录库）；风险：格式猜错 → iWnn 初始化失败 → swkbd 起不来 |
| **B. 改键位** | LayeredFS 覆盖 `0100000000001008` 的 `lyt/Qwerty.szs` 等 | 理论可行，工程偏重 | 需 Yaz0 编码器 ＋ SARC 打包 ＋ bflyt 编辑器（SwitchLayoutEditor/Switch-Toolbox 量级）；**且逻辑键位映射在 code 里，改图不改行为** |
| **C. 换引擎** | LayeredFS 覆盖 `0100000000001008` 的 ExeFS `main` | 唯一能交付「全新输入法」的路 | 数人月；swkbd 崩溃 → **全系统键盘失效**（含所有游戏与系统界面）。先例：uLaunch 重写 qlaunch |
| ~~D. sysmodule 做 am 层 mitm~~ | — | **只能改参数/重定向，造不出拼音引擎** | sysmodule 拿不到 applet 代理（switchbrew 明载） |

**关于 LayeredFS 覆盖系统 Data title：置信度已由「中」升为「高」（代码级证实，见 §9）**。

v2 时这还是猜测；本版已用 **Atmosphere 官方源码 + swkbd 自身 rodata** 完成三环闭环：
词典走的正是 `OpenDataStorageByDataId` —— 而这恰好是 `fs.mitm` 会套 LayeredFS 的路径之一。
**剩余风险已不在「能不能覆盖」，而在「NJDC 能否正确构造」**（见 §7 第 2 项）。

---

### 7. 下一步验证清单（按性价比排序）

1. **LayeredFS 覆盖冒烟测试**（约 10 分钟，零风险）
   在 `sdmc:/atmosphere/contents/0100000000000805/romfs/` 放一个**改动 1 字节**的
   `Iwnn/ZH/CN/pinyin/GB18030/njexyomi.a`；进游戏呼出键盘 → 中文拼音模式。
   若中文候选消失/键盘异常 → 证明覆盖生效（路径通）；若毫无变化 → 该 title 不可覆盖，转 §6 退路。
   *注意：先备份原文件；此测试只影响 emuMMC。*
2. **NJDC 结构测绘**：对 `njubase1.a`（90 KB，最小完整样本）做段划分与索引试探，
   判断能否在不重排索引的前提下「追加记录」。
3. **实机确认可输入集**：系统语言设为简体中文 + 3~5 个游戏，记录 swkbd 实际给出的
   输入模式（拼音/注音/仓颉/笔画/粤拼）与候选行为，量化「联想差」的体感。
4. 备用：把 0805/0808 的全部 `NJDC` 词条导出为文本，与市面词库（如 Rime、Google 拼音）diff，
   量化缺词规模，作为路线 A 的收益预估。

---

### 8. 本版推翻 v1 的结论

| v1 说法 | 实际（本版证据） |
| --- | --- |
| 「swkbd 内没有任何词典数据，**也没有中文输入**；语言表只有 16 西文 + 4 日文」 | **错**。`message/CNzh/swkbd.msbt` 明确列出 **简体中文 / 繁體中文 / 한국어**；引擎是 **iWnn 1.16.2**；中文词典 17.25 MB 在 title `0100000000000805` |
| 「③ 没有游戏词库 —— **没有词库可换，因为它本来就没有**」 | **错**。词库是**独立 title 的独立 RomFS 文件**，落点真实存在（只是格式是私有的 `NJDC`） |
| 「② 联想功能不行 —— **不可改**」 | **过强**。数据侧可扩充（`njtan.a`/`njubase*.a`）；只有「模型级」改进不可做 |
| 「RomFS 629 KB 内无词典 → 故无词典」 | 推理跳跃。**swkbd 的 RomFS 不是词典的存放位置**，词典在独立 title |
| enum 标注：`crypt_type=3 → BKTR` | **3 = CTR**；`1=NONE,2=XTS,3=CTR,4=BKTR` |
| NSO 头：`0x1C` 读作 mod0 偏移 | `0x1C` 是 text 的 `align`；mod0 是 `segments[0].align_or_total_size` 的语义 |

> 附带纠正：`sound/swkbd.bfsar` 的 `FSAR` magic 是**音效归档**，不是字体；swkbd 的字体来自 `nn::font`（`common/sead/nvn_font/nvn_font_shader.bin`）。

---

### 9. 已验证（代码级）：LayeredFS 能不能覆盖词典 title

**结论：能。** 判定链三环，每环都有 Atmosphere 官方源码或 swkbd 自身二进制作为硬证据。
本节的全部结论来自 `refs/ams/` 下已存档的 Atmosphere 源文件（见 §10 末）。

#### 9.1 数据侧：swkbd 拿词典走的是 `OpenDataStorageByDataId`

扫 `main.rodata.bin`（1,103,596 B）得到的 **Nintendo SDK 符号 / 日志格式串**：

| 偏移 | 字符串 | 含义 |
| --- | --- | --- |
| `0x0000dcab` | `OpenDataStorageByDataId` | **`nn::fs` 打开 Data title romfs 归档的 API** |
| `0x0000c0b6` | `MountRom` | `nn::fs::MountRom`，把 Data title 的 romfs 挂成命名挂载点 |
| `0x0000d3cb` | `QueryMountRomCacheSize` | 上述 MountRom 的缓存预查询 |
| `0x000288a0` | `fsp-srv` | 文件系统服务名（全部 fs 调用都经它） |
| `0x000087b4` | `, systemdataid: 0x%lX, size: %zu` | 日志格式串：**按 SystemDataId 打开**，印证上两条 |
| `0x0002fcb1` | `N2nn2fs15RomFsFileSystemE` | C++ mangled → `nn::fs::RomFsFileSystem` |
| `0x0002fce0` | `N2nn2fs12_GLOBAL__N_114RomFsDirectoryE` | → `nn::fs::(anonymous)::RomFsDirectory` |
| `0x00006f94` / `0x00008b34` | `dic2://Iwnn` / `dic://Iwnn` | iWnn 侧的挂载 URI |
| `0x0010d610` | `SDK MW+OmronSoftware+iWnn-1_16_2` | 引擎版本串 |

**关键推论**：`dic://Iwnn` 不是磁盘路径，而是「一个**命名 romfs 挂载点**」，
该挂载点由 swkbd 用 `nn::fs::MountRom` + `OpenDataStorageByDataId(systemdataid, …)` 建立。
即 swkbd **不是**从自己的 romfs 里取词典，而是**按 title id 打开 Data title 的归档**。

> 补充证据：main 三段内**没有**硬编码的 `…0805` / `…0808` / `…1008` 立即数（LE/BE 全 0 命中），
> 说明 systemdataid 是运行期由 iWnn / ncm 给出，而不是写死在代码里。

#### 9.2 Atmosphere 侧：`OpenDataStorageByDataId` 正是被 mitm 的那条路

`stratosphere/ams_mitm/source/fs_mitm/fs_mitm_service.cpp`：

```cpp
Result FsMitmService::OpenDataStorageByDataId(Out<IStorage> out, ncm::DataId _data_id, u8 storage_id) {
    /* Only mitm if we should override contents for the current process. */
    R_UNLESS(m_client_info.override_status.IsProgramSpecific(), sm::mitm::ResultShouldForwardToSession());

    const ncm::ProgramId data_id = {_data_id.value};

    /* Only mitm if there is actually an override romfs. */
    R_UNLESS(mitm::fs::HasSdRomfsContent(data_id), sm::mitm::ResultShouldForwardToSession());

    FsStorage data_storage;
    R_TRY(fsOpenDataStorageByDataIdFwd(fwd, &data_storage, (u64)data_id, (NcmStorageId)storage_id));
    ...
    /* Get a layered storage for the data id. */
    out.SetValue(MakeSharedStorage(GetLayeredRomfsStorage(data_id, data_storage, false)), target_object_id);
}
```

**第一道 gate 看「调用方（swkbd）的 status」，第二道 gate 才看「目标 data_id」。两个都得为真。**

对照：`OpenFileSystemWithId` / `OpenFileSystemWithPatch` 走的是 `OpenWebContentFileSystem`，
开头就 `R_UNLESS(ncm::IsWebAppletId(client_program_id) && filesystem_type == ContentManual, forward)`
—— 只服务 web applet 的手册内容，**跟 romfs 覆盖无关**。这解释了「为什么必须确认走的是哪条 API」。

`amsmitm_fs_utils.cpp` 里 `HasSdRomfsContent` 的判定：

```cpp
bool HasSdRomfsContent(ncm::ProgramId program_id) {
    /* Check if romfs.bin is present. */
    { if (OpenAtmosphereSdFile(&romfs_file, program_id, "romfs.bin", OpenMode_Read) 成功) return true; }

    /* Check for romfs folder with content. */
    if (OpenAtmosphereSdRomfsDirectory(&romfs_dir, program_id, "", OpenDirectoryMode_All) 失败) return false;
    return fsDirGetEntryCount(&romfs_dir, &num_entries) && num_entries > 0;
}
```

路径由 `FormatAtmosphereRomfsPath` → `FormatAtmosphereSdPath(…, program_id, "romfs", …)` 拼出：

```
/atmosphere/contents/%016lx/romfs/<src_path>
```

#### 9.3 gate ①（调用方 swkbd 必须是 ProgramSpecific）默认成立

`libraries/libstratosphere/source/cfg/cfg_override.board.nintendo_nx.inc`：

```cpp
OverrideKey g_default_override_key = {
    .key_combination     = HidNpadButton_L,
    .override_by_default = true,
};

constexpr inline bool IsOverrideMatch(const OverrideStatus &status, const OverrideKey &cfg) {
    bool keys_triggered = ((status.keys_held & cfg.key_combination) != 0);
    return (cfg.override_by_default ^ keys_triggered);
}
```

未按 L → `true ^ false = true` → `status.SetProgramSpecific()`。
**这既是社区「按住 L 启动即禁用该游戏全部 mod」的机制，也说明默认所有 title 都是 ProgramSpecific。**

> 另有一条无条件分支：`program_id < ncm::SystemAppletId::Start` 或 `!HasLaunchedBootProgram(Qlaunch)` 时直接
> ProgramSpecific。swkbd = `…1008` **大于** `Start = …1000`，不在该分支，走上面的默认键判定。

#### 9.4 实机配方

```
sd:/atmosphere/contents/0100000000000805/romfs/Iwnn/ZH/CN/pinyin/GB18030/njexyomi.a
sd:/atmosphere/contents/0100000000000805/romfs/Iwnn/ZH/CN/pinyin/GB18030/njtan.a
sd:/atmosphere/contents/0100000000000805/romfs/Iwnn/ZH/CN/pinyin/GB18030/njubase1.a
```

- **overlay 语义**：只需放**要改的文件**，其余自动回落到原 romfs（不是整包替换）
- **不要**只建空的 `romfs/` 目录 —— `num_entries > 0` 才算命中（`0` 条 = 不生效）
- 也可用 `romfs.bin` 整包替换（需自建完整 romfs，成本高、内存风险大）
- 同一机制对 swkbd 自身（`…1008`）成立：`contents/0100000000001008/romfs/` 可覆盖 `lyt/*.szs`，
  `exefs/` 可换 `main`（§6 的路线 B / C）

#### 9.5 残余风险（诚实标注）

| 风险 | 说明 | 缓解 |
| --- | --- | --- |
| **内存预算** | LayeredFS 要在内存里**重建虚拟 romfs**（`QueryMountRomCacheSize`、`MaximumRomfsBuildAppletMemorySize`）。词典 title 17–18 MB / 76+ 文件，applet 内存池有硬上限 | 先只放**单个小文件**（`njexyomi.a` 仅 1.5 KB）验证通路；避免整包 `romfs.bin` |
| **NJDC 必须合法** | 覆盖进去的必须是 iWnn 能解析的 NJDC；格式错 → iWnn 初始化失败 → 键盘起不来 | 先做 §7 第 2 项的 NJDC 测绘；冒烟测试用「改 1 字节」而非「换文件」 |
| **缓存 lifecycle** | `GetLayeredRomfsStorage` 按 program_id 缓存；`is_process_romfs=false` 不进回收队列 | 换文件后重启机器（或至少重进 HOME） |
| **未实机验证** | 以上全部由**官方源码 + 静态二进制**推导，**尚未在实机跑过** | §7 第 1 项冒烟测试 |

---

### 10. 本工程工具（`tools/`）

| 工具 | 作用 |
| --- | --- |
| `nca.py` | NCA 头部 XTS 解密、FS header / FsEntry 解析 |
| `index_fw.py` | 固件包全量索引（238 NCA 头部 → titleId / kg / 分区） |
| `dump_nca.py` | 按 hactool 参数解密任意 section（**含正确的 CTR IV 构造**） |
| `nso_dump.py` | ExeFS → `main` → NSO0 头解析 + **单块 LZ4** 分段解压 |
| `nca_romfs.py` | NCA → 解密 section → **IVFC 层表 → RomFS 文件树遍历 / 提取** |
| `romfs_dump.py` | Yaz0 解压（**无终止符**实现）＋ SARC 解析 |
| `id_applets.py` | 批量读 `main.npdm` 的 META 名 → 识别全部 applet（swkbd / qlaunch / …） |
| `scan_data.py` | 全 Data title 普查：解密 Section0 + 关键词命中 + 名称提取 |
| `nand.py` / `probe_entropy.py` | emuMMC raw NAND 访问与明/密文诊断（已证伪，留档） |
| `verify_keys.py` | prod.keys 内部自洽性审计（master_key / titlekek 全 OK） |
| `nso_scan.py` | 扫 NSO 三段：ASCII/UTF-16 关键词字符串 + title id 立即数（LE/BE）——§9 证据来源 |
| `nso_kw.py` | 按自定义关键词表扫 NSO 字符串（判断引擎是否读外部词典文件）——§11 证据来源 |
| `njdc_probe.py` | NJDC 头部字段 / UTF-16 串分布探测（判断明文 or 加密、字符串池位置） |
| `njdc_parse.py` | 按 GBATEK 描述尝试解析词条表，抽取词条验证可读性 |
| `njdc_layout.py` | dump NJDC 关键区域，观察索引表 / 记录区 / 字符串池的分区 |

**参考源码存档**：`refs/ams/` 下保存了判定 §9 所需的 Atmosphere 源文件
（`fs_mitm_service.cpp/.hpp`、`fsmitm_romfs.cpp/.hpp`、`fsmitm_layered_romfs_storage.cpp/.hpp`、
`amsmitm_fs_utils.cpp`、`cfg_override.cpp`、`cfg_override.board.nintendo_nx.inc`、
`ldr_content_management.cpp`、`ldr_ro_manager.cpp`），
来源 `github.com/Atmosphere-NX/Atmosphere` master 分支（raw 直取）。
下载注意：本机 curl 走 schannel，需加 `--ssl-no-revoke`，否则报 `CRYPT_E_NO_REVOCATION_CHECK`。

**PFS0 注意**：本固件（22.x）system title 的 ExeFS 条目是
**0x18 字节、三个 u64**（`offset / size / string_table_offset`），
与 hactool 老版 `pfs0_file_entry_t`（0x10 字节、四个 u32）**不同**。
`nso_dump.py` 用「entry0.offset==0 且 entry1.offset==entry0.size」做双布局判定。

---

### 11. 「能不能插入第三方词典」——分层结论（v3 追加实测）

**一句话：能，但不是「丢一个词库文件进去」那种装法；只能改已有文件，且必须写出合法 NJDC。**

#### 11.1 引擎层：iWnn 本来就有可外部注入的词典种类

OMRON iWnn 的词典体系（Nintendo 官方《iWnn Programming Manual》公开目录页 + OMRON 官网 + Wnn SDK 公开手册）：

| 类别 | 说明 | 可外部注入 |
| --- | --- | --- |
| Integrated（统合词典） | 主词典 | 否（编译期） |
| Single Kanji（单汉字） | `njtan.a` | 否 |
| **Ancillary Word（辅助词）** | 补充词条 | **是** |
| **User（用户词典）** | 用户注册词 | **是** |
| **Learning（学习词典）** | 用户输入历史 | **是** |
| Rule（规则） | 语法/连接规则 | 否 |
| **Customized（定制词典）** | 厂商定制 | **是** |
| No Reading Prediction | 仅预测 | 否 |

Android 版（Wnn Keyboard Lab）**明确支持「追加词典」**，路径 `/sdcard/wnnlab/` → 证明引擎有该能力。

#### 11.2 但 Switch 版 swkbd 只启用了「固定文件名词典」模式（硬证据）

扫 `main.rodata`，命中**完整且硬编码的词典文件名清单**：

```
njubase1.a  njubase2.a  njubase3.a  njubase1.ad1  njubase2.ad1  njubase3.ad1
njtan.a     njtan.ad1   njexyomi.a  njexyomi.ad1
njcon.a     njcode.a    njcangjie.a njstroke.a
keisei/njubase1.ad1   keisei/njubase2.ad1   keisei/njtan.ad1   keisei/njexyomi.ad1
njubase1us.a   njubase1pt.a   njubase1br.a   njubase1gb.a
```

同时，关键词表（`njuser` / `usrdic` / `userdict` / `wdic` / `learning` / `njaddon` / `.dic` / `njx_` 等 42 个）
在 `main.text` / `main.rodata` / `main.data` **三段里零命中**。

**由此得到三条硬结论**：

1. **没有「用户词典文件」入口** —— 引擎不读 `wdic` / `*.dic` / 任何外部词库文件。
2. **没有学习词典持久化** —— 没有任何 learning 相关字符串；这也解释了为什么 NS 输入法**"不记事"**。
3. **不能新增文件** —— iWnn 按**硬编码文件名**去找词典。往 romfs 里塞一个 `mydict.a` **不会被加载**。
   **只能覆盖已有文件**。

#### 11.3 好消息：NJDC 是明文结构化词库，不是加密黑盒

`njubase1.a`（90,402 B）实测分区：

| 区间 | 内容 | 证据 |
| --- | --- | --- |
| `0x00–0x54` | NJDC 头（84 B） | 与 GBATEK 的 3DS NJDC 文档**字段完全吻合**：大端、`0x0C = filesize − 0x70`、`0x10 = 0x54` |
| `0x54–0x47A` | 索引 / bucket 表 | `0x70` 起大量 `00 00 00 01`；`0x1F8` 起为**递增 u32 偏移数组** |
| `0x47A–0x8760` | 记录区（定长 + 变长混合） | 条目形如 `00 00 0d 18 00 00 0d 18 08 06 06 00 …`；小偶数（`0x0A`/`0x0C`/`0x0E`/`0x10`）高频出现 = 字符串长度 |
| `0x8760–0x112E6` | **读法字符串池**（UTF-16BE） | 明文：`afuhan agenting aibushi shouaichou aidai aierlan aiguozhuyi aihao…` |
| `0x112E6–0x146F0` | **表记字符串池**（UTF-16BE 汉字） | 明文：`一下 一个 一些 一人 一件 一份 一位 一体 一切 一句 一只 一名 一周…` |
| `0x146F0–0x1611E` | 压缩/位打包表（待解） | 该区间按 UTF-16 解读全是乱码 → 位打包数据 |
| `0x1611E` + 112 B | NJDC footer + 附加数据 | `0x30 = 0x70 = 112` 对上 |

**没有加密、没有压缩、没有校验和保护字符串区** —— 词条直接可读。
→ **「写一个 NJDC 生成器」在原理上没有障碍**，难点只在记录/索引表的字段语义。

#### 11.4 `.a` 与 `.ad1` 是两套并列槽位（可降低风险）

- `.ad1` 的魔数是 **`NJAD`**（不是 NJDC），内部在 `0x28` 处**再嵌一个完整的 NJDC**。
- `njubase1.ad1` 内层 NJDC 的头部字段与主词典**逐字节相同**（含 `0x0C = 90290`）→ 它是**附属/变体**，不是独立词典。
- 只有部分词典有 `.ad1` 伴生（`njubase1/2`、`njtan`、`njexyomi`；`njcode` 没有）。
- 且存在 **`njubase1us.a` / `njubase1pt.a` / `njubase1br.a` / `njubase1gb.a`** 这种**变体词典**先例
  → 说明**同一槽位可以装内容不同的词典**，不必与原词典结构逐字节一致。

**实操建议**：先只覆盖体积最小的 `.ad1`（30,630 B），保留 `.a` 不动 → 出问题的爆炸半径最小。

#### 11.5 真实门槛（**v4 已全部突破，本节保留历史记录**）

| 门槛 | v3 时的现状 | v4 结论 |
| --- | --- | --- |
| **记录 / 索引表字段语义** | 已确认骨架，「字段含义未测完」← v3 唯一硬骨头 | **已彻底解出**，见 §12.2；往返重建 `njubase1/2` 除记录表偏移外 **0 字节差异** |
| **"加词"要重排全表** | 新增词条必须重建整个文件 | **已实现**生成器 `tools/njdc_lib.py:build_njdc()`，150,000 条实测通过 |
| **`.ad1` 的确切角色** | 「追加」还是「第二编码集」未定论 | **仍未解**（NJAD 容器语义），但已提供推测性头部同步方案，非必需，见 §12.6 |
| **内存 / 合法性** | applet 内存预算 + NJDC 非法会导致 iWnn 初始化失败 | 见 §12.5 残余风险；生成文件已过全部结构校验，**实机冒烟待跑** |

> 具体规范、往返校验数据、生成器产出与验证方法见 **§12（v4 追加）**。

#### 11.6 另一条完全不同的路（不走词典）

iWnn 暴露 `njx_*` API，Nintendo 的 `KeyboardConfig` 允许调用方（游戏）传入候选词列表。
→ **游戏可以自己往键盘里塞词**，但这是**游戏侧代码**的事，改不了系统全局输入法。
（对「系统级加词库」这个目标无效，但值得知道。）

#### 11.7 合规备注

排查过程中确认存在 Nintendo 官方开发者文档《iWnn Programming Manual》（WUP-06-0101-001-C,
2013-04-03, CONFIDENTIAL），其**公开可检索的目录页**印证了 §11.1 的 8 类词典与 `njx_*` API 体系。
该文档经非授权渠道流出，**本工程不下载、不转载、不再分发**；
本报告所有技术结论均来自**自有设备固件备份的二进制解出结果**与公开资料
（GBATEK 的 NJDC 条目、OMRON 官网 iWnn 页面、Wnn SDK 公开手册）。

---

### 12. NJDC 格式完整规范 + 生成器 + 实测词典（v4 追加，2026-09-27）

> **一句话**：NJDC 已 100% 解出并按规范实现了**读→写往返**；据此生成的
> **150,000 条**中文拼音词典已通过全部结构校验，覆盖原版 `njubase3.a` 且**原版条目零丢失**。

#### 12.1 结论先行

| 项 | 结果 | 证据 |
| --- | --- | --- |
| NJDC 结构是否解出 | **是，全部字段字面确认** | `tools/njdc_lib.py:parse_njdc()` |
| 能否字节级重建 | **能**。`njubase1.a` / `njubase2.a` 重建后除记录表内偏移外 **0 字节差异** | `verify_roundtrip()` |
| 能否生成大词库 | **能**。完整版 150,000 条 / 3,943,866 B；轻量版 80,000 条 / 1,842,608 B | `dist/verify-report.txt` |
| 是否丢原版词 | **否**。两版「原版有而新版无」均 = **0 条** | 同上 |
| 实机是否验过 | **否**（本轮为 PC 侧结构 + 功能校验，实机冒烟步骤见 §12.7） | — |

#### 12.2 NJDC 文件布局（权威规范）

所有多字节整数**大端**。记 `N` = 词条数。

**（A）头部 0x00–0x54（84 字节 = 21 × u32）**

| 偏移 | 含义 | 实测值（njubase1） |
| --- | --- | --- |
| `0x00` | 魔数 | `"NJDC"` |
| `0x04` | 版本 | `0x00020000` |
| `0x08` | 版本 | `0x00050000` |
| `0x0c` | `文件大小 − 28 − 头部长度`（头长 84 时即 `size − 112`） | `size − 112` |
| `0x10` | 头部长度 | `0x54` = 84 |
| `0x14` | **读法最大字节数**（UTF-16BE 字节长度） | 实测值 |
| `0x18` | **表记最大字节数** | 实测值 |
| `0x1c` | `0` | — |
| `0x20` | **记录表偏移** | 恒 `1146` = 0x47A |
| `0x24` | **字符串池偏移** = `0x20 + 10N` | — |
| `0x28` | **尾部表偏移** = 池偏移 + 池长 | — |
| `0x2c` | 附加区偏移（`0` = 无） | `njubase3` 非零 |
| `0x30` | `112`（尾部保留常量） | `0x70` |
| `0x34..0x40` | `0` | — |
| `0x44` | **前缀 + T 表结束**（即 2 字节间隙的起点） | `0x478` = 1144 |
| `0x48` | 常量 | `0x00010101`（`njtan` 为 `0x000e0104`） |
| `0x4c` | 常量 | `0x00010101` |
| `0x50` | **记录数 N** | `njubase1` = 3351 |

> **偏移算术链（实测 `njubase1.a`，90,402 B）**：
> `0x54`(84) ＋ 9×4 前缀(36) ＋ 256×4 T 表(1024) = **1144 = 0x478 = `0x44`**
> → 加 2 字节间隙 `08 06` → **1146 = 0x47A = `0x20`（记录表偏移）**
> → `0x24`（池偏移）= `0x1146 + 10N` = 1146 + 33,510 = **34,656 = 0x8760**
> → `0x28`（尾表偏移）= 池偏移 ＋ 池长 = **83,696 = 0x146F0**
> → 文件大小 = 尾表偏移 ＋ 2N ＋ 4 = 83,696 + 6,702 + 4 = **90,402** ✓，
> 且 `0x0c = 90,402 − 112 = 90,290` ✓。
> **生成器把 `0x44` 直接写常量 `1144`**（对任何 N 都成立，因为 T 表尺寸固定），与原版逐字节一致。

**（B）索引区 0x54–0x47A（1062 字节 = 36 ＋ 1024 ＋ 2）**

1. `0x54` 起 **9 × u32 前缀** = `[0,1,0,0,0,0,0,0,1]`（`njubase3` 等主词典一致）
2. 紧接 **256 × u32 T 表**：`T[b] = 1 + #{ 读法首字符的 ASCII 字节 ≤ b 的条目数 }`
   → `T[0] = 1`、`T[255] = N + 1`。这是**按首字母分桶**的加速索引。
3. 再接 **2 字节间隙** `08 06`（标准词典含 `njubase3` 均如此；生成器照抄）

**（C）记录表 0x20 起，每条 10 字节 × N**

```
u8  读法字节长度（UTF-16BE 字节数，非字符数）
u24BE 读法偏移（相对「读法池」首）
u8  表记字节长度
u24BE 表记偏移（相对「表记池」首）
u16 保留 = 0x0000
```

**（D）字符串池 0x24 起 = 读法池 ∥ 表记池**

- 每个池 = 若干唯一串拼接，**按 UTF-16BE 字节序升序**排列；
- 只收录**非任何其它串的子串**的串（「极大串」）——被包含者不占位，用偏移指向宿主串某次出现；
- 共享串的偏移取该串在池中的**某次出现**（厂商多数取首次，但实测 76~78% 不是；
  属**等价选择**，不影响语义）。生成器取**首次出现**，往返校验通过。

**（E）尾部表 0x28 起 = N × u16 + 4 字节 `"NJDC"`**

- 每词一个 u16，**高字节 == 低字节**：`njubase1/2/njtan` 口径为 `0x40 | v`，`v ∈ [0,63]`
  = **词条优先级 / 词频**（`ou*` 品牌名实测 `v=0`）；
- 变体：`njcode` 全 `0x4000`；`njubase3` 用 `0x8040 / 0x0000 / 0xHHHH` 混合；
- 文件大小 == **尾部表偏移 + 2N + 4**；`0x0c == 文件大小 − 112`。

**（F）四本词典分工（实测）**

| 文件 | 条数 | 角色 |
| --- | --- | --- |
| `njtan.a` | — | 单字（全表记长度 1） |
| `njubase1.a` | 3,351 | 常用词 |
| `njubase2.a` | 3,235 | 专名 |
| `njubase3.a` | 57,954 | **大词库 / 联想主力** |

#### 12.3 往返自校验（证明规范正确）

`tools/njdc_lib.py:verify_roundtrip()`：`读入 → parse_njdc() → build_njdc() → 字节比对`。

| 文件 | 结果 |
| --- | --- |
| `njubase1.a` | **除记录表内偏移外 0 字节差异**；条目语义 100% 一致 |
| `njubase2.a` | 同上 |
| `njcode` / `njtan` | 条目语义一致（差异仅尾部表变体 / 索引变体，见 §12.2(E)） |
| `njubase3.a` | 条目语义一致；尾部表变体已单独处理 |

> 「记录表偏移」这条差异来自 §12.2(D) 的**共享串偏移等价选择**（厂商不总取首次），
> 属规范内自由度，不影响任何语义。

#### 12.4 生成器与词库产出

**工具**（`D:/proj/WorkBuddy/ns-ime/tools/`）

| 脚本 | 作用 |
| --- | --- |
| `njdc_lib.py` | 核心库：`build_njdc` / `parse_njdc` / `maximal_strings` / `build_pool` / `verify_roundtrip` |
| `mkdict.py` | 词库编译器：读雾凇拼音 rime-ice `*.yaml` + 内嵌游戏词表 → 输出 NJDC |
| `verify_njdc.py` | 结构逐项校验（`[OK]/[FAIL]`）+ 命中抽查 + 与原版对账 |
| `patch_ad1.py` | 可选：把新 `.a` 的 84 字节头同步进 `.ad1`（§12.6） |

**产出**（`dist/`）

| | 原版 | 完整版 | 轻量版 |
| --- | --- | --- | --- |
| 条目 | 57,954 | **150,000** | 80,000 |
| 大小 | 1,606,890 B | 3,943,866 B | 1,842,608 B |
| 新增 | — | **+87,729** | +17,729 |
| 原版丢失 | — | **0** | **0** |

来源：单字 8,756 ＋ 游戏词表 252 ＋ **原版 57,954 全量并入** ＋ 常用词 83,038（rime-ice）。
拼音口径与设备**完全一致**（`ü` 写作 `v`：`lv/nv/lve/nve`），已在设备词典逐条核对。

#### 12.5 验证方法（PC 侧 + 实机侧）

**PC 侧结构校验**（`verify.bat`）：逐项检查魔数、头部长度、`0x20=1146`、`0x24=0x20+10N`、
`文件大小=尾部表+2N+4`、`0x0c=大小-112`、`0x44=1144`、间隙 `08 06`、T 表可复算、
所有记录偏移合法、读法 UTF-16BE 升序、`0x14/0x18` 一致、尾部表形态、文件尾 `NJDC`。
**两版全部通过**。

**PC 侧功能抽查**：`shalujianta → 杀戮尖塔`（**原版没有此词，关键判据**）、
`aierdengfahuan → 艾尔登法环`、`heishenhuawukong → 黑神话悟空`、`cundang → 存档`、
`lianji → 联机`、`jisuanjishu → 计算技术` 全绿；并做原版对账。

**实机侧冒烟**：先跑基线（不装 overlay 打 `shalujianta` 应打不出「杀戮尖塔」），
再装 overlay 后重测。完整步骤 / 排查清单见 本文档的「大词库成果与验证」节 §4.3。

> ⚠️ **Atmosphere 覆盖键默认是 `L` 且 `override_by_default = true`**
> （`IsOverrideMatch = override_by_default ^ keys_triggered`）→ **开机按住 L 会关闭覆盖**，
> 现象是「完全没生效」。这是最容易误判成「方案失败」的坑。

#### 12.6 仍未解出 / 残余风险（如实标注）

1. **`njubase3.ad1`（NJAD 容器）语义未解**。已知其 `0x28` 起内嵌一份与 `.a` **逐字节相同**的
   0x54 头部副本。若引擎拿该副本做一致性校验，替换 `.a` 后校验会失败。
   `dist/overlay-with-ad1/` 为**推测性**修补（保留 `.ad1` 全部原始内容，只同步那 84 字节头）。
   **策略：先试 `overlay/`，不生效再试 `overlay-with-ad1/`。**
2. **尾部表 6bit 值语义是「优先级/词频」的推断**，非实测确认；本工程按 `njubase1/2/njtan`
   口径写 `0x40|v`；影响**候选排序**，不影响「能否打出」。
3. `njtan.a` 独有 4 字节/条「读音索引区」、`njubase3` 附加区（149,352 B）语义未解；
   生成器走**无附加区的干净布局**（同 `njubase1`）。
4. **候选排序不保证优于原版**：采取「不回归」策略——原版条目沿用原优先级，新词按词频映射。
5. 繁体（`ZH/TW`）与粤拼 / 仓颉 / 笔画路径未覆盖，本轮只做简体拼音 `ZH/CN/pinyin`。

#### 12.7 设备拼音口径（实测，与雾凇拼音一致）

`ü → v`（`lv/nv/lve/nve`）；`qu/xu/yu/ju` 用 `u`；`谁=shei/shui`、`血=xie/xue`、
`熟=shou/shu`、`钥=yao`、`壳=ke/qiao`；**读法最长 36 字符**。

#### 12.8 复现命令

```bat
python tools\mkdict.py ^
  --lex lex\ice_8105.yaml --lex lex\ice_base.yaml --lex lex\ice_ext.yaml ^
  --merge out\dat0805\files\Iwnn\ZH\CN\pinyin\GB18030\njubase3.a ^
  --limit 150000 --out dist\njubase3.a
```

哈希：`njubase3.a` = `657b6c102f09afe0…`；`njubase3-lite.a` = `c3d545372d1de134…`（完整值见 本文档的「大词库成果与验证」节）。

---

### 13. 实机验证 + 原版词典版式对照 + .nro 打包（v5 追加，2026-09-27）

#### 13.1 实机验证通过 —— 本工程最高等级证据

**用户在实机（Switch + 大气层）上测试成功**：LayeredFS 覆盖 `njubase3.a` 生效，
系统输入法拼音可以打出新词库的内容（`shalujianta → 杀戮尖塔` 等）。

→ **路线②由「源码推导（高置信度）」正式升级为「实机已验证」。**

**附带确认的一个关键性质（原报告没料到）**：
我们把原版 `njubase3.a`（**版式 A**：带 662 KB 附加区、记录表偏移 81726）
**整个换成了「干净版式」**（同 `njubase1`：记录表偏移 1146、无附加区、不同尾部表形态），
**引擎照常接受**。

> 结论：**iWnn 完全按文件自身的头部字段寻址，不要求同槽位文件的版式一致。**
> 这解释了为什么我们的生成器可以走最简版式 —— 也说明「必须逐字节模仿原文件」是不必要的
> （§11.4 当初「先只覆盖 `.ad1` 降低风险」的谨慎策略，事后看不必要）。

#### 13.2 原版 6 本词典的头部对照（本轮新数据，全部实测）

| 文件 | size | N | `0x0c` | 头长`0x10` | `0x20`记录表 | `0x24`池 | `0x28`尾表 | `0x2c`附加区 | `0x44` |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `njubase1.a` | 90,402 | 3,351 | 90,290 | 84 | **1146** | 34,656 | 83,696 | 0 | **1144** |
| `njubase2.a` | 91,258 | 3,235 | 91,146 | 84 | **1146** | 33,496 | 84,784 | 0 | **1144** |
| `njcode.a` | 8,204 | 285 | 8,092 | 84 | **1146** | 3,996 | 7,630 | 0 | **1144** |
| `njtan.a` | 256,025 | 14,184 | 255,913 | 84 | 57,895 | 199,735 | 227,653 | 0 | 57,880 |
| **`njubase3.a`** | 1,606,890 | 57,954 | 1,606,778 | 84 | **81,726** | 810,618 | 1,490,978 | **661,266** | 81,724 |
| `njexyomi.a` | 1,528 | **0** | 1,440 | **60** | 13 | 73 | 438 | 1,158 | 196,866 |

版式分三类：**clean**（`njubase1/2`、`njcode`，也是本工程生成器的产出）、
**extra**（`njubase3`，多一块 149,352 B 附加区）、**other**（`njtan`，自有索引区）、
以及 `njexyomi` 这个 N=0 的异构小文件。

> `njubase3` 的附加区大小 = `0x24 − (0x20 + 10N)` = 810,618 − 661,266 = **149,352 B**；
> 与 §12.6 记的「149,352 B 未解附加区」对上。

#### 13.3 两条被推翻的「假规范」（重要教训）

v4 把下面两条当成了 NJDC 的通用规律写进校验器，**都是错的**：

| v4 的写法 | 真相 |
| --- | --- |
| `0x20 == 1146`、`0x44 == 1144` 是 NJDC 不变量 | **只是「干净版式」的特征**。原版 `njubase3` 是 81,726 / 81,724，`njtan` 是 57,895 / 57,880 → 写死会把**原版文件误判成坏文件** |
| `0x0c == 文件大小 − 112` | **巧合**。正确通式是 **`0x0c = 文件大小 − 28 − 头部长度`**（头长 84 → 减 112 才对上；`njexyomi` 头长 60 → 减 88，故 `0x0c = 1440` 而非 1416） |

**怎么抓出来的**：把校验逻辑抽成平台无关的 `nro/source/njdc_check.h`，配一个 PC 端回归
`nro/tools/host_test.cpp`，拿**真实固件词典**跑，并加三个负例（破坏魔数 / 截断 4 字节 /
把 N 改大）。结果：`njexyomi` 被判错、原版 `njubase3` 被判错 —— 两个都是真 bug。

**最终校验器改成两层**：Tier 1 通用（魔数、头长取值、`0x0c` 通式、偏移单调性与边界）＋
Tier 2 严格（仅当文件自称干净版式时才施加 1146 / 1144 / 尺寸精确等式）。
现全样本 `ALL PASSED`，证据：`report/njdc_checker_regression.txt`。

> **方法论**：单一样本「量出来的规律」必须用第二个样本验证；把结论写成代码并用真实数据回归，
> 是发现「假规范」最有效的手段 —— 这比再多读几个字节有用。

#### 13.4 `.nro` 打包（HexDict）

**问题**：overlay 方案唯一的软肋是「出问题要拔卡 + 开电脑才能救回来」。

**结论**：能做成 `.nro`，但只到「安装器 / 管理器」这一层，**做不到热接管加载**。

| | 可行性 | 依据 |
| --- | --- | --- |
| 写文件到 `atmosphere/contents/.../romfs/` | **能** | 就是 SD 上的普通目录，homebrew 有写权限 |
| 装 / 卸 / 切换版本 / 自检 / 一键重启 | **能** | devkitPro + libnx 标准 homebrew |
| 热接管词典加载（不重启即换） | **不能** | 加载在 `fs.mitm`（sysmodule）层，`.nro` 碰不到 |

**决定「要不要重启」的源码结论**（`refs/ams/`）：

1. `HasSdRomfsContent()`（`amsmitm_fs_utils.cpp:187`）**实时**查 SD（打开 `romfs.bin` /
   列 `romfs/` 目录数条目），**无缓存** → 换文件后下一次打开就能看到。
2. layered storage 按 `program_id` 缓存在 `g_storage_set`，但 **非持久的**：
   finalizer 线程每 500 ms 扫一遍，引用计数为 0 的先给一次 second chance，再下一轮就
   `erase + delete`（`fsmitm_layered_romfs_storage.cpp:121-137`）→ **旧句柄释放后约 1 s 内回收**。
3. → **理论上不需要重启主机**，只要 swkbd 的旧 storage 句柄被释放（= 关掉键盘再打开）。
   若 swkbd 是常驻 applet（句柄不释放），则仍需重启。**这是一个可以实机实测的假设**（见 §13.5）。
4. applet 侧 romfs 构建预算是 `MaximumRomfsBuildAppletMemorySize = 32 MB`
   （`fsmitm_romfs.cpp:30`），远大于中文词典 romfs 的 ~18 MB → 内存不是瓶颈。
   注意 `ConfigureDynamicHeap` 只对 **application** 生效（`R_SUCCEED_IF(!is_application)`），
   swkbd 是 applet，走的是 applet 内存池。

**工程现状**：`nro/` 已备齐（Makefile / `source/main.cpp` / `njdc_check.h` / `gen_embed.py` /
`build.bat` / README / 已内嵌两版词典共 5.52 MB），**只缺 devkitPro 工具链**（本机未装）。

#### 13.5 待验 / 待办

- **实机冒烟（该做）**：装完**先不重启**直接打 `shalujianta` —— 能出即证明 §13.4-3 的推论，
  省掉一次重启；不能出则重启（且**开机勿按 L**）。
- **`njexyomi.a` 仍未解**：N=0、头长 60 的异构小文件。它是**痛点②「联想差」的直接落点**
  （中文版仅 1,528 B，近乎空壳），本轮的生成器与 `.nro` 都**没覆盖它**。
  要真正解决「联想」还需要单独解它的版式。
- **`.ad1`（NJAD）语义**仍未解（但实机已证明**不处理它也能工作**）。
- 候选词排序、繁中 / 粤拼路径、`njtan` 自有索引区，同 §12.6。

---

### 14. 重复条目修复 + 简拼（首字母联想）+ 校验器统一（v6 追加，2026-09-27）

#### 14.1 生成器有两个 bug，一个是真 bug，一个是「骗人的打印」

**真 bug：产物含 4,316 个重复键 / 4,317 行冗余。**

`compile_dict()` 把词条分四组拼装（单字 → 游戏词 → 原版并入 → 其余按权重降序），
但 `add()` **没有跨组去重**。三组之间在 `(读法, 表记)` 层面有 4,317 条重叠：

```
('a','啊') ('a','阿') ('ai','爱') …   ← 单字表与原版词典天然重叠
('ling','零') × 3                      ← 三组同时命中，候选列表里出现三次
```

后果：用户打 `ling` 时候选里「零」出现三次。四份产物（完整版 / 轻量版 / 两份简拼包）
**全都**中招，因为都走同一条拼装路径。

修法：`add()` 改为**首次出现者胜**（保留「单字 → 游戏词 → 原版」的组间优先序），
并让去重省下来的额度**自动被常用词补上**（`budget = limit − len(pick)`，`pick` 是去重后的真实条数）
→ 上限不浪费，实际词数反而多了 4,317 条。

**次生 bug：去重计数打印恒为 `-0`，差点让人以为修复没生效。**

```python
# 错误写法（v5）：dropped 在并入 rest 之后才算
dropped = len(singles) + len(gamed) + len(merged) - len(pick)
print(... max(0, dropped))     # pick 已被 rest 填到 limit → 相减恒为负 → 打印 -0
```

`rest` 会把 `pick` 补到 `limit`，之后再算「三组之和 − pick」必然是负数，
被 `max(0, ·)` 抹成 `0`。「跨组去重 -0」这个输出**看起来像结论，实际是恒等式**。

修法：把 `dedup_drop` 提到并入 `rest` **之前**计算。修后正确输出 `跨组去重 -4317`，
且四份产物 **sha256 与修复前逐字节一致** —— 反证了「只是打印错、产物一直是对的」。

> **方法论（第二次踩同类坑）**：
> ① 统计量必须在**正确的时点**采样，否则会打印出一个「永远成立、因而毫无信息量」的值；
> ② 交叉验证要用**独立手段**（这次是直接解析产物数重复键），不能只看程序自报。
> 这与 §13.3 的教训是同一类：**别相信单一口径，尤其是自己写的那个口径。**

#### 14.2 简拼（首字母联想）：`sljt` → 杀戮尖塔

**用户问题：「能变成安卓电视搜索那种吗，就是打首字母联想」。**

**答：能。已于 2026-09-27 实机验证通过。**（下文保留当时的推理链与探针设计 ——
它正是这次能一次成功的原因，也是可复用的方法论。）

**实机冒烟结果（我实测，2026-09-27）**：

| 输入 | 结果 | 性质 | 说明 |
| --- | --- | --- | --- |
| `sha` | 只有单字 | 正常 | 全拼前缀命中 **1,827 条**候选，目标词被挤出可视区 |
| `shal` | **杀戮尖塔** | 命中 | 候选降到 27 条，目标词露出来 |
| `0000` | **杀戮尖塔** | 命中 | 纯数字探针 |
| `zzzz` | **杀戮尖塔** | 命中 | 非音节字母串探针 |
| `jt` | **尖塔** | 命中 | 2 字母 |
| `bkm` | **宝可梦** | 命中 | 3 字母 |
| `sljt` | **杀戮尖塔** | 命中 | ★ 目标方案 |

**两条关键结论**：

1. **引擎对读法形态零校验**。原先最担心的「引擎按音节切分 → 辅音串被丢弃」**被实测否定**：
   `0000`（纯数字）与 `zzzz`（非音节串）都命中。
   这同时**反证了 `njcode.a` 的解读是对的** —— 那 285 条十六进制码点读法（`20164 → 𠅤`）
   不是特例，而是引擎支持「任意串读法」的正常用法。
   → **推论：任意编码的快捷输入都可行**（数字编码、自定义快捷词），是明确的扩展方向。
2. **大前缀下的「看起来没生效」是排序与候选数量问题，不是覆盖失败**。
   `sha` 有 1,827 条候选，`shal` 只剩 27 条 —— 同一个词在两处的可见性完全不同。
   **判断覆盖是否生效必须用「唯一前缀」**（`shal` / `shalujianta`），
   不能用 `sha` 这种几千条候选的大前缀。

**顺带修掉一个会露馅的问题：简拼串与同词全拼撞车**。

`阿呆` 全拼 `adai`，简拼 `ad` → 打 `ad` 时全拼前缀与简拼条目**各命中一次**，
候选列表里「阿呆」出现两次。这与 §14.1 修掉的 4,316 重复键是**同类问题，只是跨读法**。

- 判定条件：**简拼串是该词「其它读法」的前缀** ⟺ 会重复。
  （注意不能用「是任意读法的前缀」—— 那条太宽，会把 `sed→塞尔达` 误判，
  因为「塞尔达」自己的读法 `saierda` 并不以 `sed` 开头。）
- 规模：full 包 60,000 条里 295 条（0.5%）会重复，其中 293 条是 2 字母。
  几乎全是**首字零声母**的词（阿X / 按X / 沙盒 `shahe`）——
  因为首字拼音只有 `a/e/o` 一个字母时，简拼前两位正好等于全拼前两位。
- **处理：生成时直接丢弃（`--abbrev-allow-dup` 可关）。零功能损失** ——
  按定义，被丢的条目其全拼已以该串为前缀，且优先级相同 → 候选位置不变，
  用户看到的东西**完全一样**。丢弃后**会重复候选 = 0**。

做法：给多字词**额外追加一条「首字母读法」条目**，与全拼条目并存：

```
sljt   → 杀戮尖塔     （原条目 shalujianta 仍在）
aedfh  → 艾尔登法环
hshwk  → 黑神话悟空
bkm    → 宝可梦
cd     → 存档        zm → 周目
```

实现要点（`tools/abbrev.py` + `mkdict.py --abbrev*`）：

- 字→拼音表**从设备自己的 `njtan.a` 提取**（12,873 汉字 / 707 个多音字），
  与设备口径强一致 —— 否则会出现「按设备读音打的简拼匹配不上」这种玄学问题。
- 多音字生成多解并设上限（`--abbrev-max-combos 4`）：如「独立游戏」→ `dlyx` 与 `dlyh`
  （「戏」有 `xi` / `hu` 两读）。
- 只对长度 ≥ 2 字的词生成（`--abbrev-min-len 2`），避免单字简拼与全拼撞车。

**为什么不能直接说「能」**（这是本节的诚实底线）：

两条硬事实，**方向相反**：

| | 证据 | 指向 |
| --- | --- | --- |
| **支持** | 原版 `njcode.a`（285 条）的读法**全是十六进制码点串**：`20164 → 𠅤`、`20cd0 → 𠳐`、`2139a → 𡎚`……字符集是 `0-9` + `a-f`，长度 4–5，**不是任何拼音** | 引擎**至少存在一条**不做「合法拼音」校验的读法匹配路径 |
| **反对** | 原版 57,954 条拼音读法用设备 415 个合法音节去切分 **100% 可切、零例外** | 引擎可能把读法当**音节序列**处理，`sljt` 切不动（`sl` 不是合法音节）→ 查不到 |

⚠️ **不能直接外推**：`njcode` 位于 `pinyin/` 目录但与 `njubase1/2/3` 并列，
可能走的是**另一套输入模式**（unicode 码点直输），而拼音模式另有音节解析层。

**因此冒烟包加了数字探针**（`tools/mk_probe.py`，内部先做往返自检）：

```
sha   正常拼音前缀         —— 应照常出词（排除「overlay 根本没生效」）
0000  探针：纯数字         —— 模仿 njcode 风格
zzzz  探针：纯字母、非音节  —— 目标方案的同类
jt    探针：2 字母简拼
bkm   探针：3 字母简拼
sljt  探针：4 字母简拼      —— ★ 目标
```

一次实机即可把失败定位到层级：

| 观察 | 结论 | 下一步 |
| --- | --- | --- |
| `sljt` 出 | 引擎不校验读法形态 → **方案成立** | 换 `abbr-full` / 完整版 |
| 只有 `0000` 出 | 引擎区分「数字/码点串」与「字母串」 | 简拼改编码形态（体验打折） |
| `0000`/`zzzz` 出、`sljt` 不出 | 引擎限制**辅音簇长度**或做音节切分 | 仅 2–3 字母简拼可用 |
| 全不出 | 拼音词典读法有**强校验** | 简拼此路不通 |

**产物**（`dist/abbr/`）：

| 包 | 条目数 | 大小 | 简拼条数 |
| --- | --- | --- | --- |
| `njubase3-abbr-probe.a` | 150,300 | 4,030,790 B | +298 + 2 探针 |
| `njubase3-abbr-test.a` | 150,298 | 4,030,750 B | +298（仅 252 条游戏词） |
| `njubase3-abbr-full.a` | 210,000 | 4,865,640 B | +60,000（全量） |

两份包的**唯一表记数与完整版相同**（149,030）—— 简拼只增加「读法入口」，**不引入新词**，
这是设计使然，不是 bug。

**与「安卓电视搜索」的真实差距**（必须说清，否则是误导）：

| | 安卓电视搜索 | 本方案 |
| --- | --- | --- |
| 匹配方式 | 实时模糊匹配（子串 / 错拼 / 多语） | 词典**前缀**匹配 |
| 排序 | 按相关性动态算分 | 尾部表 6bit 优先级，**静态**且语义未完全确认 |
| 词库来源 | 在线可更新 | 本地文件；换库要重启（见 `.nro`） |
| 首字母联想 | 原生 | **待实机冒烟** |

结论：**「打首字母出候选」有望做到；「像电视搜索那样聪明」做不到** ——
匹配与排序发生在 iWnn 引擎内部（编译在 swkbd 的 `main` 段里），词典层只能提供数据。

#### 14.3 校验器统一：Python 版补齐两层判据，并把「本工程约定」降级

§13.3 只修了 `.nro` 用的 C++ 校验器（`nro/source/njdc_check.h`），
**`tools/verify_njdc.py`（用户按 README 直接跑的那个）仍留着两条假规范** ——
`0x20 == 1146`、`0x0c == 文件大小 − 112`。

后果很实际：README 建议「拿原版 `njubase3.a` 做对照」，而用户一跑就会看到
`[FAIL] 记录表偏移 = 1146  0x20=81726` —— **校验器把好文件判成坏文件**。

修复：

1. 同步为 **Tier 1 通用 + Tier 2 干净版式** 两层，与 C++ 版一致；
2. 新增 `N == 0` 分支：`njexyomi.a` 打印 `[ -- ] 非记录型文件`，不再误判；
3. 把另外两条也降级 —— **「尾部表高低字节成对相同」与「读法仅含 a-z」也不是规范**，
   而是**本工程产物**的写法约定。抓出它的样本是原版 `njcode.a`（记号/小键盘词典，
   285 条读法**全部**非字母、尾部表**全部**不是成对相同，却是个完全正常的文件）。
   现在这两项改为 `[info]` 只报告比例：
   本工程产物恒为 `150000/150000`，`njcode` 显示 `0/285`，一眼可辨、且不误杀。

**回归结果：10 个文件（4 份产物 ＋ 原版 6 本）/ 0 个 FAIL**（`dist/verify-report.txt`，523 行）。
`.nro` 侧回归见 `report/njdc_checker_regression.txt`。

> **教训升级**：假规范的杀伤面比想象中大 —— 它会**反向污染**：
> 一个写坏的校验器让好文件报错，用户第一反应是「文件坏了」而不是「校验器坏了」。
> 所以校验器的每一条判据都应能回答：**这条是从几个样本得出的？有没有反例样本？**

#### 14.4 暴露出来的既有问题：候选排序偏差（未解，如实标注）

抽查时发现（不属本轮 bug，是 §12.6 未解项的表现）：

```
youxi      → 首选是「有戏」而非「游戏」
jisuanji   → 首选是「计算技」（一个很生僻的词）
yuanzhoulv → 圆周率   未收录（权重 4880，落在 --limit 150000 截断线外）
```

前两条是**尾部表 6bit 优先级语义未完全解出**导致的静态排序偏差；
第三条是**上限截断**，提高 `--limit` 即可。三条都**不影响「能不能打出来」**，
只影响「首屏第一个候选是不是你想要的那个」。

#### 14.5 待验 / 待办（更新）

- ~~**简拼冒烟**（决定方案成立与否）~~ → **已完成，2026-09-27 实机全部通过**，见 §14.2。
- **★ 下一步：简拼全量包实机确认**：装 `dist/overlay-abbr-full/`（一键脚本选 `[5]`）。
  该包 210,000 条 / **4,865,870 B（4.64 MB）**，比已验证的 4.03 MB 大 0.84 MB ——
  **需确认引擎吃得下**（applet romfs 预算 32 MB，理论够，但未实测）。
  验证点：`sljt`、`aedfh`、以及同一词走两条路（`cundang` 与 `cd` 都该到「存档」）。
  若键盘起不来 → **文件大小是首要嫌疑**，回退 `[1] full` 并记录现象。
- **实机验证「不需重启」推论**：装完**先不重启**直接打 `shalujianta`（对应 §13.4-3）。
- **devkitPro 工具链**（本机未装）→ 装好后 `nro/build.bat` 出 `HexDict.nro`。
  当前 `.nro` 工程已把最新两版词典（4,025,516 B / 1,922,644 B）重新内嵌，PC 侧自检 `ALL PASSED`。
- **`njexyomi.a`（N=0、头长 60）仍未解** —— 痛点②「联想差」的直接落点，见 §13.5。
- 尾部表 6bit 语义（候选排序）、`.ad1`（NJAD）、`njtan` 自有索引区，同上。

---

### 15. 规模上限诊断：大词典「能弹键盘但不出词」（v7 追加，2026-09-27）

#### 15.1 现象（实机反馈，最高等级证据）

| 档位 | 记录数 | 文件 | 结果 |
|---|---|---|---|
| `[1] full` | 150,000 | 3.84 MB | ✅ 正常出词 |
| `[5] abbr-full` | 210,000 | 4.64 MB | ✅ 正常出词 |
| `[6] big250` | 250,000 | 6.73 MB | ⚠️ **键盘能弹出，候选列表为空** |
| `[7] big400` | 400,000 | 11.42 MB | ⚠️ 同上 |

**「键盘能弹出」本身是极有价值的信息**，它同时证明了两件事：

1. **Atmosphere LayeredFS 覆盖生效了** —— 否则 swkbd 会用回原版词典、正常出词；
2. **swkbd applet 正常启动** —— 失败发生在 **iWnn 引擎加载词典那一步**，
   加载失败后引擎退化为「无词典模式」：按键有反馈、界面正常，但永远没有候选。

因此 §12.6 / §13.5 里「上限 = applet romfs 预算 32 MB」的推断**被实测推翻**。
真正的天花板远低于 32 MB，且**与 romfs 构建预算无关**（该预算管的是「能不能把文件
挂进 romfs」，而这里文件明明挂上了）。

#### 15.2 静态检查：四条候选机制全部排除

`tools/check_scaling.py` 对四档产物做结构与内容体检，结论：

| 检查项 | 结果 |
|---|---|
| 头部字段隐藏差异 | **无** —— 除规模相关字段（0x0c/0x24/0x28/0x50）外，四档头部**逐字节相同** |
| 长度字段溢出 | **无** —— 读法最大 72 B、表记最大 22 B，全部 ≪ 255（记录表长度字段是 u8） |
| 偏移字段溢出 | **无** —— 记录表偏移是 u24（上限 16 MB），池最大 7.17 MB |
| 字符集异常 | **无** —— 读法 100% 纯 ASCII；非 BMP 字符只在表记且仅 200 余条，各档一致 |
| 空串 / 记录表对齐 | **无** |

**「产物本身是坏的」也被排除**：解析 250,000 条读法得到 `纯 ASCII 250000/250000`
—— 若偏移错位，读法不可能全部落在合法可解码区间。

#### 15.3 正交诊断设计（为什么要这么做）

四档里 **N（记录数）/ 池长（内容量）/ 文件大小 三个量同时在涨**，
所以无法判断是哪个触限。`tools/mk_scaling_probe.py` 的解法：
**把已验证可用的 `[1] full` 的记录再复制一遍，池字节原样复用** ——
于是「记录数」被单独放大，而**词条集合与池完全不变**。

**⚠️ 本轮踩到的坑（重要）：第一次实现用 `rec * k` 直接整段复制，是错的。**

原文件记录表按读法 UTF-16BE **升序**排列。整段复制后序列变成
「[升序 150k][升序 150k]」，**第 150,000 条切换回最小值 —— 整体降序跳变**。
引擎若用二分查找定位读法，就会直接查不到 —— 那会把「顺序错」**误判成「规模超限」**，
整个实验的结论就是假的。

正确做法：**每条记录重复 k 次后再按读法做稳定排序**，同读法的记录保持原有相对顺序。
脚本自检三项：①产物读法序列升序；②读回条目 == 预期序列；③原 150k 词条零丢失。

#### 15.4 数据点矩阵

**第一轮（已测）**：

| 包 | 记录数 N | 池长 | 文件 | 状态 |
|---|---|---|---|---|
| `[1] full` | 150,000 | 2.22 MB | 3.84 MB | ✅ 实测 |
| `[5] abbr-full` | 210,000 | 2.34 MB | 4.64 MB | ✅ 实测 |
| `[9] dup250` | **250,000** | **2.22 MB** | **4.98 MB** | ❌ 实测 |
| `[10] dup300` | 300,000 | 2.22 MB | 5.56 MB | ❌ 实测 |
| `[11] pure225` | 225,000 | 3.65 MB | 5.98 MB | ❌ 实测 |
| `[6] big250` | 250,000 | 4.06 MB | 6.73 MB | ❌ 实测 |
| `[7] big400` | 400,000 | 7.17 MB | 11.42 MB | ❌ 实测 |

第一轮把范围压得很窄，**但留下两个必须先排除的疑点**，否则结论会是错的：

1. `[9]`/`[10]` 都含**大量完全重复的条目**（同一 读法+表记 出现两次）——
   失败有可能是「重复条目」触发的，与记录数无关；
2. `[11]` 的 N=225,000 **小于** 250,000 却也失败。

**第一轮最关键的一条对照**：`[9] dup250` vs **可用**的 `[5] abbr-full` ——
前者池更小（2.22 vs 2.34 MB）、文件只大 0.11 MB，**唯一显著差别是 N（250,000 vs 210,000）**。
这条对照把矛头指向「记录数」，但因为疑点 1，还不能定论。

**第二轮（已测：三个全部失败，且结论是「方法作废」）**：

| 包 | 记录数 N | 池长 | 文件 | 结果 |
|---|---|---|---|---|
| `[12] dup210` | **210,000** | 2.22 MB | 4.53 MB | ❌ |
| `[13] dup230` | 230,000 | 2.22 MB | 4.75 MB | ❌ |
| `[14] trim200` | 200,000 | 4.06 MB | 6.16 MB | ❌ |

**★ 本轮真正的收获是一个确定结论：重复条目会让引擎拒绝加载整个词典。**

| | `[5] abbr-full` | `[12] dup210` |
|---|---|---|
| 记录数 N | 210,000 | **210,000（相同）** |
| 唯一表记 | 149,030 | **149,030（相同）** |
| 池长 | 2.34 MB | **2.22 MB（更小）** |
| 文件 | 4.87 MB | **4.53 MB（更小）** |
| 差异 | 60,000 条**别名读法** | 60,000 条**重复条目** |
| 结果 | ✅ | ❌ |

N 与唯一表记相同、`dup210` 的池和文件**还更小** → **唯一变量就是「重复条目」**。
⇒ 四个 dup 包的数据全部作废，不能用来推断记录数上限。

`[14] trim200` 也不干净：删记录后**池里留下不再被引用的孤儿串**，
失败原因可能是「池里有垃圾」而非「池大」，故同样**不能**证明「N 与上限无关」。

**第三轮（待测）—— pad 法，目前唯一「只动一个变量」的手段**：

`pad_pool` 只往 `[1]` 的**池末尾追加填充字节**，`N`／记录表／T 表／
唯一读法与唯一表记**全部保持原值**，只有池长与文件大小变大
（填充用私用区字符，不与拼音 / 汉字构成子串关系，且放在池最末尾）。

| 包 | 记录数 N | 池长 | 文件 | 设计意图 |
|---|---|---|---|---|
| `[15] pad150-lite` | 150,000 | 2.62 MB | **4.22 MB** | **控制组**：验证追加填充手法安全 |
| `[16] pad150-mid` | 150,000 | 3.42 MB | **4.98 MB** | 夹阈值 |
| `[17] pad150` | 150,000 | 4.22 MB | **5.75 MB** | **关键**：与可用档 `[1]` 的 N / 词表 / 记录表完全相同 |
| `[18] pure210` | **210,000** | 3.14 MB | **5.54 MB** | 真实词、无重复条目，**N 与可用的 `[5]` 相同** |

#### 15.5 判读矩阵（第三轮）

第二轮的真实产出是**一个确定结论**（见 15.4）：**重复条目会让引擎拒绝加载整个词典**。
这条结论本身很有价值，但它同时把第二轮其余数据全部作废了。

**先看 `[15] pad150-lite`**（控制组）：

| `[15]` | 含义 |
|---|---|
| ❌ | 「池末尾追加填充」手法本身有问题 → 第三轮作废，需另找分离手段 |
| ✅ | 手法安全，继续看 `[17]` |

`[15]` 通过后：

| `[17]` pad150 | 结论 |
|---|---|
| ❌ | **限制是「池长 / 文件大小」** —— `[17]` 的记录数、词表、记录表与**可用的 `[1]` 完全相同**，只有文件变大 → 上限由**字节量**决定 |
| ✅ | 限制不是字节量 → 转向**记录数 / 唯一表记数** |

**独立交叉验证**：`[18] pure210`（真实词、无重复条目、**N 与可用的 `[5]` 相同**）
若失败，同样只能归因于池 / 文件大小。

#### 15.6 本轮新增的通用经验

1. **「键盘能弹但无候选」是引擎层失败的指纹**，不是 romfs/安装失败 ——
   安装失败的现象是「完全没变化（仍是原版词典）」，两者要分清。
2. **改词典规模做实验前，必须先确认记录表仍按读法升序** ——
   整段复制会破坏有序性，制造出假阳性。
3. **静态排除要逐项写明**（头部差异 / 长度溢出 / 偏移溢出 / 字符集）——
   「查了没问题」和「没查」在结论里必须区分开。
4. 四档头部**逐字节相同**这件事本身就是强证据：说明问题不在「我们漏设了某字段」，
   而在规模本身。
5. **对照实验必须先放一个「控制组」来证明手法本身无害。** 第一轮三包全败，
   但其中两包用了「复制条目」的特殊手法 —— 若手法本身会让引擎拒绝，
   那这组数据就完全无效。所以第二轮把 `[12] dup210`（与**已验证可用**的档位同 N）
   放在最前面当控制组：**先证明手法无害，再拿它去推断规模上限。**
6. **一个变量要能「正交」地动，必须同时具备两个方向。** 只会「放大」不会「缩小」，
   就无法把「数量」与「体积」分开。本轮补的 `trim_from`（缩小记录数、体积不变）
   与 `dup_to`（放大记录数、体积不变）合起来才构成正交对。
7. **变换手法的「副作用」必须与「自变量」分开 —— 副作用本身可能就是失败原因。**
   三种变换各带一种副作用：`dup_to` 引入**重复条目**，`trim_from` 引入**孤儿串**，
   `pad_pool` 引入**未引用字节**。前两种各自都成了独立的失败原因，
   一度被误读为「规模超限」。
   → 每次变换后先问：**它除了动目标变量，还动了什么？**
8. **「控制组失败」也是一种收获。** 经验 6 要求先证明手法无害；
   本工程的控制组 `[12] dup210` 恰恰**失败**了 —— 但它与可用档的 N、唯一表记完全相同、
   池和文件**还更小**，于是「重复条目致命」这条独立结论被直接钉死。
   → 控制组不是走流程，它的成败都能产出结论。
9. **只有「池长 / 文件大小」类假设还在场上时，`pad_pool` 是最干净的刀** ——
   它只追加池尾填充，N、记录表、T 表、唯一读法与唯一表记全部原值。

#### 15.7 副产品：简体拼音有「两套并行词典」（GB18030 / GB2312）

查 `Iwnn/ZH/CN/pinyin/` 时发现**两个并列目录**，逐文件对比：

| 文件 | `GB18030/` | `GB2312/` | 关系 |
|---|---|---|---|
| `njtan.a` | **256,025** | **137,190** | **差 46%** |
| `njcode.a` | 8,204 | **不存在** | GB2312 侧没有 |
| `njubase3.a` | 1,606,890 | 1,606,358 | 差 532 字节 |
| `njubase1.a` / `njubase2.a` / `njexyomi.a` | 90,402 / 91,258 / 1,528 | 完全相同 | **SAME** |

**GB18030 / GB2312 不是「文件系统编码」，而是「候选字集范围」标识**：

- NJDC 词典内部**一律 UTF-16BE**，与 GB 编码无关；
- `njtan.a` 差 46%，**推测**对应「GB2312 只有 6,763 个基本汉字、GB18030 覆盖七万余字（含扩展区）」；
- `njcode.a`（Unicode 码点 → 汉字）只在 GB18030 侧存在。

**本工程只覆盖 `GB18030/` 的理由**：① 实测证明它生效（`[1]`/`[5]` 都只覆盖它且正常出词）；
② 本词表含 205 个 CJK 扩展区字符（非 BMP），**GB2312 装不下**；③ GB2312 是基本字集的降级版。

> **待验证的新假设**：两套并列 ⇒ 引擎**可能按模式选一套**，也**可能同时加载两套**。
> 若是后者，实际加载量 = 两套之和，「把 `GB2312/` 换小」或许能腾出空间给 `GB18030/`。
> 判定法：把 `GB2312/njubase3.a` 覆盖成带独有探针词的小词典，
> 若在 **GB18030 模式**下也能打出探针词 ⇒ 引擎同时加载两套。
> （LayeredFS 只能覆盖、不能删除。）

#### 15.8 待验（更新）

- **`[15]` → `[17]` 两档实机判读**（用户执行）。`[15]` 是控制组，**必须先看它**。
- `[15]` ❌ → pad 手法有毒，第三轮作废，需另找「只动一个变量」的手段。
- `[15]` ✅ 且 `[17]` ❌ → **限制是池长 / 文件大小**：在 4.87–5.75 MB 间造 3 个点二分找阈值；
  并优先验证 §15.7 的假设（两套词典是否被同时加载）——那可能是绕过上限的突破口。
- `[15]` ✅ 且 `[17]` ✅ → 限制不是字节量：用 `[16]` / `[18]` 转向**记录数 / 唯一表记数**。
- 未解项不变：`njexyomi.a`（联想）、尾部表 6bit（排序）、`.ad1`（NJAD）。

---

### 16. 清理失败产物 + 扩容路线转向（v8 追加，2026-09-27 晚）

#### 16.1 已清理的产物

以下产物经实机确认失败、或所用手法已被证明有毒，**已从工程中删除**（需要时可按 §9.6 命令重建）：

| 产物 | 结论 |
|---|---|
| `big/njubase3-250000.a`（6.73 MB）、`big/njubase3-400000.a`（11.42 MB） | 键盘能弹、无候选 |
| `probe/njubase3-225000.a`（5.98 MB） | 同上 |
| `probe/njubase3-dup{210000,230000,250000,300000}.a` | **手法作废**（含重复条目） |
| `probe/njubase3-trim200000.a`（6.16 MB） | **手法不干净**（池含孤儿串） |

**保留**：`probe/njubase3-pad150-lite.a` / `pad150-mid.a` / `pad150.a` / `pure210000.a`
—— 这四个**尚未实测**，仍是干净的对照点。

> ⚠️ 一键脚本的选项号随之重排：pad / pure 由 `[15]`–`[18]` 变为 **`[10]`–`[13]`**。
> §15 正文中的旧编号请以此为准。

#### 16.2 路线转向：在已验证可用的基础上「逐档加词」

放弃「一次性冲大、再回头找边界」，改为**在 `[5] abbr-full`（4.64 MB，已实测可用）上逐档加词**：

| 档 | 词数 | 记录数 | 简拼条数 | 池 | 文件 |
|---|---|---|---|---|---|
| `abbr-full` | 150,000 | 210,000 | 57,811 | 2.24 MB | 4.64 MB ✅ 已验证 |
| `abbr-160000` | 160,000 | 220,000 | 57,811 | 2.41 MB | 4.92 MB 待测 |
| `abbr-175000` | 175,000 | 235,000 | 57,811 | 2.67 MB | 5.36 MB 待测 |
| `abbr-190000` | 190,000 | 250,000 | 57,811 | 2.92 MB | 5.78 MB 待测 |

**四档的简拼条数完全相同（57,811）**，唯一变化的变量是「真实词数」——
所以**哪一档开始失败，就直接给出词数上限**。

**优点**：每一档都保留简拼功能、都像成品；不必先搞清限制究竟是字节量还是条数，
逐档试就能找到最大可用档。四档均已通过结构校验，`sljt` / `cundang` / `shalujianta` 全部命中。

**测试判据**：打 `shalujianta`（杀戮尖塔），**出现候选即加载成功**。
（曾误用 `cundang` —— 它其实在 `njubase2.a` 里，见 §17.2。）

---

### 17. 规模上限定论 + 判据纠错（v9 追加，2026-09-27 晚）

#### 17.1 ★ 结论：上限由「文件字节大小」决定

实机结果：

| 包 | 记录数 | 词数 | 池 | 文件 | 结果 |
|---|---|---|---|---|---|
| `pad150-lite` | 150,000 | 149,030 | **2.62 MB** | **4.22 MB** | ✅ |
| `abbr-full` | 210,000 | 149,030 | 2.24 MB | **4.64 MB** | ✅ |
| `abbr160` | 220,000 | 159,003 | 2.41 MB | **4.92 MB** | ❌ |
| `abbr175` | 235,000 | 174,000 | 2.67 MB | 5.36 MB | ❌ |
| `abbr190` | 250,000 | 249,000 | 2.92 MB | 5.78 MB | ❌ |
| `pad150-mid` | 150,000 | 149,030 | **3.42 MB** | **4.98 MB** | ❌ |
| `pad150` | 150,000 | 149,030 | 4.22 MB | 5.75 MB | ❌（推定） |

**推理链**：

1. `pad150-lite` 与 `pad150-mid` 的**记录数、词数完全相同**（都与 `[1] full` 一致），
   只有池长与文件大小不同 → **记录数与词数被排除**；
2. `pad150-lite` 的池（2.62 MB）**大于** `abbr160` 的池（2.41 MB）却成功
   → 池长不单调 → **池长被排除**；
3. 剩下的唯一单调变量是**文件总字节数** → **上限 = 文件大小，约 4.64 ~ 4.92 MB**。

**含义**：`abbr-full`（4.64 MB）已用掉约 94–95% 的空间。
每条真实词约 **36 字节**（记录表 10 + 尾表 2 + 读法 ≈17 + 表记 ≈5.5），
每条简拼约 **20 字节** → 剩余空间只够加 **约 900 ~ 3,000 个词（+0.6% ~ 2%）**。
**「继续堆词」的收益已可忽略。**

> 顺带算清了文件构成（abbr-full / 4,865,870 B）：
> 记录表+尾表 **2,520,000 B（51.8%）**、池 2,344,720 B（48.2%）。
> **条数本身（12 B/条）就是最大单项开销** —— 这也是「词越多越贵」的根本原因。

#### 17.2 判据纠错：必须查遍原版 **6 本**词典

**用户当场发现我的错误**：我推荐用 `cundang`（存档）当「新词判据」，
但**原版 `njubase2.a` 里就有** —— 不装插件也打得出来，判据完全无效。

**根因**：判断「是不是新词」时**只查了 `njubase3.a` 一本**。

| 原版词典 | N |
|---|---|
| `njubase1.a` | 3,351 |
| `njubase2.a` | 3,235 ← 「存档」在这里 |
| `njubase3.a` | 57,954 |
| `njtan.a` | 14,184 |
| `njcode.a` | 285 |
| `njexyomi.a` | 0（中文版） |

六本表记合计 **71,344** 个。可靠判据（六本全都没有）：`shalujianta` ★、`baokemeng`、
`aierdengfahuan`、`sipuladun`、`heishenhuawukong`。

> **这是本工程同类错误的第二次**（第一次见 §13.3：校验器只按「干净版式」判，
> 把原版 `njubase3` / `njexyomi` 误判为坏文件）。
> **教训：判定「新增」必须遍历全部数据源，不能只查一份。** 已写入 skill。

#### 17.3 新增方向：多本分担

`njubase1/2` 与 `njubase3` **同为干净版式**（`0x20=1146`），可以直接替换；
`njtan.a` 是另一套版式（重建后差 56,749 字节），暂不考虑。

`[17] njb1probe` 探针：**只替换 `njubase1.a`**（不动 njubase3），
塞入两个独创词 `nbprobe` / `nbprobe2`。

- 打出这两个词 ⇒ 引擎查 `njubase1`，且每本可能有**独立大小预算** ⇒ **总容量可翻几倍**；
- 打不出 ⇒ 该方向关闭。

#### 17.4 待验

- `[14]`/`[15]`/`[16]`（4.70 / 4.80 / 4.90 MB）精确标定阈值。
- `[17] njb1probe` 验证多本分担是否可行 —— **当前最有价值的下一步**。
- 未解项不变：`njexyomi.a`（联想，痛点②）、尾部表 6bit（排序）。

---

### 18. ★ 多本分担扩容打通（v10 追加，2026-09-27 晚）

#### 18.1 探针结果：引擎确实会读 njubase1

`[17] njb1probe`（只替换 `njubase1.a`、不动 njubase3，内塞独创词 `nbprobe`/`nbprobe2`）
**实测成功** —— 独创词能被打出来。

> **⇒ ① 引擎会读取 `njubase1`；② 每本词典有各自独立的大小预算。**
>
> 这**推翻了 §17.1 的悲观结论**：单本上限约 4.6 MB，但**总容量是各本之和**。

> ### ⚠️ 2026-09-30 复审：② 这一步缺证据（详见 §21 与 `reports/证据链审查-词典大小上限.md`）
>
> 探针只证明了 ①。**② 是未经实验的推断** ——
> 探针放进 `njubase1` 的是「原版 + 2 个词」的**小词典**（≈90 KB），从未触及
> 「某本单独接近上限」的场景；那时引擎可见总量约 2.0~5.1 MB，**在任何假设下都能出词**。
>
> 更关键：§15 的全部阈值实验**只动过 `njubase3` 一本**（其余本是原版小文件，恒 447,417 B），
> 因此观测到的「失败点」既可解读为 **base3 文件大小**（4.87 MB ✅ / 5.16 MB ❌），
> 也可解读为 **总量**（5.31 MB ✅ / 5.61 MB ❌）——
> **两个假设数学等价，现有数据无法区分。**
>
> 且 §18.5 自己写着 MULTI 包「**待验**」—— 三本都是 4.x MB 的配置**从未上机**。
> **结论：「每本独立预算」目前是假说，不是结论。**

#### 18.2 六本词典的角色（实测）

| 词典 | 原条目 | 唯一表记 | 唯一读法 | 内容特征 | 能否扩容 |
|---|---|---|---|---|---|
| `njubase1.a` | 3,351 | 3,351 | 3,183 | 2 字专名（阿坝、阿富汗…） | ✅ |
| `njubase2.a` | 3,235 | 3,235 | 3,103 | 2 字专名（阿布扎比、阿斗…） | ✅ |
| `njubase3.a` | 57,954 | 57,807 | 43,913 | 主词库 | ✅ 已扩 |
| `njtan.a` | 14,184 | 12,874 | **415** | **读法极少 → 单字表** | ⚠️ 版式不同 |
| `njcode.a` | 285 | 285 | 285 | 码点 → 汉字 | ❌ |
| `njexyomi.a` | 0 | 0 | 0 | 联想（中文版空） | ❌ |

六本合并去重后仅 **71,344** 个表记。
重叠关系：`njubase1 ∩ njubase2 = 0`（**天然互补**）；
`njubase1 ∩ njubase3 = 1,248`、`njubase2 ∩ njubase3 = 603`。

> **`njtan.a` 的判读**：12,874 个表记却只有 415 个读法 ——
> 确认它是「一个拼音 → 一批同音字」的单字表，与 base1/2/3 完全不同类。

#### 18.3 分片实现（`tools/mk_multi.py`）

流程：建词表（**按表记去重**，同词只留最高权重读法）→ 读 `--exclude` 词典剔除已有表记
→ 按片切分 → **并入该本原版条目** → `build_njdc` 写出。

| 词典 | 新增词 | 本有 | 合计 | 文件 |
|---|---|---|---|---|
| `njubase1.a` | 137,379 | 3,351 | 140,730 | **4.28 MB** |
| `njubase2.a` | 124,218 | 3,235 | 127,453 | **4.42 MB** |
| `njubase3.a` | —（abbr-full 不变） | — | 210,000 | **4.64 MB** |

**总不同词数 ≈ 411,000**（此前 150,000 → **2.7 倍**）。词源剩余 485,008 条未用。

三条硬约束（脚本保证）：

1. **分片之间、分片与 `abbr-full` 之间不得有重复表记**；
2. **每片并入该本原版全部条目**（否则丢覆盖）；
3. **按目标字节数切，不按条数切** —— 实测同样 150,000 条，base1 = 4.80 MB
   而 base2 = 5.69 MB（**后一批词更长**），按条数切会直接撞单本上限。

#### 18.4 字节预算的实现细节

`take_by_budget()` 用保守成本模型逐条累加：

```
每条 = 12（记录表 10 + 尾表 2）
     + 2×len(读法)   若该读法首次出现
     + 2×len(表记)   若该表记首次出现
```

**忽略「极大串共享」**（子串不重复存），因此估算 ≥ 实际，切出来偏安全。
实测校准：目标 5.6 MB → 实际 5.09 / 5.24 MB；目标 4.7 MB → 实际 4.28 / 4.42 MB。

#### 18.5 交付与待验

- `overlay-multi`（`[18]`，推荐）：base1 4.28 MB + base2 4.42 MB + base3 4.64 MB
- `overlay-multi-big`（`[19]`，探针）：5.09 / 5.24 MB（超过单本已知上限，仅作对照）
- `overlay-njb1probe`（`[17]`）：探针本身，保留备查

**待验**：`[18]` 实机（能否正常出词 + 新本是否被读取）。
**若失败** → ⚠️ 优先怀疑「**总量上限**」而不是「单本上限」（见 §21）。
**若成功** → 总容量 41 万词，且理论上还能再开 `njtan`（另一套版式，需先解出）。

> ⚠️ **§21（2026-09-30）指出：在 `[18]` 实测之前，上面两条都还是假设。**
> 当前 `04_Outputs/` 三本引擎可见总量 ≈ 13.46 MB，是已知可用最大值（5.31 MB）的 **2.5 倍**。
> **上机前请先读 §21。**

---

### 19. 2026-09-30 整理：简拼重复条目 bug 回归修复 + 部署包脚本化（v11 追加）

系统重装后第一次完整重跑全流程时发现并修掉的问题。**结论先行：
`tools/build_from_lexicon.py` 产出的 base3 含 98 条重复条目，按 §15.4 的铁律应当会让
引擎拒绝加载整个词典 —— 这是从 `mkdict.py` 迁移到 ALL.tsv 闭环时丢掉的去重逻辑。**

#### 19.1 复现（全流程端到端）

```bat
python tools\mk_lexicon.py            :: lex/*.yaml + game.txt -> lex\ALL.tsv
python tools\build_from_lexicon.py    :: ALL.tsv -> njubase3 / njubase1 / njubase2
python tools\pack_dist.py             :: 三本 -> overlay-* / manual-*.zip + nro\assets
python dist\verify\verify_njdc.py <产物> <原版>
```

可复现性实测（**这是本次最有价值的验证**）：

| 阶段 | 结果 |
|---|---|
| `mk_lexicon.py` | 883,019 条，输出与整理前的 `lex/ALL.tsv` **逐字节一致**（sha256 `0aa3a09e…`） |
| `build_from_lexicon.py --base3-words 130000` | 三本条目数/字节数与 §11.3 记录**逐一吻合**，且与整理前产物**逐字节一致** |
| 结论 | **主链完全可复现** —— 给定同样的 `lex/`，产物确定 |

#### 19.2 发现的 bug：简拼条目重复

`verify_njdc.py` 对 base3 报 `重复条目（同一 读法+表记 出现多次）: 98`。

成因（98 条**全部**符合这一模式）：

> 同一个词的**不同读法**会算出**同一个简拼**。
> 例：「不了」有 `buliao` / `bule` 两读，两者简拼都是 `bl` → `(bl, 不了)` 被写入两次。

`verify_njdc.py` 把这一项做成**报告而非判 FAIL**，所以此前一直没被注意。

**为什么必须修**：§15.4 的对照实验（`[5] abbr-full` 210,000 条 vs `[12] dup210` 210,000 条）
已经钉死 —— 两者记录数、唯一表记、池长、文件大小几乎相同，**唯一差别是后者含 60,000 条
重复条目，结果被引擎拒绝加载**。98 条是否同样致命**未单独实测**，但既已确知重复条目有害，
且过滤是零功能损失（那些入口本就重复），就没有保留理由。

#### 19.3 修复

`build_from_lexicon.py` 补齐 `mkdict.py` 原有的两道去重（迁移时丢失）：

```python
have = set(b3_full)                    # 全拼条目先占位
byword = {}                            # word -> [各读法]
def collides(ab, word):                # 简拼串是同一词其它读法的前缀
    return any(r.startswith(ab) for r in byword.get(word, []) if r != ab)
```

* `k in have` → 跳过（**消灭「多读法同简拼」这一类**，即那 98 条）
* `collides(abbr, word)` → 跳过（消灭「简拼与同词全拼前缀撞车」，§5.2 记录过的那类）
* 新增 `--abbrev-allow-dup` 开关，默认开启过滤

修复后：**重复条目 = 0**，丢弃同词撞车 294 条（与 §5.2 的 295 条同量级）。
base3 从 203,093 → 202,702 条，4,756,404 → 4,751,712 B。

#### 19.4 顺带修正：`--base3-words` 的默认值是失效的旧值

脚本默认写的是 `150000`，但 §11.3 已实测「150,000 → 5.06 MB（会挂）、
130,000 → 4.54 MB（安全）」，而仓库产物一直是 130,000 版。
默认值已改为 **130000** 并注明原因 —— 否则任何人直接跑不加参数，都会产出一个超限的坏包。

#### 19.5 部署包脚本化：`tools/pack_dist.py`（新增）

整理前 `dist/` 里积了**四代产物**，同一份 `njubase3.a` 有四个 sha256：

| 代 | sha256 | 大小 | 来源 | 实机 |
|---|---|---|---|---|
| 1 | `414f4d8c` | 4,025,516 | mkdict 150k 词 | ✅ |
| 2 | `f82208c8` | 4,865,870 | mkdict abbr-full | ✅ |
| 3 | `f7a84460` | 4,756,404 | build_from_lexicon（**含上述 98 重复**） | ❌ 未验 |
| 4 | `d9b9c226` | 4,751,712 | 本次修复后 | 待验 |

更糟的是 `overlay-multi` 与 `manual-multi` 里的 base1/base2 **彼此不一致**
（4.49/4.63 vs 4.08/4.36 MB）—— 全是手工 `cp` 造成的漂移。

`pack_dist.py` 把这一步变成一条命令：读 `dist/build_stats.json`（生成器写出的结构化统计，
README 里的数字不再手抄），产出 `overlay{,-lite,-multi}/` 与 `manual-{multi,abbr}.{dir,zip}`，
并同步 `nro/assets/`。同时重写了 `install-to-sd.bat`（原为 19 选项诊断菜单，
其中 15 个指向已删除的目录）。

#### 19.6 目录整理

清理约 194 MB（`678 MB → 484 MB`）：诊断探针包、已实测失败的档位包、重复目录、
可重解的 `out/` 中间件。逐条清单见 `.backup-before-clean/DELETED-2026-09-30.txt`。

**保留**：`lex/`（词源 + 主词库）、`out/dat0805`（生成器依赖的原版词典）、
`out/dat0808`（日文/欧美原版，当前无脚本引用）、`.cache/dkp`（devkitPro 离线安装素材）、
`prod.keys`、`.backup-before-clean/`。

#### 19.7 遗留：nro 构建链不可用

系统重装清空了 `C:\devkitPro`、Qt（`mingw32-make`）、CMake。
`nro/HexDict.nro` 是 09-27 编译的旧产物，而 `nro/assets/` 已在本次更新为 `d9b9c226`
→ **两者不匹配，`.nro` 必须重编译**。重建需：devkitPro（`.cache/dkp` 可离线装）
+ `devkitA64/base_rules`（codeload 可下）+ **一个 make**（需另装 MinGW-w64 / MSYS2）。

不需要工具链的那一步已验证：`python nro/tools/gen_embed.py` 通过（内嵌 18.96 MB）。

#### 19.8 待办

1. **实机验证产物**（`d9b9c226`）：测 `shalujianta` / `sljt`。
2. 重建 nro 工具链并重编译 `HexDict.nro`。

---

### 20. 2026-09-30 目录重组（第二次整理）

工程根目录原先所有文件平铺，现按编号目录分类：

| 目录 | 内容 |
|---|---|
| `01_Inputs/` | `lex/`（词源 + ALL.tsv）、`firmware/`（dat0805 / dat0808）、`prod.keys` |
| `02_References/` | `hactool/`（原 `ref/`）、`atmosphere/`（原 `refs/ams/`） |
| `03_Documents/` | 早期 HTML 报告（`report.html`、`reports/`）；**说明文档已全部并入本文件** |
| `04_Outputs/` | **最终产物**：`<v版本>/atmosphere/…`（已铺成 SD 卡结构，整目录拷过去即可 —— 见 §22） |
| `05_Code/` | `tools/`、`nro/` |
| `10_Other/` | `cache/`、`dkp-cache/`（原 `.cache/`）、`backup/`（原 `.backup-before-clean/`） |

#### 20.1 移除了什么

- **全部部署相关**：`dist/overlay*/`、`dist/manual*/`、`manual-*.zip`、`install-to-sd.bat`、
  `tools/pack_dist.py`（§19.5 刚引入的打包脚本，因不再需要自动部署而废弃）
- **校验交付物**：`dist/verify/`、`verify.bat`、`verify-report.txt`、`tools/make_verify_report.py`
- **诊断脚本**：`check_scaling.py`、`mk_scaling_probe.py`、`mk_probe.py`、`mk_multi.py`
  （均依赖已删除的 `dist/` 产物）
- **多余产物**：`njubase3-lite.a`、150,000 词版 `njubase3.a` —— 现在**只交付三本**

#### 20.2 生成链的路径改动

移动后脚本的根目录从「上一级」变成「上两级」，输入输出全部改为编号目录：

```python
ROOT    = os.path.normpath(os.path.join(HERE, "..", ".."))   # ns-ime/
LEX     = os.path.join(ROOT, "01_Inputs", "lex")
OUTPUTS = os.path.join(ROOT, "04_Outputs")
ORIG    = os.path.join(ROOT, "01_Inputs", "firmware", "dat0805", ...)
```

涉及 `mk_lexicon.py`、`build_from_lexicon.py`、`mkdict.py`、`abbrev.py`、`njdc_lib.py`、
`nro/check-pc.bat`。另有 30 余个侦察脚本的路径用 sed 批量修正
（其中 `nso_kw.py` / `nso_scan.py` 指向的 `out/c65a99…` 已在 §19.6 删除，无法修正）。

#### 20.3 重组后的回归验证（**重点**）

跑完整生成链，产物 sha256 与重组前**完全一致**：

| 产物 | sha256(前16) | 大小 | 条目 |
|---|---|---|---|
| `04_Outputs/njubase1.a` | `47e800fab10d5d8c` | 4,077,346 B | 127,210 |
| `04_Outputs/njubase2.a` | `64b722eadb5bb610` | 4,363,516 B | 121,564 |
| `04_Outputs/njubase3.a` | `d9b9c226ec3ca1b4` | 4,751,712 B | 202,702 |

三本 `verify_njdc.py` 结构校验全通过、**重复条目 = 0**。
⇒ **目录重组未改变任何生成结果**（等价于一次纯搬运）。
74 个 Python 脚本全部通过 `py_compile` 语法检查。

#### 20.4 文中的旧路径

本报告 §1–§19 保留 09-27 时的原始路径（`dist/`、`lex/`、`out/`、`../tools/`），
以存史；实际路径以本节为准。

---

### 21. ⚠️ 证据链复审：大小上限是「单本」还是「总量」？（v13 追加，2026-09-30）

**触发**：我质疑「感觉是按三本总大小来的」。

**结论：质疑成立。「每本有独立预算」目前是假说、不是结论 ——
现有全部数据在「单本上限」与「总量上限」两种假设下都能自洽解释。**

完整审查见 `reports/证据链审查-词典大小上限.md`。要点如下。

#### 21.1 三个断点

**① 探针（`[17] njb1probe`）的设计不支撑推论。**

它往 `njubase1` 里放的是「原版 3,351 条 + 2 个独创词」的**小词典**（≈90 KB），
只能回答「引擎读不读 base1」。而「每本独立预算」需要验证的是
「**某本单独接近上限时仍能工作**」—— 探针**根本没触及这个场景**：
当时引擎可见总量约 2.0~5.1 MB，**在任何假设下都能出词**。

> 措辞演变也印证这一点：§17.3 写的是「每本**可能有**独立大小预算」，
> 到 §18.1 变成「每本词典**有**各自独立的大小预算」——
> **中间没有新增任何实验。**

**② §15 的全部阈值实验只动过 `njubase3` 一本。**

其余本恒为原版小文件（`njubase1` 90,402 + `njubase2` 91,258 + `njtan` 256,025
+ `njcode` 8,204 + `njexyomi` 1,528 = **447,417 B**，恒定）。因此：

```
观测到的「失败点」 = base3 文件大小 = 总量 − 447,417 B
```

两个假设**数学等价**，这组数据永远无法区分：

| 解读 | ✅ 最高（`[5] abbr-full`） | ❌ 最低（`abbr160`） |
|---|---|---|
| 单本（base3 文件大小） | 4,865,870 | 5,163,826 |
| 总量（+ 447,417） | 5,313,287 | 5,611,243 |

**③ MULTI 包从未实机验证。** §18.5 自己写着「**待验**」，
而 §12.2 / §13 已把它列为「★ 主推」「411,000 词」—— 属于**未验证先推荐**。

#### 21.2 风险量化

当前 `04_Outputs/` 三本 + 未动的其余本，引擎可见总量：

```
njubase3 4,751,712 + njubase1 4,077,346 + njubase2 4,363,516 + 265,757
= 13,458,331 B ≈ 13.46 MB
```

| 若假设成立 | 结果 |
|---|---|
| 单本上限 | 每本 4.0~4.75 MB 均在阈值内 → **可用** |
| 总量上限 | 13.46 MB ≈ 已知可用最大值（5.31 MB）的 **2.5 倍** → **必然失败** |

附加风险：部署说明要求 `GB18030/` 与 `GB2312/` 两套都放。若引擎**同时加载两套**
（§9.5 把这条列为待验证假设），总量还要再翻一倍。

#### 21.3 判别实验

**实验 A（先做，成本最低）** —— 在**已验证可用**的配置上只加一点：

1. 取 `[5] abbr-full`（base3 = 4,865,870，总 5.31 MB，**已实测可用**）；
2. 把 `njubase1` 换成一个**约 0.5 MB** 的包（**远低于**单本上限 4.6 MB）；
3. 新总量 ≈ 5.81 MB（base3 **一个字节都没动**）。

| 结果 | 推论 |
|---|---|
| ❌ 候选为空 | **总量是限制** → 单本假设破产，MULTI 方案作废 |
| ✅ 正常出词 | 总量不是限制 → 支撑单本假设（仍需实验 B 确认） |

**实验 B（终局判据）** —— 直接实机跑当前三本（总 13.46 MB）：

- ✅ → 总量上限 > 13.46 MB，**证伪总量假设**
- ❌ → MULTI 方案作废，**退回单本交付**（只给 `njubase3.a`，4.53 MB）

**配套**：只放 `GB18030/` 装一次、两套都放再装一次，对比 —— 顺带判定引擎
是「按模式选一套」还是「同时加载两套」。

#### 21.4 行动项

- [ ] 文档里「约 39 万词」「三本分担」的表述补齐「**未实机验证**」标注
- [ ] 做实验 A（低成本，先定方向）
- [ ] 做实验 B（上机跑三本）
- [ ] 视结果改写 §18.1 的措辞

---

### 22. 产物改为「版本化 + SD 卡结构」布局（v14 追加，2026-09-30）

**要求**：`04_Outputs` 先加一层版本目录，然后从 `atmosphere` 文件夹开始 ——
方便直接替换主机上的文件。

#### 22.1 新布局

```
04_Outputs/
└─ v0.1/                                ← 版本号取自根目录 VERSION（`0.1` → `v0.1`）
   └─ atmosphere/                       ← ★ 整个文件夹拷到 <SD>:\ 即可
      └─ contents/0100000000000805/romfs/Iwnn/ZH/CN/pinyin/
         ├─ GB18030/njubase{1,2,3}.a
         └─ GB2312/njubase{1,2,3}.a     （与 GB18030 内容完全相同）
```

- 生成器**直接产出**这个结构，不再输出扁平的三本 `.a`；
- 双编码目录各写一份 —— 对应 §9.5 观察到的「两套并列编码目录」，
  设备走哪套都能命中；
- 版本目录名由 `VERSION` 决定，**旧版本目录不会被覆盖**，可并存。

#### 22.2 生成器改动（`build_from_lexicon.py`）

```python
ATMO_BASE = ("atmosphere", "contents", "0100000000000805", "romfs",
             "Iwnn", "ZH", "CN", "pinyin")
ENCODINGS = ("GB18030", "GB2312")

def version_tag(): ...   # 读 VERSION -> "v0.1"
def out_dirs(): ...      # 返回两个编码目录的绝对路径

write_dict(entries, merge_path, out_paths, tail_v)   # out_paths 由「单路径」改为「路径列表」
```

`write_dict` 的第三参数由「单个路径」变成「路径列表」，同一份内容写到每个路径。

#### 22.3 产物哈希未变

| 产物（`v0.1/.../pinyin/<编码>/`） | sha256(前16) | 大小 |
|---|---|---|
| `njubase1.a` | `47e800fab10d5d8c` | 4,077,346 B |
| `njubase2.a` | `64b722eadb5bb610` | 4,363,516 B |
| `njubase3.a` | `d9b9c226ec3ca1b4` | 4,751,712 B |

与布局变更前**逐一相同** —— 只改了摆放方式，**没动内容**。

#### 22.4 配套改动

- `.gitignore`：`04_Outputs/*.a` → **`04_Outputs/**/*.a`**。
  原规则**只匹配一层**，产物下沉到 `v0.1/.../` 后会**漏网**；
  已用 `git check-ignore` 验证 6 个产物文件全部命中。
- 本文档的「04_Outputs」节 重写（新布局 + 部署/回滚步骤 + 待验证警示）。
- 根 `README.md`、`大词库说明.md` 的目录树与命令同步更新。

> ⚠️ §21 的未决问题**不受本次改动影响**：三本方案仍需实机验证，
> **验证前实机可用交付视为单本 `njubase3.a`（4.53 MB）**。

---

### 23. 判别测试包：探针 +「总量 vs 单本」（v15 追加，2026-09-30）

为回答 §21 的未决问题（大小上限是「单本」还是「三本总量」），
新增 `05_Code/tools/mk_probe_tests.py`，生成一组**可直接上机**的测试包。

#### 23.1 设计要点

**① 每本都塞独有探针** —— 不只回答「装成功没有」，还能回答「**哪一本被读取了**」：

| 文件 | 打 | 出 |
|---|---|---|
| `njubase1.a` | `nbp1` | 探针一 |
| `njubase2.a` | `nbp2` | 探针二 |
| `njubase3.a` | `nbp3` | 探针三 |

（引擎对读法形态零校验，`0000`/`zzzz` 都能命中 —— §5.2。）

**② 用例刻意做成「每本都远小于单本上限，但总量超过总量阈值」**：

| 用例 | base3 | base1 | base2 | 引擎可见总量 | 用途 |
|---|---|---|---|---|---|
| `t0-baseline` | 4.53 | 0.09 | 0.09 | **4.96 MB** | 基线（≈§15 已知可用配置） |
| `t1-b1-2m` | 4.53 | **1.79** | 0.09 | **6.66 MB** | ★关键：base3 字节未动，只加大 base1 |
| `t2-three-3m` | 2.06 | 2.65 | 2.69 | **7.65 MB** | 三本都小，总量超 |
| `t3-full` | 4.53 | 3.81 | 4.09 | **12.68 MB** | 当前交付配置 |

（单位 MB。引擎可见总量 = 三本 + 未动的 `njtan` / `njcode` / `njexyomi`。）

**③ 判读逻辑**：

- `t0` 是控制组，**必须 ✅**（连它都不出 → 是装法/路径问题，先解决那个）；
- **`t1` 是关键**：它与 `t0` 的**唯一差别**是 base1 从 0.09 → 1.79 MB，
  而 1.79 MB **远低于**单本上限 4.6 MB：
  - `t1` ❌ → **总量是限制**，「每本独立预算」被否证 → 三本方案作废
  - `t1` ✅ → 总量不是限制，单本假设成立

#### 23.2 实测数据（生成时校验）

| 用例 | 三本实际大小 | 引擎可见总量 | 校验 |
|---|---|---|---|
| `t0-baseline` | 4.53 / 0.09 / 0.09 | 4.96 MB | 探针 3/3 就位，重复条目 0 |
| `t1-b1-2m` | 4.53 / 1.79 / 0.09 | 6.66 MB | 探针 3/3 就位，重复条目 0 |
| `t2-three-3m` | 2.06 / 2.65 / 2.69 | 7.65 MB | 探针 3/3 就位，重复条目 0 |
| `t3-full` | 4.53 / 3.81 / 4.09 | 12.68 MB | 探针 3/3 就位，重复条目 0 |

#### 23.3 顺带修的两个问题

1. **`build_from_lexicon.py` 重构**：把 base3 的构造（含简拼去重）抽成
   `build_base3_entries()` 供测试脚本复用 —— 否则测试包会引入重复条目而**自毁**
   （触发 §15.4 的整本拒载）。
2. **`njubase3` 的「基础体积」实测**：原版 `njubase3.a` 是 1,606,890 B，
   但换成干净版式后 57,954 条约 **1.30 MB** —— 差额来自原版的 662 KB 附加区。
   这会影响任何「按字节切片」的预算估算。

#### 23.4 用法

```bat
python 05_Code/tools/mk_probe_tests.py               :: 生成全部用例
python 05_Code/tools/mk_probe_tests.py --only t1     :: 只生成某一个
python 05_Code/tools/mk_probe_tests.py --readme-only :: 只重写判读表
```

产物：`04_Outputs/tests/<用例>/atmosphere/…`；判读表：本文档的「判别测试包」节。
**换用例前务必先清空卡上的 `contents/0100000000000805/`**，否则会残留上一次的文件。


---

## Switch 中文输入法大词库（替换 njubase3.a）

给 **Nintendo Switch 系统输入法（swkbd / OMRON iWnn）** 换一本大词库，
对应三个真实痛点里的 **②联想差** 和 **③没有游戏词库**。
（痛点 ①按键位置属于界面/键盘布局，词库层面解决不了，见文末「不解决什么」。）

- 目标文件：`0100000000000805`（词典数据 title）里的
  `Iwnn/ZH/CN/pinyin/{GB18030,GB2312}/njubase3.a`
- 覆盖方式：**Atmosphere LayeredFS**（只覆盖这一个文件，不动固件）
- 状态：**已实机验证生效**（2026-09-27，覆盖 `njubase3.a` 后可打出原版没有的词）
- 简拼（首字母联想）：**已实机验证可用**（打 `sljt` 出「杀戮尖塔」，详见 §5.2）

---

> ## ⚠️ 2026-09-30 整理与修复（最新状态，先读这一节）
>
> 本目录经过一次系统性整理。**§2 的目录树已过时，以本节为准。**
>
> ### 1) 修掉一个产物级 bug：简拼条目重复
>
> `tools/build_from_lexicon.py` 生成 njubase3 时**没有对简拼条目去重**，产物里含
> **98 条重复条目**（同一条 `读法+表记` 出现两次）。成因：同一个词的多个读法会算出
> 同一个简拼 —— 例「不了」有 `buliao` / `bule` 两读，两者简拼都是 `bl`，于是
> `(bl, 不了)` 被写入两次。
>
> 按 §9.3 的实测铁律 ——「**重复条目本身就会让引擎拒绝加载整个词典**」——
> 该产物在实机上应当是坏的（表现为「键盘能弹出但候选为空」）。
> `mkdict.py`（旧路径）本来有 `have` / `collides` 两道去重，迁移到 ALL.tsv 闭环时丢了，
> 现已在 `build_from_lexicon.py` 中补齐，并新增 `--abbrev-allow-dup` 开关。
>
> 重新生成后：**重复条目 = 0**，生成时丢弃「与同词其它读法撞车」的简拼 294 条
> （量级与 §5.2 记录的 295 条一致）。
>
> ### 2) 部署包曾脚本化，随后按需求移除
>
> 此前 `dist/` 里积了**四代产物**：同一份 `njubase3.a` 有四个不同 sha256，
> 且 `overlay-multi` 与 `manual-multi` 里的 base1/base2 竟不一致 —— 全是手工 cp 造成的漂移。
> 曾用 `tools/pack_dist.py` 统一生成部署包；**该脚本与全部部署包已在 09-30 第二次整理中移除**
> （见下面第 5 条）。本项目现只交付 `04_Outputs/` 下的三本 `.a`，部署改为手动拷贝。
>
> ### 3) 目录清理（释放约 194 MB）
>
> 已删除：`probe/`、`multi-big/`、`overlay-{pad150*,pure210000,njb1probe,probe,abbr,abbr-full - 复制,multi-big,abbr-160000/175000/190000}/`、
> `abbr/njubase3-abbr-{test,probe,160000,175000,190000}.a`、`manual-abbr (2)/`、
> `out/c5d032…`、`out/c65a99…`。删除清单与理由见 `10_Other/backup/DELETED-2026-09-30.txt`。
>
> ### 4) ⚠️ nro 构建链当前跑不通
>
> 2026-09-30 系统重装后，`C:\devkitPro`、Qt（`mingw32-make`）、CMake **全部被清空**。
> `nro/HexDict.nro` 仍是 09-27 编译的旧产物。重建需要：
> devkitPro（可由 `10_Other/dkp-cache/` 的 7 个包**离线**重装）+ `devkitA64/base_rules`（codeload 可下）+ **一个 make**。
>
> ### 5) ★ 第二次整理：移除部署与校验，目录改为编号分类
>
> 工程根目录原先所有文件平铺，现按 `01_Inputs` / `02_References` / `03_Documents` /
> `04_Outputs` / `05_Code` / `10_Other` 六类归置。
>
> **移除**：全部部署包（`overlay-*`、`manual-*`、`*.zip`）、`install-to-sd.bat`、
> 校验交付物（`verify.bat`、`verify/`、`verify-report.txt`）、部署与诊断脚本
> （`pack_dist.py`、`make_verify_report.py`、`check_scaling.py`、`mk_scaling_probe.py`、
> `mk_probe.py`、`mk_multi.py`）。
>
> **最终产物只有三本**（`njubase1.a` / `njubase2.a` / `njubase3.a`），并已铺成
> SD 卡结构：`04_Outputs/<版本>/atmosphere/contents/…/pinyin/{GB18030,GB2312}/`（见 FINDINGS §22）。
> 原先另有的 `njubase3-lite.a` 与 150,000 词版 `njubase3.a` 已一并移除。
>
> ### 当前目录结构
>
> ```
> ns-ime/
> ├─ 01_Inputs/
> │   ├─ lex/          rime 词源 yaml + game.txt + ALL.tsv（883,019 条）
> │   ├─ firmware/     dat0805 / dat0808（从主机备份解包的原版词典）
> │   └─ prod.keys
> ├─ 02_References/    hactool/ + atmosphere/
> ├─ 03_Documents/     FINDINGS.md、本文件、reports/
> ├─ 04_Outputs/       <v版本>/atmosphere/contents/…/pinyin/{GB18030,GB2312}/  ★最终产物
> ├─ 05_Code/
> │   ├─ tools/        mk_lexicon.py / build_from_lexicon.py / mkdict.py / abbrev.py / njdc_lib.py …
> │   └─ nro/          HexDict .nro 工程
> ├─ 10_Other/         cache/  dkp-cache/  backup/  fw_index.json  扩展词典v0.1.zip
> └─ README.md         工程入口说明
> ```
>
> **生成流程（两条命令）**：
>
> ```bat
> python 05_Code/tools/mk_lexicon.py            :: 词源    -> 01_Inputs/lex/ALL.tsv
> python 05_Code/tools/build_from_lexicon.py    :: ALL.tsv -> 04_Outputs/<版本>/atmosphere/...
> ```
>
> ⚠️ **本文件 §2 起各节的路径均为 09-27 重组前的旧结构**（`dist/`、`lex/`、`out/`、`../tools/`），
> 保留原样以存史。实际路径以本节为准。
>
> ### ⚠️ 待办：实机验证
>
> 当前产物（`d9b9c226`，修复后，4.53 MB）**尚未实机验证**。
> 此前实机通过的是第二代（`f82208c8`，4.64 MB / 210,000 条）。
> 上机后按 §4.3 的流程测 `shalujianta` 与 `sljt` 两个词即可判定。

---

### 1. 成果一览

| | 原版固件 | 完整版 | 轻量版 |
|---|---|---|---|
| 条目数 | 57,954 | **150,000** | 80,000 |
| 文件大小 | 1,606,890 B | 4,025,516 B | 1,922,644 B |
| 唯一表记（去重后词数） | 57,807 | **149,030** | 79,277 |
| **重复条目** | — | **0** | **0** |
| 原版条目丢失 | — | **0** | **0** |
| 新增表记 | — | **+91,223** | +21,470 |

来源构成（完整版）：

```
单字 8,756 ＋ 游戏词表 252 ＋ 原版条目 57,954   = 66,962
                        ↓ 跨组去重 −4,317
                                               = 62,645
                    ＋ 常用词 87,355（按词频降序补足） = 150,000
```

- 单字/常用词：雾凇拼音 `rime-ice` 的 `8105 / base / ext` 词库（MIT/开源）
- 游戏词表：本工程手工整理 252 条，含主机/PC/手游常见作品名与术语，例如
  `杀戮尖塔 shalujianta`、`艾尔登法环 aierdengfahuan`、`黑神话悟空 heishenhuawukong`、
  `宝可梦 baokemeng`、`存档 cundang`、`联机 lianji`、`爆率 baolv`、`周目 zhoumu` …
- 拼音口径与设备**完全一致**（`ü` 写作 `v`：`lv / nv / lve / nve`），已在设备词典里逐条核对过。

> **关于「跨组去重 −4,317」**：单字表、游戏词表、原版词典三者在 `(读法, 表记)` 层面
> 有 4,317 条重叠（如 `('a','啊')`、`('ling','零')`）。若不去重，候选列表里同一个词会出现
> 两次乃至三次（`零` 曾出现 3 次）。现策略为**首次出现者胜**，保持「单字 → 游戏词 → 原版」
> 的组间优先序。去重省下的 4,317 条额度会**自动被常用词补上**，不浪费上限。

#### 1.1 还能放多大（扩容档位）

词源总量 **890,859 条**（雾凇拼音 `8105` + `base` + `ext` 去重后），当前只用 150,000 条
→ **余量 74 万条**。已生成各档如下：

| 档位 | 条目 | 文件大小 | 状态 |
|---|---|---|---|
| `njubase3.a` | 150,000 | 3.84 MB | ✅ 已实机验证 |
| `abbr/njubase3-abbr-full.a` | 210,000（150,000 词＋58,000 简拼） | **4.64 MB** | ✅ **已实机验证，当前最大可用档** |
| `abbr/njubase3-abbr-160000.a` | 220,000（160,000 词＋简拼） | 4.92 MB | ❌ 实测无候选 |
| `abbr/njubase3-abbr-175000.a` | 235,000 | 5.36 MB | ❌ 同上 |
| `abbr/njubase3-abbr-190000.a` | 250,000 | 5.78 MB | ❌ 同上 |

> ## ★ 结论：上限由「文件字节大小」决定，约在 4.64 ~ 4.92 MB 之间
>
> 这一条是**实测定下来的**，不是推测：
>
> | 包 | 记录数 | 词数 | 池 | 文件 | 结果 |
> |---|---|---|---|---|---|
> | `pad150-lite` | 150,000 | 149,030 | **2.62 MB** | **4.22 MB** | ✅ |
> | `abbr-full` | 210,000 | 149,030 | 2.24 MB | **4.64 MB** | ✅ |
> | `abbr160` | 220,000 | 159,003 | 2.41 MB | **4.92 MB** | ❌ |
> | `pad150-mid` | 150,000 | 149,030 | **3.42 MB** | **4.98 MB** | ❌ |
>
> **`pad150-lite` 与 `pad150-mid` 的记录数、词数完全相同**（都与 `[1] full` 一样），
> 只有池长和文件大小不同 —— 所以**记录数和词数都被排除**。
> 而 `pad150-lite` 的池（2.62 MB）**比** `abbr160` 的池（2.41 MB）**还大却成功** ——
> 池长也不单调，**也被排除**。剩下的唯一解释就是：**引擎限制的是文件总字节数**。
>
> **这意味着扩容基本到顶了**：`abbr-full` 已用掉约 94–95% 的空间。
> 每条真实词约 36 字节（记录 10 + 尾表 2 + 读法 ≈17 + 表记 ≈5.5），
> 剩余空间只够再加 **约 900 ~ 3,000 个词（+0.6% ~ 2%）**。
> **继续堆词的收益已经可以忽略**，力气应该转到别处（见 §9.7）。

**上限由什么决定**：原以为受 Atmosphere 的 applet romfs 构建预算
`MaximumRomfsBuildAppletMemorySize = 32 MB`（`fsmitm_romfs.cpp:30`）约束，
但实测显示 6.73 MB 就已经不工作 —— 说明真正的瓶颈在 **iWnn 引擎加载词典的那一步**，
与 romfs 预算无关（「键盘能弹出」恰好证明 romfs 覆盖是生效的）。详见 §9。

**权重断崖（决定「加词」会不会变成「加垃圾」）**：

| 排名 | 该名次的权重 |
|---|---|
| 150,000 | 3,725 |
| 250,000 | ~900 |
| 300,000 | 327 |
| **400,000 以上** | **100（一整段平台）** |

400,000 名之后是一大段「权重 100」的补充词（yaml 里未标权重），**词频信息为零**，
质量无法保证 —— 这是「高质量扩容」与「单纯堆量」的分界线。
所以推荐路径是 **150,000 → 250,000**（仍在正常词频区），而不是一步吃到 40 万。
（注：此路径现在**卡在上限诊断上**，先解决 §9 再谈扩容到哪。）

**权重断崖（决定「加词」会不会变成「加垃圾」）**：

| 排名 | 该名次的权重 |
|---|---|
| 150,000 | 3,725 |
| 250,000 | ~900 |
| 300,000 | 327 |
| **400,000 以上** | **100（一整段平台）** |

400,000 名之后是一大段「权重 100」的补充词（yaml 里未标权重），**词频信息为零**，
质量无法保证 —— 这是「高质量扩容」与「单纯堆量」的分界线。
所以推荐路径是 **150,000 → 250,000**（仍在正常词频区），而不是一步吃到 40 万。

> ⚠️ **扩容只增加「有没有」，不改善「排第几」。**
> 例：`youxi` 的首选仍是「有戏」而不是「游戏」—— 这是尾部表 6bit 优先级语义未解导致的
> **静态排序偏差**（见 §6 第 2 条），加再多词也不会变，反而候选更多、竞争更挤。
> 要改善排序必须另解那 6 个 bit，那是独立的一件事。

### 2. 目录说明

```
dist/
├─ njubase3.a              完整版词典（150,000 条 / 3.84 MB）
├─ njubase3-lite.a         轻量版词典（80,000 条 / 1.83 MB）
├─ abbr/                   ★ 简拼系（在 [5] 基础上逐档加词）
│   ├─ njubase3-abbr-test.a   简拼冒烟包（仅游戏词表出简拼，+297 条）
│   ├─ njubase3-abbr-probe.a  简拼冒烟包 + 2 条诊断探针（+299 条）
│   ├─ njubase3-abbr-full.a   150,000 词 + 58,000 简拼 / 210,000 条 / 4.64 MB ✅ 已实测
│   ├─ njubase3-abbr-160000.a 160,000 词 + 58,000 简拼 / 220,000 条 / 4.92 MB ★待实测
│   ├─ njubase3-abbr-175000.a 175,000 词 + 58,000 简拼 / 235,000 条 / 5.36 MB ★待实测
│   └─ njubase3-abbr-190000.a 190,000 词 + 58,000 简拼 / 250,000 条 / 5.78 MB ★待实测
├─ probe/                  规模上限诊断包（见 §9；只保留尚未实测的四个）
│   ├─ njubase3-pad150-lite.a  N=150,000、只加长池、4.22 MB
│   ├─ njubase3-pad150-mid.a   N=150,000、只加长池、4.98 MB
│   ├─ njubase3-pad150.a       N=150,000、只加长池、5.75 MB
│   └─ njubase3-pure210000.a   N=210,000、真实词、5.54 MB
├─ overlay/                ★首选部署包：只覆盖 njubase3.a
├─ overlay-lite/           轻量版部署包
├─ overlay-probe/          简拼冒烟部署包（内容 = abbr-probe，已实测通过）
├─ overlay-abbr/           简拼冒烟部署包（内容 = abbr-test，无探针）
├─ overlay-abbr-full/      150,000 词 + 简拼（已实测通过）
├─ overlay-abbr-160000/    160,000 词 + 简拼 ★建议先测这档
├─ overlay-abbr-175000/    175,000 词 + 简拼
├─ overlay-abbr-190000/    190,000 词 + 简拼（最大）
├─ overlay-pad150-lite/    诊断部署包 [10]（见 §9）
├─ overlay-pad150-mid/     诊断部署包 [11]
├─ overlay-pad150/         诊断部署包 [12]
├─ overlay-pure210000/     诊断部署包 [13]
├─ overlay-with-ad1/       备用部署包：同时同步了 njubase3.ad1 内嵌头（推测性，见 §6）
├─ install-to-sd.bat       一键拷贝到 SD 卡（ASCII 脚本，双击运行）
├─ verify.bat              一键跑校验（需要本机有 Python 3）
├─ verify/                 校验脚本（verify_njdc.py + njdc_lib.py）
├─ verify-report.txt      已跑出的校验报告
└─ README.md               本文件
```

### 3. 部署（3 步）

1. 用读卡器把 SD 卡插到电脑，运行 `install-to-sd.bat`，按提示输入 SD 卡根目录（如 `E:\`）。
   也可以手工把 `overlay\atmosphere` 整个拖到 SD 卡根目录（与已有的 `atmosphere` 合并）。
2. 安全弹出 SD 卡，插回主机，进 **CFW（大气层）** 启动。
   ⚠️ **开机时不要按住 L 键**。Atmosphere 的覆盖键默认就是 `L` 且 `override_by_default = true`，
   按住 L 会把 LayeredFS 覆盖**关掉**（`IsOverrideMatch = override_by_default ^ keys_triggered`），
   现象就是「好像完全没生效」。
3. 随便找个能打字的地方（设置里改昵称、eShop 搜索框等），切到**简体中文 · 拼音**，就绪。

回滚：删掉 SD 卡上 `atmosphere/contents/0100000000000805/` 整个目录即可，固件原文件不会被改动。

### 4. 怎么验证（这就是你要的验证方法）

#### 4.1 PC 侧：结构校验（部署前先做）

```
verify.bat  njubase3.a   <原版 njubase3.a>
```

脚本逐项检查并打印 `[OK]`：魔数 `NJDC`、头部长度取值、各区偏移的算术关系
（`0x0c = 文件大小 − 28 − 头部长度`、`0x24 = 0x20 + 10N`、文件大小 `= 尾部表偏移 + 2N + 4`）、
间隙 `08 06`、T 表可复算、所有记录偏移/长度合法、读法按 UTF-16BE 升序、
`0x14/0x18` 与实测最大长度一致、尾部表形态（高低字节成对相同、落在 `0x40..0x7f`）、文件尾 `NJDC`。

> ⚠️ 早期版本这里写过「`0x20=1146`、`0x0c=大小-112`」作为通用判据，**那是错的**——
> 它们只是「干净版式」文件（`njubase1/2`、`njcode`）的特征值，不是 NJDC 通用不变量
> （原版 `njubase3` 是 `81726/81724`，`njtan` 是 `57895/57880`）。现在校验器分
> **Tier 1 通用** + **Tier 2 仅干净版式**两层，能正确通过全部 6 本原版词典。

本次结果：**四份产物全部通过，0 条 FAIL**（见 `verify-report.txt`）。

#### 4.2 PC 侧：功能抽查（不依赖主机）

同上脚本会打印命中抽查，例如：

```
shalujianta      -> 杀戮尖塔     命中     ← 原版没有，最关键的判据
aierdengfahuan   -> 艾尔登法环   命中
heishenhuawukong -> 黑神话悟空   命中
cundang          -> 存档         命中
lianji           -> 联机         命中
jisuanjishu      -> 计算技术     命中
```

并与原版对账三项硬指标：**重复条目 = 0**、**原版有而新版无 = 0**、**新增表记数**。

#### 4.3 实机侧：LayeredFS 冒烟测试（最终判据）

先做一次**基线**（很重要，用来排除「本来就不生效」）：

1. 不装 overlay，开机，进输入法，打 `shalujianta` → 预期**打不出「杀戮尖塔」**。
2. 关机，按 §3 装 overlay，开机（**不按 L**）。
3. 进输入法，依次打：

| 输入 | 期望 | 说明 |
|---|---|---|
| `ni` | 你 | 基数能力仍在（单字没问题） |
| `beijing` | 北京 | 常用词仍在 |
| `shalujianta` | **杀戮尖塔** | ★生效判据：原版没有这个词 |
| `aierdengfahuan` | 艾尔登法环 | 游戏词表生效 |
| `youxi` | 游戏（可能不是首选） | 大词库生效 |
| `jisuanjishu` | 计算技术 | 长词/联想 |

**判定**：只要 `shalujianta` 能打出「杀戮尖塔」，覆盖一定生效了（旧词典里根本没有这条）。

**没生效时的排查顺序**：

1. 是否开 CFW、是否**按住过 L 开机** → 重启，全程不碰手柄。
2. 路径大小写与层级是否精确：
   `sd:/atmosphere/contents/0100000000000805/romfs/Iwnn/ZH/CN/pinyin/GB18030/njubase3.a`
   （注意是 `contents` 不是 `contens`；`0100000000000805` 是 16 位）
3. titleId 是否真是 `0100000000000805`：用 DBI / nxdumptool 查
   `0100000000001008`（swkbd）挂载的词典数据 title。
4. 简体中文目录是 `ZH/CN/pinyin`；若你系统语言不是简体中文，可能走 `ZH/TW`（本工程未覆盖）。
5. 编码分支：本工程同时放了 `GB18030/` 与 `GB2312/` 两处，若只放一处可能不命中。
6. 试 `GB2312` 单路径 / 试轻量版；再不行试 `overlay-with-ad1`（见 §6）。
7. 仍无效 → 大概率是 `.a` 与 `.ad1` 的一致性校验（§6 的未知项），把现象记下来反馈。

### 5. 简拼（首字母联想）：`sljt` → 杀戮尖塔

回答「能不能做成安卓电视搜索那种、打首字母就联想」。

#### 5.1 已经做了什么

给多字词**额外追加一条「首字母读法」条目**，与全拼条目并存：

```
sljt   → 杀戮尖塔        （原条目 shalujianta 仍在）
aedfh  → 艾尔登法环
hshwk  → 黑神话悟空
bkm    → 宝可梦
cd     → 存档
zm     → 周目
```

实现要点：

- 字→拼音表**从设备自己的 `njtan.a` 提取**（12,873 汉字 / 707 个多音字），
  保证与设备口径一致（否则会出现「你按设备读音打的简拼却匹配不上」）。
- 多音字会生成多个变体（如「独立游戏」→ `dlyx` 与 `dlyh`，因「戏」有 `xi/hu` 两读）；
  上限 `--abbrev-max-combos 4`。
- 只对**长度 ≥ 2 个字**的词生成（避免单字简拼与全拼撞车）。

| 包 | 条目数 | 大小 | 简拼条数 | 用途 |
|---|---|---|---|---|
| `abbr/njubase3-abbr-test.a` | 150,297 | 4,030,738 B | +297（仅 252 条游戏词） | 冒烟包（**已实测通过**） |
| `abbr/njubase3-abbr-probe.a` | 150,299 | 4,030,778 B | +297 ＋ 2 条探针 | 带诊断探针的冒烟包 |
| `abbr/njubase3-abbr-full.a` | 210,000 | 4,865,870 B | +60,000（全量） | ★ 正式版（待实机确认 4.64 MB 是否吃得下） |

> 注意：三份简拼包的**唯一表记数都与完整版相同**（149,030）——
> 简拼只增加「读法入口」，不引入新词。这是设计使然。

#### 5.2 实机冒烟结果：★ 全部通过（2026-09-27）

在真机上装 `overlay-probe`，按顺序逐个打，结果如下：

| 输入 | 实测结果 | 说明 |
|---|---|---|
| `sha` | 只有单字 | **正常现象** —— 打 `sha` 走全拼前缀，命中的候选有 **1,827 条**，「杀戮尖塔」被挤在后面没显示出来 |
| `shal` | **杀戮尖塔** ✓ | 候选降到 27 条，它自然就露出来了 |
| `0000` | **杀戮尖塔** ✓ | 纯数字探针 |
| `zzzz` | **杀戮尖塔** ✓ | 非音节字母串探针 |
| `jt` | **尖塔** ✓ | 2 字母简拼 |
| `bkm` | **宝可梦** ✓ | 3 字母简拼 |
| `sljt` | **杀戮尖塔** ✓ | ★ 目标方案 |

**结论：简拼（首字母联想）方案成立。**

两个关键副产品：

1. **引擎对读法形态零校验** —— `0000`（纯数字）和 `zzzz`（非音节字母串）都能命中。
   原先担心的「引擎按音节切分、辅音串被丢弃」**被实测否定**。
   顺带说明：原版 `njcode.a` 那 285 条十六进制码点读法（`20164 → 𠅤`）确实是引擎的正常用法，不是特例。
   这意味着**任意编码的快捷输入都可行**（数字编码、自定义快捷词），是后续可做的扩展方向。
2. **`sha` 只出单字是候选数量/排序问题，不是覆盖失败** ——
   判断覆盖是否生效要看 `shal`、`shalujianta` 这种**唯一前缀**，别看 `sha` 这种 1,800 条候选的大前缀。

> **顺带修掉一个会露馅的问题**：简拼串若是**同一个词其它读法**的前缀，会撞车。
> 例：`阿呆` 全拼 `adai`，简拼 `ad` —— 打 `ad` 时全拼前缀与简拼条目**各命中一次**，
> 候选列表里「阿呆」出现两次。这类条目**本来就是冗余的**（入口已存在），
> 现已生成时自动丢弃：full 包 60,000 条里丢掉 295 条（0.5%，几乎全是「首字零声母」的词：
> 阿X / 按X / 沙盒 shahe）。丢弃后**会重复候选 = 0**，且这些词的全拼入口不受影响、
> 优先级相同、候选位置不变 —— **用户体验完全一致，等于零损失**。
> （生成器默认开启，`--abbrev-allow-dup` 可关。）

#### 5.3 与「安卓电视搜索」的真实差距（如实说）

**能做到「打首字母出候选」**（已实测），但**做不到「像电视搜索那么聪明」**：

| | 安卓电视搜索 | 本方案 |
|---|---|---|
| 匹配方式 | 实时模糊匹配（子串、错拼、多语） | 词典**前缀**匹配（改词典能加入口，改不了匹配算法） |
| 排序 | 按相关性动态算分 | 靠尾部表的 6bit 优先级字段，**静态**、语义未完全确认 |
| 词库来源 | 在线、可更新 | 本地文件，换词库要重启（见 `.nro` 工程） |
| 首字母联想 | 原生支持 | **已实测可用** ✓ |

一句话：匹配与排序发生在 iWnn 引擎内部（编译在 swkbd 的 `main` 段里），
词典层只能提供数据 —— **能加"入口"，改不了"算法"**。

### 6. 已知风险 / 尚未解出的部分（如实说明）

1. **`njubase3.ad1` 未解出**。它是 NJAD 容器，`0x28` 起内嵌一份与 `.a` **逐字节相同**的
   NJDC 头部。若引擎拿这份副本做一致性校验，替换 `.a` 后校验会失败。
   `overlay-with-ad1/` 是**推测性**修补：保留 `.ad1` 全部原始内容，只把内嵌那 84 字节头
   同步成新 `.a` 的头部。**先试 `overlay/`，不生效再试 `overlay-with-ad1/`。**
   > 实机已验证：把整个 `njubase3.a` 从「带附加区的 extra 版式」换成「干净版式」，
   > 引擎照常接受 → iWnn 完全按文件自身头部字段寻址，**不要求同槽位文件版式一致**。
2. **尾部表的 6bit 值语义是「优先级/词频」的推断**，非实测确认。
   本工程按 `njubase1/2/njtan` 的口径写 `0x40|v` 高低字节相同；
   原版 `njubase3` 用的是一个变体（含 `0x8040`、`0x0000` 等值），`njcode` 又是 `0x4000`。
   若候选词排序看起来不合意，是这一层的影响，不影响「能不能打出来」。
   实测到的例子：`youxi` 首选是「有戏」而非「游戏」，`jisuanji` 首选是「计算技」——
   都属于这一层未解带来的排序偏差。
3. **简拼行为未经实机确认**（见 §5.2）。
4. `njtan.a` 独有的 4 字节/条「读音索引区」、`njubase3` 的附加区（149,352 B）语义未解，
   本工程生成的词典走的是「无附加区」的干净布局（同 `njubase1`）。
5. **候选排序不保证优于原版**：本次为「不回归」策略——原版条目沿用其原优先级，
   新词按词频映射。

### 7. 不解决什么

- **痛点 ①按键位置不好**：那是 swkbd 键盘布局 / 按键映射层面，改词典无效。
- **繁体中文（`ZH/TW`）与粤拼/仓颉路径未覆盖**，只做了简体拼音 `ZH/CN/pinyin`。
- 不涉及破解、密钥获取；本工程只做「自有主机上替换一个数据文件」。

### 8. 自己重编（可复现）

```bat
:: 完整版（150,000 条）
python tools\mkdict.py ^
  --lex lex\ice_8105.yaml --lex lex\ice_base.yaml --lex lex\ice_ext.yaml ^
  --merge out\dat0805\files\Iwnn\ZH\CN\pinyin\GB18030\njubase3.a ^
  --limit 150000 --out dist\njubase3.a

:: 轻量版（80,000 条）
... --limit 80000 --out dist\njubase3-lite.a

:: 简拼冒烟包（只给游戏词出简拼）
... --limit 150000 --abbrev games --out dist\abbr\njubase3-abbr-test.a

:: 简拼全量包（150,000 词 + 简拼，上限 60,000 条简拼）★已验证可用，作为加词基底
... --limit 150000 --abbrev all --abbrev-limit 60000 --out dist\abbr\njubase3-abbr-full.a

:: 逐档加词 —— 这就是现在的扩容路线（在 [5] 基础上加真实词，简拼保留）
... --limit 160000 --abbrev all --abbrev-limit 60000 --out dist\abbr\njubase3-abbr-160000.a
... --limit 175000 --abbrev all --abbrev-limit 60000 --out dist\abbr\njubase3-abbr-175000.a
... --limit 190000 --abbrev all --abbrev-limit 60000 --out dist\abbr\njubase3-abbr-190000.a
... --limit 250000 --out dist\big\njubase3-250000.a
... --limit 400000 --out dist\big\njubase3-400000.a
```

`--limit` 可调条目上限（决定文件大小）；`--no-game` 可去掉游戏词表；
简拼相关参数见 `--abbrev*` 系列（`--abbrev-min-len` / `--abbrev-max-combos` / `--abbrev-limit`）。
简拼包默认会**自动丢弃「与同词全拼撞车」的条目**（见 §5.2 末尾），
加 `--abbrev-allow-dup` 可关闭该过滤（不建议）。
词库文件已随工程放在 `lex/`（雾凇拼音 `rime-ice`，取自 GitHub）。

**本次产出哈希（可复现）**

| 文件 | 大小 | sha256（前 16 位） |
|---|---|---|
| `njubase3.a` | 4,025,516 | `414f4d8c7647a06f` |
| `njubase3-lite.a` | 1,922,644 | `630fa0cecdf81064` |
| `abbr/njubase3-abbr-test.a` | 4,030,738 | `6714dd240ee3e9f0` |
| `abbr/njubase3-abbr-full.a` | 4,865,870 | `f82208c8a2b4fe7b` |
| `abbr/njubase3-abbr-probe.a` | 4,030,778 | `9b5e34c0874d2b76` |
| `abbr/njubase3-abbr-160000.a` | 5,163,826 | `10653f9680d88237` |
| `abbr/njubase3-abbr-175000.a` | 5,616,608 | `a1a0e85ccc6670ed` |
| `abbr/njubase3-abbr-190000.a` | 6,060,350 | `469399f499bc3ae1` |
| `probe/njubase3-pad150-lite.a` | 4,425,516 | `4c4a4a666342a18d` |
| `probe/njubase3-pad150-mid.a` | 5,225,516 | `fdf20192001e7e12` |
| `probe/njubase3-pad150.a` | 6,025,516 | `99dd8c5c48b139d4` |
| `probe/njubase3-pure210000.a` | 5,814,430 | `693c5d4e0d9624d0` |

> `probe/` 四个包是**规模上限诊断**的对照包（见 §9），不是给日常使用的。
> `pad*` 三个由 `tools/mk_scaling_probe.py` 从 `dist/njubase3.a` **追加池尾填充**生成 ——
> N、记录表、唯一表记全部不变，只有池长与文件大小变大。

> 已清理的失败产物（不再随工程分发，可用 §9.6 的命令重建）：
> `big/njubase3-250000.a`、`big/njubase3-400000.a`、`probe/njubase3-225000.a`、
> `probe/njubase3-dup{210000,230000,250000,300000}.a`、`probe/njubase3-trim200000.a`。

> `abbr-probe` 由 `abbr-test` 再跑一步得到（脚本内部会先做**往返自检**：
> 原样重建必须逐字节一致，否则说明 build 参数与原文件不符、后面的输出不可信）：
>
> ```bat
> python tools\mk_probe.py dist\abbr\njubase3-abbr-test.a dist\abbr\njubase3-abbr-probe.a
> ```

> 说明：完整版按 150,000 条上限截断，因此部分低频词（如「圆周率」，权重 4880）
> 落在集合之外；提高 `--limit` 即可纳入更多。轻量版（80,000 条）主要是给
> 「担心内存 / 想先小步试」的场景，内容与完整版同源。

### 9. 规模上限诊断（进行中，2026-09-27）

> **状态更新（当晚）**：实测失败的产物**已从工程中清理**（见 §8 末尾清单），
> 只保留尚未实测的 4 个 pad/pure 诊断包。
> 扩容路线已改为**「在已验证可用的 `[5] abbr-full` 上逐档加词」** —— 见 §1.1。
> 下面 §9.1–§9.6 是诊断过程与已得结论，保留备查。
>
> ⚠️ **本节正文里的选项号是当时的编号，已随清理重排**，对照如下：
>
> | 本节正文写法 | 现在的一键脚本选项 |
> |---|---|
> | `[6] big250`、`[7] big400` | **已删除**（不再有这些选项） |
> | `[9]`–`[14]`（dup / trim / pure225） | **已删除** |
> | `[15] pad150-lite` | → `[10]` |
> | `[16] pad150-mid` | → `[11]` |
> | `[17] pad150` | → `[12]` |
> | `[18] pure210` | → `[13]` |
> | — | `[7]`/`[8]`/`[9]` = **新增的 abbr160 / abbr175 / abbr190** |

#### 9.1 现象

实机反馈：

| 包 | 现象 |
|---|---|
| `[1] full`（150,000 条 / 3.84 MB） | ✅ 正常出词 |
| `[5] abbr-full`（210,000 条 / 4.64 MB） | ✅ 正常出词 |
| `[6] big250`（250,000 条 / 6.73 MB） | ⚠️ **键盘能弹出，但候选列表为空** |
| `[7] big400`（400,000 条 / 11.42 MB） | ⚠️ 同上 |
| `[9] dup250`（250,000 条 / 4.98 MB） | ⚠️ 同上（第一轮诊断） |
| `[10] dup300`（300,000 条 / 5.56 MB） | ⚠️ 同上 |
| `[11] pure225`（225,000 条 / 5.98 MB） | ⚠️ 同上 |

**「键盘能弹出」是关键信息**：说明 Atmosphere LayeredFS 覆盖本身生效了、
swkbd applet 正常启动 —— 失败发生在 **iWnn 引擎加载词典那一步**，
加载失败后引擎退化为「无词典模式」，于是按键有反应但永远没有候选。

因此 §1.1 里「上限 = applet romfs 预算 32 MB」的说法**不成立**：
真正的天花板远低于 32 MB，而且和 romfs 预算无关。

#### 9.2 为什么不能直接判断

四档产物里，**三个量同时在涨**，无法确定是哪个触限：

| 包 | 记录数 N | 池长（内容量） | 文件大小 | 结果 |
|---|---|---|---|---|
| `[1] full` | 150,000 | 2.22 MB | 3.84 MB | ✅ |
| `[5] abbr-full` | 210,000 | 2.34 MB | 4.64 MB | ✅ |
| `[6] big250` | 250,000 | 4.06 MB | 6.73 MB | ❌ |
| `[7] big400` | 400,000 | 7.17 MB | 11.42 MB | ❌ |

已排除的项（静态检查，`tools/check_scaling.py`）：

- **头部字段无隐藏差异** —— 除规模相关字段外，四档头部逐字节相同
- **无长度溢出** —— 读法最大 72 字节、表记最大 22 字节，全部 ≪ 255（记录表长度字段是 u8）
- **无字符异常** —— 读法 100% 纯 ASCII，非 BMP 字符只出现在表记且仅 200 余条（各档一致）
- **无偏移溢出** —— 记录表偏移字段是 u24（上限 16 MB），池最大 7.17 MB
- **结构同构** —— 四档走同一套 `build_njdc`，参数一致

#### 9.3 诊断包（正交设计）

`tools/mk_scaling_probe.py` 把**已验证可用的 `[1] full` 的记录再重复一遍**，
池字节原样复用 —— 于是「记录数」被单独放大，而**内容与池完全不变**。

**第一轮诊断包（已测，三个全部失败）**：

| 包 | 记录数 N | 池长 | 文件 | 设计意图 |
|---|---|---|---|---|
| `[9] dup250` | **250,000** | **2.22 MB** | **4.98 MB** | 与失败的 `[6]` **记录数完全相同**，但内容只有一半 |
| `[10] dup300` | 300,000 | 2.22 MB | 5.56 MB | 记录数已超 `[6]`，内容仍很小 |
| `[11] pure225` | 225,000 | 3.65 MB | 5.98 MB | 记录数少于 `[6]`，但内容是真实词 |

**第一轮结论**：三个全部失败，把范围压得很窄 ——
`[9] dup250` 与**可用**的 `[5] abbr-full` 相比，**池还更小**（2.22 vs 2.34 MB）、
文件只大 0.11 MB，**唯一显著差别是记录数 250,000 vs 210,000**。

但它留下两个**必须先排除的疑点**，否则结论会是错的：

1. `[9]`/`[10]` 都含**大量完全重复的条目**（同一 读法+表记 出现两次）——
   失败有可能是「重复条目」触发的，与记录数无关；
2. `[11] pure225` 的 N=225,000 **小于** 250,000 却同样失败。

**第二轮诊断包（已测：三个全部失败，且结论是「方法作废」）**：

| 包 | 记录数 N | 池长 | 文件 | 结果 |
|---|---|---|---|---|
| `[12] dup210` | **210,000** | 2.22 MB | 4.53 MB | ❌ |
| `[13] dup230` | 230,000 | 2.22 MB | 4.75 MB | ❌ |
| `[14] trim200` | 200,000 | 4.06 MB | 6.16 MB | ❌ |

**★ `[12] dup210` 与 `[5] abbr-full` 的对照，得到一个确定结论：**

| | `[5] abbr-full` | `[12] dup210` |
|---|---|---|
| 记录数 N | 210,000 | **210,000（相同）** |
| 唯一表记 | 149,030 | **149,030（相同）** |
| 池长 | 2.34 MB | **2.22 MB（更小）** |
| 文件 | 4.87 MB | **4.53 MB（更小）** |
| 构建方式 | 150,000 词 + 60,000 **别名读法** | 150,000 词 + 60,000 **重复条目** |
| 结果 | ✅ | ❌ |

两者**记录数相同、唯一表记也相同**，`dup210` 的池和文件**甚至还更小**，
唯一差别是它含 **60,000 条完全重复的条目**（同一 `读法+表记` 出现两次）。

> **结论：重复条目本身就会让引擎拒绝加载整个词典。**
> 因此四个 dup 包（`[9]`/`[10]`/`[12]`/`[13]`）的数据**全部作废**，
> 不能用来推断记录数上限。

`[14] trim200` 同样不干净：它删掉记录后**池里留下了不再被引用的孤儿串**。
如果引擎在意这个，它失败的原因就不是「池大」而是「池里有垃圾」——
所以它**也不能**证明「记录数与上限无关」。

**第三轮诊断包（待测）—— 只动池长，其余全部保持可用档原值**：

`pad_pool` 只做一件事：往 `[1]` 的**池末尾追加填充字节**。
`N`、记录表、T 表、**唯一读法与唯一表记全部保持原值** —— 只有池长和文件大小变大。

| 包 | 记录数 N | 池长 | 文件 | 设计意图 |
|---|---|---|---|---|
| `[15] pad150-lite` | 150,000 | 2.62 MB | **4.22 MB** | **控制组**：验证「追加填充」这个手法本身安全 |
| `[16] pad150-mid` | 150,000 | 3.42 MB | **4.98 MB** | 夹阈值（与 `[9] dup250` 同为 4.98 MB） |
| `[17] pad150` | 150,000 | 4.22 MB | **5.75 MB** | **关键**：N、词表、记录表都与可用档 `[1]` 完全相同 |
| `[18] pure210` | **210,000** | 3.14 MB | **5.54 MB** | 真实词、无重复条目，**N 与可用的 `[5]` 相同** |

`[15]` 若失败 ⇒ 填充手法有毒，第三轮作废；
`[15]` 通过而 `[17]` 失败 ⇒ **限制就是池长 / 文件大小**
（因为 `[17]` 的记录数和词表与可用的 `[1]` 一模一样）。

> ⚠️ `[9]` / `[10]` 是**有意做成「每个词出现两次」**的（这正是「记录数涨、内容不涨」
> 的手段）。候选列表里同一个词出现两次是**预期行为，不是 bug**。

> 关键：dup 包的记录表必须**按读法重新升序排列**，不能简单整段复制 ——
> 整段复制会得到「[升序][升序]」两段、整体降序跳变，引擎二分查找直接失效，
> 会把「顺序错」误判成「规模超限」。脚本用稳定排序重建并自检升序。

#### 9.4 判读矩阵（第三轮）

第二轮的真实产出是**一个确定的结论**（见 §9.3）：**重复条目会让引擎拒绝加载整个词典**。
这条结论本身很有价值，但它同时把第二轮其余数据全部作废了。

**第一步先看 `[15] pad150-lite`**（控制组）：

| `[15]` | 含义 |
|---|---|
| ❌ | 「池末尾追加填充」这个手法本身有问题 → 第三轮作废，需另找分离手段 |
| ✅ | 手法安全，继续看 `[17]` |

`[15]` 通过后：

| `[17]` pad150 | 结论 |
|---|---|
| ❌ | **限制是「池长 / 文件大小」** —— `[17]` 的记录数、词表、记录表与**可用的 `[1]` 完全相同**，只有文件变大。规模上限由**字节量**决定 |
| ✅ | 限制不是字节量 → 转向**记录数 / 唯一表记数**，用 `[16]` 与真实词档继续夹 |

**辅助交叉验证点**：

| 包 | N | 池 | 文件 | 与可用档的 N 关系 | 若 ❌ 说明 |
|---|---|---|---|---|---|
| `[18] pure210` | **210,000** | 3.14 MB | 5.54 MB | **与 `[5]` 相同** | 池 / 文件是限制（N 相同却失败） |
| `[16] pad150-mid` | 150,000 | 3.42 MB | 4.98 MB | 与 `[1]` 相同 | 池 / 文件是限制 |

`[18] pure210` 尤其干净：**真实词、无重复条目**，且 **N 与可用的 `[5]` 完全相同**（都是 210,000）
—— 它若失败，同样只能归因于池 / 文件大小。

**这一轮为什么终于干净**：前两轮的 dup 与 trim 都引入了副作用
（**重复条目** / **孤儿串**），而 pad 与 pure210 都没有这类副作用。

**测试词表**：

| 输入 | 预期候选 | 性质 |
|---|---|---|
| **`shalujianta`** | 「杀戮尖塔」1 条 | ★ **可靠判据** —— 已核实**原版六本词典全都没有** |
| `baokemeng` | 「宝可梦」1 条 | 同上（六本全没有） |
| `youxi` | 8 条（有戏 / 有喜 / …） | 旧词、候选多，失败时对比最明显 |

> ⚠️ **不要用 `cundang` 当测试词** —— 原版 `njubase2.a` 里就有「存档」，
> 不装插件也打得出来，出现它证明不了任何事。
> **教训：判断「是不是新词」必须查遍原版全部 6 本词典**（`njubase1/2/3`、`njtan`、`njcode`、`njexyomi`），
> 只查 `njubase3.a` 会得出错误结论。

**判定**：只要**出现候选**即为加载成功；一个候选都没有即为加载失败。

#### 9.5 副产品：简体拼音其实有「两套并行词典」

查目录时发现 `Iwnn/ZH/CN/pinyin/` 下有**两个并列**的编码目录：

| 文件 | `GB18030/` | `GB2312/` | 关系 |
|---|---|---|---|
| `njtan.a` | **256,025** | **137,190** | **差 46%** |
| `njcode.a` | 8,204 | **不存在** | GB2312 侧没有 |
| `njubase3.a` | 1,606,890 | 1,606,358 | 差 532 字节 |
| `njubase1.a` / `njubase2.a` / `njexyomi.a` | 90,402 / 91,258 / 1,528 | 完全相同 | **SAME** |

**GB18030 / GB2312 不是「文件系统编码」，而是「候选字集范围」的标识**：

- NJDC 词典内部**一律用 UTF-16BE 存字符**，与 GB 编码无关；
- `njtan.a` 在两套里差 46%，**推测**对应「GB2312 只有 6,763 个基本汉字，
  GB18030 覆盖七万余汉字（含扩展区）」这一字集差距；
- `njcode.a`（Unicode 码点 → 汉字，见 §12）只在 GB18030 侧存在，GB2312 侧不需要。

**本工程为什么只覆盖 `GB18030/`**：

1. **实测证明它生效** —— `[1]` / `[5]` 两档都只覆盖 `GB18030/`，都正常出词，
   说明系统当前走的就是这条路径；
2. **本词典物理上只能放 GB18030** —— 词表含 **205 个 CJK 扩展区字符**（非 BMP），
   这些字 GB2312 装不下；
3. **覆盖 `GB2312/` 无必要** —— 那是基本字集的降级版本。

> 但它带出一个**待验证的新假设**：两套目录并列，说明引擎**可能按输入模式选一套**，
> 也**可能同时加载两套**。若是后者，实际加载量 = 两套之和，
> 那么「把 `GB2312/` 那本换小」就有可能腾出空间给 `GB18030/` —— 一条潜在绕法。
> 判定方法：把 `GB2312/njubase3.a` 也覆盖成一个带独有探针词的小词典，
> 若在 **GB18030 模式**下也能打出探针词，即证明引擎同时加载两套
> （注意 LayeredFS 只能覆盖、不能删除文件）。

#### 9.6 复现

```bat
:: 生成诊断包（dup 放大记录数 / trim 缩小记录数 / pad 只放大池长）
python tools\mk_scaling_probe.py

:: 生成真实词中间档
python tools\mkdict.py ^
  --lex lex\ice_8105.yaml --lex lex\ice_base.yaml --lex lex\ice_ext.yaml ^
  --merge out\dat0805\files\Iwnn\ZH\CN\pinyin\GB18030\njubase3.a ^
  --limit 225000 --out dist\probe\njubase3-225000.a

:: 结构体检（各档关键指标对照）
python tools\check_scaling.py
```

#### 9.7 结论与后续方向

**结论**：上限是**文件字节大小**（4.64 ~ 4.92 MB 之间）。
`abbr-full`（4.64 MB / 150,000 词 + 58,000 简拼）**已接近天花板**，
再加也只能加约 900 ~ 3,000 个词（+0.6% ~ 2%）。

三条后续方向：

**① 精确标定这条线**（`[14]`/`[15]`/`[16]`，4.70 / 4.80 / 4.90 MB）
三个包的记录数与词数都与 `[1]` **完全相同**，只有文件大小不同，一次就能夹出阈值。
价值：算出「还能加多少词」—— 结论是**不多**。

**② 多本分担（`[17]` 探针）—— 唯一可能显著扩容的方向**
系统有 6 本词典，本工程此前只动过 `njubase3.a`：

| 词典 | 条目 | 内容 |
|---|---|---|
| `njubase1.a` | 3,351 | 2 字专名（阿坝、阿富汗…） |
| `njubase2.a` | 3,235 | 2 字专名（阿布扎比、阿斗…） |
| `njubase3.a` | 57,954 | 主词库 ← 我们用的 |
| `njtan.a` | 14,184 | 全部单字 |
| `njcode.a` | 285 | 码点→汉字 |
| `njexyomi.a` | 0（中文版） | 联想（未解） |

`njubase1/2` 用的是**与 njubase3 相同的干净版式**（`0x20=1146`），可以直接替换。
`[17]` 探针只替换 `njubase1.a`，并塞入两个**任何原版词典都没有的独创词**
（`nbprobe`、`nbprobe2`）：

- **能打出这两个词** ⇒ 引擎确实会查 `njubase1`，而每本可能有**独立的大小预算**
  ⇒ **总容量有望翻几倍**（唯一的大幅扩容路径）；
- **打不出** ⇒ 这条路关闭。

> 注：`njtan.a` 采用**另一套版式**（我们重建后大小差 56,749 字节，无法逐字节复现），
> 暂不纳入此方向。

**③ 转向体验优化（推荐）**
容量既已到顶，剩下两个真痛点更值得投入：
- **候选排序偏差** —— `youxi` 首选「有戏」而非「游戏」，需解尾部表 6 bit 语义（§6 第 2 条）；
- **联想差（痛点②）** —— `njexyomi.a` 在中文版只有 1,528 字节、N=0，尚未解出。

---

### 10. ★ 多本分担扩容（2026-09-27 实测打通）

> ### ⚠️ 2026-09-30 复审：本节的结论**尚未验证**，请先读 `FINDINGS.md` §21
>
> 本节标题的「实测打通」**只指探针实验**（往 `njubase1` 塞 2 个独创词能被打出来），
> 它证明了「引擎会读 `njubase1`」，但**不能推出「每本有独立的大小预算」**：
> 探针放进去的是一个 ≈90 KB 的小词典，那时的引擎可见总量约 2.0~5.1 MB，
> **在「单本上限」和「总量上限」两种假设下都能出词**。
>
> 而 §9 的全部阈值实验**只动过 `njubase3` 一本**，观测到的「失败点」
> 既可以解读为「base3 文件大小」（4.87 ✅ / 5.16 ❌ MB），
> 也可以解读为「**三本总量**」（5.31 ✅ / 5.61 ❌ MB）—— **两个假设数学等价，未区分**。
>
> 且本节 §10.4 只写了**判据**、没有实测结果；FINDINGS §18.5 也明确写着 MULTI 包「**待验**」。
>
> **因此：下面「约 411,000 词」「总容量 = 各本之和」等表述，在实验 A/B 完成前都是假说。**
> 当前三本总量 ≈ 13.46 MB，若真限总量则必然失败。

#### 10.1 突破点

`[17] njb1probe` 实测**成功** —— 往 `njubase1.a` 里塞的独创词能被打出来：

> **⇒ 引擎确实会读取 `njubase1`，且每本词典有各自独立的大小预算。**

这条**推翻了 §9 的悲观结论**：单本上限虽然是约 4.6 MB，但**总容量 = 各本之和**。

#### 10.2 六本词典的角色

| 词典 | 原条目 | 唯一表记 | 内容特征 | 能否扩容 |
|---|---|---|---|---|
| `njubase1.a` | 3,351 | 3,351 | 2 字专名（阿坝、阿富汗…） | ✅ |
| `njubase2.a` | 3,235 | 3,235 | 2 字专名（阿布扎比、阿斗…） | ✅ |
| `njubase3.a` | 57,954 | 57,807 | 主词库 | ✅ 已扩 |
| `njtan.a` | 14,184 | 12,874 | **只有 415 个读法** → 单字表 | ⚠️ 版式不同，暂不动 |
| `njcode.a` | 285 | 285 | 码点 → 汉字 | ❌ 特殊用途，不宜塞词 |
| `njexyomi.a` | 0 | 0 | 联想（中文版为空） | ❌ 不是词库 |

> 六本合并去重后仅 **71,344** 个表记；且 **`njubase1 ∩ njubase2 = 0`**（天然互补）。

#### 10.3 分片方案（工具：`tools/mk_multi.py`）

把词源按权重排开、**按表记去重**，再切成互不重叠的多份：

| 词典 | 新增词 | 本有 | 合计 | 文件 |
|---|---|---|---|---|
| `njubase1.a` | 137,379 | 3,351 | 140,730 | **4.28 MB** |
| `njubase2.a` | 124,218 | 3,235 | 127,453 | **4.42 MB** |
| `njubase3.a` | —（保持 abbr-full 不变） | — | 210,000 | **4.64 MB** |

**总不同词数 ≈ 411,000**（此前 150,000 → **翻了 2.7 倍**）。

三条硬约束（脚本内部保证）：

1. **片与片、片与 `abbr-full` 之间不得有重复表记** —— 否则候选会重复显示；
2. **每片必须并入该本原版的全部条目** —— 否则丢掉原有覆盖；
3. **按「目标字节数」而不是条数切** —— 实测同样 150,000 条，base1 为 4.80 MB、
   base2 却 5.69 MB（后一批词更长），**按条数切会直接撞上限**。

#### 10.4 测试

| 选 | 包 | base1 | base2 | base3 |
|---|---|---|---|---|
| **`[18]`** | **multi（推荐）** | 4.28 MB | 4.42 MB | 4.64 MB（abbr-full） |
| `[19]` | multi-big（探针） | 5.09 MB | 5.24 MB | 同上 |

判据：`shalujianta` 与 `sljt` 照常可用，再用一个**不在 abbr-full 里**的词验证新本确实被读取。
**若候选为空** → 说明单本预算比 4.6 MB 更小，需要下压每本体积（脚本 `--mb` 参数）。

#### 10.5 复现

```bat
python tools\mk_multi.py ^
  --lex lex\ice_8105.yaml --lex lex\ice_base.yaml --lex lex\ice_ext.yaml ^
  --mb 4.7 ^
  --exclude dist\abbr\njubase3-abbr-full.a ^
  --merge out\dat0805\files\Iwnn\ZH\CN\pinyin\GB18030\njubase1.a --out dist\multi\njubase1.a ^
  --merge out\dat0805\files\Iwnn\ZH\CN\pinyin\GB18030\njubase2.a --out dist\multi\njubase2.a
```

---

### 11. 统一主词库 `lex/ALL.tsv`（后续生成 NS 词典的唯一输入）

把所有词源**汇总成一个文件**，格式就是「输入 → 输出」，可直接用文本编辑器 / Excel 打开编辑。

**文件**：`lex/ALL.tsv`（**883,019 条**，37 MB）

**格式**（TSV，5 列）：

| 列 | 含义 | 例 |
|---|---|---|
| 1 | **全拼**（音节连写，ü→v） | `shalujianta` |
| 2 | **简拼**（各音节首字母；单字为 `-`） | `sljt` |
| 3 | **中文**（要输出的候选） | 杀戮尖塔 |
| 4 | 权重（越大越优先入选） | 100000 |
| 5 | 来源 | `game` / `ice_8105` / `ice_base` / `ice_ext` |

```
shalujianta	sljt	杀戮尖塔	100000	game
baokemeng	bkm	宝可梦	100000	game
cundang	cd	存档	140750	game
```

**来源分布**：`ice_base` 540,098 · `ice_ext` 333,773 · `ice_8105` 8,755 · `game` 393

#### 11.1 游戏词条（`lex/game.txt`，可自由增删）

格式：一行一个词，**中文 + 分音节拼音**（空格分隔）：

```
杀戮尖塔 sha lu jian ta
手柄 shou bing
联机 lian ji
```

已扩充到 **397 条**，覆盖：游戏名（塞尔达、宝可梦、艾尔登法环、黑神话悟空…）、
类型（开放世界、肉鸽、战棋…）、术语（存档、装备、暴击、仇恨…）、
硬件（手柄、摇杆、卡带…）、联网与性能（掉线、掉帧、分辨率…）。

> 生成主词库时，游戏词表里的词**一律提升到最高优先级**（默认权重 100000）——
> 即使它在 rime 词库里已存在。否则它会带着 rime 的低权重（常见 100）沉到 88 万条最后，
> 后续按权重取词时必定被漏掉。

#### 11.2 重新生成

```bat
python tools\mk_lexicon.py
```

#### 11.3 从 ALL.tsv 生成词典（闭环已打通）

新工具 **`tools/build_from_lexicon.py`** —— 以 `ALL.tsv` 为**唯一输入**：

```bat
python tools\build_from_lexicon.py
```

产出 `dist/abbr/njubase3-abbr-full.a`、`dist/multi/njubase1.a`、`dist/multi/njubase2.a`。
**以后加词、改拼音、调优先级，只编辑 `ALL.tsv` 再跑这一条命令**，不必再动各个 yaml。

```
lex/*.yaml + lex/game.txt  ── mk_lexicon.py ──>  lex/ALL.tsv
                                                      │
                                 build_from_lexicon.py ┘
                                      └─> njubase1 / njubase2 / njubase3
```

当前实测（**全部在安全体积内**）：

| 本 | 条目 | 大小 |
|---|---|---|
| `njubase3` | 203,093（130,000 词 + 56,700 简拼 + 原版并入） | **4.54 MB** |
| `njubase1` | 127,210 | **3.89 MB** |
| `njubase2` | 121,564 | **4.16 MB** |

三本合计 428,946 条；词库还剩 510,773 条未用（受每本体积上限限制）。

> ⚠️ **base3 的词数必须压住**（`--base3-words` 默认 130,000）。
> 合并原版条目后体积涨得比预期快：试过 150,000 → **5.06 MB（会挂）**、140,000 → 4.79 MB（风险区间）、
> **130,000 → 4.54 MB（安全）**。已知失败点约 4.92 MB。

---

### 12. `.nro` 插件形式（主机端一键装 / 卸）

**能 —— 工程已经在 `nro/`（HexDict）。** 它把「插读卡器 + 电脑 + 拖文件」变成「hbmenu 里按一个键」。

#### 12.1 能做 / 不能做

**能做**：安装（**一次可写 1~3 本词典**）、卸载（删 overlay 子树，固件原版立即恢复，**NAND 从未改动**）、
切换、写入前后双校验（NJDC 结构 + CRC32）、一键重启。

**不能做**（重要，别期待）：
- ❌ **不能热生效** —— 词典加载由 `fs.mitm`（sysmodule）负责，`.nro` 只能**写文件**。
  装完要让 swkbd 重新打开词典（关掉键盘再开；保守做法是重启）。
- ❌ **开机时不要按住 L** —— Atmosphere 默认覆盖键就是 L，按住会**关掉** LayeredFS
  （表现就像完全没生效）。

#### 12.2 三个包（按 A / B / X 切换）

| 键 | 包 | 内容 | 体积 |
|---|---|---|---|
| **A** | **MULTI** | njubase1 + njubase2 + njubase3，约 **411,000 词** | 4.28 + 4.42 + 4.64 MB |
| B | ABBR | 仅 njubase3（150,000 词 + 58,000 简拼） | 4.64 MB |
| X | LITE | 仅 njubase3（80,000 条） | 1.83 MB |

其它键：`L` 从 SD 装自定义、`Y` 卸载、`-` 重启、`+` 退出。

> 安装**任一**包前都会先清掉 `njubase1/2/3` 三个目标（双编码各一次），
> 避免「先装多本、后装单本」留下混合状态。

内嵌总量 **19.82 MB**。

#### 12.3 已构建：`nro/HexDict.nro`（20.03 MB）

```bat
cd nro
build.bat
```

产物 `nro/HexDict.nro`（21,004,288 B）。拷到 SD 卡 `sdmc:/switch/`，从 hbmenu 启动即可。

#### 12.4 devkitPro 的离线安装（本机 GitHub 不可达 → 绕过官方安装器）

官方安装器托管在 GitHub，而本机 `github.com` 不通。解决办法是
**直接从 pacman 包仓库下载 `.pkg.tar.zst` 并解压**（脚本 `tools/install_devkitpro.py`）：

```bat
pip install zstandard
python tools/install_devkitpro.py
```

几个要点：
- 仓库索引：`.../packages/windows/x86_64/dkp-windows.db`、`.../packages/dkp-libs.db`
  （目录列表不开放，必须走 `.db`）；
- 包内是 msys 根布局 → 解压得到 `<root>/opt/devkitpro/...`，因此
  **DEVKITPRO 要设为 `C:/devkitPro/opt/devkitpro`**；
- **`devkitA64/base_rules` 不在任何 pacman 包里** —— 来自 GitHub 仓库 `devkitPro/devkitA64-rules`
  （`codeload.github.com` 可达）；
- **newlib 头文件是独立包** `devkita64-newlib`，`devkita64-gcc` 并不含（缺它会报 `stdint.h` 找不到）；
- 本机没有 `make`，用 Qt 自带的 `mingw32-make`（`build.bat` 会自动回退）。

**不需要 devkitPro 也能验证**：`check-pc.bat` 做语法检查 + 校验器回归，当前两项均通过。

---

### 13. 手动替换包（不依赖 .nro，直接拷 SD 卡）

如果 `.nro` 在机器上跑不起来，或你更习惯手动替换，用这两个包。
**解压后把里面的 `atmosphere` 文件夹整个拷到 SD 卡根目录**（已有则"合并/覆盖"）。

| 包 | 内容 | 体积（zip / 展开） | 适用 |
|---|---|---|---|
| **`dist/manual-multi.zip`** | njubase1 + njubase2 + njubase3，约 **372,000 词** + 56,700 简拼 | 10.4 MB / 26.4 MB | ★ 主推 |
| `dist/manual-abbr.zip` | 仅 njubase3（130,000 词 + 56,700 简拼） | 3.7 MB / 9.5 MB | 三本不行时的降级方案 |

**两个包都同时覆盖 `GB18030/` 和 `GB2312/` 两套编码目录** —— 无论设备当前用哪套都会生效。

装完后的路径：

```
<SD>:\atmosphere\contents\0100000000000805\romfs\Iwnn\ZH\CN\pinyin\
    GB18030\njubase1.a   4.28 MB
    GB18030\njubase2.a   4.42 MB
    GB18030\njubase3.a   4.64 MB
    GB2312\njubase1.a    4.28 MB
    GB2312\njubase2.a    4.42 MB
    GB2312\njubase3.a    4.64 MB
```

**生效**：关掉屏幕键盘再打开；不行就重启。**开机不要按住 L。**

**验证**：打 `shalujianta` → 「杀戮尖塔」；打 `sljt` → 同样出「杀戮尖塔」（简拼只有装了词典才有）。

**卸载**：删掉 `atmosphere\contents\0100000000000805\` 整个文件夹，固件原版立即恢复（不动 NAND）。

> ⚠️ 若从三本版换到单本版，**先删掉 `pinyin/` 两个编码目录里的 `njubase1.a` 与 `njubase2.a`**，
> 否则会留下「多本 + 单本」的混合状态。包内 `README.txt` 也写了这些。


---

## swkbd（0100000000001008）技术侦察报告

- 日期：2026-09-27
- 目标机：Switch 固件 **22.5.0** ＋ Atmosphere 1.11.2 ＋ emuMMC（file-based，SD00）
- 侦察方式：**纯离线解析固件 NCA**（不动主机、不联网）
- 报告口径：标「已验证」的项均有本次实测证据；本版**推翻了前一版的多处错误结论**，见 §7

---

### 0. 一句话结论

swkbd 是一个**纯输入界面**，不是一个输入法。它内部**没有任何词典数据**，也**不支持中文输入**。
用户感受到的三个痛点，「按键位置」理论可改（需重度工具链），「联想质量」不可改，「缺游戏词库」——**没有词库可换，因为它本来就没有**。

---

### 1. 数据来源（全部来自实机，非模拟器）

| 来源 | 路径 | 说明 |
| --- | --- | --- |
| SD 卡全量备份 | `F:/NSbackup/20260927/`（184 GB） | 我 2026-09-27 实机备份 |
| 固件包 | `F:/NSbackup/20260927/AMS-22.5.0/`（238 个 NCA） | 实机 SD 卡上的升级包 |
| FTP 副本 | `192.168.2.122:5000` → `/sdmc:/AMS-22.5.0/` | 与本地固件包**同一份**（已逐字节比对） |
| 密钥 | `F:/NSbackup/20260927/switch/prod.keys`（231 项） | 实机 Lockpick 导出；与另一份下载版**逐字节一致** |

> 前一版报告使用的 `F:/NSbackup/原文件/` 已被清除。本版全部结论基于上述实机来源。

---

### 2. 已验证：emuMMC raw NAND 不可直接解析

| 区域 | 状态 |
| --- | --- |
| LBA 0–33（MBR + GPT） | **明文**，成功解出 11 个分区 |
| PRODINFO | 密文（正常，该分区本身加密） |
| SAFE / SYSTEM / USER 头部 | **密文，4KB 熵 5.90** |
| SYSTEM 分区末尾扇区 | 全 0（未写入区域未加密） |

**判据**：SYSTEM 与 USER 分区的头 32 字节**完全相同**，说明存在按「分区内扇区号」做 tweak 的逐扇区加密，而未写入扇区保持全 0。
这既非原始 eMMC 明文（否则可直接读 FAT），也非全盘加密。

> 结论：**走 NAND raw 提取系统 title 的路线不通**（需 per-console 密钥，而 PRODINFO 本身也是密的）。
> 可行路径是**固件包**——它的 NCA 只受 NCA 层加密，与 NAND 分区加密无关。

分区表（供参考）：PRODINFO / PRODINFOF / BCPKG2-1..6 / SAFE / **SYSTEM(2684MB)** / USER(27917MB)。

---

### 3. 已验证：NCA 解密链路（本次打通）

本机无 hactool，自研实现。**所有参数以 hactool 源码为准**（`nca.c` / `nca.h` / `utils.h` / `aes.c`），不靠猜测：

| 项 | 正确做法 | 我踩过的坑 |
| --- | --- | --- |
| 头部解密 | 前 `0xC00` 字节整体 AES-XTS，tweak = BE(sector)，**sector 从 0 起** | 曾误以为 magic 在文件 `0x200` |
| `media_to_real` | `MEDIA_SIZE(0x200) * block`，**不加 0xC00** | 多加 0xC00 导致末段越界 |
| section 偏移 | FS header 在 header 块内 `0x400 + i*0x200`，section 数据区**不含** FS header | 曾把数据区开头当 `PFS0` magic（错） |
| **key index** | `max(0x206, 0x220) - 1` | 直接用 `0x220` 会**差一代**，这是最初解不开的主因 |
| key area | `AES-ECB-Dec(key_area_key_<name>_<idx>, encrypted_keys[4][0x10])` | — |
| data key | **固定 `decrypted_key_area[2]`**（CRYPT_CTR） | — |
| CTR IV | `reverse(section_ctr[0:8]) ∥ BE(section_offset >> 4)` | 这是**双段拼接**，任何单一猜测都命中不了 |
| CTR 递增 | 128 位**大端**计数器 | — |

**关键推论**：swkbd 的 `0x220 = 0x16` → key index `0x15` → 用 `key_area_key_application_15`。
而这份 keyset **恰好覆盖到 `_15`**（没有 `_16`），所以 swkbd 可以解开。

---

### 4. 已验证：swkbd 的文件构成

| 项 | 值 |
| --- | --- |
| titleId | `0100000000001008` |
| NCA 文件 | `c65a992ef0d3b7c3e5fd1daecb63c6b0.nca` |
| NCA 大小 | 3,848,192 B |
| key generation | `0x220 = 0x16`（`0x206 = 2`） |
| kaek_index | 0（application） |

**ExeFS（PFS0）3,215,872 B —— 只有 2 个文件：**

```
main          3,207,722 B    ← 全部代码
main.npdm         1,316 B    ← 元数据
```

**RomFS 629,248 B** —— 47 个文件，见 §5。

> ⚠️ 前一版报告称「ExeFS 629 KB / RomFS 3.2 MB，资源占 83%」——**完全反了**，实际是 **ExeFS 3.22 MB / RomFS 629 KB**。

---

### 5. 已验证：RomFS 完整文件树（47 项 / 542,852 B）

```
common/agl/agl_resource_min.Nin_Nx_NVN.release.sarc.szs          16252 B
common/lyt/CtrlDefaultAnimTable.xml                              5014 B
common/sead/primitive_renderer/primitive_drawer_nvn_shader.bin   7168 B
common/shader/VarietyOceanShader_Nx.arc.szs                     42516 B
lyt/50on.szs                                                    22035 B   ← 日文 50 音布局
lyt/Numeric.szs                                                 13893 B
lyt/Qwerty.szs                                                  25174 B   ← QWERTY 布局
lyt/Sign.szs                                                    21154 B
lyt/Swkbd.szs                                                   27081 B
lyt/common.szs                                                  33134 B
message/CNzh/common.msbt.szs                                     4535 B
message/CNzh/swkbd.msbt.szs                                      1463 B
...（16 种语言 × common + swkbd，共 32 个 msbt）
message/Ocean.msbp.szs                                           3603 B
sound/swkbd.bfsar                                              180796 B
sound/swkbd_action.bksnd                                        39124 B
sound/swkbd_event.bksnd                                            72 B
sound/swkbd_module.bksnd                                         3925 B
```

**结构判读**：

| 目录 | 内容 | 性质 |
| --- | --- | --- |
| `common/agl`、`common/shader`、`common/sead` | AGL 图形库、NVN 着色器、sead UI 库 | 纯渲染资源 |
| **`lyt/`** | **键盘布局**（Qwerty / 50on / Numeric / Sign / Swkbd / common） | **痛点①的落点** |
| `message/<16语言>/` | UI 文本表（msbt） | 纯标签，**无词典** |
| `sound/` | 按键音效 | — |

**格式已验证**：`.szs` = **Yaz0 压缩的 SARC 归档**；`.msbt` = `MsgStdBn` UTF-16 文本表。

#### 5.1 中文 UI 文本表实测内容

`message/CNzh/swkbd.msbt` —— **50 条，全部是 UI 标签**：

```
空格 / OK / 换行 / 确定
QWERTY / AZERTY / QWERTZ / QZERTY
English (US) / Français / Deutsch / Italiano / Nederlands / Português / Русский
日本語　ローマ字入力 / 日本語　50音（横並び・左から・右から）
符号 / 选择键盘 / 查看输入的文字 / 大写 / 大写锁定 / 小写 / 输入 / 退出 / 关闭
```

`message/CNzh/common.msbt` —— 171 条通用 UI 文本（确定/取消/下一步/返回/初始化…）。

> **关键**：语言选择列表 = **16 种西文布局 + 4 种日文布局**，**没有中文、没有韩文**。
>
> 即：**swkbd 的中文界面是有的，但中文输入能力不存在。**

---

### 6. 已验证：main 里也没有词典

对 `main`（3,207,722 B）做字符串与编码统计：

| 检测 | 结果 | 判读 |
| --- | --- | --- |
| 整体熵 | 6.99 | 编译代码 |
| UTF-16 CJK 连续长度 | runs=259,949，**mean=1.22**，直方图 1:220304 / 2:29130 / 3:7297 / 4:1822 | **几何衰减 = 随机噪声**（真实词典会有大量 2–4 字 run） |
| UTF-8 CJK 连续长度 | runs=390，**max=2，≥3 的 = 0** | 无中文串 |
| `你好/中文/输入/选择/键盘/候选/联想` | UTF-8 与 UTF-16 **全为 0** | 无中文词表 |
| `zhong/nihao/zhongguo/shuru/hanzi` | 全为 0 | 无拼音表 |

**main 里确实存在的相关符号**（说明「有代码，无数据」）：

```
D:\home\jenkins\workspace_slave\release_22NUP\app\swkbd\rom\NX64\   ← 构建路径
_ZN2nn2ro6detail15g_pAutoLoadListE                                  ← nn::ro SDK
nn::swkbd::  nn::atk::detail  guiKeyInputManager::update()
KeyboardPredict          ← 联想/预测模块
_Candidatej  Common_Enter_ConfirmCandidat   ← 候选词 UI
SwkbdAddKeytop_USFrench  LayoutKeyTopBase   ← 键帽
N2nn4font12ScalableFont  font_Buildin  LazyFontPane                 ← 字体
nvnWindowBuilderSetTextures / GROUP_KSND / sead::MainThread         ← NVN / KSND / sead
```

> 即：swkbd 具备**联想与候选词的代码框架**，但**不含任何词条数据**。
> 候选词只能来自**调用方游戏传入**（`KeyboardConfig.UserDictionary*`）或**用户历史词典**。

---

### 7. 本次推翻的前版错误结论

| 前版说法 | 实际 | 影响 |
| --- | --- | --- |
| 「ExeFS 629 KB / RomFS 3.2 MB，资源占 83%」 | **ExeFS 3.22 MB / RomFS 629 KB** | 资源侧「低成本改造」的前提**不成立** |
| 「固件 7.0.0 起内置中文 IME（注音/仓颉/速成/拼音）」 | **本固件 swkbd 无任何中文输入布局与词典** | 中文输入方案需重新设计 |
| 「只有『缺游戏词库』可能有低成本落点」 | **无词库文件可替换** | 该落点不存在 |
| 数据源：`F:/NSbackup/原文件/` | 已废弃，改用实机 SD 全量备份 + FTP | — |

---

### 8. 三痛点可改性判定（结论）

| 痛点 | 判定 | 依据 | 成本 |
| --- | --- | --- | --- |
| ① 按键位置不好 | **理论可改，工程很重** | 布局在 `lyt/*.szs`（Yaz0+SARC+bflyt 二进制 UI 格式），可 LayeredFS 替换 | 需 Yaz0 编码器 + SARC 打包 + bflyt 编辑器（SwitchLayoutEditor/Switch-Toolbox 量级）+ 实机回归 |
| ② 联想功能不行 | **不可改** | 联想逻辑编译在 `main` 内；无语言模型，只有用户历史词典 | — |
| ③ 没有游戏词库 | **无可换之物** | swkbd 无任何词典数据（RomFS 与 main 均已证实） | — |

**额外事实**：swkbd **不支持中文输入**。用户的「难用」感受，本质是「连中文输入都没有」。

---

### 9. 第三方输入法路线可行性

| 路线 | 结论 | 硬约束 |
| --- | --- | --- |
| sysmodule 做 am 层 mitm | **只能改参数，造不出输入法** | appletAE 的 Open*Proxy 命令**对 sysmodule 不可用**，无法代替游戏发起 swkbd 调用 |
| LayeredFS 替换 swkbd 本体 | **唯一能交付真输入法的路** | 工作量数人月；swkbd 崩溃 → **全系统键盘失效** |
| 零开发替代 | 改系统语言 + 实测目标游戏的实际可输入集 | 受调用方 `KeyboardConfig` 限制 |

**先例**：uLaunch（开源重写 qlaunch，titleId `0100000000001000`，配套 uSystem/uMenu/uLoader/uManager、Pixie/Plutonium UI 库）。

---

### 10. 本工程工具清单（`tools/`）

| 工具 | 作用 |
| --- | --- |
| `nca.py` | NCA 头部 XTS 解密、FsEntry/FS header 解析 |
| `index_fw.py` | 本地固件包全量索引（批量解头部、定位 titleId） |
| `ftp_fwhdr.py` | 经 FTP 只拉 NCA 头部（3 KB/个）做索引 |
| `ftp_probe.py` | Switch DBI FTP 目录探测 |
| `nand.py` | emuMMC raw NAND 访问层（GPT + FAT32 只读） |
| `probe_entropy.py` | NAND 明/密文区域诊断 |
| `verify_keys.py` | prod.keys 内部自洽性审计 |
| `decrypt2.py` / `dump_nca.py` | 按 hactool 参数解密 section（**正确版**） |
| `hit`/`hunt.py` / `pin_key.py` / `crib_check.py` | 参数穷举与已知明文校验（定位 bug 用） |
| `romfs_auto.py` | 读 IVFC 层表 → 自动定位 RomFS 头 → 遍历文件树 |
| `romfs_dump.py` | **Yaz0 解压 + SARC 解析**（无终止符的正确实现） |
| `msbt_dump.py` | MSBT 文本表提取（UTF-16） |

**复用要点**：Yaz0 **没有结束标记**，`00 00` 是合法回引用（dist 1、重复上一字节）；误判为 EOF 会截断大多数流。

---

### 11. 尚未验证 / 下一步可做

1. **固件包其余 title 的内容普查**：目前只完整解析了 swkbd、MiiEdit(1009)、0100000000001009。其余 115 个 Program/Data title 可批量解密看有无 IME 数据。
2. **NAND SYSTEM 分区**：若能取得 per-console 密钥（PRAGMA 层），可核对实机 SYSTEM 分区与固件包是否一致。
3. **实机验证中文可输入集**：改系统语言 + 3~5 个游戏实测 swkbd 实际提供哪些输入模式。

---

## 证据链审查：词典大小上限到底是「单本」还是「三本总量」？

- 日期：2026-09-30
- 触发：我质疑「感觉是按三本总大小来的」
- 结论：**质疑成立。「每本有独立预算」这一结论缺乏实验支撑；现有全部数据同时兼容
  「单本上限」与「总量上限」两种假设，无法区分。**

---

### 1. 被审查的结论

工程在 §18.1 给出：

> `[17] njb1probe`（只替换 `njubase1.a`、不动 njubase3，内塞独创词 `nbprobe`/`nbprobe2`）
> **实测成功** —— 独创词能被打出来。
>
> **⇒ ① 引擎会读取 `njubase1`；② 每本词典有各自独立的大小预算。**
> 这推翻了 §17.1 的悲观结论：单本上限约 4.6 MB，但**总容量是各本之和**。

由 ②推得 §18.3 的分片方案（三本各 ~4.x MB，总量 ≈ 13 MB），并成为当前
`04_Outputs/` 三本产物的全部立论基础。

### 2. 断点一：探针实验设计不支撑推论 ②

探针做的是「**把一个远小于上限的小词典放进 `njubase1`**」，它只能回答
「引擎会不会读 `njubase1`」。推论 ②（每本独立预算）要求的是
「**某本单独接近上限时仍能工作**」—— 探针**根本没有触及这个场景**。

探针场景的实际总量：

| 本 | 探针时的内容 | 大小 |
|---|---|---|
| `njubase1.a` | 原版 3,351 条 + 2 个独创词 | ≈ 90 KB |
| `njubase2.a` | 原版 | 91 KB |
| `njubase3.a` | **不动**（原版 1.6 MB，或当时的替换版） | 1.6 ~ 4.87 MB |
| `njtan.a` + `njcode.a` + `njexyomi.a` | 原版 | 266 KB |

**总量约 2.0 ~ 5.1 MB —— 从未逼近任何上限。** 所以「能打出探针词」在两种假设下
都成立，**不能作为区分证据**。

> 措辞演变值得注意：§17.3 写的是「每本**可能有**独立大小预算」（谨慎），
> 到 §18.1 变成「每本词典**有**各自独立的大小预算」（断言）——
> **中间没有增加任何新实验。**

### 3. 断点二：所有阈值实验都只动过 `njubase3` 一本

§15 的阈值实测（pad / abbr 系列）**全部只替换 base3**，base1/base2/njtan 等
始终是原版小文件。因此：

```
观测到的「失败点」= base3 文件大小
                  = 总量 − (base1 + base2 + njtan + njcode + njexyomi)
                  = 总量 − 447,417 B   ← 恒定偏移
```

**两个假设在数学上完全等价，这组数据永远无法区分它们。**

| 包 | base3 文件 | 其它本（原版） | 总量 | 结果 |
|---|---|---|---|---|
| `[1] full` | 4,025,516 | 447,417 | 4,472,933 | ✅ |
| `pad150-lite` | 4,425,516 | 447,417 | 4,872,933 | ✅ |
| **`[5] abbr-full`** | **4,865,870** | 447,417 | **5,313,287** | ✅ |
| **`abbr160`** | **5,163,826** | 447,417 | **5,611,243** | ❌ |
| `pad150-mid` | 5,225,516 | 447,417 | 5,672,933 | ❌ |
| `[7] big400` | 11,975,000+ | 447,417 | 12.4 MB+ | ❌ |

- 按**单本**解读：阈值 ∈ (4.866, 5.164) MB
- 按**总量**解读：阈值 ∈ (5.313, 5.611) MB

两组都是 (✅最高, ❌最低)，**同样自洽**。

### 4. 断点三：MULTI 包从未实机验证

`§18.5` 自己写着：

> **待验**：`[18]` 实机（能否正常出词 + 新本是否被读取）。

即「三本都是 4.x MB」这个配置**从未上过机**。而文档在 §12.2 / §13 已经把
MULTI 列为「★ 主推」「A 键」「411,000 词」——**属于未验证就先推荐**。

### 5. 风险量化

当前 `04_Outputs/` 实际大小：

| 文件 | 字节 |
|---|---|
| `njubase3.a` | 4,751,712 |
| `njubase1.a` | 4,077,346 |
| `njubase2.a` | 4,363,516 |
| **三本合计** | **13,192,574**（12.58 MB） |
| + 不动的 `njtan`/`njcode`/`njexyomi` | 265,757 |
| **引擎可见总量** | **≈ 13.46 MB** |

- 若「单本假设」为真 → 每本 4.0~4.75 MB 都在阈值内 → **可用**
- 若「总量假设」为真 → 13.46 MB ≈ 已知可用最大总量（5.31 MB）的 **2.5 倍** → **必然失败**

**两种假设给出完全相反的结果，且后果是「整个方案可用 / 完全不可用」。**

> 附加风险：部署说明要求 `GB18030/` 与 `GB2312/` **两套都放**。若引擎同时加载两套
> （§9.5 明确把「可能同时加载两套」列为待验证假设），总量还要**再翻一倍**。

### 6. 判别实验（两条，成本递增）

#### 实验 A —— 最小成本，直接检验「总量」假设 ★推荐先做

在**已验证可用**的配置上只加一点点：

1. 取 `[5] abbr-full`（base3 = 4,865,870，总 5.31 MB，**已实测可用**）；
2. 把 `njubase1.a` 换成一个**仅约 0.5 MB** 的包（远低于单本上限 4.6 MB）；
3. 新总量 ≈ 5.81 MB（base3 **一个字节都没动**）。

| 结果 | 推论 |
|---|---|
| ❌ 候选为空 | **总量是限制** —— 单本假设破产，MULTI 方案作废 |
| ✅ 正常出词 | 总量不是限制 → 支撑单本假设（但仍需实验 B 确认） |

这个实验的干净之处：**唯一的变量是"总量"，而加进去的那本远小于单本上限**。

#### 实验 B —— 交付物本身（终局判据）

直接实机跑当前 `04_Outputs/` 三本（总 13.46 MB）：

- ✅ → 总量上限 > 13.46 MB，「总量假设」被证伪，MULTI 方案成立
- ❌ → MULTI 方案作废，必须退回单本（只能交付 `njubase3.a` 一本 ≈ 4.53 MB）

#### 配套：单编码 vs 双编码

顺带验证 §9.5 的悬置假设 —— **只放 `GB18030/`** 装一次，与**两套都放**再做对比。
若两者表现相同，说明引擎只加载一套，部署说明应简化。

### 7. 建议

1. **暂停把 MULTI 当既有结论使用**。`README.md` / `大词库说明.md` 里
   「约 39 万词」「三本分担」的表述应加上「**未实机验证**」标注。
2. **先做实验 A**（成本低，一次判定方向），再上机跑实验 B。
3. `04_Outputs/` 目前的三本**不要**当作可用交付物；在验证通过前，
   实机可用版本仍以单本 `njubase3.a`（4.53 MB）为准。
4. 验证通过后，把 §18.1 的措辞从「每本有独立预算」改回
   「每本**可能**有独立预算，已由实验 A/B 确认/否证」。

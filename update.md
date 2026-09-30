# 更新说明

> 本文件内容取自 git 记录，与提交信息一致。查看原始记录：`git log` / `git tag -n`。

## v0.2

`v0.2 —— 游戏词扩充 + 内容清理 + 移除 nro`

【词库变更】
- 游戏词 393 -> 758 条（新增 game-words.txt + mk_game.py 自动注音）
- 删除 >6 字超长词：词源剔 37,649 条；原版并入时再跳 237 条
- 敏感词过滤：词源剔 327 条；原版并入时跳 33 条；白名单豁免 9 条
- 单字与生僻字按需求保留
- 产物 202,447 条 / 4,740,008 B，两个编码目录一致，重复条目 0

新增工具：
- 05_Code/tools/sensitive.py     敏感词过滤（核心库 + ≥3库交叉 + 表记精确匹配）
- 05_Code/tools/mk_game.py       游戏词自动注音（pypinyin）
- 01_Inputs/lex/game-words.txt   纯词游戏表

重要发现：公开敏感词库（Konsheng/Sensitive-lexicon）是「句子级上下文过滤」设计，
直接做词条级删除会命中 3,972 条正常词（制度/政府/网络/一个/土豆/几何…）。
已改为三层收窄：只用核心库 + 被 ≥3 库交叉标记 + 表记精确匹配，
同音词全部保住（因为/引起/银河/音色/邮件/小学/病毒）。

【产物不入库】
- 产物 .a 内含**并入的原版词典条目**（任天堂衍生版权内容），由 .gitignore 屏蔽：
    04_Outputs/**/*.a
- 产物改由使用者自行生成：跑 mk_lexicon.py + build_from_lexicon.py
- 本地文件保留，未被删除

【移除 nro 部分】
项目不再做 .nro（主机端安装器）：
- 删除 05_Code/nro/（80 MB）、10_Other/dkp-cache/（107 MB）、tools/install_devkitpro.py
- README 删除附录 A 的「HexDict」节（208 行）并清理相关引用
- 项目体积 429 MB -> 247 MB

【文档】
- 新增 update.md（版本更新说明，取自 git 记录）
- 新增 04_Outputs/update.md（给最终用户的通俗说明）
- 新增 02_References/LICENSES.md（第三方许可原文与版权声明）
- README 新增「第三方来源与许可」表，逐个给出仓库链接
- ⚠️ 修正一处许可标注错误：rime-ice 是 **GPL-3.0**，README 原写「MIT」
- 删除 README 中不实内容：早期 v1 侦察报告的「swkbd 不支持中文输入」为错误结论（已整节删除）；
  已失效的操作指南（dist/ 目录树、install-to-sd.bat、verify.bat、manual-*.zip）

入库范围：01_Inputs/sensitive/ 仍屏蔽（含政治内容，需自备 clone）。

---

## v0.1

`v0.1 —— Switch 中文输入法大词库（NJDC）`

解出 NJDC 词典格式，用 Atmosphere LayeredFS 覆盖 swkbd 词典数据，
给 Switch 系统输入法换上大词库 + 简拼（首字母联想）。

内容：
- 生成链：词源 -> 01_Inputs/lex/ALL.tsv -> 04_Outputs/<版本>/atmosphere/...
  三本分担（njubase1/2/3），产物直接铺成 SD 卡结构，整目录拷过去即可
- 目录按 01_Inputs / 02_References / 03_Documents / 04_Outputs / 05_Code / 10_Other 分类
- 说明文档全部整合进根 README.md（唯一说明文件）

⚠️ 未决：三本方案能否成立待实机验证 —— 见 README 的「判别测试包」一节。
   大小上限可能是「三本总量」而非「单本」，「每本独立预算」这一结论缺实验支撑。

按公网要求，以下内容不入库（见 .gitignore）：
  主机密钥 prod.keys · 原版固件词典 01_Inputs/firmware/dat08xx/
  含并入原版条目的产物 04_Outputs/**/*.a · nro 编译产物 · 10_Other/

---

## 备注（非 git 内容）

- **不再做 nro 部分**：`05_Code/nro/`（80 MB）与 devkitPro 相关文件已于 2026-09-30 全部删除，
  README 的 HexDict 节也已移除。项目现在只有 Python 工具链 + 词典产物。
- **产物不入库**：`04_Outputs/**/*.a` 内含**并入的原版词典条目**（任天堂衍生版权内容），
  已由 `.gitignore` 屏蔽，并已从 git 历史中清除。需要时自行运行生成脚本重新产出。
- **两个版本目录内容不同**（v0.1 曾被覆盖，已复原）：
  - `v0.1` = 202,702 条 / 4,751,712 B（**未做内容清理**，保留长词与敏感词）
  - `v0.2` = 202,447 条 / 4,740,008 B（**已清理**：游戏词 758、删长词、删敏感词）
  都是单本可用，**部署请用 `04_Outputs/v0.2/`**。
- **许可**：本工程**不是单一许可** —— rime-ice 词源为 GPL-3.0、
  Atmosphere 参考源码为 GPL-2.0、hactool 为 ISC、本工程原创部分保留所有权利。
  许可全文与映射表见 `LICENSES/`。

# 许可说明

**本工程不是单一许可。** 各内容按来源分别适用不同许可，下表说明「哪一部分 → 哪个许可 → 全文在哪」。

---

## 映射表

| 内容 | 位置 | 许可 | 版权与全文 |
|---|---|---|---|
| **本工程原创部分**<br>工具链脚本、文档、游戏词表 | `05_Code/tools/`<br>`README.md`、`update.md`<br>`01_Inputs/lex/game.txt`、`game-words.txt` | **保留所有权利**<br>（未授予使用许可） | 见下方「关于原创部分」 |
| 单字 / 常用词词源 | `01_Inputs/lex/ice_*.yaml`<br>`01_Inputs/lex/ALL.tsv`（由其派生） | **GPL-3.0** | 上游 [iDvel/rime-ice](https://github.com/iDvel/rime-ice)<br>全文：`GPL-3.0.txt` |
| LayeredFS 参考源码 | `02_References/atmosphere/` | **GPL-2.0** | Copyright (c) Atmosphère-NX<br>全文：`GPL-2.0.txt` |
| NCA / romfs 解密参考 | `02_References/hactool/` | **ISC** | Copyright (c) 2018, SciresM<br>全文：`ISC.txt` |
| 拼音标注依赖 | 运行时 `pip install pypinyin`，**不随库分发** | MIT | Copyright (c) mozillazg<br><https://github.com/mozillazg/python-pinyin> |
| 敏感词库 | `01_Inputs/sensitive/`，**不入库** | MIT | Copyright (c) Konsheng<br><https://github.com/Konsheng/Sensitive-lexicon> |

`02_References/LICENSES.md` 另有该目录的逐文件说明。

---

## 关于原创部分

本工程的原创内容（脚本、文档、游戏词表）**未附许可文件，即保留所有权利**。

这不是「使用 MIT 或 GPL」的意思——如需给他人在特定条件下使用的授权，
应显式添加许可文件。当前状态下**不授予**复制、修改、再分发的权利。

> 若要改为宽松许可（例如 MIT），在仓库根加 `LICENSE` 并在上表更新即可。

---

## ⚠️ 分发注意（重要）

本工程同时含 **GPL-3.0** 与 **GPL-2.0** 两类强著佐权内容，而这两个许可
**互不兼容**（GPL-2.0-only 与 GPL-3.0 无法合并为单一许可）。

由此产生的约束：

1. **不得**给整个工程打一个统一的宽松许可（如 MIT）——那会与 GPL 内容冲突。
2. 分发时必须**分别保留**各部分的许可与版权声明（本 `LICENSES/` 目录即为此准备）。
3. 若使用者想在此基础上以单一许可发布衍生作品，需先**剔除**不兼容的部分。
4. 上述约束**只影响分发行为**，不影响本地使用与研究。

> 本说明基于对各上游仓库许可文件的实查（2026-10-08），非法律意见。
> 涉及商业分发时请自行核实上游最新许可。

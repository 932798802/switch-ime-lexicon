# 本目录内容的许可

| 文件 | 来源 | 许可 |
|---|---|---|
| `ice_8105.yaml`、`ice_base.yaml`、`ice_ext.yaml` | [iDvel/rime-ice](https://github.com/iDvel/rime-ice) | **GPL-3.0** |
| `ALL.tsv` | 由上述 yaml + `game.txt` 生成（派生作品） | 受上游约束（GPL-3.0） |
| `game.txt`、`game-words.txt` | 本工程原创 | 保留所有权利 |

**GPL-3.0 全文**见仓库根目录的 `../../LICENSES/GPL-3.0.txt`。

---

## 分发要求

`ice_*.yaml` 与由它们派生的 `ALL.tsv` 受 **GPL-3.0** 约束：

- 分发这些文件时，必须同时提供 GPL-3.0 全文（本仓库已放在 `LICENSES/`）。
- 不得为它们附加限制性条款。
- 修改后分发需保留来源说明（本文件即承担该作用）。

⚠️ 本工程的 `02_References/atmosphere/` 使用 **GPL-2.0**，与 GPL-3.0
**互不兼容**——如需以单一许可发布衍生作品，须先剔除其中一方。
详见 `../../LICENSES/README.md`。

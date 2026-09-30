# 第三方来源与许可声明

本目录（`02_References/`）存放的是**为技术判定而摘录的第三方开源代码**，
不是本工程的原创作品。各来源的版权与许可如下。

> 用途说明：这些文件仅作为**格式解析与判定依据**被收录（例如 NCA/romfs 的
> 解密参数、LayeredFS 的覆盖路径构造逻辑）。本工程**不编译、不链接**这些代码。

---

## 1. hactool —— `02_References/hactool/`

- **来源**：<https://github.com/SciresM/hactool>
- **许可**：ISC License
- **版权**：Copyright (c) 2018, SciresM
- **收录文件**：`aes.c` `aes.h` `ivfc.c` `ivfc.h` `main.c` `nca.c` `nca.h`
  `nso.c` `nso.h` `romfs.c` `romfs.h` `types.h` `utils.c` `utils.h`

ISC 许可要求版权声明与许可声明随所有副本出现，故在此完整转载：

```
ISC License

Copyright (c) 2018, SciresM

Permission to use, copy, modify, and/or distribute this software for any
purpose with or without fee is hereby granted, provided that the above
copyright notice and this permission notice appear in all copies.

THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
```

---

## 2. Atmosphère-NX —— `02_References/atmosphere/`

- **来源**：<https://github.com/Atmosphere-NX/Atmosphere>
- **许可**：GNU General Public License v2.0（GPL-2.0）
- **版权**：Copyright (c) Atmosphère-NX
- **收录文件**：`amsmitm_fs_utils.cpp` `cfg_override.board.inc` `cfg_override.cpp`
  `fs_mitm_service.cpp` `fs_mitm_service.hpp` `fsmitm_layered_romfs_storage.cpp`
  `fsmitm_layered_romfs_storage.hpp` `fsmitm_module.cpp` `fsmitm_romfs.cpp`
  `fsmitm_romfs.hpp` `ldr_content_management.cpp` `ldr_ro_manager.cpp`

这些文件的原许可头（各文件开头均保留）声明：

> This program is free software; you can redistribute it and/or modify it
> under the terms and conditions of the GNU General Public License,
> version 2, as published by the Free Software Foundation.

GPL-2.0 完整文本：<https://www.gnu.org/licenses/old-licenses/gpl-2.0.html>

---

## 3. 本目录之外引用的第三方内容

| 内容 | 位置 | 来源 | 许可 |
|---|---|---|---|
| 单字 / 常用词词源 | `01_Inputs/lex/ice_*.yaml` | [iDvel/rime-ice](https://github.com/iDvel/rime-ice) | GPL-3.0 |
| 敏感词库（不入库） | `01_Inputs/sensitive/` | [Konsheng/Sensitive-lexicon](https://github.com/Konsheng/Sensitive-lexicon) | MIT |
| 拼音标注（运行时依赖） | `05_Code/tools/mk_game.py` | [mozillazg/python-pinyin](https://github.com/mozillazg/python-pinyin) | MIT |

---

## 4. 许可兼容性提示

本工程同时涉及 **GPL-3.0**（rime-ice）与 **GPL-2.0**（Atmosphère-NX）两类
强著佐权（copyleft）许可，且二者**互不兼容**。

- 上述约束只影响**分发行为**（公网发布 / 打包分发），不影响本地自用与研究。
- 若要以单一许可对外发布整个工程，需先决定处理方式：剔除相关第三方内容，
  或分别按各自许可分发。**不要**在未处理的情况下打上统一的宽松许可（如 MIT）。
- 许可证在评估中，如有疑问请以上游仓库的实际许可文件为准。

# -*- coding: utf-8 -*-
"""install_devkitpro.py —— 不依赖官方安装器，直接装 devkitPro。

背景
----
devkitPro 官方安装器托管在 **GitHub**（本机 `github.com` / `objects.githubusercontent.com`
均不可达），但它的 **pacman 包仓库 `pkg.devkitpro.org` 是通的**。
所以这里直接从仓库下载 pacman 包（`.pkg.tar.zst`）并解压 —— 等价效果，不碰 GitHub。

装什么（switch 开发的最小集）
----------------------------
  devkitpro-keyring   签名环
  devkit-env          环境变量脚本
  devkita64-binutils  aarch64 binutils
  devkita64-gcc       aarch64 GCC（最大的一个，约 94 MB）
  switch-tools        elf2nro / nacptool 等（产出 .nro 必需）
  libnx               Switch 的 C 运行时库

用法：  python tools/install_devkitpro.py   [--root C:/devkitPro]

解压注意事项
------------
pacman 包里可能含 **符号链接/硬链接**（Windows 包里偶发）。Windows 下不能直接建符号链接，
这里对 `islnk()` 尝试按普通文件写出内容，`issym()` 则跳过并记录（通常不影响编译）。
"""
import argparse
import io
import os
import sys
import tarfile
import urllib.request

try:
    import zstandard
except ImportError:
    sys.exit("缺少 zstandard：请先 pip install zstandard")

BASE_WIN = "https://pkg.devkitpro.org/packages/windows/x86_64/"
BASE_LIB = "https://pkg.devkitpro.org/packages/"

PKGS = [
    ("devkitpro-keyring-20241017-2-any.pkg.tar.zst", BASE_WIN),
    ("devkit-env-1.0.1-2-any.pkg.tar.zst", BASE_WIN),
    ("devkita64-binutils-2.46.0-1-x86_64.pkg.tar.zst", BASE_WIN),
    ("devkita64-gcc-16.1.0-1-x86_64.pkg.tar.zst", BASE_WIN),
    ("switch-tools-1.13.1-1-x86_64.pkg.tar.zst", BASE_WIN),
    ("libnx-4.12.0-1-any.pkg.tar.zst", BASE_LIB),
    # newlib: the aarch64 C headers (stdint.h etc). gcc alone does NOT ship them,
    # and without it the build dies on "#include_next <stdint.h>".
    ("devkita64-newlib-4.6.0.20260123-4-any.pkg.tar.zst", BASE_LIB),
    # NOTE: base_rules / base_tools come from devkitPro/devkitA64-rules on GitHub
    # (codeload is reachable); they are fetched by install_devkitpro_rules.py.
]

CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".cache", "dkp")


def download(url, dst):
    """用 curl 下载 —— urllib 会被包服务器以 403 拒绝（缺浏览器头）。"""
    import subprocess
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    if os.path.isfile(dst) and os.path.getsize(dst) > 0:
        print("    复用缓存 %s (%d B)" % (os.path.basename(dst), os.path.getsize(dst)))
        return dst
    print("    下载 %s ..." % os.path.basename(dst))
    r = subprocess.run(["curl", "-sL", "--max-time", "1800", "-o", dst, url],
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if r.returncode != 0 or not os.path.isfile(dst) or os.path.getsize(dst) == 0:
        raise RuntimeError("下载失败 rc=%d : %s\n%s" % (r.returncode, url,
                                                       r.stdout.decode("utf-8", "replace")))
    print("    完成 %d B" % os.path.getsize(dst))
    return dst


def unpack(zst_path, root):
    with open(zst_path, "rb") as f:
        raw = zstandard.ZstdDecompressor().stream_reader(f).read()
    t = tarfile.open(fileobj=io.BytesIO(raw))
    n_file = n_link = n_skip = 0
    for m in t.getmembers():
        if m.name.startswith("."):          # .PKGINFO / .MTREE / .BUILDINFO 等元数据
            n_skip += 1
            continue
        if m.issym():
            n_link += 1                     # Windows 下不建符号链接
            continue
        try:
            t.extract(m, root)
            n_file += 1
        except Exception as e:
            print("      !! 解压失败 %s (%s)" % (m.name, e))
    return n_file, n_link, n_skip


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="C:/devkitPro")
    a = ap.parse_args()

    root = a.root.replace("\\", "/")
    os.makedirs(root, exist_ok=True)
    print("安装目标：%s\n" % root)

    for fn, base in PKGS:
        print("  [%s]" % fn)
        p = download(base + fn, os.path.join(CACHE, fn))
        nf, nl, ns = unpack(p, root)
        print("    解压 %d 个文件（跳过链接 %d / 元数据 %d）\n" % (nf, nl, ns))

    print("=== 校验关键文件 ===")
    # packages are laid out relative to an msys root: <root>/opt/devkitpro/...
    P = "opt/devkitpro/"
    checks = [
        P + "devkitA64/bin/aarch64-none-elf-gcc.exe",
        P + "devkitA64/bin/aarch64-none-elf-ld.exe",
        P + "devkitA64/base_rules",
        P + "tools/bin/elf2nro.exe",
        P + "libnx/lib/libnx.a",
        P + "libnx/include/switch.h",
        P + "devkitA64/aarch64-none-elf/include/stdint.h",
    ]
    ok = True
    for rel in checks:
        p = os.path.join(root, rel.replace("/", os.sep))
        hit = os.path.isfile(p)
        ok = ok and hit
        print("  %-46s %s" % (rel, "OK" if hit else "MISSING"))
    print()
    if ok:
        print("devkitPro 就绪。")
        return 0
    print("!! 有关键文件缺失，请检查上面的输出。")
    return 1


if __name__ == "__main__":
    sys.exit(main())

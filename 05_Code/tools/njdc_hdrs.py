# -*- coding: utf-8 -*-
"""njdc_hdrs.py —— 批量 dump 所有 NJDC/NJAD 词典的头部字段，找布局差异。"""
import os
import glob
import sys

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..",
                    "..", "01_Inputs", "firmware", "dat0805", "files", "Iwnn", "ZH", "CN", "pinyin", "GB18030")

FIELDS = ["04", "08", "0c", "10", "14", "18", "1c", "20", "24", "28",
          "2c", "30", "34", "38", "3c", "40", "44", "48", "4c", "50",
          "54", "58", "5c"]


def main():
    files = sorted(glob.glob(os.path.join(BASE, "*")))
    hdrs = {}
    for f in files:
        name = os.path.basename(f)
        b = open(f, "rb").read()
        magic = b[0:4].decode("ascii", "replace")
        row = {"name": name, "size": len(b), "magic": magic}
        for k in FIELDS:
            off = int(k, 16)
            if off + 4 <= len(b):
                row[k] = int.from_bytes(b[off:off + 4], "big")
        hdrs[name] = row

    print("file            size      magic " + " ".join("%8s" % k for k in FIELDS))
    for name in sorted(hdrs):
        r = hdrs[name]
        print("%-14s %9d %s " % (name, r["size"], r["magic"]) +
              " ".join("%8d" % r.get(k, -1) for k in FIELDS))

    # 派生关系
    print("\n--- 派生量 ---")
    print("%-14s %10s %10s %10s %10s %10s %10s %10s" %
          ("file", "0x0c+0x30", "filesize", "N(0x50)", "0x20", "0x24", "0x28", "0x10"))
    for name in sorted(hdrs):
        r = hdrs[name]
        if r["magic"] != "NJDC":
            continue
        print("%-14s %10d %10d %10d %10d %10d %10d %10d" %
              (name, r.get("0c", -1) + r.get("30", 0), r["size"], r.get("50", -1),
               r.get("20", -1), r.get("24", -1), r.get("28", -1), r.get("10", -1)))


if __name__ == "__main__":
    main()

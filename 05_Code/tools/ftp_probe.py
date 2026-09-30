#!/usr/bin/env python3
"""Probe the Switch DBI FTP server to see what is actually exposed.

Switch-side DBI mounts several virtual roots. We want to find the REAL
firmware NCAs (system partition), not a Yuzu/Ryujinx emulator dump.

Usage:
    python ftp_probe.py                      # list roots + 1 level
    python ftp_probe.py <path> [depth]       # list a subtree
    python ftp_probe.py --find <pattern>     # recursive name search from root
"""
import ftplib
import sys
import time

HOST = "192.168.2.122"
PORT = 5000
USER = ""
PASS = ""

ROOTS = ["sdmc:", "album_nand:", "album_sd:", "games:", "nand:", "system:"]


def connect():
    f = ftplib.FTP()
    f.connect(HOST, PORT, timeout=20)
    f.login(USER, PASS)
    f.set_pasv(True)
    return f


def ls(f, path="", timeout=25):
    """Return raw lines from LIST. Handles the DBI quirk where cwd to a root
    then LIST works, but nested roots do not."""
    lines = []
    try:
        if path:
            f.cwd(path)
        f.retrlines("LIST", lines.append)
    except ftplib.error_perm as e:
        return None, str(e)
    except Exception as e:
        return None, "%s: %s" % (type(e).__name__, e)
    return lines, None


def parse(line):
    """Very loose Unix-listing parse -> (kind, size, name). kind in d/-/?"""
    if not line or line.startswith("total"):
        return None
    kind = line[0] if line[0] in "d-l" else "?"
    rest = line[1:].split(None, 8)
    if len(rest) < 9:
        return kind, None, line.strip()
    size = rest[4] if rest[4].isdigit() else None
    return kind, size, rest[8]


def main():
    t0 = time.time()
    f = connect()
    print("connected:", f.getwelcome())

    if len(sys.argv) > 1 and sys.argv[1] == "--find":
        pat = sys.argv[2].lower()
        hits = []

        def walk(path, depth):
            if depth > 4:
                return
            lines, err = ls(f, path)
            if lines is None:
                return
            for ln in lines:
                p = parse(ln)
                if not p:
                    continue
                kind, size, name = p
                full = (path + "/" + name) if path else name
                if pat in name.lower():
                    hits.append((full, kind, size))
                if kind == "d" and len(hits) < 400:
                    walk(full, depth + 1)
                    try:
                        f.cwd(path) if path else f.cwd("/")
                    except Exception:
                        pass

        for r in ROOTS:
            walk(r, 0)
            try:
                f.cwd("/")
            except Exception:
                pass
        print("matches for %r: %d" % (pat, len(hits)))
        for h in hits[:200]:
            print("  %s  [%s] %s" % (h[0], h[1], h[2]))
        print("elapsed %.1fs" % (time.time() - t0))
        return 0

    if len(sys.argv) > 1:
        target = sys.argv[1]
        depth = int(sys.argv[2]) if len(sys.argv) > 2 else 1
        lines, err = ls(f, target)
        print("LIST %s -> %s" % (target, err or "%d entries" % len(lines or [])))
        for ln in (lines or []):
            print("   ", ln)
        return 0

    for r in ROOTS:
        lines, err = ls(f, r)
        if lines is None:
            print("== %-14s -> %s" % (r, err))
            continue
        print("== %-14s -> %d entries" % (r, len(lines)))
        kids = [parse(x) for x in lines]
        kids = [k for k in kids if k]
        for kind, size, name in kids[:60]:
            print("     %s %-10s %s" % (kind, size or "", name))
        if len(kids) > 60:
            print("     ... +%d more" % (len(kids) - 60))
        try:
            f.cwd("/")
        except Exception:
            pass
    print("elapsed %.1fs" % (time.time() - t0))
    return 0


if __name__ == "__main__":
    sys.exit(main())

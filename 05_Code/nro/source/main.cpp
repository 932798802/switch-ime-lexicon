/*
 * HexDict —— Nintendo Switch 中文输入法（swkbd / OMRON iWnn）词典管理器
 * ---------------------------------------------------------------------------
 * 作用：把本工程生成的 NJDC 大词库，一键装到
 *
 *        sdmc:/atmosphere/contents/0100000000000805/romfs/Iwnn/ZH/CN/pinyin/
 *              {GB18030,GB2312}/njubase3.a
 *
 *        （= Atmosphere LayeredFS overlay），并支持一键卸载还原。
 *
 * 为什么需要它：
 *   overlay 方案唯一的软肋是「出问题得拔卡才能救回来」。本程序把
 *   「插读卡器 + 电脑 + 拖文件」变成「hbmenu 里点一下」，且**随时可卸载还原**，
 *   爆炸半径从「拆机」降到「按一个键」。
 *
 * 它不能做什么（重要）：
 *   词典加载是 fs.mitm（sysmodule）在做的，swkbd 打开词典后索引已建在内存。
 *   .nro 只能**写文件**，不能热接管加载 —— 装完仍需让 swkbd 重新打开词典
 *   （关掉键盘再开；保守做法是重启主机）。详见 README。
 *
 * 界面语言为 ASCII：libnx 内置点阵字体不含 CJK 字形，中文会显示成乱码。
 */

#include <switch.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>

#include "embed_meta.h"
#include "njdc_check.h"

extern "C" {
    /* 多本分担：MULTI 包一次写三本；FULL / LITE 只写 njubase3.a */
    extern const unsigned char kMulti0[], kMulti0End[];
    extern const unsigned char kMulti1[], kMulti1End[];
    extern const unsigned char kMulti2[], kMulti2End[];
    extern const unsigned char kFull0[],  kFull0End[];
    extern const unsigned char kLite0[],  kLite0End[];
}

/* ------------------------------------------------------------------ */
/* 常量                                                                */
/* ------------------------------------------------------------------ */

#define DICT_TITLE_ID   "0100000000000805"
#define OVERLAY_ROOT    "/atmosphere/contents/" DICT_TITLE_ID "/romfs/Iwnn/ZH/CN/pinyin"
#define GB18030_PATH    OVERLAY_ROOT "/GB18030/njubase3.a"
#define GB2312_PATH     OVERLAY_ROOT "/GB2312/njubase3.a"
#define CUSTOM_FS_PATH  "/switch/hexdict/njubase3.a"
#define CUSTOM_SD_PATH  "sdmc:/switch/hexdict/njubase3.a"

/* 可能被写入的目标文件名（多本分担后不再只有 njubase3 一个） */
static const char *const kTargets[] = { "njubase1.a", "njubase2.a", "njubase3.a" };
#define NTARGETS 3

/* 拼接完整的 overlay 路径：<root>/<enc>/<name> */
static void dictPath(char *out, size_t n, const char *enc, const char *name) {
    snprintf(out, n, "%s/%s/%s", OVERLAY_ROOT, enc, name);
}

/* ------------------------------------------------------------------ */
/* 词典包                                                              */
/* ------------------------------------------------------------------ */

typedef struct {
    const char             *target;   /* "njubase1.a" 等 */
    const unsigned char    *data;
    const unsigned char    *end;
} DictFile;

typedef struct {
    const char    *label;
    int            nfiles;
    const DictFile *files;
} DictPack;

static const DictFile g_multiFiles[] = {
    { "njubase1.a", kMulti0, kMulti0End },
    { "njubase2.a", kMulti1, kMulti1End },
    { "njubase3.a", kMulti2, kMulti2End },
};
static const DictFile g_fullFiles[] = {
    { "njubase3.a", kFull0, kFull0End },
};
static const DictFile g_liteFiles[] = {
    { "njubase3.a", kLite0, kLite0End },
};

static const DictPack g_packs[] = {
    { DICT_KMULTI_LABEL, 3, g_multiFiles },
    { DICT_KFULL_LABEL,  1, g_fullFiles  },
    { DICT_KLITE_LABEL,  1, g_liteFiles  },
};
enum { PACK_MULTI = 0, PACK_FULL, PACK_LITE, PACK_COUNT };

#define APP_VER      "1.0.0"
#define CUSTOM_MAX   (32ull * 1024 * 1024)

enum { ST_NONE = 0, ST_FULL, ST_LITE, ST_MULTI, ST_UNKNOWN, ST_PARTIAL };

typedef struct {
    int  state;
    bool hasA, hasB;
    u64  sizeA, sizeB;
    u32  crcA, crcB;
    bool validA, validB;
    /* 多本分担：njubase1.a / njubase2.a 是否也在 */
    bool hasB1, hasB2;
    u64  sizeB1, sizeB2;
    bool validB1, validB2;
    char note[192];
} Status;

static FsFileSystem g_sd;
static bool  g_sdOk = false;
static u32   g_crcTable[256];

static u32 g_crcFull = 0, g_crcLite = 0;
static u64 g_sizeFull = 0, g_sizeLite = 0;
static u32 g_entFull = 0, g_entLite = 0;

static Status g_st;
static char   g_toast[192] = "";
static int    g_toastKind = 0;   /* 0=none 1=ok 2=err */

/* ------------------------------------------------------------------ */
/* 小工具                                                             */
/* ------------------------------------------------------------------ */

static void crc32Init(void) {
    for (u32 i = 0; i < 256; i++) {
        u32 c = i;
        for (int k = 0; k < 8; k++)
            c = (c & 1u) ? (0xEDB88320u ^ (c >> 1)) : (c >> 1);
        g_crcTable[i] = c;
    }
}

static u32 crc32Buf(u32 crc, const unsigned char *p, size_t n) {
    crc ^= 0xFFFFFFFFu;
    for (size_t i = 0; i < n; i++)
        crc = g_crcTable[(crc ^ p[i]) & 0xFFu] ^ (crc >> 8);
    return crc ^ 0xFFFFFFFFu;
}

static bool getFileSize(const char *path, u64 *out) {
    FsFile f;
    if (R_FAILED(fsFsOpenFile(&g_sd, path, FsOpenMode_Read, &f))) return false;
    s64 sz = 0;
    Result rc = fsFileGetSize(&f, &sz);
    fsFileClose(&f);
    if (R_FAILED(rc) || sz < 0) return false;
    *out = (u64)sz;
    return true;
}

static bool getFileCrc(const char *path, u32 *out) {
    FsFile f;
    if (R_FAILED(fsFsOpenFile(&g_sd, path, FsOpenMode_Read, &f))) return false;

    static unsigned char buf[64 * 1024];
    s64 size = 0;
    if (R_FAILED(fsFileGetSize(&f, &size))) { fsFileClose(&f); return false; }

    u32 crc = 0;
    s64 off = 0;
    while (off < size) {
        u64 want = (u64)(size - off);
        if (want > sizeof(buf)) want = sizeof(buf);
        u64 got = 0;
        if (R_FAILED(fsFileRead(&f, off, buf, want, 0, &got)) || got == 0) {
            fsFileClose(&f);
            return false;
        }
        crc = crc32Buf(crc, buf, (size_t)got);
        off += (s64)got;
    }
    fsFileClose(&f);
    *out = crc;
    return true;
}

/* 逐级创建目录；已存在会返回错误，忽略即可 */
static void ensureDirs(const char *path) {
    char tmp[512];
    size_t len = strlen(path);
    if (len == 0 || len >= sizeof(tmp)) return;
    memcpy(tmp, path, len + 1);

    for (char *p = tmp + 1; *p; p++) {
        if (*p == '/') {
            *p = '\0';
            fsFsCreateDirectory(&g_sd, tmp);
            *p = '/';
        }
    }
    fsFsCreateDirectory(&g_sd, tmp);
}

static void drawProgress(const char *label, u64 done, u64 total) {
    int pct = total ? (int)(done * 100 / total) : 0;
    printf("\x1b[31;1H\x1b[K  %s: %3d%%  (%llu / %llu B)",
           label, pct, (unsigned long long)done, (unsigned long long)total);
    consoleUpdate(NULL);
}

static bool writeFileAt(const char *path, const unsigned char *data, u64 size) {
    ensureDirs(path);

    /* 先删后建：CreateFile 在文件已存在时会失败 */
    fsFsDeleteFile(&g_sd, path);
    if (R_FAILED(fsFsCreateFile(&g_sd, path, (s64)size, 0))) return false;

    FsFile f;
    if (R_FAILED(fsFsOpenFile(&g_sd, path, FsOpenMode_Write, &f))) {
        fsFsDeleteFile(&g_sd, path);
        return false;
    }

    const u64 CHUNK = 512 * 1024;
    u64 off = 0;
    bool ok = true;
    while (off < size) {
        u64 n = size - off;
        if (n > CHUNK) n = CHUNK;
        if (R_FAILED(fsFileWrite(&f, (s64)off, data + off, n, FsWriteOption_Flush))) {
            ok = false;
            break;
        }
        off += n;
        drawProgress("writing", off, size);
    }
    fsFileClose(&f);

    if (!ok) { fsFsDeleteFile(&g_sd, path); return false; }

    /* 回读大小，确认真的落盘 */
    u64 back = 0;
    if (!getFileSize(path, &back) || back != size) {
        fsFsDeleteFile(&g_sd, path);
        return false;
    }
    return true;
}

/* ------------------------------------------------------------------ */
/* NJDC 结构校验 —— 见 source/njdc_check.h（平台无关，PC 侧有对应测试）  */
/* ------------------------------------------------------------------ */

static bool njdcValidateFile(const char *path, u32 *outEntries, char *err, size_t errsz) {
    FsFile f;
    if (R_FAILED(fsFsOpenFile(&g_sd, path, FsOpenMode_Read, &f))) {
        snprintf(err, errsz, "open failed");
        return false;
    }

    s64 size = 0;
    if (R_FAILED(fsFileGetSize(&f, &size)) || size < 0x58) {
        fsFileClose(&f);
        snprintf(err, errsz, "bad size");
        return false;
    }

    unsigned char hdr[0x54];
    unsigned char tail[4];
    u64 got = 0;
    if (R_FAILED(fsFileRead(&f, 0, hdr, sizeof(hdr), 0, &got)) || got != sizeof(hdr)) {
        fsFileClose(&f);
        snprintf(err, errsz, "read header failed");
        return false;
    }
    if (R_FAILED(fsFileRead(&f, size - 4, tail, 4, 0, &got)) || got != 4) {
        fsFileClose(&f);
        snprintf(err, errsz, "read tail failed");
        return false;
    }
    fsFileClose(&f);

    return njdc_validate(hdr, tail, (uint64_t)size, outEntries, err, errsz) != 0;
}

static bool njdcValidateMem(const unsigned char *b, u64 size, u32 *outEntries,
                            char *err, size_t errsz) {
    if (size < 0x58) { snprintf(err, errsz, "too small"); return false; }
    return njdc_validate(b, b + size - 4, (uint64_t)size, outEntries, err, errsz) != 0;
}

/* ------------------------------------------------------------------ */
/* 状态检测                                                            */
/* ------------------------------------------------------------------ */

static const char *stateName(int s) {
    switch (s) {
        case ST_FULL:    return "INSTALLED  -  FULL build (150,000 entries)";
        case ST_LITE:    return "INSTALLED  -  LITE build ( 80,000 entries)";
        case ST_MULTI:   return "INSTALLED  -  MULTI (3 dictionaries, ~411,000 words)";
        case ST_PARTIAL: return "PARTIAL    -  only one encoding dir was written";
        case ST_UNKNOWN: return "INSTALLED  -  unrecognized dictionary (custom?)";
        default:         return "NOT INSTALLED  -  the stock dictionary is in use";
    }
}

static void refreshStatus(void) {
    memset(&g_st, 0, sizeof(g_st));
    g_st.state = ST_NONE;

    g_st.hasA = getFileSize(GB18030_PATH, &g_st.sizeA);
    g_st.hasB = getFileSize(GB2312_PATH,  &g_st.sizeB);

    char e1[96] = "", e2[96] = "";

    if (g_st.hasA) {
        u32 n = 0;
        g_st.validA = njdcValidateFile(GB18030_PATH, &n, e1, sizeof(e1));
        getFileCrc(GB18030_PATH, &g_st.crcA);
    }
    if (g_st.hasB) {
        u32 n = 0;
        g_st.validB = njdcValidateFile(GB2312_PATH, &n, e2, sizeof(e2));
        getFileCrc(GB2312_PATH, &g_st.crcB);
    }

    /* 多本分担：探测 njubase1.a / njubase2.a（只看 GB18030 侧即可判断是否多本方案） */
    char p1[320], p2[320];
    dictPath(p1, sizeof(p1), "GB18030", "njubase1.a");
    dictPath(p2, sizeof(p2), "GB18030", "njubase2.a");
    g_st.hasB1 = getFileSize(p1, &g_st.sizeB1);
    g_st.hasB2 = getFileSize(p2, &g_st.sizeB2);
    if (g_st.hasB1) { u32 n = 0; g_st.validB1 = njdcValidateFile(p1, &n, e1, sizeof(e1)); }
    if (g_st.hasB2) { u32 n = 0; g_st.validB2 = njdcValidateFile(p2, &n, e2, sizeof(e2)); }

    if (!g_st.hasA && !g_st.hasB) { g_st.state = ST_NONE; return; }

    /* 只要 njubase1 / njubase2 任一在，就按「多本方案」报告 */
    if (g_st.hasB1 || g_st.hasB2) {
        g_st.state = ST_MULTI;
        if (!g_st.validA)     snprintf(g_st.note, sizeof(g_st.note), "WARN: njubase3.a fails NJDC check: %s", e1);
        else if (!g_st.validB1 && g_st.hasB1) snprintf(g_st.note, sizeof(g_st.note), "WARN: njubase1.a fails NJDC check.");
        else if (!g_st.validB2 && g_st.hasB2) snprintf(g_st.note, sizeof(g_st.note), "WARN: njubase2.a fails NJDC check.");
        return;
    }

    if (g_st.hasA != g_st.hasB)   { g_st.state = ST_PARTIAL; return; }

    if (g_st.crcA == g_crcFull && g_st.sizeA == g_sizeFull)       g_st.state = ST_FULL;
    else if (g_st.crcA == g_crcLite && g_st.sizeA == g_sizeLite)  g_st.state = ST_LITE;
    else                                                          g_st.state = ST_UNKNOWN;

    if (!g_st.validA)          snprintf(g_st.note, sizeof(g_st.note), "WARN: GB18030 file fails NJDC structure check: %s", e1);
    else if (!g_st.validB)     snprintf(g_st.note, sizeof(g_st.note), "WARN: GB2312 file fails NJDC structure check: %s", e2);
    else if (g_st.crcA != g_st.crcB) snprintf(g_st.note, sizeof(g_st.note), "NOTE: the two encoding dirs hold different files.");
}

/* ------------------------------------------------------------------ */
/* 动作                                                                */
/* ------------------------------------------------------------------ */

static void setToast(int kind, const char *fmt, ...) {
    va_list ap;
    va_start(ap, fmt);
    vsnprintf(g_toast, sizeof(g_toast), fmt, ap);
    va_end(ap);
    g_toastKind = kind;
}

static void clearToast(void) {
    g_toast[0] = '\0';
    g_toastKind = 0;
}

/* 删掉所有可能被写过的目标 —— 避免「先装多本、后装单本」留下混合状态 */
static void removeAllTargets(void) {
    char p[320];
    for (int i = 0; i < NTARGETS; i++) {
        dictPath(p, sizeof(p), "GB18030", kTargets[i]);
        fsFsDeleteFile(&g_sd, p);
        dictPath(p, sizeof(p), "GB2312",  kTargets[i]);
        fsFsDeleteFile(&g_sd, p);
    }
}

/* 安装一个「包」：可能写 1~3 个目标文件（多本分担） */
static void doInstallPack(int idx) {
    if (!g_sdOk) { setToast(2, "SD card not available."); return; }
    if (idx < 0 || idx >= PACK_COUNT) return;

    const DictPack *p = &g_packs[idx];

    /* 先校验内嵌数据本身 */
    char err[96] = "";
    for (int i = 0; i < p->nfiles; i++) {
        u64 sz = (u64)(p->files[i].end - p->files[i].data);
        u32 n = 0;
        if (!njdcValidateMem(p->files[i].data, sz, &n, err, sizeof(err))) {
            setToast(2, "Refused: embedded file %d is not valid NJDC (%s)", i, err);
            return;
        }
    }

    clearToast();
    consoleClear();
    printf("\n  Installing %s ...\n\n", p->label);

    removeAllTargets();

    for (int i = 0; i < p->nfiles; i++) {
        u64 sz = (u64)(p->files[i].end - p->files[i].data);
        char pa[320], pb[320];
        dictPath(pa, sizeof(pa), "GB18030", p->files[i].target);
        dictPath(pb, sizeof(pb), "GB2312",  p->files[i].target);
        printf("    [%d/%d] %s  (%.2f MB)\n", i + 1, p->nfiles,
               p->files[i].target, sz / 1048576.0);
        consoleUpdate(NULL);

        if (!writeFileAt(pa, p->files[i].data, sz)) {
            setToast(2, "Write failed: %s (GB18030).", p->files[i].target);
            refreshStatus();
            return;
        }
        if (!writeFileAt(pb, p->files[i].data, sz)) {
            setToast(2, "Write failed: %s (GB2312).", p->files[i].target);
            refreshStatus();
            return;
        }
    }

    /* 落盘后回读校验 */
    bool ok = true;
    char bad[160] = "";
    for (int i = 0; i < p->nfiles && ok; i++) {
        char pa[320], pb[320];
        dictPath(pa, sizeof(pa), "GB18030", p->files[i].target);
        dictPath(pb, sizeof(pb), "GB2312",  p->files[i].target);
        u32 na = 0, nb = 0;
        char e1[64] = "", e2[64] = "";
        if (!njdcValidateFile(pa, &na, e1, sizeof(e1)) ||
            !njdcValidateFile(pb, &nb, e2, sizeof(e2))) {
            ok = false;
            snprintf(bad, sizeof(bad), "%s: %s%s", p->files[i].target, e1, e2);
        }
    }

    if (ok) {
        setToast(1, "Installed %s. Reboot, or close/reopen the keyboard.", p->label);
    } else {
        setToast(2, "Verify failed after write. (%s)", bad);
    }
    refreshStatus();
}

/* 触屏被按下时的提示：至少让用户知道程序还活着（并列出按键） */
static void drawTouchHint(void) {
    printf("\x1b[2J\x1b[H");
    printf("  HexDict\n\n");
    printf("  Touch detected - but this UI is keyboard driven.\n\n");
    printf("     [A]  install MULTI  411,000 words (3 dictionaries)\n");
    printf("     [B]  install ABBR   150,000 words + abbreviation\n");
    printf("     [X]  install LITE    80,000 entries\n");
    printf("     [Y]  uninstall              [-] reboot      [+] exit\n\n");
    printf("  If none of these respond, the applet is not receiving\n");
    printf("  controller input (common when launched from the Album).\n");
    consoleUpdate(NULL);
}

static void doInstall(const char *label, const unsigned char *data, u64 size, u32 entries) {
    if (!g_sdOk) { setToast(2, "SD card not available."); return; }
    removeAllTargets();

    char err[96] = "";
    u32 n = 0;
    if (!njdcValidateMem(data, size, &n, err, sizeof(err))) {
        setToast(2, "Refused: the embedded dictionary is not a valid NJDC (%s)", err);
        return;
    }

    clearToast();
    consoleClear();
    printf("\n  Installing %s ...\n", label);
    consoleUpdate(NULL);

    if (!writeFileAt(GB18030_PATH, data, size)) {
        setToast(2, "Write failed: GB18030 path.");
        refreshStatus();
        return;
    }
    if (!writeFileAt(GB2312_PATH, data, size)) {
        setToast(2, "Write failed: GB2312 path.");
        refreshStatus();
        return;
    }

    /* 落盘后回读校验：结构 + CRC 双查 */
    char e1[96] = "", e2[96] = "";
    u32 na = 0, nb = 0;
    if (!njdcValidateFile(GB18030_PATH, &na, e1, sizeof(e1)) ||
        !njdcValidateFile(GB2312_PATH,  &nb, e2, sizeof(e2))) {
        setToast(2, "Verify failed after write. (%s%s)", e1, e2);
    } else {
        setToast(1, "Installed %s. Now reboot, or close and reopen the keyboard.", label);
    }
    refreshStatus();
}

static void doInstallFromSd(void) {
    if (!g_sdOk) { setToast(2, "SD card not available."); return; }

    u64 size = 0;
    if (!getFileSize(CUSTOM_FS_PATH, &size)) {
        setToast(2, "Not found: %s", CUSTOM_SD_PATH);
        return;
    }
    if (size > CUSTOM_MAX) {
        setToast(2, "Too large (%llu B, limit 32 MB).", (unsigned long long)size);
        return;
    }

    char err[96] = "";
    u32 n = 0;
    if (!njdcValidateFile(CUSTOM_FS_PATH, &n, err, sizeof(err))) {
        setToast(2, "SD dictionary is not a valid NJDC: %s", err);
        return;
    }

    unsigned char *buf = (unsigned char *)malloc((size_t)size);
    if (!buf) { setToast(2, "Out of memory (%llu B).", (unsigned long long)size); return; }

    clearToast();
    consoleClear();
    printf("\n  Reading %s ...\n", CUSTOM_SD_PATH);
    consoleUpdate(NULL);

    FsFile f;
    u64 got = 0;
    bool ok = R_SUCCEEDED(fsFsOpenFile(&g_sd, CUSTOM_FS_PATH, FsOpenMode_Read, &f)) &&
              R_SUCCEEDED(fsFileRead(&f, 0, buf, size, 0, &got)) && got == size;
    if (ok) fsFileClose(&f);

    if (!ok) {
        free(buf);
        setToast(2, "Failed to read the SD dictionary.");
        return;
    }

    doInstall("custom dictionary (from SD)", buf, size, n);
    free(buf);
}

static void doUninstall(void) {
    if (!g_sdOk) { setToast(2, "SD card not available."); return; }

    clearToast();
    /* 多本分担后可能有 njubase1/2/3 三个文件，逐个显式删一次（双编码） */
    removeAllTargets();
    Result r1 = fsFsDeleteFile(&g_sd, GB18030_PATH);
    Result r2 = fsFsDeleteFile(&g_sd, GB2312_PATH);
    /* 整棵 pinyin/ 子树递归删除，连带清掉空目录 */
    Result r3 = fsFsDeleteDirectoryRecursively(&g_sd, OVERLAY_ROOT);

    bool any = R_SUCCEEDED(r1) || R_SUCCEEDED(r2) || R_SUCCEEDED(r3);
    refreshStatus();

    if (g_st.state == ST_NONE && R_SUCCEEDED(r3)) {
        setToast(1, "Overlay removed. The stock dictionary is back in use.");
    } else if (g_st.state == ST_NONE && any) {
        setToast(1, "Dictionary files removed (leftover empty dirs are harmless).");
    } else if (g_st.state == ST_NONE) {
        setToast(1, "Nothing to remove - already clean.");
    } else {
        setToast(2, "Uninstall incomplete - the overlay is still present.");
    }
}

static void doReboot(void) {
    if (R_SUCCEEDED(spsmInitialize())) {
        consoleClear();
        printf("\n  Rebooting ...\n");
        consoleUpdate(NULL);
        spsmShutdown(true);
        spsmExit();
    }
    setToast(2, "Reboot failed - please reboot manually (hold POWER 12 s).");
}

/* ------------------------------------------------------------------ */
/* 界面                                                                */
/* ------------------------------------------------------------------ */

static void humanMB(u64 bytes, char *out, size_t outsz) {
    snprintf(out, outsz, "%llu.%02llu MB",
             (unsigned long long)(bytes / 1048576ull),
             (unsigned long long)((bytes % 1048576ull) * 100ull / 1048576ull));
}

static void draw(void) {
    char sA[72], sB[72], s1[72], s2[72], mb[32];

    if (g_st.hasA) { humanMB(g_st.sizeA, mb, sizeof(mb)); snprintf(sA, sizeof(sA), "%-11s  CRC32 %08X", mb, g_st.crcA); }
    else           snprintf(sA, sizeof(sA), "not present");

    if (g_st.hasB) { humanMB(g_st.sizeB, mb, sizeof(mb)); snprintf(sB, sizeof(sB), "%-11s  CRC32 %08X", mb, g_st.crcB); }
    else           snprintf(sB, sizeof(sB), "not present");

    /* 多本分担：njubase1 / njubase2 */
    if (g_st.hasB1) { humanMB(g_st.sizeB1, mb, sizeof(mb)); snprintf(s1, sizeof(s1), "%-11s", mb); }
    else            snprintf(s1, sizeof(s1), "not present");
    if (g_st.hasB2) { humanMB(g_st.sizeB2, mb, sizeof(mb)); snprintf(s2, sizeof(s2), "%-11s", mb); }
    else            snprintf(s2, sizeof(s2), "not present");

    printf("\x1b[2J\x1b[H");
    printf("  HexDict  -  Switch Chinese IME dictionary manager             v%s\n", APP_VER);
    printf("  --------------------------------------------------------------------------\n");
    printf("  Target : title %s\n", DICT_TITLE_ID);
    printf("           romfs/Iwnn/ZH/CN/pinyin/{GB18030,GB2312}/njubase{1,2,3}.a\n");
    printf("  Method : Atmosphere LayeredFS overlay (SD card only, NAND untouched)\n");
    printf("\n");
    printf("  Status : %s\n", stateName(g_st.state));
    printf("           GB18030  %s\n", sA);
    printf("           GB2312   %s\n", sB);
    printf("           base1    %s\n", s1);
    printf("           base2    %s\n", s2);
    if (g_st.note[0]) printf("           %s\n", g_st.note);
    printf("\n");
    printf("  --------------------------------------------------------------------------\n");
    printf("   [A]  Install  MULTI  411,000 words (base1+base2+base3)  <-- recommended\n");
    printf("   [B]  Install  ABBR   full 150k + abbreviation (base3 only)\n");
    printf("   [X]  Install  LITE    80,000 entries\n");
    printf("   [L]  Install  custom  %s\n", CUSTOM_SD_PATH);
    printf("   [Y]  Uninstall        (restore the stock dictionary)\n");
    printf("   [-]  Reboot console                 [+]  Exit\n");
    printf("  --------------------------------------------------------------------------\n");

    if (g_toastKind == 1)      printf("\n  >> %s\n", g_toast);
    else if (g_toastKind == 2) printf("\n  !! %s\n", g_toast);
    else                       printf("\n");

    printf("\n  NOTES\n");
    printf("   * Changes take effect when the keyboard next OPENS the dictionary: close the\n");
    printf("     on-screen keyboard and open it again. If that is not enough, reboot.\n");
    printf("   * While BOOTING, do NOT hold the L button - Atmosphere's default override key\n");
    printf("     is L, and holding it turns LayeredFS OFF (looks like nothing worked).\n");
    printf("   * Uninstall is always safe: deleting the overlay restores the firmware copy.\n");
    printf("   * This UI is ASCII on purpose - the libnx built-in font has no CJK glyphs.\n");
    consoleUpdate(NULL);
}

/* ------------------------------------------------------------------ */
/* main                                                                */
/* ------------------------------------------------------------------ */

int main(int argc, char **argv) {
    (void)argc;
    (void)argv;

    consoleInit(NULL);
    /*
     * Launching from the Album runs us as an **applet**, not an application.
     * libnx's default focus handling can then swallow input / stall the loop,
     * which shows up as "buttons do nothing". Ask it not to suspend on focus loss.
     */
    appletSetFocusHandlingMode(AppletFocusHandlingMode_NoSuspend);
    crc32Init();

    char scratch[96];

    g_sizeFull = (u64)(kFull0End - kFull0);
    g_crcFull  = crc32Buf(0, kFull0, (size_t)g_sizeFull);
    njdcValidateMem(kFull0, g_sizeFull, &g_entFull, scratch, sizeof(scratch));

    g_sizeLite = (u64)(kLite0End - kLite0);
    g_crcLite  = crc32Buf(0, kLite0, (size_t)g_sizeLite);
    njdcValidateMem(kLite0, g_sizeLite, &g_entLite, scratch, sizeof(scratch));

    g_sdOk = R_SUCCEEDED(fsOpenSdCardFileSystem(&g_sd));

    consoleClear();
    printf("\n  Working, please wait ...\n");
    consoleUpdate(NULL);

    if (g_sdOk) refreshStatus();
    else        setToast(2, "Could not open the SD card filesystem.");

    padConfigureInput(1, HidNpadStyleSet_NpadStandard);
    PadState pad;
    /*
     * NOT padInitializeDefault: that only binds No1 + Handheld. Under the
     * Album (applet mode) the controller can end up on another input source,
     * which shows up as "text is there but buttons do nothing".
     * padInitializeAny binds every input source instead.
     */
    padInitializeAny(&pad);

    draw();

    while (appletMainLoop()) {
        padUpdate(&pad);
        u64 k = padGetButtonsDown(&pad);

        /* 触屏兜底：至少让用户知道程序还活着 */
        HidTouchScreenState ts;
        bool touched = false;
        if (R_SUCCEEDED(hidGetTouchScreenStates(&ts, 1)) && ts.count > 0) touched = true;

        if (k == 0 && !touched) continue;
        if (touched && k == 0) { drawTouchHint(); continue; }

        if (k & HidNpadButton_A) {
            doInstallPack(PACK_MULTI);          /* 411k words, base1+base2+base3 */
        } else if (k & HidNpadButton_B) {
            doInstallPack(PACK_FULL);           /* abbr-full, base3 only */
        } else if (k & HidNpadButton_X) {
            doInstallPack(PACK_LITE);
        } else if (k & HidNpadButton_L) {
            doInstallFromSd();
        } else if (k & HidNpadButton_Y) {
            doUninstall();
        } else if (k & HidNpadButton_Minus) {
            doReboot();
        } else if (k & HidNpadButton_Plus) {
            break;
        }

        draw();
    }

    consoleExit(NULL);
    if (g_sdOk) fsFsClose(&g_sd);
    return 0;
}

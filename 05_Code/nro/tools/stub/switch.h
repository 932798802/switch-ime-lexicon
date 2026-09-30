/*
 * tools/stub/switch.h —— 仅用于「语法自检」的最小 libnx 桩
 * ---------------------------------------------------------------------------
 * 目的：在没有 devkitPro 的情况下，用本机 g++ 把 nro/source/main.cpp 过一遍
 *       编译器，抓拼写错误 / 少括号 / 类型不匹配之类的低级问题。
 *
 * 它**不是** libnx 的替代品：签名是照 main.cpp 的用法手写的，
 * 函数体全空、返回值全是 0。**真机行为以 libnx 官方头文件为准。**
 *
 * 用法（见 tools/syntax_check.bat）：
 *   g++ -fsyntax-only -std=gnu++20 -I tools/stub source/main.cpp
 */
#ifndef STUB_SWITCH_H
#define STUB_SWITCH_H

#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>

typedef uint8_t  u8;
typedef uint16_t u16;
typedef uint32_t u32;
typedef uint64_t u64;
typedef int32_t  s32;
typedef int64_t  s64;
typedef u32 Result;

typedef struct { int _x; } FsFileSystem;
typedef struct { int _x; } FsFile;
typedef struct { int _x; } PadState;
typedef struct { int _x; } PrintConsole;

#define R_SUCCEEDED(r) ((r) == 0)
#define R_FAILED(r)    ((r) != 0)

enum {
    FsOpenMode_Read   = 1,
    FsOpenMode_Write  = 2,
    FsOpenMode_Append = 4,
    FsWriteOption_Flush = 1,
};

enum {
    HidNpadButton_A     = 1ull << 0,
    HidNpadButton_B     = 1ull << 1,
    HidNpadButton_X     = 1ull << 2,
    HidNpadButton_Y     = 1ull << 3,
    HidNpadButton_L     = 1ull << 6,
    HidNpadButton_Minus = 1ull << 12,
    HidNpadButton_Plus  = 1ull << 13,
};

static inline PrintConsole *consoleInit(PrintConsole *c) { return c; }
static inline void consoleClear(void) {}
static inline void consoleUpdate(PrintConsole *c) { (void)c; }
static inline void consoleExit(PrintConsole *c) { (void)c; }

static inline void padInitializeDefault(PadState *p) { (void)p; }
static inline void padUpdate(PadState *p) { (void)p; }
static inline u64  padGetButtonsDown(PadState *p) { (void)p; return 0; }

static inline bool appletMainLoop(void) { return false; }

static inline Result fsOpenSdCardFileSystem(FsFileSystem *fs) { (void)fs; return 0; }
static inline void   fsFsClose(FsFileSystem *fs) { (void)fs; }
static inline Result fsFsCreateDirectory(FsFileSystem *fs, const char *path) { (void)fs; (void)path; return 0; }
static inline Result fsFsCreateFile(FsFileSystem *fs, const char *path, s64 size, u32 option) { (void)fs; (void)path; (void)size; (void)option; return 0; }
static inline Result fsFsOpenFile(FsFileSystem *fs, const char *path, u32 mode, FsFile *out) { (void)fs; (void)path; (void)mode; (void)out; return 1; }
static inline Result fsFsDeleteFile(FsFileSystem *fs, const char *path) { (void)fs; (void)path; return 0; }
static inline Result fsFsDeleteDirectoryRecursively(FsFileSystem *fs, const char *path) { (void)fs; (void)path; return 0; }
static inline Result fsFileGetSize(FsFile *f, s64 *out) { (void)f; (void)out; return 1; }
static inline Result fsFileRead(FsFile *f, s64 off, void *buf, u64 size, u32 option, u64 *read) { (void)f; (void)off; (void)buf; (void)size; (void)option; (void)read; return 1; }
static inline Result fsFileWrite(FsFile *f, s64 off, const void *buf, u64 size, u32 option) { (void)f; (void)off; (void)buf; (void)size; (void)option; return 1; }
static inline void   fsFileClose(FsFile *f) { (void)f; }

static inline Result spsmInitialize(void) { return 0; }
static inline void   spsmExit(void) {}
static inline Result spsmShutdown(bool reboot) { (void)reboot; return 0; }

#endif /* STUB_SWITCH_H */

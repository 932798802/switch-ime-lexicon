/*
 * host_test.cpp —— 在 PC 上验证 C 版 NJDC 校验器（source/njdc_check.h）
 * ---------------------------------------------------------------------------
 * 为什么要有它：
 *   .nro 里的 NJDC 自检逻辑如果写错，后果是「装进去一个坏词典 / 误拒一个
 *   好词典」。本测试用**真实固件词典**把 C 端口跑一遍，与 tools/verify_njdc.py
 *   的结论对账；并做一次「故意损坏」的负例测试，确认它真的会拒绝坏文件。
 *
 * 编译运行（本机 MinGW）：
 *   g++ -O2 -o tools/host_test.exe tools/host_test.cpp
 *   ./tools/host_test.exe dist/njubase3.a dist/njubase3-lite.a <原版 *.a ...>
 */
#include "../source/njdc_check.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static unsigned char *readAll(const char *path, uint64_t *outSize) {
    FILE *f = fopen(path, "rb");
    if (!f) return NULL;
    if (fseek(f, 0, SEEK_END) != 0) { fclose(f); return NULL; }
    long n = ftell(f);
    if (n <= 0) { fclose(f); return NULL; }
    rewind(f);
    unsigned char *b = (unsigned char *)malloc((size_t)n);
    if (!b) { fclose(f); return NULL; }
    if (fread(b, 1, (size_t)n, f) != (size_t)n) { free(b); fclose(f); return NULL; }
    fclose(f);
    *outSize = (uint64_t)n;
    return b;
}

static int check(const unsigned char *b, uint64_t size, uint32_t *outN, char *err, size_t errsz) {
    if (size < NJDC_HEADER_SIZE) { snprintf(err, errsz, "too small"); return 0; }
    return njdc_validate(b, b + size - 4, size, outN, err, errsz);
}

int main(int argc, char **argv) {
    if (argc < 2) {
        fprintf(stderr, "usage: host_test <file.a> [more.a ...]\n");
        return 2;
    }

    int bad = 0;

    for (int i = 1; i < argc; i++) {
        uint64_t size = 0;
        unsigned char *b = readAll(argv[i], &size);
        if (!b) { printf("[SKIP]   %-58s (cannot read)\n", argv[i]); continue; }

        uint32_t n = 0;
        char err[128] = "";
        int ok = check(b, size, &n, err, sizeof(err));

        /*
         * njexyomi.a 是「纯预测型」小文件（N=0，头部 60 字节），不属记录表型词典，
         * 按设计被本校验器排除。这里显式标注为「预期拒绝」，不算失败。
         */
        int expectedReject = (strstr(argv[i], "njexyomi") != NULL);

        const char *layout = "variant";
        if (size >= NJDC_HEADER_SIZE && memcmp(b, "NJDC", 4) == 0) {
            if (njdc_be32(b + 0x20) == NJDC_REC_OFF_CLEAN) layout = "clean  ";
            else if (njdc_be32(b + 0x2c) != 0)             layout = "extra  ";
            else                                           layout = "other  ";
        }

        if (ok) {
            printf("%-10s %-54s %10llu B   N=%-7u %s\n",
                   "[OK]", argv[i], (unsigned long long)size, n, layout);
        } else if (expectedReject) {
            printf("%-10s %-54s %10llu B   N=%-7u %s  <- by design: %s\n",
                   "[EXPECTED]", argv[i], (unsigned long long)size, n, layout, err);
        } else {
            printf("%-10s %-54s %10llu B   N=%-7u %s  %s\n",
                   "[FAIL]", argv[i], (unsigned long long)size, n, layout, err);
            bad++;
        }

        /* ---- 负例 1：破坏魔数，必须被拒绝 ---- */
        if (ok) {
            unsigned char *c = (unsigned char *)malloc((size_t)size);
            memcpy(c, b, (size_t)size);
            c[0] ^= 0xFF;
            uint32_t n2 = 0;
            char e2[128] = "";
            if (check(c, size, &n2, e2, sizeof(e2))) {
                printf("         [FAIL] negative 1: corrupted magic NOT rejected\n");
                bad++;
            } else {
                printf("         [ok]   negative 1 (corrupt magic) rejected: %s\n", e2);
            }
            free(c);
        }

        /* ---- 负例 2：末尾截断 4 字节（尾部 magic 消失），必须被拒绝 ---- */
        if (ok && size > 8) {
            uint32_t n3 = 0;
            char e3[128] = "";
            if (check(b, size - 4, &n3, e3, sizeof(e3))) {
                printf("         [FAIL] negative 2: truncated file NOT rejected\n");
                bad++;
            } else {
                printf("         [ok]   negative 2 (truncate -4) rejected: %s\n", e3);
            }
        }

        /* ---- 负例 3：把条目数改大，让尾部表超出文件末尾，必须被拒绝 ---- */
        if (ok && size > NJDC_HEADER_SIZE) {
            unsigned char *c = (unsigned char *)malloc((size_t)size);
            memcpy(c, b, (size_t)size);
            uint32_t huge = 0x00FFFFFFu;
            c[0x50] = (unsigned char)(huge >> 24);
            c[0x51] = (unsigned char)(huge >> 16);
            c[0x52] = (unsigned char)(huge >> 8);
            c[0x53] = (unsigned char)(huge);
            uint32_t n4 = 0;
            char e4[128] = "";
            if (check(c, size, &n4, e4, sizeof(e4))) {
                printf("         [FAIL] negative 3: bogus entry count NOT rejected\n");
                bad++;
            } else {
                printf("         [ok]   negative 3 (bogus N) rejected: %s\n", e4);
            }
            free(c);
        }

        free(b);
    }

    printf("\n%s  (%d failure(s))\n", bad ? "*** FAILED ***" : "ALL PASSED", bad);
    return bad ? 1 : 0;
}

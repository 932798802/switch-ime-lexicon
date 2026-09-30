/*
 * njdc_check.h —— NJDC 结构校验（纯逻辑，无 libnx 依赖）
 * ---------------------------------------------------------------------------
 * 平台无关，可被两处复用：
 *   1) source/main.cpp      —— .nro 里装文件前后自检
 *   2) tools/host_test.cpp  —— 在 PC 上用真实固件词典回归本校验器
 *
 * 只读「头部 84 字节 + 末尾 4 字节 + 文件大小」即可判定，不需要读全文件。
 *
 * --- 为什么是「分层」校验（重要，别改回单一常量判断）----------------------
 * 原版固件 6 本词典实测并非同一套版式（数值均为十进制）：
 *
 *   文件          size       N       0x0c      hdr(0x10) 0x20记录表 0x24池   0x28尾表  0x2c附加区 0x44
 *   njubase1.a    90402      3351    90290     84        1146      34656    83696     0          1144
 *   njubase2.a    91258      3235    91146     84        1146      33496    84784     0          1144
 *   njcode.a      8204       285     8092      84        1146      3996     7630      0          1144
 *   njtan.a       256025     14184   255913    84        57895     199735   227653    0          57880
 *   njubase3.a    1606890    57954   1606778   84        81726     810618   1490978   661266     81724
 *   njexyomi.a    1528       0       1440      60        13        73       438       1158       196866
 *
 * 两个教训（都是 tools/host_test.cpp 抓出来的真实回归）：
 *
 * 1) `0x20 == 1146` / `0x44 == 1144` 只是「干净版式」(njubase1/2/njcode，也正是
 *    本工程生成器产出的版式) 的特征，**不是 NJDC 的通用不变量**。把这两条写成硬性
 *    判断，会把原版 njubase3 / njtan 误判为坏文件。
 *
 * 2) `0x0c = size - 112` 也只是巧合，正确通式是 **`0x0c = size - 28 - 头部长度`**
 *    （头部 84 时 28+84=112 才对上；njexyomi 头部 60，28+60=88，故 0x0c=1440 而非 1416）。
 *
 * 因此分两层：
 *   Tier 1（通用，凡是有词条的 NJDC 都该满足）：魔数、头部尺寸取值、0x0c 通式、
 *           偏移的单调性与边界（记录表 -> 池 -> 尾表）
 *   Tier 2（严格，仅当文件自称「干净版式」时施加）：1146 / 1144 / 尺寸精确等式
 *
 * njexyomi.a（N=0，纯预测型小文件）**结构性排除在 Tier 1 之外**（要求 N>0）——
 * 它不是记录表型词典。将来若要改联想词典，需要单独解它的版式。
 *
 * 对 .nro 而言，真正的「有没有写对」判据是 **文件大小 + CRC32**（见 main.cpp），
 * 结构校验只是「这明显不是一本词典」的兜底。
 */
#ifndef NJDC_CHECK_H
#define NJDC_CHECK_H

#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include <stdio.h>

#define NJDC_HEADER_SIZE   0x54u   /* 干净版式 */
#define NJDC_HEADER_SIZE_A 0x3Cu   /* njexyomi 等变体 */
#define NJDC_REC_OFF_CLEAN 1146u
#define NJDC_IDX_END_CLEAN 1144u
#define NJDC_TRAILER_CONST 28u     /* 0x0c = size - 28 - header_size */

static inline uint32_t njdc_be32(const unsigned char *p) {
    return ((uint32_t)p[0] << 24) | ((uint32_t)p[1] << 16) |
           ((uint32_t)p[2] << 8)  | (uint32_t)p[3];
}

/*
 * 返回 1 表示结构可信，并把条目数写入 *outEntries；0 表示不像合法 NJDC。
 * 失败原因写进 err。
 */
static inline int njdc_validate(const unsigned char hdr[NJDC_HEADER_SIZE],
                                const unsigned char tail[4],
                                uint64_t size,
                                uint32_t *outEntries,
                                char *err, size_t errsz) {
#define NJDC_FAIL(...) do { if (err && errsz) snprintf(err, errsz, __VA_ARGS__); return 0; } while (0)

    uint64_t hdr_size, rec, pool, ttail, n;

    if (size < 0x58)
        NJDC_FAIL("file too small: %llu B", (unsigned long long)size);
    if (memcmp(hdr, "NJDC", 4) != 0)
        NJDC_FAIL("bad magic");
    if (memcmp(tail, "NJDC", 4) != 0)
        NJDC_FAIL("bad trailing magic");

    hdr_size = njdc_be32(hdr + 0x10);
    if (hdr_size != NJDC_HEADER_SIZE && hdr_size != NJDC_HEADER_SIZE_A)
        NJDC_FAIL("unexpected header size: 0x%llx", (unsigned long long)hdr_size);
    if ((uint64_t)njdc_be32(hdr + 0x0c) != size - NJDC_TRAILER_CONST - hdr_size)
        NJDC_FAIL("0x0c != size - %u - %llu", NJDC_TRAILER_CONST, (unsigned long long)hdr_size);

    n     = njdc_be32(hdr + 0x50);
    rec   = njdc_be32(hdr + 0x20);
    pool  = njdc_be32(hdr + 0x24);
    ttail = njdc_be32(hdr + 0x28);

    if (n == 0)
        NJDC_FAIL("entry count is 0 (prediction-style file? not a record dictionary)");
    if (rec < hdr_size)
        NJDC_FAIL("record table (0x20=%llu) overlaps the header", (unsigned long long)rec);
    if (pool < rec + 10ull * n)
        NJDC_FAIL("pool (0x24=%llu) before the end of the record table (%llu)",
                  (unsigned long long)pool, (unsigned long long)(rec + 10ull * n));
    if (ttail < pool)
        NJDC_FAIL("tail table (0x28=%llu) before the pool (0x24=%llu)",
                  (unsigned long long)ttail, (unsigned long long)pool);
    if (ttail + 2ull * n + 4ull > size)
        NJDC_FAIL("tail table + 2N + 4 exceeds the file size");

    /* Tier 2：自称「干净版式」的，必须完全符合本工程生成器的产出规则 */
    if (hdr_size == NJDC_HEADER_SIZE && rec == NJDC_REC_OFF_CLEAN) {
        if (njdc_be32(hdr + 0x44) != NJDC_IDX_END_CLEAN)
            NJDC_FAIL("clean layout but 0x44 != %u", NJDC_IDX_END_CLEAN);
        if (pool != NJDC_REC_OFF_CLEAN + 10ull * n)
            NJDC_FAIL("clean layout but 0x24 != 0x20 + 10N");
        if (ttail + 2ull * n + 4ull != size)
            NJDC_FAIL("clean layout but size != tail + 2N + 4");
    }

    if (outEntries) *outEntries = (uint32_t)n;
    return 1;

#undef NJDC_FAIL
}

#endif /* NJDC_CHECK_H */

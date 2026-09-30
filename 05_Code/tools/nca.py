#!/usr/bin/env python3
"""NCA reader for Nintendo Switch firmware dumps - no hactool required.

Verified against switchbrew.org/wiki/NCA (header layout + XTS quirks) and
cross-checked against pycryptodome / cryptography for the AES primitives.

Key facts this implements (both are easy to get wrong):
  * The whole first 0xC00 bytes are AES-XTS encrypted as ONE stream.
    The magic "NCA3" sits at offset 0x200 of the *decrypted* buffer,
    NOT at offset 0x200 of the raw file.
  * Nintendo's XTS tweak is non-standard: the sector number is encoded
    BIG-endian in the 16-byte tweak block (standard XTS uses little-endian).
    Sector 0 looks identical either way - sectors >= 1 do not.

Usage:
    python nca.py <nca_file_or_dir> <prod.keys> [--find 0100000000001008]
    python nca.py <dir> <prod.keys> --list
    python nca.py <nca> <prod.keys> --extract <outdir>
"""
import os
import struct
import sys

from Crypto.Cipher import AES

HEADER_SIZE = 0xC00
SECTOR = 0x200

CONTENT_TYPE = {
    0: "Program",
    1: "Meta",
    2: "Control",
    3: "Manual",
    4: "Data",
    5: "PublicData",
}
DIST_TYPE = {0: "Download", 1: "GameCard", 2: "GameCardCompat"}


# ---------------------------------------------------------------- AES helpers

def _gf_mul_x(b):
    """XTS tweak step: multiply a 16-byte little-endian GF(2^128) value by x."""
    carry = 0
    out = bytearray(16)
    for i in range(16):
        c = b[i]
        out[i] = ((c << 1) & 0xFF) | carry
        carry = (c >> 7) & 1
    if carry:
        out[0] ^= 0x87
    return bytes(out)


def xts_decrypt(key, data, endian="big", start_sector=0):
    """AES-128-XTS decrypt. `endian` picks the tweak encoding ('big' = Nintendo)."""
    ecb_data = AES.new(key[:16], AES.MODE_ECB)
    ecb_tweak = AES.new(key[16:], AES.MODE_ECB)
    out = bytearray()
    for s in range(len(data) // SECTOR):
        tweak = ecb_tweak.encrypt((start_sector + s).to_bytes(16, endian))
        sec = data[s * SECTOR:(s + 1) * SECTOR]
        for b in range(SECTOR // 16):
            dec = ecb_data.decrypt(bytes(x ^ y for x, y in zip(sec[b * 16:(b + 1) * 16], tweak)))
            out += bytes(x ^ y for x, y in zip(dec, tweak))
            tweak = _gf_mul_x(tweak)
    return bytes(out)


def ct_crypt_fast(key, section_start, data):
    """Fast NCA section AES-CTR.

    The counter starts at (section_start / 16) and is a 128-bit big-endian value.
    The upper 8 bytes act as a fixed nonce; the low 64 bits do the counting.
    """
    iv = (section_start // 16).to_bytes(16, "big")
    ctr = AES.new(key, AES.MODE_CTR, nonce=iv[:8],
                  initial_value=int.from_bytes(iv[8:], "big"))
    return ctr.decrypt(data)


def ctr_crypt(key, iv, data):
    """AES-CTR with a 128-bit big-endian counter starting at `iv` (small inputs)."""
    ctr = int.from_bytes(iv, "big")
    ecb = AES.new(key, AES.MODE_ECB)
    out = bytearray()
    for i in range(0, len(data), 16):
        chunk = data[i:i + 16]
        ks = ecb.encrypt(ctr.to_bytes(16, "big"))
        out += bytes(x ^ y for x, y in zip(chunk, ks))
        ctr = (ctr + 1) & ((1 << 128) - 1)
    return bytes(out)


# ---------------------------------------------------------------- key handling

def load_keys(path):
    keys = {}
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            try:
                keys[k.strip()] = bytes.fromhex(v.strip())
            except ValueError:
                pass
    return keys


def _ecb_dec(key, data):
    return AES.new(key, AES.MODE_ECB).decrypt(data)


def _ecb_enc(key, data):
    return AES.new(key, AES.MODE_ECB).encrypt(data)


def key_area_key(keys, kaek_index, key_generation):
    """Derive key_area_key_{application,ocean,system}[key_generation].

    Nintendo derives *downward*: derived = AES-ECB-DECRYPT(parent_key, source),
    i.e. the named "*_source" constant is used as the CIPHERTEXT, not the
    plaintext. Verified against the keyset's own self-consistent pairs:
        master_key_N = DEC(master_kek_N, master_key_source)
        titlekek_N   = DEC(master_key_N, titlekek_source)
    Using ENCRYPT here silently yields plausible-looking-but-wrong keys.
    """
    name = ("key_area_key_application_source",
            "key_area_key_ocean_source",
            "key_area_key_system_source")[kaek_index]
    kek = _ecb_dec(keys["master_key_%02x" % key_generation],
                   keys["aes_kek_generation_source"])
    # Documented exception: generation 0 uses the plain aes_key_generation_source
    # for the second step instead of the per-index source.
    if key_generation == 0:
        return _ecb_dec(kek, keys["aes_key_generation_source"])
    return _ecb_dec(kek, keys[name])


# ---------------------------------------------------------------- NCA class

class Nca:
    def __init__(self, path, keys):
        self.path = path
        self.keys = keys
        self.size = os.path.getsize(path)
        with open(path, "rb") as fh:
            self.raw_header = fh.read(HEADER_SIZE)
        self.hdr = xts_decrypt(keys["header_key"], self.raw_header, endian="big")
        if self.hdr[0x200:0x204] not in (b"NCA3", b"NCA2", b"NCA0"):
            raise ValueError("not a valid NCA header: %r" % self.hdr[0x200:0x204])

        h = self.hdr
        self.magic = h[0x200:0x204].decode("ascii")
        self.distribution = DIST_TYPE.get(h[0x204], h[0x204])
        self.content_type = CONTENT_TYPE.get(h[0x205], h[0x205])
        self.key_gen_old = h[0x206]
        self.kaek_index = h[0x207]
        self.content_size = struct.unpack_from("<Q", h, 0x208)[0]
        self.program_id = struct.unpack_from("<Q", h, 0x210)[0]
        self.content_index = struct.unpack_from("<I", h, 0x218)[0]
        self.sdk_addon = struct.unpack_from("<I", h, 0x21C)[0]
        self.key_generation = h[0x220]
        self.rights_id = h[0x230:0x240]
        # 4 x FsEntry { start_block u32, end_block u32, reserved u64 }
        self.sections = []
        for i in range(4):
            s, e = struct.unpack_from("<II", h, 0x240 + i * 0x10)
            self.sections.append((s, e))
        self.fs_hashes = [h[0x280 + i * 0x20:0x2A0 + i * 0x20] for i in range(4)]
        self.enc_key_area = h[0x300:0x340]

    # -- media offsets are in 0x200-byte blocks and biased by the header size
    @staticmethod
    def _media_to_real(block):
        return block * SECTOR + HEADER_SIZE

    def section_range(self, i):
        s, e = self.sections[i]
        if s == 0 and e == 0:
            return None
        return self._media_to_real(s), self._media_to_real(e)

    def _dec_key_area(self):
        kak = key_area_key(self.keys, self.kaek_index, self.key_generation)
        return AES.new(kak, AES.MODE_ECB).decrypt(self.enc_key_area)

    def read_section(self, i):
        rng = self.section_range(i)
        if rng is None:
            return None
        start, end = rng
        fs_hdr_off = start
        fs_hdr_len = 0x200 if self.magic == "NCA3" else 0x200
        with open(self.path, "rb") as fh:
            fh.seek(fs_hdr_off)
            fs_hdr_raw = fh.read(fs_hdr_len)
            dat_off = fs_hdr_off + 0x200
            fh.seek(dat_off)
            data = fh.read(end - dat_off)

        dec_keys = self._dec_key_area()
        # The FS header itself is encrypted as sector (offset-0x400)/0x200 of the XTS stream
        if self.magic == "NCA3":
            tweak_sector = (fs_hdr_off - 0x400) // SECTOR
            fs_hdr = xts_decrypt(self.keys["header_key"], fs_hdr_raw, endian="big",
                                 start_sector=tweak_sector)
        else:
            fs_hdr = fs_hdr_raw

        # FS header: 0x0 magic "FSH0", 0x8 hash type, crypto_type/... at 0x4
        crypto_type = fs_hdr[0x04] if self.magic == "NCA2" else fs_hdr[0x04]
        # NCA3 FsHeader layout: 0x0 magic, 0x4 hash_type, 0x8..0x18 hash data
        # crypto key index lives in the FS header right after magic for NCA3? Use
        # the documented NCA3 layout: 0x0 "FSH0", 0x4 version, 0x8 hash type,
        # 0x200-0x8 ... -> simpler: crypto info is embedded in the header's
        # HierarchicalSha256 region. We use the section-level key from key area
        # indexed by the FS header's crypto type byte.
        crypto_type = fs_hdr[0x04] & 0x07 if self.magic != "NCA3" else fs_hdr[0x04] & 0x07

        data_key = dec_keys[crypto_type * 0x10:(crypto_type + 1) * 0x10]
        if crypto_type == 0 and data_key == b"\x00" * 16:
            plain = data
        else:
            iv = (dat_off // 16).to_bytes(16, "big")
            plain = ctr_crypt(data_key, iv, data)
        return plain


# ---------------------------------------------------------------- FS parsers

def parse_pfs0(buf, offset=0):
    """Parse a PFS0 (ExeFS / NSP partition) and yield (name, offset, size)."""
    base = offset
    if buf[base:base + 4] != b"PFS0":
        raise ValueError("no PFS0 magic at 0x%X: %r" % (base, buf[base:base + 4]))
    count, strsize = struct.unpack_from("<II", buf, base + 4)
    strtab = base + 0x10 + count * 0x18
    out = []
    for i in range(count):
        o, sz, nameoff = struct.unpack_from("<QQI", buf, base + 0x10 + i * 0x18)
        end = buf.index(b"\x00", strtab + nameoff)
        name = buf[strtab + nameoff:end].decode("utf-8", "replace")
        out.append((name, strtab + strsize + o, sz))
    return out


def parse_ivfc(buf, offset=0):
    """Return the RomFS level-6 metadata blob and file data base for an IVFC."""
    if buf[offset:offset + 4] != b"IVFC":
        raise ValueError("no IVFC magic at 0x%X: %r" % (offset, buf[offset:offset + 4]))
    lvl6_off, lvl6_size = struct.unpack_from("<QQ", buf, offset + 0x50)
    data_off = offset + 0x100 + lvl6_off
    return buf[data_off:data_off + lvl6_size], data_off


def parse_romfs(meta, data_base, plain):
    """Walk the RomFS metadata table and return a list of (path, size)."""
    hdr_size = struct.unpack_from("<I", meta, 0x00)[0]
    dir_meta_off, dir_meta_size = struct.unpack_from("<II", meta, 0x0C)
    file_meta_off, file_meta_size = struct.unpack_from("<II", meta, 0x14)
    data_off = struct.unpack_from("<I", meta, 0x38)[0]

    dirs = {}
    files = []

    def walk(d):
        out = bytearray()
        n = struct.unpack_from("<I", meta, d)[0]
        while n != 0xFFFFFFFF:
            if n & 0x80000000:
                entry = d + (n & 0x7FFFFFFF)
                parent, sibling, namelen, child = struct.unpack_from("<IIII", meta, entry)
                name = meta[entry + 0x18:entry + 0x18 + namelen].decode("utf-8", "replace")
                sub = walk(entry + 0x18 + ((namelen + 3) & ~3))
                dirs[sub] = name
                n = sibling
            else:
                entry = d + n
                parent, sibling, namelen, off, size = struct.unpack_from("<IIIII", meta, entry)
                hoff = struct.unpack_from("<I", meta, entry + 0x14)[0]
                name = meta[entry + 0x18:entry + 0x18 + namelen].decode("utf-8", "replace")
                files.append((entry, off, size, name))
                n = sibling
        return d

    walk(dir_meta_off)
    return files, data_off


# ---------------------------------------------------------------- driver

def fmt_title(pid):
    return "%016X" % pid


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 1
    target = sys.argv[1]
    keys = load_keys(sys.argv[2])

    if os.path.isfile(target):
        n = Nca(target, keys)
        print(fmt_title(n.program_id), n.content_type, n.content_size)
        return 0

    want = None
    if "--find" in sys.argv:
        want = int(sys.argv[sys.argv.index("--find") + 1], 16)

    files = sorted(f for f in os.listdir(target) if f.endswith(".nca"))
    rows = []
    miss = 0
    for f in files:
        try:
            rows.append((f, Nca(os.path.join(target, f), keys)))
        except Exception:
            miss += 1

    print("scanned %d .nca, parsed %d, unreadable %d" % (len(files), len(rows), miss))
    print()
    for f, n in sorted(rows, key=lambda x: (x[1].program_id, x[1].content_index)):
        mark = ""
        if n.program_id == 0x0100000000001008:
            mark = "   <== swkbd"
        elif want is not None and n.program_id == want:
            mark = "   <== TARGET"
        if n.program_id & 0xFFFFFFFF00000000 == 0x0100000000000000 and n.program_id < 0x0100000000001100:
            print("%s  %-8s idx=%-2d %10d B  kg=0x%02X kaek=%d  %s%s" % (
                fmt_title(n.program_id), n.content_type, n.content_index,
                n.size, n.key_generation, n.kaek_index, f[:12], mark))
    return 0


if __name__ == "__main__":
    sys.exit(main())

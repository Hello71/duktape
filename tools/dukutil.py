#!/usr/bin/env python2
#
#  Python utilities shared by the build scripts.
#

import datetime
import json

class BitEncoder:
    "Bitstream encoder."

    _bits = None

    def __init__(self):
        self._bits = []

    def bits(self, x, nbits):
        if (x >> nbits) != 0:
            raise Exception('input value has too many bits (value: %d, bits: %d)' % (x, nbits))
        for shift in xrange(nbits - 1, -1, -1):  # nbits - 1, nbits - 2, ..., 0
            self._bits.append((x >> shift) & 0x01)

    def string(self, x):
        for i in xrange(len(x)):
            ch = ord(x[i])
            for shift in xrange(7, -1, -1):  # 7, 6, ..., 0
                self._bits.append((ch >> shift) & 0x01)

    def getNumBits(self):
        "Get current number of encoded bits."
        return len(self._bits)

    def getNumBytes(self):
        "Get current number of encoded bytes, rounded up."
        nbits = len(self._bits)
        while (nbits % 8) != 0:
            nbits += 1
        return nbits / 8

    def getBytes(self):
        "Get current bitstream as a byte sequence, padded with zero bits."
        bytes = []

        for i in xrange(self.getNumBytes()):
            t = 0
            for j in xrange(8):
                off = i*8 + j
                if off >= len(self._bits):
                    t = (t << 1)
                else:
                    t = (t << 1) + self._bits[off]
            bytes.append(t)

        return bytes

    def getByteString(self):
        "Get current bitstream as a string."
        return ''.join([chr(i) for i in self.getBytes()])

class GenerateC:
    "Helper for generating C source and header files."

    _data = None
    wrap_col = 76

    def __init__(self):
        self._data = []

    def emitRaw(self, text):
        "Emit raw text (without automatic newline)."
        self._data.append(text)

    def emitLine(self, text):
        "Emit a raw line (with automatic newline)."
        self._data.append(text + '\n')

    def emitHeader(self, autogen_by):
        "Emit file header comments."

        # Note: a timestamp would be nice but it breaks incremental building
        self.emitLine('/*')
        self.emitLine(' *  Automatically generated by %s, do not edit!' % autogen_by)
        self.emitLine(' */')
        self.emitLine('')

    def emitArray(self, data, tablename, visibility=None, typename='char', size=None, intvalues=False, const=True):
        "Emit an array as a C array."

        # lenient input
        if isinstance(data, unicode):
            data = data.encode('utf-8')
        if isinstance(data, str):
            tmp = []
            for i in xrange(len(data)):
                tmp.append(ord(data[i]))
            data = tmp

        size_spec = ''
        if size is not None:
            size_spec = '%d' % size
        visib_qual = ''
        if visibility is not None:
            visib_qual = visibility + ' '
        const_qual = ''
        if const:
            const_qual = 'const '
        self.emitLine('%s%s%s %s[%s] = {' % (visib_qual, const_qual, typename, tablename, size_spec))

        line = ''
        for i in xrange(len(data)):
            if intvalues:
                suffix = ''
                if data[i] < -32768 or data[i] > 32767:
                    suffix = 'L'
                t = "%d%s," % (data[i], suffix)
            else:
                t = "(%s)'\\x%02x', " % (typename, data[i])
            if len(line) + len(t) >= self.wrap_col:
                self.emitLine(line)
                line = t
            else:
                line += t
        if line != '':
            self.emitLine(line)
        self.emitLine('};')

    def emitDefine(self, name, value, comment=None):
        "Emit a C define with an optional comment."

        # XXX: there is no escaping right now (for comment or value)
        if comment is not None:
            self.emitLine('#define %-60s  %-30s /* %s */' % (name, value, comment))
        else:
            self.emitLine('#define %-60s  %s' % (name, value))

    def getString(self):
        "Get the entire file as a string."
        return ''.join(self._data)

def json_encode(x):
    "JSON encode a value."
    try:
        return json.dumps(x)
    except AttributeError:
        pass

    # for older library versions
    return json.write(x)

def json_decode(x):
    "JSON decode a value."
    try:
        return json.loads(x)
    except AttributeError:
        pass

    # for older library versions
    return json.read(x)

# Compute a byte hash identical to duk_util_hashbytes().
DUK__MAGIC_M = 0x5bd1e995
DUK__MAGIC_R = 24
def duk_util_hashbytes(x, off, nbytes, str_seed, big_endian):
    h = (str_seed ^ nbytes) & 0xffffffff

    while nbytes >= 4:
        # 4-byte fetch byte order:
        #  - native (endian dependent) if unaligned accesses allowed
        #  - little endian if unaligned accesses not allowed

        if big_endian:
            k = ord(x[off + 3]) + (ord(x[off + 2]) << 8) + \
                (ord(x[off + 1]) << 16) + (ord(x[off + 0]) << 24)
        else:
            k = ord(x[off]) + (ord(x[off + 1]) << 8) + \
                (ord(x[off + 2]) << 16) + (ord(x[off + 3]) << 24)

        k = (k * DUK__MAGIC_M) & 0xffffffff
        k = (k ^ (k >> DUK__MAGIC_R)) & 0xffffffff
        k = (k * DUK__MAGIC_M) & 0xffffffff
        h = (h * DUK__MAGIC_M) & 0xffffffff
        h = (h ^ k) & 0xffffffff

        off += 4
        nbytes -= 4

    if nbytes >= 3:
        h = (h ^ (ord(x[off + 2]) << 16)) & 0xffffffff
    if nbytes >= 2:
        h = (h ^ (ord(x[off + 1]) << 8)) & 0xffffffff
    if nbytes >= 1:
        h = (h ^ ord(x[off])) & 0xffffffff
        h = (h * DUK__MAGIC_M) & 0xffffffff

    h = (h ^ (h >> 13)) & 0xffffffff
    h = (h * DUK__MAGIC_M) & 0xffffffff
    h = (h ^ (h >> 15)) & 0xffffffff

    return h

# Compute a string hash identical to duk_heap_hashstring() when dense
# hashing is enabled.
DUK__STRHASH_SHORTSTRING = 4096
DUK__STRHASH_MEDIUMSTRING = 256 * 1024
DUK__STRHASH_BLOCKSIZE = 256
def duk_heap_hashstring_dense(x, hash_seed, big_endian=False, strhash16=False):
    str_seed = (hash_seed ^ len(x)) & 0xffffffff

    if len(x) <= DUK__STRHASH_SHORTSTRING:
        res = duk_util_hashbytes(x, 0, len(x), str_seed, big_endian)
    else:
        if len(x) <= DUK__STRHASH_MEDIUMSTRING:
            skip = 16 * DUK__STRHASH_BLOCKSIZE + DUK__STRHASH_BLOCKSIZE
        else:
            skip = 256 * DUK__STRHASH_BLOCKSIZE + DUK__STRHASH_BLOCKSIZE

        res = duk_util_hashbytes(x, 0, DUK__STRHASH_SHORTSTRING, str_seed, big_endian)
        off = DUK__STRHASH_SHORTSTRING + (skip * (res % 256)) / 256

        while off < len(x):
            left = len(x) - off
            now = left
            if now > DUK__STRHASH_BLOCKSIZE:
                now = DUK__STRHASH_BLOCKSIZE
            res = (res ^ duk_util_hashbytes(str, off, now, str_seed, big_endian)) & 0xffffffff
            off += skip

    if strhash16:
        res &= 0xffff

    return res

# Compute a string hash identical to duk_heap_hashstring() when sparse
# hashing is enabled.
DUK__STRHASH_SKIP_SHIFT = 5   # XXX: assumes default value
def duk_heap_hashstring_sparse(x, hash_seed, strhash16=False):
    res = (hash_seed ^ len(x)) & 0xffffffff

    step = (len(x) >> DUK__STRHASH_SKIP_SHIFT) + 1
    off = len(x)
    while off >= step:
        assert(off >= 1)
        res = ((res * 33) + ord(x[off - 1])) & 0xffffffff
        off -= step

    if strhash16:
        res &= 0xffff

    return res

# Must match src-input/duk_unicode_support:duk_unicode_unvalidated_utf8_length().
def duk_unicode_unvalidated_utf8_length(x):
    assert(isinstance(x, str))
    clen = 0
    for c in x:
        t = ord(c)
        if t < 0x80 or t >= 0xc0:  # 0x80...0xbf are continuation chars, not counted
            clen += 1
    return clen

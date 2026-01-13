#!/bin/sh
# Ghost EDR Performance Benchmark Script
# Tests CPU-intensive and I/O-intensive workloads

set -e

# Function to get time in milliseconds
get_ms() {
  python3 -c "import time; print(int(time.time() * 1000))"
}

echo "========================================"
echo "Ghost EDR Performance Benchmark"
echo "========================================"
echo ""

# Create temp directory
WORKDIR=/tmp/benchmark_$$
mkdir -p $WORKDIR
cd $WORKDIR

# ----------------------------------------
# TEST 1: CPU-Heavy - Compression
# ----------------------------------------
echo "TEST 1: CPU-Heavy - Compressing 100MB of random data"
dd if=/dev/urandom of=random_100mb.bin bs=1M count=100 2>/dev/null
start=$(get_ms)
gzip -k random_100mb.bin
end=$(get_ms)
COMPRESS_TIME=$((end - start))
echo "  Compression time: ${COMPRESS_TIME}ms"
rm -f random_100mb.bin.gz

# ----------------------------------------
# TEST 2: CPU-Heavy - SHA256 Hashing
# ----------------------------------------
echo ""
echo "TEST 2: CPU-Heavy - SHA256 hashing 100MB file 10 times"
start=$(get_ms)
for i in 1 2 3 4 5 6 7 8 9 10; do
  sha256sum random_100mb.bin > /dev/null
done
end=$(get_ms)
HASH_TIME=$((end - start))
echo "  Hashing time (10 iterations): ${HASH_TIME}ms"
rm -f random_100mb.bin

# ----------------------------------------
# TEST 3: I/O-Heavy - Create many small files
# ----------------------------------------
echo ""
echo "TEST 3: I/O-Heavy - Creating 5,000 small files"
mkdir -p smallfiles
start=$(get_ms)
i=0
while [ $i -lt 5000 ]; do
  echo "content line 1 for file $i" > smallfiles/file_$i.txt
  echo "content line 2 for file $i" >> smallfiles/file_$i.txt
  i=$((i + 1))
done
end=$(get_ms)
SMALLFILES_CREATE_TIME=$((end - start))
echo "  Create time: ${SMALLFILES_CREATE_TIME}ms"

# ----------------------------------------
# TEST 4: I/O-Heavy - Read many small files
# ----------------------------------------
echo ""
echo "TEST 4: I/O-Heavy - Reading 5,000 small files"
start=$(get_ms)
i=0
while [ $i -lt 5000 ]; do
  cat smallfiles/file_$i.txt > /dev/null
  i=$((i + 1))
done
end=$(get_ms)
SMALLFILES_READ_TIME=$((end - start))
echo "  Read time: ${SMALLFILES_READ_TIME}ms"

# ----------------------------------------
# TEST 5: I/O-Heavy - Large file sequential write
# ----------------------------------------
echo ""
echo "TEST 5: I/O-Heavy - Sequential write 200MB"
start=$(get_ms)
dd if=/dev/zero of=large_200mb.bin bs=1M count=200 2>/dev/null
sync
end=$(get_ms)
LARGE_WRITE_TIME=$((end - start))
echo "  Write time: ${LARGE_WRITE_TIME}ms"

# ----------------------------------------
# TEST 6: I/O-Heavy - Large file sequential read
# ----------------------------------------
echo ""
echo "TEST 6: I/O-Heavy - Sequential read 200MB"
# Clear cache
echo 3 > /proc/sys/vm/drop_caches 2>/dev/null || true
start=$(get_ms)
dd if=large_200mb.bin of=/dev/null bs=1M 2>/dev/null
end=$(get_ms)
LARGE_READ_TIME=$((end - start))
echo "  Read time: ${LARGE_READ_TIME}ms"
rm -f large_200mb.bin

# ----------------------------------------
# TEST 7: Mixed - Compile Python bytecode
# ----------------------------------------
echo ""
echo "TEST 7: Mixed - Compiling 500 Python files to bytecode"
mkdir -p pyfiles
i=0
while [ $i -lt 500 ]; do
  cat > pyfiles/module_$i.py << 'PYEOF'
import os
import sys
import json
import hashlib

def function_a(data):
    return [x*2 for x in range(100)]

def function_b(items):
    return {str(i): i**2 for i in range(50)}

class DataProcessor:
    def __init__(self, name):
        self.name = name
        self.data = []
        self.cache = {}

    def process(self, items):
        result = []
        for item in items:
            if item not in self.cache:
                self.cache[item] = self._transform(item)
            result.append(self.cache[item])
        return result

    def _transform(self, item):
        return hashlib.md5(str(item).encode()).hexdigest()

def main():
    processor = DataProcessor("test")
    data = list(range(1000))
    return processor.process(data)

if __name__ == "__main__":
    main()
PYEOF
  i=$((i + 1))
done

start=$(get_ms)
python3 -m compileall -q -f pyfiles 2>/dev/null
end=$(get_ms)
COMPILE_TIME=$((end - start))
echo "  Compile time: ${COMPILE_TIME}ms"

# ----------------------------------------
# TEST 8: Mixed - Extract tarball with many files
# ----------------------------------------
echo ""
echo "TEST 8: Mixed - Creating and extracting tarball (5k files)"
start=$(get_ms)
tar czf smallfiles.tar.gz smallfiles
end=$(get_ms)
TAR_CREATE_TIME=$((end - start))
echo "  Tar create time: ${TAR_CREATE_TIME}ms"

rm -rf smallfiles
start=$(get_ms)
tar xzf smallfiles.tar.gz
end=$(get_ms)
TAR_EXTRACT_TIME=$((end - start))
echo "  Tar extract time: ${TAR_EXTRACT_TIME}ms"

# ----------------------------------------
# TEST 9: Process spawning stress test
# ----------------------------------------
echo ""
echo "TEST 9: Process spawning - 1000 short-lived processes"
start=$(get_ms)
i=0
while [ $i -lt 1000 ]; do
  echo "test" > /dev/null
  i=$((i + 1))
done
end=$(get_ms)
SPAWN_TIME=$((end - start))
echo "  Spawn time: ${SPAWN_TIME}ms"

# ----------------------------------------
# Cleanup and Summary
# ----------------------------------------
cd /
rm -rf $WORKDIR

echo ""
echo "========================================"
echo "SUMMARY (all times in milliseconds)"
echo "========================================"
echo "CPU-Heavy:"
echo "  Compression (100MB):    ${COMPRESS_TIME}ms"
echo "  SHA256 (10x100MB):      ${HASH_TIME}ms"
echo ""
echo "I/O-Heavy:"
echo "  Create 5k files:        ${SMALLFILES_CREATE_TIME}ms"
echo "  Read 5k files:          ${SMALLFILES_READ_TIME}ms"
echo "  Write 200MB:            ${LARGE_WRITE_TIME}ms"
echo "  Read 200MB:             ${LARGE_READ_TIME}ms"
echo ""
echo "Mixed:"
echo "  Python compile (500):   ${COMPILE_TIME}ms"
echo "  Tar create (5k):        ${TAR_CREATE_TIME}ms"
echo "  Tar extract (5k):       ${TAR_EXTRACT_TIME}ms"
echo "  Process spawn (1k):     ${SPAWN_TIME}ms"
echo "========================================"

# Output CSV format for easy parsing
echo ""
echo "CSV:${COMPRESS_TIME},${HASH_TIME},${SMALLFILES_CREATE_TIME},${SMALLFILES_READ_TIME},${LARGE_WRITE_TIME},${LARGE_READ_TIME},${COMPILE_TIME},${TAR_CREATE_TIME},${TAR_EXTRACT_TIME},${SPAWN_TIME}"

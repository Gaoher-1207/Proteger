# C core engine

`scanner.c` exposes `scan_text()` for byte-length-safe scanning and counts email markers, digit runs and HTTP URL markers. Python calls it with `ctypes`; the metrics accompany scan output. It does not receive or persist a copy of content. Compile from this directory with `make` (GCC/Make required); on Windows with MinGW use `gcc -shared -O2 -Wall -Wextra -std=c11 -o build/scanner.dll src/scanner.c -Iinclude`. If the shared library is absent, Python remains usable and reports the fallback engine.

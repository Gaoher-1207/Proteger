CC ?= gcc
CFLAGS ?= -O2 -Wall -Wextra -std=c11
all: build/scanner.dll
build/scanner.dll: src/scanner.c include/scanner.h
	mkdir -p build
	$(CC) $(CFLAGS) -shared -o $@ src/scanner.c -Iinclude
clean:
	rm -f build/scanner.dll
.PHONY: all clean

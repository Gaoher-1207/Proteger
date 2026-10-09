CC ?= gcc
CFLAGS ?= -O2 -Wall -Wextra -std=c11
UNAME_S := $(shell uname -s 2>/dev/null)
ifneq (,$(filter MINGW% MSYS% CYGWIN%,$(UNAME_S)))
TARGET := build/scanner.dll
SHARED_FLAGS := -shared
else ifeq ($(UNAME_S),Darwin)
TARGET := build/libscanner.dylib
SHARED_FLAGS := -dynamiclib
else
TARGET := build/libscanner.so
SHARED_FLAGS := -fPIC -shared
endif

all: $(TARGET)
$(TARGET): src/scanner.c include/scanner.h
	mkdir -p build
	$(CC) $(CFLAGS) $(SHARED_FLAGS) -o $@ src/scanner.c -Iinclude
clean:
	rm -f build/scanner.dll build/libscanner.so build/libscanner.dylib
.PHONY: all clean

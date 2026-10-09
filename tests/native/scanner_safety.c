#include <stddef.h>
#include "scanner.h"

int main(void) {
    size_t emails = 1, digit_runs = 1, urls = 1;
    const char text[] = "user@example.test 123 https://example.test/\0tail";

    if (scan_text(NULL, 0, &emails, &digit_runs, &urls) != -1) return 1;
    if (scan_text("x", 1, NULL, &digit_runs, &urls) != -1) return 2;
    if (scan_text("", 0, &emails, &digit_runs, &urls) != 0) return 3;
    if (emails || digit_runs || urls) return 4;
    if (scan_text(text, sizeof(text) - 1, &emails, &digit_runs, &urls) != 0) return 5;
    if (emails != 1 || digit_runs != 1 || urls != 1) return 6;
    return 0;
}

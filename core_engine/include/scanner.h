#ifndef PROTEGER_SCANNER_H
#define PROTEGER_SCANNER_H
#include <stddef.h>
int scan_text(const char *text, size_t length, size_t *email_count, size_t *digit_run_count, size_t *url_count);
#endif

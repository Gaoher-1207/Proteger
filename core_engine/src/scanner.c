#include "scanner.h"
#include <ctype.h>

int scan_text(const char *text, size_t length, size_t *emails, size_t *digits, size_t *urls) {
    if (!text || !emails || !digits || !urls) return -1;
    *emails = *digits = *urls = 0;
    for (size_t i = 0; i < length; ++i) {
        if (text[i] == '@') ++*emails;
        if (isdigit((unsigned char)text[i]) && (i == 0 || !isdigit((unsigned char)text[i-1]))) ++*digits;
        if ((i + 7 <= length && (text[i]=='h' || text[i]=='H') && text[i+1]=='t' && text[i+2]=='t' && text[i+3]=='p' && text[i+4]==':' && text[i+5]=='/' && text[i+6]=='/') ||
            (i + 8 <= length && (text[i]=='h' || text[i]=='H') && text[i+1]=='t' && text[i+2]=='t' && text[i+3]=='p' && text[i+4]=='s' && text[i+5]==':' && text[i+6]=='/' && text[i+7]=='/')) ++*urls;
    }
    return 0;
}

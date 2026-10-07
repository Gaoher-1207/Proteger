import ctypes
import re
from app.config import LIBRARY_PATH

def scan_metrics(text):
    if not LIBRARY_PATH.exists():
        return {"email_markers": text.count("@"), "digit_runs": len(re.findall(r"\d+", text)), "urls": text.lower().count("http://") + text.lower().count("https://"), "engine": "python-fallback"}
    lib = ctypes.CDLL(str(LIBRARY_PATH))
    fn = lib.scan_text
    fn.argtypes = [ctypes.c_char_p, ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t), ctypes.POINTER(ctypes.c_size_t), ctypes.POINTER(ctypes.c_size_t)]
    fn.restype = ctypes.c_int
    data = text.encode("utf-8")
    a, b, c = ctypes.c_size_t(), ctypes.c_size_t(), ctypes.c_size_t()
    if fn(data, len(data), ctypes.byref(a), ctypes.byref(b), ctypes.byref(c)) != 0:
        raise RuntimeError("C scanner rejected input")
    return {"email_markers": a.value, "digit_runs": b.value, "urls": c.value, "engine": "c-ctypes"}

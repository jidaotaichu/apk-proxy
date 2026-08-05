#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""在 GitHub Actions runner(海外)上下载 binance/okx 官方 APK，校验后输出到 release"""
import urllib.request, re, sys, os, zipfile

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
OUTDIR = "apks"
os.makedirs(OUTDIR, exist_ok=True)

def get(url, timeout=90, binary=False):
    req = urllib.request.Request(url, headers=UA)
    return urllib.request.urlopen(req, timeout=timeout).read()

def apk_links_from_page(url):
    """从页面提取所有 .apk 直链"""
    links = set()
    try:
        html = get(url).decode("utf-8", "ignore")
    except Exception as e:
        print("  [page err]", url, e)
        return links
    for m in re.finditer(r'https?://[^\s"\'<>\\]+\.apk(?:\?[^\s"\'<>\\]*)?', html):
        links.add(m.group(0))
    # 也找转义过的
    for m in re.finditer(r'https?:\\/\\/[^\s"\'<>\\]+\\u002F[^\s"\'<>\\]*\.apk', html):
        links.add(m.group(0).replace("\\u002F", "/").replace("\\/", "/"))
    return links

def pick(links, pats):
    for l in links:
        if any(p in l.lower() for p in pats):
            return l
    return None

def dl(url, out):
    data = get(url, timeout=180)
    with open(out, "wb") as f:
        f.write(data)
    size = os.path.getsize(out)
    ok = "?"
    try:
        z = zipfile.ZipFile(out)
        bad = z.testzip()
        ok = "zip-OK" if bad is None else "ZIP-BAD:" + str(bad)
    except Exception as e:
        ok = "not-zip:" + str(e)
    print("  saved", out, size, "bytes |", ok, flush=True)
    return size > 100000 and ok.startswith("zip-OK")

def fetch(name, pages, pats, out):
    print("== fetch", name, flush=True)
    links = set()
    for p in pages:
        links |= apk_links_from_page(p)
        print("  page", p, "->", len(links), "apk links", flush=True)
    u = pick(links, pats)
    print("  chosen:", u, flush=True)
    if not u:
        return False
    return dl(u, out)

ok_all = True
# ---- Binance ----
pages = [
    "https://www.binance.com/en/download",
    "https://www.binance.com/zh-CN/download",
]
if not fetch("binance", pages, ["binance", "com.binance"], os.path.join(OUTDIR, "binance.apk")):
    ok_all = False

# ---- OKX ----
pages = [
    "https://www.okx.com/en/download",
    "https://www.okx.com/zh-hans/download",
    "https://www.okx.com/help/how-do-i-download-the-okx-app",
]
if not fetch("okx", pages, ["okx", "okex", "okinc"], os.path.join(OUTDIR, "okx.apk")):
    ok_all = False

print("ALL_OK" if ok_all else "PARTIAL", flush=True)
sys.exit(0 if ok_all else 1)

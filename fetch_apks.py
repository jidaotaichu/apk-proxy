#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GitHub Actions runner(海外) 下载 binance/okx 官方 APK, 多级 fallback"""
import urllib.request, re, sys, os, zipfile, html as htmlmod

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
OUTDIR = "apks"
os.makedirs(OUTDIR, exist_ok=True)

def get(url, timeout=120, referer=None):
    h = dict(UA)
    if referer:
        h["Referer"] = referer
    req = urllib.request.Request(url, headers=h)
    return urllib.request.urlopen(req, timeout=timeout).read()

def apk_links(html):
    links = set()
    for m in re.finditer(r'https?://[^\s"\'<>\\]+\.(?:apk|xapk)(?:\?[^\s"\'<>\\]*)?', html):
        links.add(htmlmod.unescape(m.group(0)))
    for m in re.finditer(r'https?:\\/\\/[^\s"\'<>\\]+\.(?:apk|xapk)', html):
        links.add(htmlmod.unescape(m.group(0)).replace("\\u002F", "/").replace("\\/", "/"))
    return links

def pick(links, pats):
    for l in links:
        if any(p in l.lower() for p in pats):
            return l
    return None

def try_page(url, pats, debug=False):
    try:
        html = get(url).decode("utf-8", "ignore")
    except Exception as e:
        print("  [page err]", url, repr(e)[:120], flush=True)
        return None
    links = apk_links(html)
    if debug:
        print("  [page]", url, "html_len=", len(html), "links=", len(links), flush=True)
        for l in list(links)[:5]:
            print("     ", l[:160], flush=True)
    return pick(links, pats)

def dl(url, out, referer=None):
    try:
        data = get(url, timeout=300, referer=referer)
    except Exception as e:
        print("  [dl err]", repr(e)[:150], flush=True)
        return False
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

def fetch(name, candidates, out):
    print("== fetch", name, flush=True)
    for src, url in candidates:
        u = try_page(url, [name.lower(), "binance", "okx", "okex", "okinc"], debug=True)
        if u:
            print("  chosen:", u[:180], flush=True)
            if dl(u, out, referer=url):
                return True
            else:
                print("  dl failed, try next", flush=True)
        else:
            print("  no link from", url, flush=True)
    print("  FAILED", name, flush=True)
    return False

ok_all = True
if not fetch("binance", [
    ("official-en", "https://www.binance.com/en/download"),
    ("official-zh", "https://www.binance.com/zh-CN/download"),
    ("apkpure", "https://apkpure.com/binance/com.binance.dev"),
    ("apkcombo", "https://apkcombo.com/binance/com.binance.dev/download/apk"),
    ("uptodown", "https://binance.en.uptodown.com/android/download"),
], os.path.join(OUTDIR, "binance.apk")):
    ok_all = False

if not fetch("okx", [
    ("official-en", "https://www.okx.com/en/download"),
    ("official-zh", "https://www.okx.com/zh-hans/download"),
    ("apkpure", "https://apkpure.com/okx/com.okinc.okex"),
    ("apkcombo", "https://apkcombo.com/okx/com.okinc.okex/download/apk"),
    ("uptodown", "https://okx.en.uptodown.com/android/download"),
], os.path.join(OUTDIR, "okx.apk")):
    ok_all = False

print("ALL_OK" if ok_all else "PARTIAL", flush=True)
sys.exit(0 if ok_all else 1)

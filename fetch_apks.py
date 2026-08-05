#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v3: 完整浏览器 headers + JSON 解析 + wayback + apkmirror"""
import urllib.request, re, sys, os, zipfile, json, html as htmlmod

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
HDR = {
    "User-Agent": UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
    "Accept-Encoding": "identity",
    "Referer": "https://www.google.com/",
    "sec-ch-ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "cross-site",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
    "Connection": "close",
}
OUTDIR = "apks"
os.makedirs(OUTDIR, exist_ok=True)

def get(url, timeout=90, raw=False):
    req = urllib.request.Request(url, headers=HDR)
    r = urllib.request.urlopen(req, timeout=timeout)
    return r.read() if raw else r.read().decode("utf-8", "ignore")

def norm(s):
    return htmlmod.unescape(s).replace("\\u002F", "/").replace("\\/", "/")

def apk_links(text):
    links = set()
    for m in re.finditer(r'https?://[^\s"\'<>\\]+\.(?:apk|xapk)(?:\?[^\s"\'<>\\]*)?', text):
        links.add(norm(m.group(0)))
    for m in re.finditer(r'https?:\\/\\/[^\s"\'<>\\]+\.(?:apk|xapk)', text):
        links.add(norm(m.group(0)))
    # JSON 里的 "url":"...apk"
    for m in re.finditer(r'"url"\s*:\s*"(https?[^"]+\.(?:apk|xapk)[^"]*)"', text):
        links.add(norm(m.group(1)))
    return links

def pick(links, pats):
    for l in links:
        if any(p in l.lower() for p in pats):
            return l
    return None

def try_page(url, pats, debug=False):
    try:
        html = get(url)
    except Exception as e:
        print("  [page err]", url, repr(e)[:100], flush=True)
        return None
    links = apk_links(html)
    if debug:
        print("  [page]", url, "html_len=", len(html), "links=", len(links), flush=True)
        for l in list(links)[:4]:
            print("     ", l[:160], flush=True)
    return pick(links, pats)

def dl(url, out, referer=None):
    h = dict(HDR)
    if referer:
        h["Referer"] = referer
    try:
        req = urllib.request.Request(url, headers=h)
        data = urllib.request.urlopen(req, timeout=300).read()
    except Exception as e:
        print("  [dl err]", repr(e)[:120], flush=True)
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
        u = try_page(url, [name.lower(), "binance", "okx", "okex", "okinc", "apk"], debug=True)
        if u:
            print("  chosen:", u[:180], flush=True)
            if dl(u, out, referer=url):
                return True
            print("  dl failed, next", flush=True)
        else:
            print("  no link from", src, flush=True)
    print("  FAILED", name, flush=True)
    return False

# OKX: 官方页 HTML 里搜 json 下载链接
print("== okx json scan ==", flush=True)
try:
    h = get("https://www.okx.com/zh-hans/download")
    for m in re.finditer(r'.{80}apk.{120}', h, re.I):
        print("  ...", m.group(0)[:200], flush=True)
except Exception as e:
    print("  okx err", e, flush=True)

ok_all = True
if not fetch("binance", [
    ("official-en", "https://www.binance.com/en/download"),
    ("official-zh", "https://www.binance.com/zh-CN/download"),
    ("apkpure", "https://apkpure.com/binance/com.binance.dev"),
    ("apkcombo", "https://apkcombo.com/binance/com.binance.dev/download/apk"),
    ("apkmirror", "https://www.apkmirror.com/apk/binance/"),
    ("apkfab", "https://apkfab.com/binance/com.binance.dev"),
], os.path.join(OUTDIR, "binance.apk")):
    ok_all = False

if not fetch("okx", [
    ("official-en", "https://www.okx.com/en/download"),
    ("official-zh", "https://www.okx.com/zh-hans/download"),
    ("apkpure", "https://apkpure.com/okx/com.okinc.okex"),
    ("apkcombo", "https://apkcombo.com/okx/com.okinc.okex/download/apk"),
    ("apkmirror", "https://www.apkmirror.com/apk/okx/"),
    ("apkfab", "https://apkfab.com/okx/com.okinc.okex"),
], os.path.join(OUTDIR, "okx.apk")):
    ok_all = False

print("ALL_OK" if ok_all else "PARTIAL", flush=True)
sys.exit(0 if ok_all else 1)

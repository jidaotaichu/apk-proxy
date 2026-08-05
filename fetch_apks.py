#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v4: 专攻 binance - CDN 探测 + wayback + 镜像 + evozi"""
import urllib.request, re, sys, os, zipfile, json, html as htmlmod

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
HDR = {
    "User-Agent": UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "identity",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Connection": "close",
}
OUTDIR = "apks"
os.makedirs(OUTDIR, exist_ok=True)

def get(url, timeout=60):
    req = urllib.request.Request(url, headers=HDR)
    r = urllib.request.urlopen(req, timeout=timeout)
    return r.read().decode("utf-8", "ignore")

def head(url, timeout=30):
    try:
        req = urllib.request.Request(url, headers=HDR, method="HEAD")
        r = urllib.request.urlopen(req, timeout=timeout)
        return r.status, dict(r.headers)
    except Exception as e:
        return getattr(e, "code", None), repr(e)[:80]

def norm(s):
    return htmlmod.unescape(s).replace("\\u002F", "/").replace("\\/", "/")

def apk_links(text):
    links = set()
    for m in re.finditer(r'https?://[^\s"\'<>\\]+\.(?:apk|xapk)(?:\?[^\s"\'<>\\]*)?', text):
        links.add(norm(m.group(0)))
    for m in re.finditer(r'"url"\s*:\s*"(https?[^"]+\.(?:apk|xapk)[^"]*)"', text):
        links.add(norm(m.group(1)))
    return links

def dl(url, out, referer=None, timeout=300):
    h = dict(HDR)
    if referer:
        h["Referer"] = referer
    try:
        req = urllib.request.Request(url, headers=h)
        data = urllib.request.urlopen(req, timeout=timeout).read()
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

# --- 0. OKX 已知直链 ---
print("== 0. okx known link ==", flush=True)
if dl("https://static.okx.com/upgradeapp/android.apk", os.path.join(OUTDIR, "okx.apk"), referer="https://www.okx.com/en/download"):
    print("OKX_OK", flush=True)
else:
    print("OKX_FAIL", flush=True)

# --- 1. CDN 域名探测 ---
print("== 1. cdn probe ==", flush=True)
for d in ["https://download.binance.com", "https://static.binance.com",
          "https://bin.bnbstatic.com", "https://www.binance.com/en/download"]:
    st, info = head(d)
    print("  ", d, "->", st, flush=True)

# --- 2. wayback 存档 ---
print("== 2. wayback ==", flush=True)
try:
    wb = json.loads(get("http://archive.org/wayback/available?url=www.binance.com/en/download&timestamp=2026"))
    snap = wb.get("archived_snapshots", {}).get("closest", {}).get("url")
    print("  snapshot:", snap, flush=True)
    if snap:
        html = get(snap.replace("http://", "https://"), timeout=90)
        links = apk_links(html)
        print("  links from snapshot:", len(links), flush=True)
        for l in list(links)[:5]:
            print("    ", l[:160], flush=True)
            if ".apk" in l and "binance" in l.lower():
                if dl(l, os.path.join(OUTDIR, "binance.apk"), referer=snap):
                    print("BINANCE_OK_VIA_WAYBACK", flush=True)
except Exception as e:
    print("  wayback err:", repr(e)[:150], flush=True)

# --- 3. 镜像站 ---
print("== 3. mirrors ==", flush=True)
for src, url in [
    ("apk.support", "https://apk.support/app/com.binance.dev"),
    ("apkhere", "https://apkhere.com/app/com.binance.dev"),
    ("apkmonk", "https://www.apkmonk.com/app/com.binance.dev/"),
    ("androidapksfree", "https://www.androidapksfree.com/apk/com-binance-dev-binance/"),
    ("apkdl", "https://apkdl.in/app/details?id=com.binance.dev"),
    ("apkcombo2", "https://apkcombo.com/binance/com.binance.dev/"),
]:
    try:
        html = get(url)
        links = apk_links(html)
        print("  ", src, "len=", len(html), "links=", len(links), flush=True)
        for l in list(links)[:3]:
            print("     ", l[:150], flush=True)
        if links:
            for l in links:
                if ".apk" in l.lower():
                    if dl(l, os.path.join(OUTDIR, "binance.apk"), referer=url):
                        print("BINANCE_OK_VIA_" + src, flush=True)
                        break
    except Exception as e:
        print("  ", src, "err:", repr(e)[:100], flush=True)

# --- 4. evozi (Google Play 下载器) ---
print("== 4. evozi ==", flush=True)
try:
    ev = get("https://apps.evozi.com/apk-downloader/?id=com.binance.dev", timeout=90)
    print("  evozi len:", len(ev), flush=True)
    m = re.search(r'https?://[^"\']+\.apk[^"\']*', ev)
    if m:
        print("  evozi link:", m.group(0)[:160], flush=True)
        if dl(m.group(0), os.path.join(OUTDIR, "binance.apk"), referer="https://apps.evozi.com/apk-downloader/"):
            print("BINANCE_OK_VIA_EVOZI", flush=True)
    else:
        print("  no apk link in evozi page", flush=True)
        print("  page sample:", ev[:400], flush=True)
except Exception as e:
    print("  evozi err:", repr(e)[:150], flush=True)

print("DONE", flush=True)

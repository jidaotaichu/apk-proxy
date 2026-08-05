#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v8: 精确 CDX + availability + 存档下载 binance; okx 直链"""
import urllib.request, re, sys, os, zipfile, json

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
OUTDIR = "apks"
os.makedirs(OUTDIR, exist_ok=True)

def get(url, timeout=90):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Encoding": "identity"})
    return urllib.request.urlopen(req, timeout=timeout).read()

def check(fn):
    if not os.path.exists(fn):
        return False
    size = os.path.getsize(fn)
    ok = "?"
    try:
        z = zipfile.ZipFile(fn)
        bad = z.testzip()
        ok = "zip-OK" if bad is None else "ZIP-BAD:" + str(bad)
    except Exception as e:
        ok = "not-zip:" + str(e)
    print("  ", fn, size, ok, flush=True)
    return size > 100000 and ok.startswith("zip-OK")

def dl_wayback(original, ts, out):
    u = "https://web.archive.org/web/%sid_/%s" % (ts, original)
    try:
        data = get(u, timeout=600)
        open(out, "wb").write(data)
        print("  wayback dl:", original[:100], len(data), flush=True)
        return True
    except Exception as e:
        print("  wayback dl err:", repr(e)[:100], flush=True)
        return False

def cdx(domain, extra, limit=30):
    url = ("http://web.archive.org/cdx/search/cdx?url=%s&matchType=domain&%s&limit=%d"
           "&output=json&collapse=urlkey" % (domain, extra, limit))
    try:
        data = get(url, timeout=120).decode("utf-8", "ignore")
        rows = json.loads(data)
        return rows[1:] if len(rows) > 1 else []
    except Exception as e:
        print("  cdx err:", repr(e)[:120], flush=True)
        return []

# ---- Binance ----
print("== binance cdx precise ==", flush=True)
rows = cdx("binance.com", "filter=original:.*\\.apk.*&filter=statuscode:200&fl=original,timestamp", 30)
for r in rows[:15]:
    print("  ", r, flush=True)
bin_ok = False
for orig, ts in rows:
    if ".apk" in orig and not bin_ok:
        if dl_wayback(orig, ts, os.path.join(OUTDIR, "binance.apk")):
            bin_ok = check(os.path.join(OUTDIR, "binance.apk"))

if not bin_ok:
    print("== binance availability ==", flush=True)
    try:
        av = json.loads(get("http://archive.org/wayback/available?url=www.binance.com/en/download&timestamp=20260701", timeout=60))
        snap = av.get("archived_snapshots", {}).get("closest", {})
        print("  snap:", snap.get("url"), snap.get("timestamp"), flush=True)
        if snap.get("url"):
            html = get(snap["url"].replace("http://", "https://"), timeout=120).decode("utf-8", "ignore")
            links = set(re.findall(r'https?://[^\s"\'<>\\]+\.(?:apk|xapk)', html))
            print("  apk links in snapshot:", list(links)[:5], flush=True)
            for l in links:
                if not bin_ok:
                    try:
                        data = get(l, timeout=300)
                        open(os.path.join(OUTDIR, "binance.apk"), "wb").write(data)
                        print("  dl:", l[:120], len(data), flush=True)
                        bin_ok = check(os.path.join(OUTDIR, "binance.apk"))
                    except Exception as e:
                        print("  dl err:", repr(e)[:100], flush=True)
    except Exception as e:
        print("  avail err:", repr(e)[:120], flush=True)

# ---- OKX ----
print("== okx ==", flush=True)
try:
    data = get("https://static.okx.com/upgradeapp/android.apk", timeout=600)
    open(os.path.join(OUTDIR, "okx.apk"), "wb").write(data)
    print("  okx downloaded", len(data), flush=True)
except Exception as e:
    print("  okx err:", repr(e)[:120], flush=True)
okx_ok = check(os.path.join(OUTDIR, "okx.apk"))

bin_ok = check(os.path.join(OUTDIR, "binance.apk"))
print("RESULT binance=%s okx=%s" % (bin_ok, okx_ok), flush=True)
sys.exit(0 if (bin_ok and okx_ok) else 1)

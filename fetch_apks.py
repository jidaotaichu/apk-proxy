#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v7: wayback CDX 找 binance/okx APK 存档并下载 + bapi 探测"""
import urllib.request, re, sys, os, zipfile, json

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
OUTDIR = "apks"
os.makedirs(OUTDIR, exist_ok=True)

def get(url, timeout=90, referer=None):
    h = {"User-Agent": UA, "Accept-Encoding": "identity"}
    if referer:
        h["Referer"] = referer
    req = urllib.request.Request(url, headers=h)
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

def cdx_find(domain, pat, limit=40):
    url = ("http://web.archive.org/cdx/search/cdx?url=%s*&filter=urlkey:.*%s.*&limit=%d"
           "&output=json&collapse=urlkey&fl=original,timestamp,statuscode,length&filter=statuscode:200" % (domain, pat, limit))
    try:
        data = get(url, timeout=90).decode("utf-8", "ignore")
        rows = json.loads(data)
        return rows[1:] if len(rows) > 1 else []
    except Exception as e:
        print("  cdx err:", repr(e)[:120], flush=True)
        return []

def dl_wayback(original, ts, out):
    u = "https://web.archive.org/web/%sid_/%s" % (ts, original)
    try:
        data = get(u, timeout=600)
        open(out, "wb").write(data)
        print("  wayback dl:", original, ts, len(data), flush=True)
        return True
    except Exception as e:
        print("  wayback dl err:", repr(e)[:120], flush=True)
        return False

ok_all = True

# ---- Binance ----
print("== binance cdx ==", flush=True)
rows = cdx_find("binance.com", r"\.apk")
for r in rows[:20]:
    print("  ", r, flush=True)
bin_done = False
for r in rows:
    if not bin_done and ".apk" in r[0]:
        if dl_wayback(r[0], r[1], os.path.join(OUTDIR, "binance.apk")):
            bin_done = check(os.path.join(OUTDIR, "binance.apk"))
if not bin_done:
    ok_all = False
    print("  binance wayback failed, try bapi", flush=True)
    # bapi 探测
    for ep in [
        "https://www.binance.com/bapi/asset/v2/public/asset-service/product/download-center/list",
        "https://www.binance.com/bapi/asset/v2/public/asset-service/product/download-center?type=android",
        "https://www.binance.com/gateway-api/v1/public/asset-service/product/download-center/list",
    ]:
        try:
            d = get(ep, timeout=30)
            print("  bapi", ep[:80], "->", len(d), d[:200], flush=True)
        except Exception as e:
            print("  bapi", ep[:80], "err", repr(e)[:80], flush=True)

# ---- OKX ----
print("== okx ==", flush=True)
if not check(os.path.join(OUTDIR, "okx.apk")):
    try:
        data = get("https://static.okx.com/upgradeapp/android.apk", timeout=600)
        open(os.path.join(OUTDIR, "okx.apk"), "wb").write(data)
        print("  okx downloaded", len(data), flush=True)
    except Exception as e:
        print("  okx err:", repr(e)[:120], flush=True)
        rows = cdx_find("okx.com", r"\.apk")
        for r in rows[:10]:
            print("  okx cdx:", r, flush=True)
        for r in rows:
            if ".apk" in r[0]:
                if dl_wayback(r[0], r[1], os.path.join(OUTDIR, "okx.apk")):
                    break
    check(os.path.join(OUTDIR, "okx.apk"))

bin_ok = check(os.path.join(OUTDIR, "binance.apk"))
okx_ok = check(os.path.join(OUTDIR, "okx.apk"))
print("RESULT binance=%s okx=%s" % (bin_ok, okx_ok), flush=True)
sys.exit(0 if (bin_ok and okx_ok) else 1)

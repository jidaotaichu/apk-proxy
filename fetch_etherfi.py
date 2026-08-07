#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fetch ether.fi app (etherfi.app) via APKPure API"""
import os, sys, json, urllib.request, urllib.error, zipfile

OUTDIR = "apks"
os.makedirs(OUTDIR, exist_ok=True)
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")

def http_get(url, headers=None, timeout=60):
    req = urllib.request.Request(url, headers=headers or {"User-Agent": UA})
    return urllib.request.urlopen(req, timeout=timeout)

ok = False
try:
    # APKPure 下载 API
    api_url = "https://apkpure.com/api/v1/apps/etherfi.app/download"
    print("API:", api_url, flush=True)
    try:
        r = http_get(api_url)
        data = json.loads(r.read().decode('utf-8', errors='replace'))
        print("API resp:", json.dumps(data)[:500], flush=True)
        dl_url = data.get("url") or data.get("download_url") or data.get("data", {}).get("url")
        if not dl_url and isinstance(data, dict):
            for k, v in data.items():
                if isinstance(v, str) and v.startswith("http"):
                    dl_url = v
                    break
        if dl_url:
            print("DL:", dl_url[:200], flush=True)
            r2 = http_get(dl_url, headers={"User-Agent": UA, "Referer": "https://apkpure.com/"}, timeout=600)
            fn = os.path.join(OUTDIR, "etherfi.apk")
            with open(fn, "wb") as f:
                total = 0
                while True:
                    c = r2.read(1 << 20)
                    if not c:
                        break
                    f.write(c)
                    total += len(c)
            print("saved", fn, total, "bytes", flush=True)
            ok = total > 100000
    except Exception as e:
        print("API err:", repr(e)[:200], flush=True)
except Exception as e:
    print("ERR:", repr(e)[:200], flush=True)

if ok:
    fn = os.path.join(OUTDIR, "etherfi.apk")
    try:
        z = zipfile.ZipFile(fn)
        bad = z.testzip()
        dex = sum(z.getinfo(n).file_size for n in z.namelist() if n.endswith(".dex"))
        libs = set(n.split("/")[1] for n in z.namelist() if n.startswith("lib/"))
        print("zip:", "OK" if bad is None else "BAD", "dex MB:", round(dex/1048576,1), "ABIs:", libs, flush=True)
        ok = bad is None and dex > 1000000
    except Exception as e:
        print("zip err:", repr(e)[:100], flush=True)

print("ETHERFI_OK" if ok else "ETHERFI_FAIL", flush=True)
sys.exit(0 if ok else 1)

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v5: okx 直链 + binance 用 playwright 真实浏览器过 Cloudflare 抓 APK"""
import os, sys, zipfile, urllib.request

OUTDIR = "apks"
os.makedirs(OUTDIR, exist_ok=True)
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")

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

# ---- OKX 直链 ----
print("== okx ==", flush=True)
try:
    req = urllib.request.Request("https://static.okx.com/upgradeapp/android.apk",
                                 headers={"User-Agent": UA})
    data = urllib.request.urlopen(req, timeout=600).read()
    open(os.path.join(OUTDIR, "okx.apk"), "wb").write(data)
    print("  okx downloaded", len(data), flush=True)
    check(os.path.join(OUTDIR, "okx.apk"))
except Exception as e:
    print("  okx err:", repr(e)[:150], flush=True)

# ---- Binance: playwright ----
print("== binance playwright ==", flush=True)
try:
    from playwright.sync_api import sync_playwright
except ImportError as e:
    print("  playwright not installed:", e, flush=True)
    sys.exit(1)

with sync_playwright() as p:
    b = p.chromium.launch(headless=False, args=["--no-sandbox", "--disable-blink-features=AutomationControlled"])
    ctx = b.new_context(user_agent=UA, accept_downloads=True, locale="en-US", viewport={"width": 1366, "height": 900})
    page = ctx.new_page()

    def click_and_capture(patterns, outfile, tries=12):
        for i in range(tries):
            try:
                with page.expect_download(timeout=12000) as dl_info:
                    clicked = page.evaluate("""(pats) => {
                        const els = [...document.querySelectorAll('a,button')];
                        for (const e of els) {
                            const t = (e.innerText||'').toLowerCase().trim();
                            if (t && pats.some(p => t.includes(p))) { e.click(); return t.slice(0,50); }
                        }
                        return null;
                    }""", patterns)
                    if not clicked:
                        print("  no clickable element, break", flush=True)
                        return False
                dl = dl_info.value
                dl.save_as(outfile)
                print("  captured:", dl.suggested_filename, "via", clicked, flush=True)
                return True
            except Exception as e:
                print("  attempt", i, repr(e)[:90], flush=True)
        return False

    # 1) binance 官方站
    try:
        page.goto("https://www.binance.com/en/download", timeout=60000, wait_until="domcontentloaded")
        page.wait_for_timeout(15000)
        print("  binance title:", page.title(), flush=True)
        if not click_and_capture(["download apk", "download for android", "android apk"], os.path.join(OUTDIR, "binance.apk")):
            links = page.eval_on_selector_all("a", "els => els.map(e=>e.href).filter(h=>h && h.includes('.apk'))")
            print("  href apk links:", links[:5], flush=True)
            if links:
                try:
                    req = urllib.request.Request(links[0], headers={"User-Agent": UA})
                    data = urllib.request.urlopen(req, timeout=300).read()
                    open(os.path.join(OUTDIR, "binance.apk"), "wb").write(data)
                    print("  downloaded from href", flush=True)
                except Exception as e:
                    print("  href dl err:", repr(e)[:100], flush=True)
    except Exception as e:
        print("  binance page err:", repr(e)[:150], flush=True)

    # 2) apkpure fallback
    if not check(os.path.join(OUTDIR, "binance.apk")):
        print("  fallback apkpure", flush=True)
        try:
            page.goto("https://apkpure.com/binance/com.binance.dev", timeout=60000, wait_until="domcontentloaded")
            page.wait_for_timeout(10000)
            print("  apkpure title:", page.title(), flush=True)
            if not click_and_capture(["download apk", "download"], os.path.join(OUTDIR, "binance.apk")):
                links = page.eval_on_selector_all("a", "els => els.map(e=>e.href).filter(h=>h && (h.includes('.apk')||h.includes('cdnpure')))")
                print("  apkpure links:", links[:5], flush=True)
                if links:
                    try:
                        req = urllib.request.Request(links[0], headers={"User-Agent": UA, "Referer": "https://apkpure.com/"})
                        data = urllib.request.urlopen(req, timeout=300).read()
                        open(os.path.join(OUTDIR, "binance.apk"), "wb").write(data)
                        print("  apkpure downloaded from href", flush=True)
                    except Exception as e:
                        print("  apkpure href dl err:", repr(e)[:100], flush=True)
        except Exception as e:
            print("  apkpure err:", repr(e)[:150], flush=True)

    b.close()

ok = check(os.path.join(OUTDIR, "binance.apk")) and check(os.path.join(OUTDIR, "okx.apk"))
print("ALL_OK" if ok else "PARTIAL", flush=True)
sys.exit(0 if ok else 1)

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v11: playwright stealth + apkpure 下载 binance 官方签名原版"""
import os, sys, zipfile, json

OUTDIR = "apks"
os.makedirs(OUTDIR, exist_ok=True)
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")

from playwright.sync_api import sync_playwright
import stealth

bin_ok = False
with sync_playwright() as p:
    b = p.chromium.launch(headless=False, args=["--no-sandbox", "--disable-blink-features=AutomationControlled"])
    ctx = b.new_context(user_agent=UA, accept_downloads=True, locale="en-US", viewport={"width": 1366, "height": 900})
    page = ctx.new_page()
    stealth.apply_sleights(page)

    def click_download():
        """点击下载按钮并捕获文件"""
        for pat in [["download apk"], ["download"], ["apk"]]:
            try:
                with page.expect_download(timeout=25000) as dl_info:
                    clicked = page.evaluate("""(pats) => {
                        const els = [...document.querySelectorAll('button,a')];
                        for (const e of els) {
                            const t = (e.innerText||'').toLowerCase().trim();
                            if (t && pats.some(p => t.includes(p))) { e.click(); return t.slice(0,50); }
                        }
                        return null;
                    }""", pat)
                    if not clicked:
                        print("  no element for", pat, flush=True)
                        continue
                dl = dl_info.value
                dl.save_as(os.path.join(OUTDIR, "binance.apk"))
                print("  CAPTURED via", clicked, "->", dl.suggested_filename, flush=True)
                return True
            except Exception as e:
                print("  click", pat, "err:", repr(e)[:70], flush=True)
        return False

    for url in ["https://apkpure.com/binance/com.binance.dev",
                "https://apkpure.com/cn/binance/com.binance.dev"]:
        try:
            page.goto(url, timeout=90000, wait_until="domcontentloaded")
            passed = False
            for i in range(8):
                page.wait_for_timeout(10000)
                t = page.title()
                print("  [%s] t+%ds title=%r" % (url[:35], (i+1)*10, t[:60]), flush=True)
                if t and "moment" not in t.lower() and "just a" not in t.lower():
                    passed = True
                    break
            if not passed:
                print("  CF not passed", flush=True)
                continue
            print("  page loaded:", page.title(), flush=True)
            if click_download():
                break
            # 可能跳到下载确认页
            if "download" in page.url:
                print("  on download page:", page.url[:80], flush=True)
                if click_download():
                    break
            # 检查 d.cdnpure 链接
            links = page.eval_on_selector_all("a", "els => els.map(e=>e.href).filter(h=>h && h.includes('cdnpure'))")
            print("  cdnpure links:", links[:3], flush=True)
            if links:
                import urllib.request
                try:
                    req = urllib.request.Request(links[0], headers={"User-Agent": UA, "Referer": url})
                    data = urllib.request.urlopen(req, timeout=300).read()
                    open(os.path.join(OUTDIR, "binance.apk"), "wb").write(data)
                    print("  dl cdnpure:", len(data), flush=True)
                    break
                except Exception as e:
                    print("  cdnpure dl err:", repr(e)[:80], flush=True)
        except Exception as e:
            print("  page err:", repr(e)[:120], flush=True)
    b.close()

fn = os.path.join(OUTDIR, "binance.apk")
if os.path.exists(fn):
    size = os.path.getsize(fn)
    print("  file size:", size, flush=True)
    if size > 100000:
        try:
            z = zipfile.ZipFile(fn)
            bad = z.testzip()
            dex = sum(z.getinfo(n).file_size for n in z.namelist() if n.endswith(".dex"))
            libs = set(n.split("/")[1] for n in z.namelist() if n.startswith("lib/"))
            print("  zip:", "OK" if bad is None else "BAD", "dex MB:", round(dex/1048576,1), "ABIs:", libs, flush=True)
            bin_ok = bad is None and dex > 10000000
        except Exception as e:
            print("  zip err:", repr(e)[:80], flush=True)

print("BINANCE_OK" if bin_ok else "BINANCE_FAIL", flush=True)
sys.exit(0 if bin_ok else 1)

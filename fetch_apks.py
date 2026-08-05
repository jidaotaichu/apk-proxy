#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v10: playwright-stealth 专攻 binance.com 官方下载页"""
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
    ctx = b.new_context(user_agent=UA, accept_downloads=True, locale="zh-CN", viewport={"width": 1366, "height": 900})
    page = ctx.new_page()
    stealth.apply_sleights(page)

    apk_urls = []
    def on_response(resp):
        try:
            u = resp.url
            if ".apk" in u.lower():
                apk_urls.append(u)
                print("  [net-apk]", u[:200], flush=True)
        except Exception:
            pass
    page.on("response", on_response)

    try:
        page.goto("https://www.binance.com/en/download", timeout=90000, wait_until="domcontentloaded")
        # 等 CF 挑战(最长 90s)
        passed = False
        for i in range(9):
            page.wait_for_timeout(10000)
            t = page.title()
            print("  t+%ds title=%r" % ((i+1)*10, t[:60]), flush=True)
            if t and "moment" not in t.lower() and "just a" not in t.lower() and "attention" not in t.lower():
                passed = True
                break
        if not passed:
            print("  CF challenge did not pass", flush=True)
        else:
            # dump 按钮
            info = page.evaluate("""() => {
                const out = {btns: [], links: []};
                document.querySelectorAll('button').forEach(e => {
                    const t = (e.innerText||'').trim().slice(0,45);
                    if (t && out.btns.length < 25) out.btns.push(t);
                });
                document.querySelectorAll('a').forEach(e => {
                    const t = (e.innerText||'').trim().slice(0,45);
                    if (t && out.links.length < 25) out.links.push(t + ' => ' + (e.href||'').slice(0,100));
                });
                return out;
            }""")
            print("  BUTTONS:", json.dumps(info["btns"], ensure_ascii=False), flush=True)
            print("  LINKS:", json.dumps(info["links"], ensure_ascii=False), flush=True)

            # 点击流程: Download -> Android -> APK
            for pat in [["download"], ["android"], ["apk"]]:
                try:
                    with page.expect_download(timeout=20000) as dl_info:
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
                    bin_ok = os.path.getsize(os.path.join(OUTDIR, "binance.apk")) > 100000
                    break
                except Exception as e:
                    print("  click", pat, "err:", repr(e)[:70], flush=True)
    except Exception as e:
        print("  page err:", repr(e)[:150], flush=True)

    print("  network apk urls:", apk_urls[:5], flush=True)
    b.close()

fn = os.path.join(OUTDIR, "binance.apk")
if os.path.exists(fn):
    size = os.path.getsize(fn)
    print("  file size:", size, flush=True)
    if size > 100000:
        try:
            z = zipfile.ZipFile(fn)
            bad = z.testzip()
            print("  zip:", "OK" if bad is None else "BAD", flush=True)
            libs = set(n.split("/")[1] for n in z.namelist() if n.startswith("lib/"))
            print("  ABIs:", libs, flush=True)
            dex = sum(z.getinfo(n).file_size for n in z.namelist() if n.endswith(".dex"))
            print("  dex MB:", round(dex/1048576, 1), flush=True)
            bin_ok = bad is None and dex > 10000000  # dex > 10MB 才算完整版
        except Exception as e:
            print("  zip err:", repr(e)[:80], flush=True)

print("BINANCE_OK" if bin_ok else "BINANCE_FAIL", flush=True)
sys.exit(0 if bin_ok else 1)

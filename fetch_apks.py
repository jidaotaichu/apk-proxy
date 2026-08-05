#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v9: 多域名 urllib 快测 + playwright-stealth 兜底"""
import urllib.request, re, sys, os, zipfile, json

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
OUTDIR = "apks"
os.makedirs(OUTDIR, exist_ok=True)

def get(url, timeout=45):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Encoding": "identity",
                                               "Accept-Language": "en-US,en;q=0.9"})
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

def links_in(html):
    out = set()
    for m in re.finditer(r'https?://[^\s"\'<>\\]+\.(?:apk|xapk)(?:\?[^\s"\'<>\\]*)?', html):
        out.add(m.group(0))
    return out

def quick_try(url):
    try:
        html = get(url).decode("utf-8", "ignore")
    except Exception as e:
        print("  [q] err", url[:60], repr(e)[:60], flush=True)
        return None
    links = links_in(html)
    print("  [q]", url[:70], "len=", len(html), "links=", len(links), flush=True)
    for l in list(links)[:3]:
        print("     ", l[:150], flush=True)
    for l in links:
        if ".apk" in l.lower():
            return l
    return None

# ---- urllib 快测多个域名 ----
print("== quick domain probes ==", flush=True)
probe_urls = [
    "https://apkpure.net/binance/com.binance.dev",
    "https://apkpure.co/binance/com.binance.dev",
    "https://apkpure.mobi/binance/com.binance.dev",
    "https://apkcombo.net/binance/com.binance.dev/",
    "https://m.apkpure.com/binance/com.binance.dev",
    "https://www.apk.support/app/com.binance.dev",
    "https://apkmonk.com/app/com.binance.dev",
    "https://apkhome.net/app/com.binance.dev",
    "https://www.androidapksfree.com/apk/com-binance-dev-binance/",
    "https://apk-dl.com/binance/com.binance.dev",
]
bin_ok = False
for u in probe_urls:
    l = quick_try(u)
    if l and not bin_ok:
        try:
            data = get(l, timeout=300)
            open(os.path.join(OUTDIR, "binance.apk"), "wb").write(data)
            print("  downloaded", l[:100], len(data), flush=True)
            bin_ok = check(os.path.join(OUTDIR, "binance.apk"))
        except Exception as e:
            print("  dl err:", repr(e)[:100], flush=True)

# ---- playwright-stealth 兜底 ----
if not bin_ok:
    print("== playwright stealth ==", flush=True)
    try:
        from playwright.sync_api import sync_playwright
        import stealth  # playwright-stealth
    except ImportError as e:
        print("  stealth not installed:", e, flush=True)
        sys.exit(1)
    with sync_playwright() as p:
        b = p.chromium.launch(headless=False, args=["--no-sandbox", "--disable-blink-features=AutomationControlled"])
        ctx = b.new_context(user_agent=UA, accept_downloads=True, locale="en-US", viewport={"width": 1366, "height": 900})
        page = ctx.new_page()
        stealth.apply_sleights(page)
        for url in ["https://apkpure.com/binance/com.binance.dev", "https://www.binance.com/en/download"]:
            try:
                page.goto(url, timeout=90000, wait_until="domcontentloaded")
                for i in range(6):
                    page.wait_for_timeout(10000)
                    t = page.title()
                    print("  ", url[:40], "wait", (i+1)*10, "s:", t[:60], flush=True)
                    if "moment" not in t.lower() and t:
                        break
                info = page.evaluate("""() => {
                    const btns = [];
                    document.querySelectorAll('button,a').forEach(e => {
                        const t = (e.innerText||'').trim();
                        if (t && /download|apk|android/i.test(t) && btns.length < 12) btns.push(t.slice(0,40));
                    });
                    return btns;
                }""")
                print("  download-ish:", json.dumps(info, ensure_ascii=False), flush=True)
                for pat in [["download apk"], ["download"], ["apk"]]:
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
                                continue
                        dl = dl_info.value
                        dl.save_as(os.path.join(OUTDIR, "binance.apk"))
                        print("  CAPTURED via", clicked, flush=True)
                        bin_ok = check(os.path.join(OUTDIR, "binance.apk"))
                        break
                    except Exception as e:
                        print("  click", pat, "err", repr(e)[:70], flush=True)
                if bin_ok:
                    break
            except Exception as e:
                print("  page err", url[:40], repr(e)[:100], flush=True)
        b.close()

print("BINANCE_OK" if bin_ok else "BINANCE_FAIL", flush=True)
sys.exit(0 if bin_ok else 1)

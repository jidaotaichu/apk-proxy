#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v6: binance playwright - 分步点击 + network 监听 + dump 页面"""
import os, sys, zipfile, json

OUTDIR = "apks"
os.makedirs(OUTDIR, exist_ok=True)
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")

from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    b = p.chromium.launch(headless=False, args=["--no-sandbox", "--disable-blink-features=AutomationControlled"])
    ctx = b.new_context(user_agent=UA, accept_downloads=True, locale="en-US", viewport={"width": 1366, "height": 900})
    page = ctx.new_page()

    apk_urls = []
    def on_response(resp):
        try:
            u = resp.url
            if "apk" in u.lower() or "download" in u.lower():
                ct = resp.headers.get("content-type", "")
                if "json" in ct or "apk" in u.lower():
                    apk_urls.append(u)
                    print("  [net]", u[:200], ct[:40], flush=True)
        except Exception:
            pass
    page.on("response", on_response)

    try:
        page.goto("https://www.binance.com/en/download", timeout=90000, wait_until="domcontentloaded")
        # 等 Cloudflare 挑战
        for i in range(6):
            page.wait_for_timeout(10000)
            t = page.title()
            print("  wait", (i+1)*10, "s title:", t, flush=True)
            if "binance" in t.lower() or "币安" in t:
                break
        print("  final title:", page.title(), flush=True)

        # dump 所有可见按钮和链接文本
        info = page.evaluate("""() => {
            const out = {btns: [], links: []};
            document.querySelectorAll('button, a').forEach(e => {
                const t = (e.innerText||'').trim().slice(0,50);
                if (t && (e.tagName==='BUTTON' || e.href)) {
                    if (e.tagName==='BUTTON') out.btns.push(t);
                    else out.links.push(t + ' => ' + e.href.slice(0,120));
                }
            });
            return out;
        }""")
        print("  BUTTONS:", json.dumps(info["btns"][:30], ensure_ascii=False), flush=True)
        print("  LINKS:", json.dumps(info["links"][:30], ensure_ascii=False), flush=True)

        # 尝试分步点击: Download -> Android -> APK
        for pat in [["download"], ["android", "apk"], ["apk"]]:
            try:
                with page.expect_download(timeout=15000) as dl_info:
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
                print("  CAPTURED via", clicked, dl.suggested_filename, flush=True)
                break
            except Exception as e:
                print("  click", pat, "err:", repr(e)[:80], flush=True)

        # 检查页面里所有含 apk 的 URL
        urls = page.evaluate("""() => {
            const s = document.documentElement.outerHTML;
            const m = s.match(/https?:\\/\\/[^\"'\\s]+\\.apk[^\"'\\s]*/g) || [];
            return m.slice(0,10);
        }""")
        print("  apk urls in html:", urls, flush=True)
    except Exception as e:
        print("  binance err:", repr(e)[:200], flush=True)

    print("  network apk urls:", apk_urls[:10], flush=True)
    b.close()

fn = os.path.join(OUTDIR, "binance.apk")
if os.path.exists(fn):
    print("  size:", os.path.getsize(fn), flush=True)
print("DONE", flush=True)

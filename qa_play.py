#!/usr/bin/env python3
"""Playwright QA for Skyline Riot v0.1."""
import asyncio, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SHOTS = ROOT / "shots"
SHOTS.mkdir(exist_ok=True)
BASE = "http://127.0.0.1:8765/"

async def run():
    from playwright.async_api import async_playwright
    results = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        viewports = [("portrait", 390, 844), ("landscape", 844, 390), ("desktop", 1280, 720)]

        for name, w, h in viewports:
            errs = []
            page = await browser.new_page(viewport={"width": w, "height": h})
            page.on("console", lambda m: errs.append(f"console:{m.text}") if m.type == "error" else None)
            page.on("pageerror", lambda e: errs.append(f"page:{e}"))
            await page.goto(BASE, wait_until="networkidle", timeout=60000)
            await page.wait_for_function("() => window.__SR && window.THREE", timeout=15000)
            await page.wait_for_timeout(500)
            await page.screenshot(path=str(SHOTS / f"title_{name}.png"))

            await page.click("#btnStart")
            await page.wait_for_timeout(300)
            st = await page.evaluate("() => window.__SR.getState()")
            assert st["mode"] == "play", st

            # Move with keys
            await page.keyboard.down("KeyW")
            await page.wait_for_timeout(400)
            await page.evaluate("() => window.__SR.jump()")
            await page.wait_for_timeout(350)
            await page.screenshot(path=str(SHOTS / f"gameplay_{name}.png"))

            # Grind
            ok = await page.evaluate("() => window.__SR.snapGrind()")
            await page.wait_for_timeout(200)
            st = await page.evaluate("() => window.__SR.getState()")
            await page.screenshot(path=str(SHOTS / f"grind_{name}.png"))
            print(f"[{name}] grind ok={ok} state={st['playerState']}")

            # Airborne
            await page.evaluate("() => window.__SR.launchAir()")
            await page.wait_for_timeout(150)
            await page.screenshot(path=str(SHOTS / f"airborne_{name}.png"))
            st = await page.evaluate("() => window.__SR.getState()")
            print(f"[{name}] air state={st['playerState']}")

            # Tag
            await page.evaluate("() => window.__SR.forceTag(0)")
            await page.wait_for_timeout(100)
            await page.keyboard.press("KeyF")
            await page.wait_for_timeout(200)
            st = await page.evaluate("() => window.__SR.getState()")
            await page.screenshot(path=str(SHOTS / f"tag_{name}.png"))
            print(f"[{name}] tags={st['tagsDone']} score={st['score']}")

            await page.keyboard.up("KeyW")
            real = [e for e in errs if "favicon" not in e.lower() and "Download the React" not in e]
            results.append({"vp": name, "errs": real, "state": st})
            for e in real:
                print("  ERR", e)
            await page.close()

        # Canonical shots
        page = await browser.new_page(viewport={"width": 1280, "height": 720})
        errs = []
        page.on("pageerror", lambda e: errs.append(str(e)))
        await page.goto(BASE, wait_until="networkidle")
        await page.wait_for_function("() => window.__SR")
        await page.wait_for_timeout(400)
        await page.screenshot(path=str(SHOTS / "title.png"))
        await page.click("#btnStart")
        await page.wait_for_timeout(200)
        await page.evaluate("() => { window.__SR.snapGrind(); }")
        await page.wait_for_timeout(250)
        await page.screenshot(path=str(SHOTS / "gameplay_grind.png"))
        await page.evaluate("() => window.__SR.launchAir()")
        await page.wait_for_timeout(120)
        await page.screenshot(path=str(SHOTS / "gameplay_airborne.png"))
        await page.evaluate("() => window.__SR.forceTag(0)")
        await page.wait_for_timeout(80)
        await page.keyboard.press("KeyF")
        await page.wait_for_timeout(250)
        await page.screenshot(path=str(SHOTS / "tag.png"))
        # also how-to and a free roam shot
        await page.click("#pauseBtn")
        await page.wait_for_timeout(200)
        await page.click("#btnToMenu")
        await page.wait_for_timeout(200)
        await page.click("#btnHow")
        await page.wait_for_timeout(200)
        await page.screenshot(path=str(SHOTS / "howto.png"))
        st = await page.evaluate("() => window.__SR.getState()")
        print("CANONICAL final mode", st.get("mode"), "errs", errs)
        results.append({"vp": "canonical", "errs": errs, "state": st})
        await page.close()
        await browser.close()

    failed = [r for r in results if r["errs"]]
    tags_ok = any((r.get("state") or {}).get("tagsDone", 0) > 0 for r in results)
    print("SUMMARY viewports", len(results), "with_errors", len(failed), "tagged", tags_ok)
    return 0 if not failed and tags_ok else 1

if __name__ == "__main__":
    sys.exit(asyncio.run(run()))

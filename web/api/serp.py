import sys
import json
import asyncio
import os
from urllib.parse import urlparse, unquote
from playwright.async_api import async_playwright

def determine_page_type(url):
    path = urlparse(url).path.lower()
    if path == "" or path == "/": return "homepage"
    if "blog" in path or "article" in path or "news" in path or "guide" in path: return "blog"
    if "product" in path or "item" in path or "/p/" in path: return "product"
    if "category" in path or "collection" in path: return "category"
    return "informational"

async def scrape_google(keyword, country="us"):
    async with async_playwright() as p:
        
        # PROXY INFRASTRUCTURE INTEGRATION (Reads securely from your server .env)
        proxy_server = os.getenv("PROXY_SERVER")
        proxy_username = os.getenv("PROXY_USERNAME")
        proxy_password = os.getenv("PROXY_PASSWORD")

        launch_args = {
            "headless": True,
            "args": ["--disable-blink-features=AutomationControlled"]
        }

        # If you add proxies to your server, Playwright activates them here automatically
        if proxy_server:
            launch_args["proxy"] = {
                "server": proxy_server,
                "username": proxy_username,
                "password": proxy_password
            }

        browser = await p.chromium.launch(**launch_args)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            locale="en-US"
        )
        await context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        page = await context.new_page()
        
        try:
            search_url = f"https://www.google.com/search?q={keyword}&gl={country}&hl=en"
            await page.goto(search_url, wait_until="domcontentloaded")
            await page.wait_for_timeout(2000)
            
            features_found = ["Organic"]
            
            ads_present = await page.locator("text='Sponsored'").count() > 0 or await page.locator("text='Ad'").count() > 0
            if ads_present: features_found.append("Ads")
                
            paa_present = await page.locator("text='People also ask'").count() > 0
            if paa_present: features_found.append("People Also Ask")
                
            snippet_present = await page.locator("div[data-attrid='wa:/description']").count() > 0 or await page.locator(".c2xzTb").count() > 0
            if snippet_present: features_found.append("Featured Snippet")

            results = []
            elements = await page.locator("a:has(h3)").all()
            
            position = 1
            for el in elements:
                if position > 10: break
                url = await el.get_attribute("href")
                if not url: continue
                
                if url.startswith("/url?q="):
                    url = url.split("/url?q=")[1].split("&")[0]
                    url = unquote(url)
                    
                if not url.startswith("http") or "google.com" in url: continue
                    
                domain = urlparse(url).netloc.replace("www.", "")
                page_type = determine_page_type(url)
                
                results.append({
                    "position": position,
                    "url": url,
                    "domain": domain,
                    "page_type": page_type
                })
                position += 1
                
            await browser.close()
            return {
                "keyword": keyword,
                "country": country,
                "success": True if len(results) > 0 else False,
                "urls": [r["url"] for r in results],
                "detailed_results": results,
                "serp_features": features_found
            }
            
        except Exception as e:
            await browser.close()
            return {"keyword": keyword, "success": False, "error": str(e)}

if __name__ == "__main__":
    if len(sys.argv) > 1:
        target_keyword = sys.argv[1]
        target_country = sys.argv[2] if len(sys.argv) > 2 else "us"
        print(json.dumps(asyncio.run(scrape_google(target_keyword, target_country))))
    else:
        print(json.dumps(asyncio.run(scrape_google("seo software", "us"))))
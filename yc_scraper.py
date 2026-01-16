import asyncio
import pandas as pd
from playwright.async_api import async_playwright
from datetime import datetime
import random

# --- CONFIGURATION ---
TARGET_URL = "https://www.ycombinator.com/companies"
TARGET_COUNT = 500          # Goal: Scrape 500 unique startups
CONCURRENCY_LIMIT = 3       # Max number of browser tabs open at once (prevents rate-limiting)
BATCH_SIZE = 50             # Save progress to CSV after every 50 companies

async def scroll_and_extract_links(page, target_count):
    """
    Handles infinite scrolling on the main directory page to collect startup URLs.
    """
    print(f"[*] Navigating to {TARGET_URL}...")
    await page.goto(TARGET_URL, timeout=60000)
    
    company_links = set()
    scroll_attempts = 0
    
    # Continue scrolling until we reach the target count or a safety limit
    while len(company_links) < target_count and scroll_attempts < 150:
        # Locate all links that point to company profiles
        links = await page.locator('a[href^="/companies/"]').all()
        for link in links:
            href = await link.get_attribute('href')
            if href and "/companies/" in href:
                full_url = f"https://www.ycombinator.com{href}"
                company_links.add(full_url)
        
        if len(company_links) >= target_count:
            break

        # Execute JavaScript to scroll to the bottom of the page to trigger lazy-loading
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await page.wait_for_timeout(2000) # Wait for new companies to load
        scroll_attempts += 1
    
    print(f"[*] Collected {len(company_links)} company URLs.")
    return list(company_links)[:target_count]

async def scrape_company_details(context, url, semaphore):
    """
    Visits an individual company profile to extract deep-level data.
    """
    async with semaphore: # Ensure only 'CONCURRENCY_LIMIT' tasks run at once
        for attempt in range(2): # Simple retry logic for network stability
            page = await context.new_page()
            try:
                # OPTIMIZATION: Block heavy assets like images/CSS to save bandwidth and speed up loading
                await page.route("**/*", lambda route: route.abort() 
                                 if route.request.resource_type in ["image", "font", "stylesheet"] 
                                 else route.continue_())
                
                # Human-like behavior: Random delay before navigating
                await asyncio.sleep(random.uniform(1, 2))
                await page.goto(url, timeout=40000, wait_until="domcontentloaded")
                
                # SMART DISCOVERY: Wait for LinkedIn links to "hydrate" (render via JS) 
                try:
                    await page.wait_for_selector('a[href*="linkedin.com/in/"]', timeout=3000)
                except:
                    pass # Continue even if no LinkedIn is found

                # --- 1. Basic Data Extraction ---
                name = await page.locator("h1").first.inner_text()
                
                # Extract the YC Batch (e.g., W24, S22) via href pattern
                batch = "N/A"
                batch_loc = page.locator("a[href*='batch=']").first
                if await batch_loc.is_visible():
                    batch = await batch_loc.inner_text()

                # Extract the short company description
                desc = "N/A"
                desc_loc = page.locator("p.whitespace-pre-line, div.text-xl").first
                if await desc_loc.is_visible():
                    desc = await desc_loc.inner_text()

                # --- 2. Founder & LinkedIn Enrichment ---
                founder_names = []
                founder_links = []

                # Find all unique LinkedIn URLs on the profile page
                li_elements = await page.locator('a[href*="linkedin.com/in/"]').all()
                for li in li_elements:
                    link = await li.get_attribute("href")
                    if link:
                        # CLEANUP: Remove tracking parameters (?miniProfile...) and trailing slashes
                        clean_link = link.split('?')[0].rstrip('/')
                        if clean_link not in founder_links:
                            founder_links.append(clean_link)

                # HEURISTIC NAME DISCOVERY: Target bolded text/headers in the founder section
                name_selectors = ["div.font-bold", "h3"]
                for selector in name_selectors:
                    elements = await page.locator(selector).all()
                    for el in elements:
                        text = (await el.inner_text()).strip()
                        # FILTER: Real names are usually 1-3 words. Ignore UI buttons/headers.
                        if 0 < len(text.split()) <= 3:
                            blacklist = ["Founders", "Jobs", "Blog", "Team", "Company", "Launch", "News"]
                            if not any(word in text for word in blacklist):
                                if text not in founder_names:
                                    founder_names.append(text)

                await page.close()
                
                # Return dictionary for easy DataFrame conversion
                return {
                    "Company Name": name.strip(),
                    "Batch": batch.strip(),
                    "Short Description": desc.strip(),
                    "Founder Name(s)": ", ".join(founder_names),
                    "Founder LinkedIn URL(s)": ", ".join(founder_links)
                }

            except Exception as e:
                await page.close()
                if attempt == 1: # On second failure, return error placeholders
                    return {"Company Name": "Error", "URL": url}
                await asyncio.sleep(3) # Wait before retrying

async def main():
    """
    Orchestrates the scraping process: Navigation -> Enrichment -> Export.
    """
    async with async_playwright() as p:
        # Launch headless Chromium browser
        browser = await p.chromium.launch(headless=True)
        # Use a standard User-Agent to avoid generic bot detection
        context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        # PHASE 1: Collect the 500 URLs from the directory
        page = await context.new_page()
        urls = await scroll_and_extract_links(page, TARGET_COUNT)
        await page.close()

        # PHASE 2: Deep-Scrape each individual company profile
        print(f"[*] Scraping {len(urls)} profiles...")
        semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)
        results = []

        # Process companies in batches to show progress and save incrementally
        for i in range(0, len(urls), BATCH_SIZE):
            batch_urls = urls[i:i + BATCH_SIZE]
            print(f"[*] Processing batch {i//BATCH_SIZE + 1}...")
            
            # Create concurrent tasks for the current batch
            tasks = [scrape_company_details(context, u, semaphore) for u in batch_urls]
            batch_data = await asyncio.gather(*tasks)
            results.extend([r for r in batch_data if r is not None])
            
            # INTERIM SAVE: Prevents data loss if the script crashes or internet drops
            try:
                pd.DataFrame(results).to_csv("yc_scraping_progress.csv", index=False)
            except PermissionError:
                # Occurs if the user has the CSV file open in Excel during the write
                print("[!] Permission Denied: Close Excel to allow progress saving!")

        await browser.close()
        
        # FINAL EXPORT: Save the complete dataset with a timestamped filename
        df = pd.DataFrame(results)
        final_filename = f"yc_scraping_{datetime.now().strftime('%Y%m%d')}.csv"
        df.to_csv(final_filename, index=False)
        print(f"[*] Done! Final data saved to {final_filename}")

if __name__ == "__main__":
    # Entry point for the asynchronous event loop
    asyncio.run(main())
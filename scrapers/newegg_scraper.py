"""
newegg_scraper.py — Newegg (Selenium with undetected-chromedriver)
"""

import re
import time
import urllib.parse
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

class NeweggScraper:
    SITE = "Newegg"

    def __init__(self, driver):
        self.driver = driver

    def scrape(self, product_name: str) -> list[dict]:
        print(f"[Newegg] Searching for: {product_name}")
        query = urllib.parse.quote_plus(product_name)
        
        # رابط مع شرط جديد وبدون شرط
        urls = [
            f"https://www.newegg.com/p/pl?d={query}&N=4131",
            f"https://www.newegg.com/p/pl?d={query}"
        ]
        
        for url in urls:
            try:
                self.driver.get(url)
                time.sleep(4)
                
                # التمرير لأسفل
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
                
                try:
                    WebDriverWait(self.driver, 20).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, ".item-cell, .item-container, [class*='item']"))
                    )
                except TimeoutException:
                    continue
                
                soup = BeautifulSoup(self.driver.page_source, "html.parser")
                items = soup.select(".item-cell, .item-container")
                if not items:
                    items = soup.find_all("div", class_=re.compile(r"item"))
                
                if not items:
                    continue
                
                candidates = []
                for item in items[:5]:
                    title_elem = item.find("a", class_=re.compile(r"item-title"))
                    if not title_elem:
                        continue
                    title = title_elem.get_text(strip=True)
                    link = title_elem.get("href", "")
                    if link and not link.startswith("http"):
                        link = "https://www.newegg.com" + link
                    
                    price_elem = item.find("li", class_="price-current")
                    if not price_elem:
                        continue
                    strong = price_elem.find("strong")
                    sup = price_elem.find("sup")
                    if not strong:
                        continue
                    dollar = re.sub(r"[^\d]", "", strong.text)
                    cent = re.sub(r"[^\d]", "", sup.text) if sup else "00"
                    try:
                        price = float(f"{dollar}.{cent.ljust(2,'0')[:2]}")
                    except ValueError:
                        continue
                    
                    if price < 50 or price > 5000:
                        continue
                    
                    if not any(part.lower() in title.lower() for part in product_name.split()):
                        continue
                    
                    # التقييم
                    rating = 0.0
                    rating_i = item.find("i", class_=re.compile(r"rating"))
                    if rating_i:
                        classes = " ".join(rating_i.get("class", []))
                        m = re.search(r"rating[-_](\d+)", classes)
                        if m:
                            rating = float(m.group(1)) / 10.0
                    
                    reviews = 0
                    rev_elem = item.find("span", class_="item-rating-num")
                    if rev_elem:
                        rev_text = re.sub(r"[^\d]", "", rev_elem.text)
                        if rev_text:
                            reviews = int(rev_text)
                    
                    candidates.append({
                        "Product_URL": link,
                        "Site": self.SITE,
                        "Product": title[:80],
                        "Price": price,
                        "Currency": "USD",
                        "Rating": rating,
                        "Reviews": reviews,
                    })
                
                if candidates:
                    best = min(candidates, key=lambda x: x["Price"])
                    print(f"[Newegg] Found: {best['Product'][:50]} - ${best['Price']}")
                    return [best]
                    
            except Exception as e:
                print(f"[Newegg] Error with URL {url}: {e}")
                continue
        
        print("[Newegg] No products found after all attempts")
        return []
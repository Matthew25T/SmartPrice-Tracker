"""
bestbuy_scraper.py — Best Buy (Selenium with undetected-chromedriver)
"""

import re
import time
import urllib.parse
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

class BestBuyScraper:
    SITE = "BestBuy"

    def __init__(self, driver):
        self.driver = driver

    def scrape(self, product_name: str) -> list[dict]:
        print(f"[BestBuy] Searching for: {product_name}")
        query = urllib.parse.quote_plus(product_name)
        
        # محاولة رابطين مختلفين
        urls = [
            f"https://www.bestbuy.com/site/searchpage.jsp?st={query}",
            f"https://www.bestbuy.com/site/searchpage.jsp?cp=1&st={query}"
        ]
        
        for url in urls:
            try:
                self.driver.get(url)
                time.sleep(4)
                
                # التمرير لأسفل لتحميل المنتجات
                self.driver.execute_script("window.scrollBy(0, 1200);")
                time.sleep(2)
                
                # انتظار ظهور أي عنصر منتج
                try:
                    WebDriverWait(self.driver, 20).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, ".sku-item, .product-item, [class*='product']"))
                    )
                except TimeoutException:
                    continue  # جرب الرابط التالي
                
                soup = BeautifulSoup(self.driver.page_source, "html.parser")
                items = soup.find_all("li", class_="sku-item")
                if not items:
                    items = soup.find_all("div", class_=re.compile(r"product-item|productCard"))
                
                if not items:
                    continue  # لا منتجات، جرب الرابط التالي
                
                candidates = []
                for item in items[:5]:
                    # العنوان
                    title_elem = item.find("h4", class_="sku-title") or item.find("h3", class_="product-title")
                    if not title_elem:
                        continue
                    title = title_elem.get_text(strip=True)
                    if not title:
                        continue
                    
                    # الرابط
                    a_tag = title_elem.find("a") if title_elem.name != "a" else title_elem
                    link = ""
                    if a_tag and a_tag.get("href"):
                        href = a_tag["href"]
                        link = href if href.startswith("http") else "https://www.bestbuy.com" + href
                    
                    # السعر
                    price_elem = item.find(class_=re.compile(r"priceView-hero-price|priceView-customer-price"))
                    if not price_elem:
                        price_elem = item.find("div", attrs={"data-testid": "customer-price"})
                    if not price_elem:
                        continue
                    price_text = price_elem.get_text(strip=True)
                    m = re.search(r"[\d,]+\.\d+", price_text)
                    if not m:
                        continue
                    price = float(m.group().replace(",", ""))
                    
                    if price < 10 or price > 5000:
                        continue
                    
                    # قبول أي منتج يحتوي على كلمة من البحث
                    if not any(part.lower() in title.lower() for part in product_name.split()):
                        continue
                    
                    # التقييمات
                    rating, reviews = 0.0, 0
                    hidden = item.find("p", class_="visually-hidden")
                    if hidden:
                        txt = hidden.get_text()
                        r_match = re.search(r"([\d.]+)\s*out of", txt)
                        if r_match:
                            rating = float(r_match.group(1))
                        rev_match = re.search(r"(\d[\d,]*)\s*reviews?", txt)
                        if rev_match:
                            reviews = int(rev_match.group(1).replace(",", ""))
                    
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
                    print(f"[BestBuy] Found: {best['Product'][:50]} - ${best['Price']}")
                    return [best]
                    
            except Exception as e:
                print(f"[BestBuy] Error with URL {url}: {e}")
                continue
        
        print("[BestBuy] No products found after all attempts")
        return []
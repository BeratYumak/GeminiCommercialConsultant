from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def scrape_amazon(product_name):
    data = {"site": "Amazon", "title": "Not Found", "link": "", "price": "N/A", "rating": "N/A", "comments": "N/A", "image": ""}
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    try:
        url = f"https://www.amazon.com.tr/s?k={product_name.replace(' ', '+')}"
        logger.info(f"Amazon: Searching {url}")
        driver.get(url)
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.s-result-item:not(.AdHolder)")))
        
        product = driver.find_element(By.CSS_SELECTOR, "div.s-result-item:not(.AdHolder)")
        try:
            data["title"] = product.find_element(By.CSS_SELECTOR, "h2, span.a-text-normal").text.strip()
            logger.info(f"Amazon: Başlık bulundu: {data['title']}")
        except:
            logger.warning("Amazon: Başlık bulunamadı")
        
        try:
            data["link"] = product.find_element(By.CSS_SELECTOR, "a.a-link-normal").get_attribute("href")
            logger.info(f"Amazon: Link bulundu: {data['link']}")
        except:
            logger.warning("Amazon: Link bulunamadı")
        
        try:
            price_whole = product.find_element(By.CSS_SELECTOR, "span.a-price-whole").text.strip()
            price_fraction = product.find_element(By.CSS_SELECTOR, "span.a-price-fraction").text.strip()
            data["price"] = f"{price_whole}.{price_fraction} TL"
            logger.info(f"Amazon: Fiyat bulundu: {data['price']}")
        except:
            logger.warning("Amazon: Fiyat bulunamadı")
        
        try:
            data["rating"] = product.find_element(By.CSS_SELECTOR, "span[data-hook='rating-out-of-text'], i.a-icon-star, span.a-icon-alt").text.strip()
            logger.info(f"Amazon: Puan bulundu: {data['rating']}")
        except:
            logger.warning("Amazon: Puan bulunamadı")
        
        try:
            data["comments"] = product.find_element(By.CSS_SELECTOR, "span[data-hook='total-review-count'], a#acrCustomerReviewLink").text.strip()
            logger.info(f"Amazon: Yorum bulundu: {data['comments']}")
        except:
            logger.warning("Amazon: Yorum bulunamadı")
        
        try:
            data["image"] = product.find_element(By.CSS_SELECTOR, "img.s-image, img[src*='media'], img.a-dynamic-image").get_attribute("src")
            logger.info(f"Amazon: Resim bulundu: {data['image']}")
        except:
            logger.warning("Amazon: Resim bulunamadı")
    
    except Exception as e:
        logger.error(f"Amazon hatası: {e}")
        data["title"] = "Hata"
        data["link"] = f"Amazon aramasında hata: {str(e)}"
    
    finally:
        driver.quit()
    return data
# scraper_trendyol.py
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

def scrape_trendyol(product_name):
    """Trendyol'dan ilk ürünün verilerini ve 10 yorumu çeker."""
    data = {
        "site": "Trendyol",
        "title": "Bulunamadı",
        "link": "",
        "price": "N/A",
        "rating": "N/A",
        "comments": "N/A",
        "image": "",
        "user_comments": []
    }
    
    # Chrome ayarları
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.0.0 Safari/537.36")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    try:
        # Arama sayfasını ziyaret et
        url = f"https://www.trendyol.com/sr?q={product_name.replace(' ', '%20')}"
        logger.info(f"Trendyol: Arama yapılıyor: {url}")
        driver.get(url)
        
        # Arama sonuçlarının yüklenmesini bekle
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.p-card-wrppr")))
        logger.info("Trendyol: Arama sonuçları yüklendi")
        
        # İlk ürünü seç ve ürün sayfasına git
        product = driver.find_element(By.CSS_SELECTOR, "div.p-card-wrppr")
        product_link = product.find_element(By.CSS_SELECTOR, "a").get_attribute("href")
        data["link"] = product_link
        # Yorumlar sayfasına yönlendir
        comments_url = f"{product_link}/yorumlar"
        logger.info(f"Trendyol: Yorumlar sayfasına gidiliyor: {comments_url}")
        driver.get(comments_url)
        
        # Ürün sayfası yüklenmesini sağla
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        time.sleep(3)  # Dinamik içeriklerin yüklenmesi için
        
        # Verileri çek
        try:
            title_element = driver.find_element(By.CSS_SELECTOR, "div.product-details-product-details-container .product-title")
            data["title"] = title_element.text.strip()
            logger.info(f"Trendyol: Başlık bulundu: {data['title']}")
        except:
            logger.warning("Trendyol: Başlık bulunamadı")
            try:
                data["title"] = driver.execute_script("return document.querySelector('div.product-details-product-details-container .product-title').innerText").strip()
                logger.info(f"Trendyol: Başlık JavaScript ile bulundu: {data['title']}")
            except:
                logger.warning("Trendyol: JavaScript ile başlık bulunamadı")
        
        try:
            # Fiyat için önce price-view-original, sonra campaign-price denensin
            try:
                price_element = driver.find_element(By.CSS_SELECTOR, "span.price-view-original")
                data["price"] = price_element.text.strip()
                logger.info(f"Trendyol: Fiyat bulundu (price-view-original): {data['price']}")
            except:
                price_element = driver.find_element(By.CSS_SELECTOR, "span.campaign-price")
                data["price"] = price_element.text.strip()
                logger.info(f"Trendyol: Fiyat bulundu (campaign-price): {data['price']}")
        except:
            logger.warning("Trendyol: Fiyat bulunamadı")
            try:
                price = driver.execute_script(
                    "return document.querySelector('span.price-view-original')?.innerText || "
                    "document.querySelector('span.campaign-price')?.innerText"
                )
                if price:
                    data["price"] = price.strip()
                    logger.info(f"Trendyol: Fiyat JavaScript ile bulundu: {data['price']}")
                else:
                    logger.warning("Trendyol: JavaScript ile fiyat bulunamadı")
            except:
                logger.warning("Trendyol: JavaScript ile fiyat bulunamadı")
        
        try:
            data["rating"] = driver.find_element(By.CSS_SELECTOR, "span.reviews-summary-average-rating").text.strip()
            logger.info(f"Trendyol: Puan bulundu: {data['rating']}")
        except:
            logger.warning("Trendyol: Puan bulunamadı")
            try:
                data["rating"] = driver.execute_script("return document.querySelector('span.reviews-summary-average-rating').innerText").strip()
                logger.info(f"Trendyol: Puan JavaScript ile bulundu: {data['rating']}")
            except:
                logger.warning("Trendyol: JavaScript ile puan bulunamadı")
        
        try:
            comments_element = driver.find_element(By.CSS_SELECTOR, "div.reviews-summary-reviews-summary [data-testid='review-info-link']")
            data["comments"] = comments_element.text.strip()
            logger.info(f"Trendyol: Yorum sayısı bulundu: {data['comments']}")
        except:
            try:
                driver.find_element(By.CSS_SELECTOR, "div.reviews-summary-no-reviews")
                data["comments"] = "Henüz değerlendirilmedi"
                logger.info("Trendyol: Ürün henüz değerlendirilmedi")
            except:
                logger.warning("Trendyol: Yorum sayısı bulunamadı")
        
        try:
            data["image"] = driver.find_element(By.CSS_SELECTOR, "img._carouselImage_abb7111").get_attribute("src")
            logger.info(f"Trendyol: Resim bulundu: {data['image']}")
        except:
            logger.warning("Trendyol: Resim bulunamadı")
            try:
                data["image"] = driver.execute_script("return document.querySelector('img._carouselImage_abb7111').src").strip()
                logger.info(f"Trendyol: Resim JavaScript ile bulundu: {data['image']}")
            except:
                logger.warning("Trendyol: JavaScript ile resim bulunamadı")
    
    except Exception as e:
        logger.error(f"Trendyol hatası: {e}")
        data["title"] = "Hata"
        data["link"] = f"Trendyol için hata: {str(e)}"
    
    finally:
        driver.quit()
    return data
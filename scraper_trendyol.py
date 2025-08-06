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
    """Trendyol'dan ilk 5 ürünün verilerini çeker."""
    products = []
    
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
        WebDriverWait(driver, 15).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.p-card-wrppr")))
        logger.info("Trendyol: Arama sonuçları yüklendi")
        
        # İlk 5 ürünün bağlantılarını topla
        product_elements = driver.find_elements(By.CSS_SELECTOR, "div.p-card-wrppr")[:5]
        product_links = []
        for product in product_elements:
            try:
                link = product.find_element(By.CSS_SELECTOR, "a").get_attribute("href")
                product_links.append(link)
                logger.info(f"Trendyol: Bağlantı toplandı: {link}")
            except:
                logger.warning("Trendyol: Ürün bağlantısı alınamadı")
                continue
        
        logger.info(f"Trendyol: {len(product_links)} ürün bulundu")
        
        # Her ürün için verileri çek
        for index, product_link in enumerate(product_links, 1):
            data = {
                "site": "Trendyol",
                "title": "Bulunamadı",
                "link": product_link,
                "price": "N/A",
                "rating": "N/A",
                "comments": "N/A",
                "image": "",
                "user_comments": []
            }
            
            try:
                # Ürün sayfasına git
                logger.info(f"Trendyol: Ürün {index}: Ürün detay sayfasına gidiliyor: {product_link}")
                driver.get(product_link)
                WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
                time.sleep(3)  # Dinamik içeriklerin yüklenmesi için
                
                # Başlık
                try:
                    title_element = driver.find_element(By.CSS_SELECTOR, "div.product-details-product-details-container .product-title")
                    data["title"] = title_element.text.strip()
                    logger.info(f"Trendyol: Ürün {index}: Başlık bulundu: {data['title']}")
                except:
                    logger.warning(f"Trendyol: Ürün {index}: Başlık bulunamadı")
                    try:
                        data["title"] = driver.execute_script("return document.querySelector('div.product-details-product-details-container .product-title').innerText").strip()
                        logger.info(f"Trendyol: Ürün {index}: Başlık JavaScript ile bulundu: {data['title']}")
                    except:
                        logger.warning(f"Trendyol: Ürün {index}: JavaScript ile başlık bulunamadı")
                
                # Fiyat
                try:
                    price_element = driver.find_element(By.CSS_SELECTOR, "div.product-details-product-details-container .discounted")
                    data["price"] = price_element.text.strip()
                    logger.info(f"Trendyol: Ürün {index}: Fiyat bulundu: {data['price']}")
                except:
                    logger.warning(f"Trendyol: Ürün {index}: Fiyat bulunamadı")
                    try:
                        price = driver.execute_script("return document.querySelector('div.product-details-product-details-container').innerText")
                        if price:
                            data["price"] = price.strip()
                            logger.info(f"Trendyol: Ürün {index}: Fiyat JavaScript ile bulundu: {data['price']}")
                        else:
                            logger.warning(f"Trendyol: Ürün {index}: JavaScript ile fiyat bulunamadı")
                    except:
                        logger.warning(f"Trendyol: Ürün {index}: JavaScript ile fiyat bulunamadı")
                
                # Puan
                try:
                    data["rating"] = driver.find_element(By.CSS_SELECTOR, "span.reviews-summary-average-rating").text.strip()
                    logger.info(f"Trendyol: Ürün {index}: Puan bulundu: {data['rating']}")
                except:
                    logger.warning(f"Trendyol: Ürün {index}: Puan bulunamadı")
                    try:
                        data["rating"] = driver.execute_script("return document.querySelector('span.reviews-summary-average-rating').innerText").strip()
                        logger.info(f"Trendyol: Ürün {index}: Puan JavaScript ile bulundu: {data['rating']}")
                    except:
                        logger.warning(f"Trendyol: Ürün {index}: JavaScript ile puan bulunamadı")
                
                # Değerlendirme sayısı
                try:
                    comments_element = driver.find_element(By.CSS_SELECTOR, "div.product-details-product-details-container .reviews-summary-reviews-detail")
                    data["comments"] = comments_element.text.strip().split()[0] 
                    logger.info(f"Trendyol: Ürün {index}: Değerlendirme sayısı bulundu: {data['comments']}")
                except:
                    logger.warning(f"Trendyol: Ürün {index}: Değerlendirme sayısı bulunamadı")
                    try:
                        comments = driver.execute_script("return document.querySelector('div.pr-rnr-sm-p span').innerText").strip().split()[0]
                        data["comments"] = comments
                        logger.info(f"Trendyol: Ürün {index}: Değerlendirme sayısı JavaScript ile bulundu: {data['comments']}")
                    except:
                        logger.warning(f"Trendyol: Ürün {index}: JavaScript ile değerlendirme sayısı bulunamadı")
                        data["comments"] = "N/A"
                
                # Resim
                try:
                    data["image"] = driver.find_element(By.CSS_SELECTOR, "img._carouselImage_abb7111").get_attribute("src")
                    logger.info(f"Trendyol: Ürün {index}: Resim bulundu: {data['image']}")
                except:
                    logger.warning(f"Trendyol: Ürün {index}: Resim bulunamadı")
                    try:
                        data["image"] = driver.execute_script("return document.querySelector('img._carouselImage_abb7111').src").strip()
                        logger.info(f"Trendyol: Ürün {index}: Resim JavaScript ile bulundu: {data['image']}")
                    except:
                        logger.warning(f"Trendyol: Ürün {index}: JavaScript ile resim bulunamadı")
                
                products.append(data)
            
            except Exception as e:
                logger.error(f"Trendyol: Ürün {index} hatası: {e}")
                products.append(data)
        
    except Exception as e:
        logger.error(f"Trendyol hatası: {e}")
        products.append({
            "site": "Trendyol",
            "title": "Hata",
            "link": f"Trendyol için hata: {str(e)}",
            "price": "N/A",
            "rating": "N/A",
            "comments": "N/A",
            "image": "",
            "user_comments": []
        })
    
    finally:
        driver.quit()
    return products

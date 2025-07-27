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

def scrape_hepsiburada(product_name):
    data = {
        "site": "Hepsiburada",
        "title": "Bulunamadı",
        "link": "",
        "price": "Bilinmiyor",
        "rating": "Bilinmiyor",
        "comments": "Bilinmiyor",
        "image": "",
        "user_comments": []
    }
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")  # Yeni headless mod, pencere açmaz
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-gpu")
    options.add_argument("--ignore-certificate-errors")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    try:
        url = f"https://www.hepsiburada.com/ara?q={product_name.replace(' ', '+')}"
        logger.info(f"Hepsiburada: Arama yapılıyor {url}")
        driver.get(url)
        # Arama sayfasının yüklendiğini doğrula
        try:
            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div[class*='productListContent-']"))
            )
            logger.info("Hepsiburada: Arama sayfası yüklendi")
        except Exception as e:
            logger.error(f"Hepsiburada: Arama sayfası yüklenemedi: {e}")
            data["title"] = "Hata"
            data["link"] = f"Arama sayfası yüklenemedi: {str(e)}"
            logger.info(f"Sayfa kaynağı: {driver.page_source[:500]}")
            driver.save_screenshot("hepsiburada_error.png")
            return data

        # İlk ürünü seç ve ürün sayfasına git
        try:
            products = driver.find_elements(By.CSS_SELECTOR, "div[class*='productListContent-']")
            product_link = None
            for product in products:
                try:
                    link = product.find_element(By.CSS_SELECTOR, "article[class*='productCard-module_article__'] a").get_attribute("href")
                    if "adservice" not in link:
                        product_link = link
                        break
                except:
                    continue
            if not product_link:
                raise Exception("Geçerli ürün linki bulunamadı")
            data["link"] = product_link
            logger.info(f"Hepsiburada: Ürün sayfasına gidiliyor {product_link}")
            driver.get(product_link)
            WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            time.sleep(2)
        except Exception as e:
            logger.error(f"Hepsiburada: Ürün sayfasına gidilemedi: {e}")
            data["title"] = "Hata"
            data["link"] = f"Ürün sayfasına gidilemedi: {str(e)}"
            driver.save_screenshot("hepsiburada_product_error.png")
            return data

        # Başlık
        try:
            title_element = driver.find_element(By.CSS_SELECTOR, "div.container.desktop [data-test-id='title-area'], h1#product-name, h1.product-name, span.product-name, h1.title")
            data["title"] = title_element.text.strip()
            logger.info(f"Hepsiburada: Başlık bulundu: {data['title']}")
        except:
            logger.warning("Hepsiburada: Başlık bulunamadı")
            data["title"] = "Bulunamadı"

        # Fiyat
        try:
            price = driver.find_element(By.CSS_SELECTOR, "[data-test-id='price'], span#offering-price, span.price-value, span.product-price, span.current-price, span.price").text.strip()
            data["price"] = price
            logger.info(f"Hepsiburada: Fiyat bulundu: {price}")
        except:
            logger.warning("Hepsiburada: Fiyat bulunamadı")

        # Puan ve Yorum Sayısı
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[data-test-id='has-review'], span[class*='rating'], div[class*='rating'], span[class*='review']"))
            )
            review_element = driver.find_element(By.CSS_SELECTOR, "[data-test-id='has-review'], span[class*='rating'], div[class*='rating'], span[class*='review']")
            review_text = review_element.text.strip()
            # Puan ve yorum sayısı genellikle "3,5(24)" veya "3,5 24 Değerlendirme" formatında
            rating = "Bilinmiyor"
            comments = "Bilinmiyor"
            if '(' in review_text and ')' in review_text:
                rating = review_text.split('(')[0].strip().replace(',', '.')
                comments = review_text.split('(')[1].replace(')', '').strip()
            elif 'Değerlendirme' in review_text:
                parts = review_text.split()
                rating = parts[0].replace(',', '.')
                for part in parts:
                    if part.isdigit():
                        comments = part
                        break
            data["rating"] = rating
            data["comments"] = comments
            logger.info(f"Hepsiburada: Puan bulundu: {rating}, Yorum sayısı bulundu: {comments}")
        except:
            logger.warning("Hepsiburada: Puan ve yorum sayısı bulunamadı")
            data["rating"] = "Bilinmiyor"
            data["comments"] = "Bilinmiyor"

        # Resim
                # Resim
        try:
            images = driver.find_elements(By.CSS_SELECTOR, "div.hb-image-view img, div[class*='imageArea-module_imageLeftBottomArea__'] img, img#productImage, img.product-image, img.main-img")
            image_url = ""
            for img in images:
                src = img.get_attribute("src") or ""
                if not src:
                    continue
                # Fotoğraf boyutunu kontrol et
                try:
                    width = int(img.get_attribute("width") or img.size.get("width", 0))
                    height = int(img.get_attribute("height") or img.size.get("height", 0))
                    if width <= 600 and height <= 600:
                        image_url = src
                        break
                except:
                    # Boyut bilgisi alınamazsa, bu görseli kullan
                    image_url = src
                    break
            if not image_url and images:
                image_url = images[0].get_attribute("src") or ""  # Fallback: İlk resmi al
            data["image"] = image_url
            logger.info(f"Hepsiburada: Resim bulundu: {data['image']}")
        except:
            logger.warning("Hepsiburada: Resim bulunamadı")
            data["image"] = ""

    except Exception as e:
        logger.error(f"Hepsiburada genel hata: {e}")
        data["title"] = "Hata"
        data["link"] = f"Hepsiburada arama hatası: {str(e)}"
        driver.save_screenshot("hepsiburada_general_error.png")
    finally:
        driver.quit()
    return data
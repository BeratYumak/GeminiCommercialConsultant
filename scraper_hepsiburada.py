from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
import logging
import re
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def clean_price(text):
    """Fiyat metnini temizler, sadece sayısal fiyat ve para birimini döner."""
    try:
        match = re.search(r'(\d{1,3}(?:\.\d{3})*,\d+\s?TL)', text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return text.strip() if text else "N/A"
    except Exception as e:
        logger.warning(f"Fiyat temizleme hatası: {str(e)}")
        return "N/A"

def clean_comments(text):
    """<b> etiketinden değerlendirme sayısını çeker."""
    try:
        match = re.search(r'(\d+)', text)  # Herhangi bir sayı çek
        if match:
            return match.group(1).strip()
        return "0"
    except Exception as e:
        logger.warning(f"Değerlendirme sayısı temizleme hatası: {str(e)} - Metin: {text}")
        return "0"

def scrape_hepsiburada(product_name):
    """Hepsiburada'dan ilk 5 geçerli ürünü çeker, adservice içeren linkleri atlar."""
    data = []  # Tek bir sözlük yerine ürün listesi
    
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.set_page_load_timeout(30)
    
    try:
        # Arama sayfasını ziyaret et
        url = f"https://www.hepsiburada.com/ara?q={product_name.replace(' ', '%20')}"
        logger.info(f"Hepsiburada: Arama yapılıyor {url}")
        driver.get(url)
        
        # Arama sonuçlarının yüklenmesini bekle
        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "article.productCard-module_article__HJ97o"))
            )
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            logger.info("Hepsiburada: Arama sayfası yüklendi")
        except TimeoutException:
            logger.error("Hepsiburada: Arama sonuçları yüklenemedi, sayfa içeriği kontrol ediliyor")
            if "Aradığınız kriterlere uygun ürün bulunamadı" in driver.page_source:
                logger.warning(f"Hepsiburada: '{product_name}' için ürün bulunamadı")
                data.append({
                    "site": "Hepsiburada",
                    "title": "Hata",
                    "link": f"Hepsiburada: '{product_name}' için ürün bulunamadı",
                    "price": "N/A",
                    "rating": "N/A",
                    "comments": "0",
                    "image": "",
                    "user_comments": []
                })
                with open("hepsiburada_error_page.html", "w", encoding="utf-8") as f:
                    f.write(driver.page_source)
                driver.save_screenshot("hepsiburada_error.png")
                return data
            raise TimeoutException("Hepsiburada: Arama sonuçları yüklenemedi")
        
        # İlk 5 geçerli ürünü seç (adservice içermeyen)
        try:
            products = driver.find_elements(By.CSS_SELECTOR, "article.productCard-module_article__HJ97o a")
            if not products:
                logger.warning(f"Hepsiburada: '{product_name}' için ürün bulunamadı")
                data.append({
                    "site": "Hepsiburada",
                    "title": "Hata",
                    "link": f"Hepsiburada: '{product_name}' için ürün bulunamadı",
                    "price": "N/A",
                    "rating": "N/A",
                    "comments": "0",
                    "image": "",
                    "user_comments": []
                })
                with open("hepsiburada_no_product.html", "w", encoding="utf-8") as f:
                    f.write(driver.page_source)
                driver.save_screenshot("hepsiburada_no_product.png")
                return data
            
            valid_products = []
            for product in products[:5]:  # İlk 5 ürünü al
                try:
                    link = product.get_attribute("href")
                    if link and "hepsiburada.com" in link and not any(x in link for x in ["adservice", "sponsored", "magaza", "kampanya", "satici"]):
                        valid_products.append(link)
                except:
                    continue
            
            if not valid_products:
                logger.warning(f"Hepsiburada: Geçerli 5 ürün linki bulunamadı")
                data.append({
                    "site": "Hepsiburada",
                    "title": "Hata",
                    "link": "Hepsiburada: Geçerli 5 ürün linki bulunamadı",
                    "price": "N/A",
                    "rating": "N/A",
                    "comments": "0",
                    "image": "",
                    "user_comments": []
                })
                with open("hepsiburada_no_product.html", "w", encoding="utf-8") as f:
                    f.write(driver.page_source)
                driver.save_screenshot("hepsiburada_no_product.png")
                return data
            
            # Her ürün için veri çek
            for i, product_link in enumerate(valid_products[:5], 1):  # Maksimum 5 ürün
                product_data = {
                    "site": "Hepsiburada",
                    "title": "Hata",
                    "link": product_link,
                    "price": "N/A",
                    "rating": "N/A",
                    "comments": "0",
                    "image": "",
                    "user_comments": []
                }
                
                try:
                    driver.get(product_link)
                    WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
                    time.sleep(3)
                    logger.info(f"Hepsiburada: Ürün {i} sayfası yüklendi: {product_link}")
                    
                    # Başlık
                    try:
                        title_element = driver.find_element(By.CSS_SELECTOR, "[data-test-id='title-area'], [data-test-id='title']")
                        product_data["title"] = title_element.text.strip()
                        logger.info(f"Hepsiburada: Ürün {i} - Başlık bulundu: {product_data['title']}")
                    except NoSuchElementException:
                        logger.warning(f"Hepsiburada: Ürün {i} - Başlık bulunamadı")
                        try:
                            product_data["title"] = driver.execute_script("return document.querySelector('[data-test-id=\"title-area\"], [data-test-id=\"title\"]').innerText").strip()
                            logger.info(f"Hepsiburada: Ürün {i} - Başlık JavaScript ile bulundu: {product_data['title']}")
                        except:
                            logger.warning(f"Hepsiburada: Ürün {i} - JavaScript ile başlık bulunamadı")
                    
                    # Fiyat
                    try:
                        price_element = driver.find_element(By.CSS_SELECTOR, "[data-test-id='price'], [data-test-id='default-price'], span.foQSHpIYwZWy8nHeqapl.QfKHfu57dLi9hPNDl1UL, span.PO95DoKzLwH3oI6s8acH, span.IMDzXKdZKh810YOI6k5Q, span.z7kokklsVwh0K5zFWjIO")
                        product_data["price"] = clean_price(price_element.text)
                        logger.info(f"Hepsiburada: Ürün {i} - Fiyat bulundu: {product_data['price']}")
                    except NoSuchElementException:
                        logger.warning(f"Hepsiburada: Ürün {i} - Fiyat bulunamadı")
                        try:
                            product_data["price"] = clean_price(driver.execute_script("return document.querySelector('[data-test-id=\"price\"], [data-test-id=\"default-price\"]').innerText").strip())
                            logger.info(f"Hepsiburada: Ürün {i} - Fiyat JavaScript ile bulundu: {product_data['price']}")
                        except:
                            logger.warning(f"Hepsiburada: Ürün {i} - JavaScript ile fiyat bulunamadı")
                    
                    # Puan
                    try:
                        rating_element = driver.find_element(By.CSS_SELECTOR, "span.JYHIcZ8Z_Gz7VXzxFB96, span.rating-score")
                        product_data["rating"] = rating_element.text.strip()
                        logger.info(f"Hepsiburada: Ürün {i} - Puan bulundu: {product_data['rating']}")
                    except NoSuchElementException:
                        product_data["rating"] = "Henüz puanlanmadı"
                        logger.warning(f"Hepsiburada: Ürün {i} - Puan bulunamadı")
                    
                    # Değerlendirme sayısı
                    try:
                        comments_element = driver.find_element(By.CSS_SELECTOR, "a.yPPu6UogPlaotjhx1Qki > b")
                        product_data["comments"] = clean_comments(comments_element.text)
                        logger.info(f"Hepsiburada: Ürün {i} - Değerlendirme sayısı bulundu: {product_data['comments']} - Element metni: {comments_element.text}")
                    except NoSuchElementException:
                        product_data["comments"] = "0"
                        logger.warning(f"Hepsiburada: Ürün {i} - Değerlendirme sayısı bulunamadı")
                    
                    # Resim
                    try:
                        image_element = driver.find_element(By.CSS_SELECTOR, "img.i9jTSpEeoI29_M1mOKct.hb-HbImage-view__image, img.product-image")
                        product_data["image"] = image_element.get_attribute("src")
                        logger.info(f"Hepsiburada: Ürün {i} - Resim bulundu: {product_data['image']}")
                    except NoSuchElementException:
                        logger.warning(f"Hepsiburada: Ürün {i} - Resim bulunamadı")
                    
                    data.append(product_data)
                
                except Exception as e:
                    logger.error(f"Hepsiburada: Ürün {i} için hata: {str(e)}")
                    product_data["link"] = f"Hepsiburada için hata: {str(e)}"
                    with open(f"hepsiburada_product_{i}_error.html", "w", encoding="utf-8") as f:
                        f.write(driver.page_source)
                    driver.save_screenshot(f"hepsiburada_product_{i}_error.png")
                    data.append(product_data)
        
        except Exception as e:
            logger.error(f"Hepsiburada: Genel hata: {str(e)}")
            data.append({
                "site": "Hepsiburada",
                "title": "Hata",
                "link": f"Hepsiburada için hata: {str(e)}",
                "price": "N/A",
                "rating": "N/A",
                "comments": "0",
                "image": "",
                "user_comments": []
            })
            with open("hepsiburada_general_error.html", "w", encoding="utf-8") as f:
                f.write(driver.page_source)
            driver.save_screenshot("hepsiburada_general_error.png")
    
    finally:
        try:
            driver.quit()
        except:
            logger.warning("Hepsiburada: Tarayıcı kapatılamadı")
    
    return data

if __name__ == "__main__":
    result = scrape_hepsiburada("iphone 13")
    for i, product in enumerate(result, 1):
        print(f"Ürün {i}: {product}")

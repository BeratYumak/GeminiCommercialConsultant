# app.py
from time import time
from flask import Flask, render_template, request
from scraper_trendyol import scrape_trendyol
from scraper_hepsiburada import scrape_hepsiburada
from scraper_youtube import scrape_youtube
import google.generativeai as genai
from concurrent.futures import ThreadPoolExecutor
from functools import wraps
import html
import bleach
import logging
import json
import re

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

YOUTUBE_API_KEY = "AIzaSyBc6CuoZ0gjYG6FtDrA2MVM1GoAyc4Hjgw"
GENAI_API_KEY = "AIzaSyB7ZvG_Fx5sOwIkEK2wkMajXEbTuwH5S5Y"

def optimize_title_with_gemini(title):
    try:
        genai.configure(api_key=GENAI_API_KEY)
        model = genai.GenerativeModel(model_name="gemini-2.5-pro")
        prompt = (
            f"Verilen ürün başlığını YouTube'da aranabilir. "
            f"Kategori 2-3 kelimeyi geçmesin, çok genel (örneğin, sadece 'Tablo') olmamalı. "
            f"Sadece kategori adını döndür, başka açıklama ekleme.\n"
            f"Başlık: {title}"
        )
        response = model.generate_content(prompt)
        optimized_title = response.text.strip()
        logger.info(f"Başlık optimizasyonu: '{title}' → '{optimized_title}'")
        return optimized_title
    except Exception as e:
        logger.error(f"Gemini başlık optimizasyon hatası: {str(e)}")
        return title

def clean_response(text):
    """HTML etiketlerini kaldır, encode edilmiş karakterleri çöz ve liste işaretlerini temizle."""
    cleaned_text = html.unescape(text)
    cleaned_text = bleach.clean(cleaned_text, tags=[], strip=True)
    lines = cleaned_text.split('\n')
    cleaned_lines = [line.strip().lstrip('*-•1234567890. ').strip() for line in lines if line.strip()]
    return '\n'.join(cleaned_lines)

def research_precautions_with_gemini(category):
    try:
        genai.configure(api_key=GENAI_API_KEY)
        model = genai.GenerativeModel(model_name="gemini-2.5-pro")
        prompt = (
            f"{category} alınırken dikkat edilmesi gerekenler hakkında araştırma yap. "
            "Cevabı 3-5 madde, her madde en fazla 15 kelime olacak şekilde kısa ve net bir liste yap. "
            "Sadece madde liste döndür, başka hiçbir şey ekleme."
        )
        response = model.generate_content(prompt)
        cleaned_text = clean_response(response.text)
        logger.info(f"Gemini: '{category}' için dikkat edilmesi gerekenler araştırıldı")
        return cleaned_text.split('\n')
    except Exception as e:
        logger.error(f"Gemini araştırma hatası: {str(e)}")
        return [f"hata: {str(e)}"]

def performance_log(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time()
        result = func(*args, **kwargs)
        logger.info(f"{func.__name__} executed in {time() - start_time:.2f} seconds")
        return result
    return wrapper

@app.route('/', methods=['GET', 'POST'])
@performance_log
def home():
    results = []
    youtube_videos = []
    precautions_videos = []
    precautions_text = []
    optimized_category = ""
    search_query = ""
    precautions_search_query = ""
    gemini_response_list = []

    if request.form.get('gemini_response_list'):
        try:
            gemini_response_list = json.loads(request.form.get('gemini_response_list'))
            for item in gemini_response_list:
                if 'title' in item:
                    item['title'] = str(item['title'])
                else:
                    item['title'] = "Hata: Başlık bulunamadı"
                    item['is_button'] = False
        except json.JSONDecodeError as e:
            logger.error(f"Gemini yanıtları JSON parse hatası: {str(e)}")
            gemini_response_list = [{"title": "Hata: Gemini yanıtları yüklenemedi", "is_button": False}]

    is_consultancy = request.form.get('is_consultancy', 'False') == 'True'

    if request.method == 'POST':
        product_name = request.form.get('product_name')
        logger.info(f"Ürün araması: {product_name}")
        if product_name:
            search_query = product_name
            with ThreadPoolExecutor(max_workers=5) as executor:
                future_heps = executor.submit(scrape_hepsiburada, product_name)
                future_trendyol = executor.submit(scrape_trendyol, product_name)
                results = [future_heps.result(), future_trendyol.result()]

            for result in results:
                if result["title"] and result["title"] not in ["hata", "Bulunamadı", "Hata"]:
                    optimized_category = optimize_title_with_gemini(result["title"])
                    logger.info(f"YouTube ve Gemini için kategori: {optimized_category}")
                    break

            if optimized_category:
                with ThreadPoolExecutor(max_workers=2) as executor:
                    future_youtube = executor.submit(scrape_youtube, search_query, YOUTUBE_API_KEY, max_results=3)
                    future_precautions = executor.submit(scrape_youtube, f"{optimized_category} alınırken dikkat edilmesi gerekenler", YOUTUBE_API_KEY, max_results=3)
                    videos = future_youtube.result()
                    precautions_vids = future_precautions.result()

                if videos and videos[0]["title"] != "Hata":
                    youtube_videos.append({"site": "Genel", "videos": videos})
                    logger.info(f"YouTube: '{search_query}' için {len(videos)} video bulundu")
                else:
                    logger.warning(f"YouTube: '{search_query}' için video bulunamadı")

                precautions_search_query = f"{optimized_category} alınırken dikkat edilmesi gerekenler"
                if precautions_vids and precautions_vids[0]["title"] != "Hata":
                    precautions_videos.append({"site": "Genel", "videos": precautions_vids})
                    logger.info(f"YouTube: '{precautions_search_query}' için {len(precautions_vids)} video bulundu")
                else:
                    logger.warning(f"YouTube: '{precautions_search_query}' için video bulunamadı")

                precautions_text = research_precautions_with_gemini(optimized_category)
            else:
                logger.warning("YouTube ve Gemini aramaları atlandı: Geçerli başlık bulunamadı")

    return render_template('index.html',
        results=results,
        youtube_videos=youtube_videos,
        precautions_videos=precautions_videos,
        precautions_text=precautions_text,
        optimized_category=optimized_category,
        gemini_response_list=gemini_response_list,
        is_consultancy=is_consultancy,
        search_query=search_query,
        precautions_search_query=precautions_search_query
    )

@app.route('/gemini-chat', methods=['POST'])
def gemini_chat():
    prompt = request.form['chat_prompt']
    genai.configure(api_key=GENAI_API_KEY)
    model = genai.GenerativeModel(model_name="gemini-2.5-pro")
    chat = model.start_chat()

    consultancy_keywords = ["öneri", "tavsiye", "liste", "ne almalıyım", "hangi", "tavsiyeler"]
    is_consultancy = any(keyword in prompt.lower() for keyword in consultancy_keywords)

    try:
        if is_consultancy:
            full_prompt = (
                f"{prompt}\n"
                "Lütfen cevabını kısa tut ve sadece sana sorulan şeye liste şeklinde cevap ver. "
                "Cevaplarının sonuna ürünün ne olduğunu ekle mesela tablo ise cevabın sonuna tablo ekle. "
                "Aralara duygusal veya görünüşleriyle ilgili yorum katma, sadece ne olduğunu söyle. "
                "Cevabının başına veya sonuna 'elbette' veya 'rica ederım' gibi bitirme sözleri ekleme."
            )
            response = chat.send_message(full_prompt)
            raw_text = clean_response(response.text)
            # Ürün kategorisini kaldır (son kelimeyi temizle)
            cevaplar = []
            for line in raw_text.split("\n"):
                if line.strip():
                    # Son kelimeyi kaldır (kategori genellikle son kelime)
                    words = line.strip().split()
                    if words:
                        cleaned_line = " ".join(words[:-1]) if len(words) > 1 else line
                        cevaplar.append({"title": str(cleaned_line), "is_button": True})
            with open("gemini_cevaplar.txt", "a", encoding="utf-8") as f:
                f.write(f"Soru: {prompt}\nCevaplar:\n")
                for c in cevaplar:
                    f.write(f"- {c['title']}\n")
                f.write("\n")
            logger.info(f"Gemini cevabı alındı (liste): {len(cevaplar)} öneri")
            return render_template('index.html',
                results=[],
                gemini_response_list=cevaplar,
                youtube_videos=[],
                precautions_videos=[],
                precautions_text=[],
                optimized_category="",
                is_consultancy=True,
                search_query="",
                precautions_search_query=""
            )
        else:
            full_prompt = (
                f"{prompt}\n"
                "Soruya doğrudan, kısa ve net bir cevap ver. "
                "Cevabın sonuna 'Size nasıl yardımcı olabilirim?' ekle."
            )
            response = chat.send_message(full_prompt)
            raw_text = clean_response(response.text)
            cevaplar = [{"title": str(raw_text), "is_button": False}]
            logger.info(f"Gemini cevabı alındı (düz metin): {raw_text[:100]}...")
            with open("gemini_cevaplar.txt", "a", encoding="utf-8") as f:
                f.write(f"Soru: {prompt}\nCevap: {raw_text}\n\n")
            return render_template('index.html',
                results=[],
                gemini_response_list=cevaplar,
                youtube_videos=[],
                precautions_videos=[],
                precautions_text=[],
                optimized_category="",
                is_consultancy=False,
                search_query="",
                precautions_search_query=""
            )
    except Exception as e:
        logger.error(f"Gemini hata: {str(e)}")
        cevaplar = [{"title": f"Hata: {str(e)}", "is_button": False}]
        return render_template('index.html',
            results=[],
            gemini_response_list=cevaplar,
            youtube_videos=[],
            precautions_videos=[],
            precautions_text=[],
            optimized_category="",
            is_consultancy=False,
            search_query="",
            precautions_search_query=""
        )

if __name__ == '__main__':
    app.run(debug=True)
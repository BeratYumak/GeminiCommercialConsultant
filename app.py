import time
import os
import logging
import json
import html
import bleach
from flask import Flask, render_template, request, jsonify, send_file
from scraper_trendyol import scrape_trendyol
from scraper_hepsiburada import scrape_hepsiburada
from scraper_youtube import scrape_youtube
import google.generativeai as genai
from concurrent.futures import ThreadPoolExecutor
from functools import wraps
import audio_output
from PIL import Image
import io
from gtts import gTTS

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

YOUTUBE_API_KEY = "AIzaSyBc6CuoZ0gjYG6FtDrA2MVM1GoAyc4Hjgw" 
GENAI_API_KEY = "AIzaSyB7ZvG_Fx5sOwIkEK2wkMajXEbTuwH5S5Y"

def optimize_title_with_gemini(title, product_category=None):
    try:
        genai.configure(api_key=GENAI_API_KEY)
        model = genai.GenerativeModel(model_name="gemini-2.5-pro")
        if product_category:
            prompt = (
                f"Verilen ürün başlığını YouTube'da aranabilir, kısa ve genel bir forma dönüştür. "
                f"Başlığın sonuna ürün kategorisini ekle (örneğin, 'Ahşap tablo {product_category}'). "
                f"Sadece sonucu döndür, başka açıklama ekleme.\n"
                f"Başlık: {title}\nKategori: {product_category}"
            )
        else:
            prompt = (
                f"Verilen ürün başlığını YouTube'da aranabilir, kısa ve genel bir forma dönüştür. "
                f"Başlığın sonuna ürün kategorisini ekle (örneğin, 'Ninova Silver Küpe' için 'Küpe küpe'). "
                f"Sadece sonucu döndür, başka açıklama ekleme.\n"
                f"Başlık: {title}"
            )
        response = model.generate_content(prompt)
        optimized_title = response.text.strip()
        logger.info(f"Başlık optimizasyonu: '{title}' → '{optimized_title}'")
        return optimized_title
    except Exception as e:
        logger.error(f"Gemini başlık optimizasyon hatası: {str(e)}")
        return title if product_category is None else f"{title} {product_category}"

def clean_response(text):
    cleaned_text = html.unescape(text)
    cleaned_text = bleach.clean(cleaned_text, tags=[], strip=True)
    lines = cleaned_text.split('\n')
    cleaned_lines = []
    for line in lines:
        line = line.strip().lstrip('*-•1234567890. ').strip()
        if line and len(line.split()) >= 1 and line.lower() not in ["liste", "list"]:
            cleaned_lines.append(line)
    return '\n'.join(cleaned_lines)

def research_precautions_with_gemini(product):
    try:
        genai.configure(api_key=GENAI_API_KEY)
        model = genai.GenerativeModel(model_name="gemini-2.5-pro")
        prompt = (
            f"{product} alınırken dikkat edilmesi gerekenler hakkında araştırma yap. "
            "Cevabı 3-5 madde, her madde en fazla 15 kelime olacak şekilde kısa ve net bir liste yap. "
            "Sadece madde liste döndür, başka hiçbir şey ekleme."
        )
        response = model.generate_content(prompt)
        cleaned_text = clean_response(response.text)
        logger.info(f"Gemini: '{product}' için dikkat edilmesi gerekenler araştırıldı")
        return cleaned_text
    except Exception as e:
        logger.error(f"Gemini araştırma hatası: {str(e)}")
        return f"hata: {str(e)}"

def performance_log(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        logger.info(f"{func.__name__} executed in {time.time() - start_time:.2f} seconds")
        return result
    return wrapper

@app.route('/', methods=['GET', 'POST'])
@performance_log
def home():
    results = []
    youtube_videos = []
    precautions_videos = []
    precautions_text = []
    gemini_response_list = []
    is_consultancy = False
    chat_prompt = ""

    if request.form.get('gemini_response_list'):
        try:
            gemini_response_list = json.loads(request.form.get('gemini_response_list'))
            for item in gemini_response_list:
                if 'title' in item:
                    item['title'] = str(item['title'])
                else:
                    item['title'] = "Hata: Başlık bulunamadı"
                    item['is_button'] = False
            is_consultancy = request.form.get('is_consultancy', 'False') == 'True'
        except json.JSONDecodeError as e:
            logger.error(f"Gemini yanıtları JSON parse hatası: {str(e)}")
            gemini_response_list = [{"title": "Hata: Gemini yanıtları yüklenemedi", "is_button": False}]

    if request.method == 'POST' and 'product_name' in request.form:
        product_name = request.form.get('product_name')
        logger.info(f"Ürün araması: {product_name}")
        if product_name:
            with ThreadPoolExecutor(max_workers=5) as executor:
                future_heps = executor.submit(scrape_hepsiburada, product_name)
                future_trendyol = executor.submit(scrape_trendyol, product_name)
                trendyol_results = future_trendyol.result()
                hepsiburada_result = future_heps.result()
                
                # Hepsiburada ve Trendyol sonuçlarını birleştir
                results.extend(trendyol_results)
                results.extend(hepsiburada_result)
                
                # Hata kontrolü: Tüm ürünler hata içeriyorsa tek bir hata ekle
                if not results or all(item.get('title') == "Hata" for item in results):
                    results = [{"site": "Hepsiburada/Trendyol", "title": "Hata", "link": f"{product_name} için ürün bulunamadı", "price": "N/A", "rating": "N/A", "comments": "0", "image": "", "user_comments": []}]

            precautions = research_precautions_with_gemini(product_name)
            if precautions and not precautions.startswith("hata"):
                precautions_text = [{"text": precautions}]

            words = product_name.split()
            product_category = words[-1] if words else product_name
            optimized_title = optimize_title_with_gemini(product_name, product_category)
            logger.info(f"YouTube araması: '{optimized_title}'")
            with ThreadPoolExecutor(max_workers=2) as executor:
                future_youtube = executor.submit(scrape_youtube, optimized_title, YOUTUBE_API_KEY, max_results=3)
                future_precautions = executor.submit(scrape_youtube, f"{optimized_title} alınırken dikkat edilmesi gerekenler", YOUTUBE_API_KEY, max_results=3)
                videos = future_youtube.result()
                precautions_vids = future_precautions.result()
            
            if videos and videos[0]["title"] != "hata":
                youtube_videos.append({"search_term": optimized_title, "videos": videos})
                logger.info(f"YouTube: '{optimized_title}' için {len(videos)} video bulundu")
            else:
                logger.warning(f"YouTube: '{optimized_title}' için video bulunamadı: {videos}")
            
            if precautions_vids and precautions_vids[0]["title"] != "hata":
                precautions_videos.append({"search_term": f"{optimized_title} alınırken dikkat edilmesi gerekenler", "videos": precautions_vids})
            else:
                logger.warning(f"YouTube: '{optimized_title} alınırken dikkat edilmesi gerekenler' için video bulunamadı: {precautions_vids}")

    return render_template('index.html',
        results=results,
        youtube_videos=youtube_videos,
        precautions_videos=precautions_videos,
        precautions_text=precautions_text,
        gemini_response_list=gemini_response_list,
        is_consultancy=is_consultancy,
        chat_prompt=chat_prompt
    )

@app.route('/image-search', methods=['POST'])
def image_search():
    try:
        if 'image' not in request.files:
            logger.error("Görsel dosyası yüklenmedi")
            return render_template('index.html',
                results=[],
                gemini_response_list=[{"title": "Hata: Görsel dosyası yüklenmedi", "is_button": False}],
                youtube_videos=[],
                precautions_videos=[],
                precautions_text=[],
                is_consultancy=False,
                chat_prompt=""
            )

        image_file = request.files['image']
        if image_file.filename == '':
            logger.error("Boş dosya seçildi")
            return render_template('index.html',
                results=[],
                gemini_response_list=[{"title": "Hata: Boş dosya seçildi", "is_button": False}],
                youtube_videos=[],
                precautions_videos=[],
                precautions_text=[],
                is_consultancy=False,
                chat_prompt=""
            )

        genai.configure(api_key=GENAI_API_KEY)
        model = genai.GenerativeModel(model_name="gemini-2.5-pro")
        image = Image.open(image_file)
        image_bytes = io.BytesIO()
        image.save(image_bytes, format=image.format or 'JPEG')
        image_data = image_bytes.getvalue()

        prompt = (
            "Bu görseldeki ürünü analiz et ve ürünün türünü veya kategorisini kısa ve net bir şekilde belirt. "
            "Sadece ürün adını veya kategorisini döndür (örneğin, 'Tablo', 'Küpe'). "
            "Başka açıklama ekleme."
        )
        response = model.generate_content([prompt, {"mime_type": f"image/{image.format.lower() or 'jpeg'}", "data": image_data}])
        product_name = clean_response(response.text).strip()
        logger.info(f"Görsel analizi: Ürün kategorisi '{product_name}' olarak belirlendi")

        if not product_name or product_name.lower() in ["hata", "bulunamadı"]:
            logger.error("Görselden ürün kategorisi belirlenemedi")
            return render_template('index.html',
                results=[],
                gemini_response_list=[{"title": "Hata: Ürün kategorisi belirlenemedi", "is_button": False}],
                youtube_videos=[],
                precautions_videos=[],
                precautions_text=[],
                is_consultancy=False,
                chat_prompt=""
            )

        with ThreadPoolExecutor(max_workers=5) as executor:
            future_heps = executor.submit(scrape_hepsiburada, product_name)
            future_trendyol = executor.submit(scrape_trendyol, product_name)
            results = [future_heps.result(), future_trendyol.result()]

        precautions = research_precautions_with_gemini(product_name)
        precautions_text = [{"text": precautions}] if precautions and not precautions.startswith("hata") else []

        words = product_name.split()
        product_category = words[-1] if words else product_name
        optimized_title = optimize_title_with_gemini(product_name, product_category)
        logger.info(f"YouTube araması: '{optimized_title}'")
        with ThreadPoolExecutor(max_workers=2) as executor:
            future_youtube = executor.submit(scrape_youtube, optimized_title, YOUTUBE_API_KEY, max_results=3)
            future_precautions = executor.submit(scrape_youtube, f"{optimized_title} alınırken dikkat edilmesi gerekenler", YOUTUBE_API_KEY, max_results=3)
            videos = future_youtube.result()
            precautions_vids = future_precautions.result()

        youtube_videos = [{"search_term": optimized_title, "videos": videos}] if videos and videos[0]["title"] != "hata" else []
        precautions_videos = [{"search_term": f"{optimized_title} alınırken dikkat edilmesi gerekenler", "videos": precautions_vids}] if precautions_vids and precautions_vids[0]["title"] != "hata" else []

        return render_template('index.html',
            results=results,
            youtube_videos=youtube_videos,
            precautions_videos=precautions_videos,
            precautions_text=precautions_text,
            gemini_response_list=[{"title": f"Görselden belirlenen ürün: {product_name}", "is_button": False}],
            is_consultancy=False,
            chat_prompt=""
        )

    except Exception as e:
        logger.error(f"Görsel arama hatası: {str(e)}")
        return render_template('index.html',
            results=[],
            gemini_response_list=[{"title": f"Hata: Görsel arama başarısız ({str(e)})", "is_button": False}],
            youtube_videos=[],
            precautions_videos=[],
            precautions_text=[],
            is_consultancy=False,
            chat_prompt=""
        )

@app.route('/play-outputs', methods=['POST'])
def play_outputs():
    try:
        gemini_responses = json.loads(request.form.get('gemini_response_list', '[]'))
        precautions = request.form.get('precautions_text', '')
        
        selected_texts = []
        # Ürün önerilerini ekle (is_button: True olanlar)
        for item in gemini_responses:
            if item.get('is_button', False):
                selected_texts.append(item.get('title', ''))
        
        # Dikkat edilmesi gerekenleri ekle
        if precautions:
            for line in precautions.split('\n'):
                line = line.strip()
                if line:
                    selected_texts.append(line)

        if not selected_texts:
            logger.error("Seslendirilecek çıktı bulunamadı")
            return jsonify({"error": "Hata: Seslendirilecek çıktı bulunamadı"})

        combined_text = ". ".join(selected_texts) + "."
        logger.info(f"Seslendirilecek metin: {combined_text}")

        tts = gTTS(text=combined_text, lang='tr', slow=True)  # Daha net okuma için slow=True
        audio_path = os.path.join('static', 'audio', 'output.mp3')
        os.makedirs(os.path.dirname(audio_path), exist_ok=True)
        tts.save(audio_path)
        logger.info(f"Ses dosyası oluşturuldu: {audio_path}")

        return send_file(audio_path, mimetype='audio/mpeg')
    except Exception as e:
        logger.error(f"Sesli okuma hatası: {str(e)}")
        return jsonify({"error": f"Hata: Sesli okuma başarısız ({str(e)})"})

@app.route('/gemini-chat', methods=['POST'])
def gemini_chat():
    prompt = request.form['chat_prompt']
    genai.configure(api_key=GENAI_API_KEY)
    try:
        model = genai.GenerativeModel(model_name="gemini-2.5-pro")
        chat = model.start_chat()

        consultancy_keywords = ["öneri", "tavsiye", "liste", "ne almalıyım", "hangi", "tavsiyeler"]
        is_consultancy = any(keyword in prompt.lower() for keyword in consultancy_keywords)

        if is_consultancy:
            full_prompt = (
                f"{prompt}\n"
                "Lütfen cevabını kısa tut ve sadece 5 farklı ürün önerisi şeklinde liste ver. "
                "Her öneri ayrı bir satırda olacak, ürünün ne olduğunu sonuna ekle (örneğin, 'Ahşap tablo tablo'). "
                "Aralara duygusal veya görünüşleriyle ilgili yorum katma, sadece ürün adını söyle. "
                "Cevabının başına veya sonuna 'elbette' veya 'rica ederim' gibi bitirme sözleri ekleme."
            )
            response = chat.send_message(full_prompt)
            raw_text = clean_response(response.text)
            cevaplar = []
            for line in raw_text.split("\n"):
                if line.strip():
                    words = line.strip().split()
                    if words and len(words) > 1:
                        cleaned_line = " ".join(words[:-1])
                        cevaplar.append({"title": str(cleaned_line), "is_button": True})
            if len(cevaplar) < 5:
                logger.warning(f"Gemini sadece {len(cevaplar)} öneri üretti, tekrar deneniyor")
                response = chat.send_message(full_prompt)
                raw_text = clean_response(response.text)
                for line in raw_text.split("\n"):
                    if line.strip() and len(cevaplar) < 5:
                        words = line.strip().split()
                        if words and len(words) > 1:
                            cleaned_line = " ".join(words[:-1])
                            cevaplar.append({"title": str(cleaned_line), "is_button": True})
            cevaplar = cevaplar[:5]
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
                is_consultancy=True,
                chat_prompt=prompt
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
                is_consultancy=False,
                chat_prompt=prompt
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
            is_consultancy=False,
            chat_prompt=prompt
        )

@app.route('/start-audio', methods=['POST'])
def start_audio():
    try:
        transcription, success = audio_output.translate_audio()
        
        if transcription and success:
            logger.info(f"Metin alındı: {transcription[:100]}...")
            genai.configure(api_key=GENAI_API_KEY)
            model = genai.GenerativeModel(model_name="gemini-2.5-pro")
            chat = model.start_chat()
            consultancy_keywords = ["öneri", "tavsiye", "liste", "ne almalıyım", "hangi", "tavsiyeler"]
            is_consultancy = any(keyword in transcription.lower() for keyword in consultancy_keywords)
            if is_consultancy:
                full_prompt = (
                    f"{transcription}\n"
                    "Lütfen cevabını kısa tut ve sadece 5 farklı ürün önerisi şeklinde liste ver. "
                    "Her öneri ayrı bir satırda olacak, ürünün ne olduğunu sonuna ekle (örneğin, 'Ahşap tablo tablo'). "
                    "Aralara duygusal veya görünüşleriyle ilgili yorum katma, sadece ürün adını söyle. "
                    "Cevabının başına veya sonuna 'elbette' veya 'rica ederım' gibi bitirme sözleri ekleme."
                )
                response = chat.send_message(full_prompt)
                raw_text = clean_response(response.text)
                cevaplar = []
                for line in raw_text.split("\n"):
                    if line.strip():
                        words = line.strip().split()
                        if words and len(words) > 1:
                            cleaned_line = " ".join(words[:-1])
                            cevaplar.append({"title": str(cleaned_line), "is_button": True})
                if len(cevaplar) < 5:
                    logger.warning(f"Gemini sadece {len(cevaplar)} öneri üretti, tekrar deneniyor")
                    response = chat.send_message(full_prompt)
                    raw_text = clean_response(response.text)
                    for line in raw_text.split("\n"):
                        if line.strip() and len(cevaplar) < 5:
                            words = line.strip().split()
                            if words and len(words) > 1:
                                cleaned_line = " ".join(words[:-1])
                                cevaplar.append({"title": str(cleaned_line), "is_button": True})
                cevaplar = cevaplar[:5]
                with open("gemini_cevaplar.txt", "a", encoding="utf-8") as f:
                    f.write(f"Sesli Soru: {transcription}\nCevaplar:\n")
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
                    is_consultancy=True,
                    chat_prompt=transcription
                )
            else:
                full_prompt = (
                    f"{transcription}\n"
                    "Soruya doğrudan, kısa ve net bir cevap ver. "
                    "Cevabın sonuna 'Size nasıl yardımcı olabilirim?' ekle."
                )
                response = chat.send_message(full_prompt)
                raw_text = clean_response(response.text)
                cevaplar = [{"title": str(raw_text), "is_button": False}]
                logger.info(f"Gemini cevabı alındı (düz metin): {raw_text[:100]}...")
                with open("gemini_cevaplar.txt", "a", encoding="utf-8") as f:
                    f.write(f"Sesli Soru: {transcription}\nCevap: {raw_text}\n\n")
                return render_template('index.html',
                    results=[],
                    gemini_response_list=cevaplar,
                    youtube_videos=[],
                    precautions_videos=[],
                    precautions_text=[],
                    is_consultancy=False,
                    chat_prompt=transcription
                )
        else:
            logger.info("Metin alınamadı, konuşma algılanmadı")
            return render_template('index.html',
                results=[],
                gemini_response_list=[{"title": "Konuşma algılanmadı", "is_button": False}],
                youtube_videos=[],
                precautions_videos=[],
                precautions_text=[],
                is_consultancy=False,
                chat_prompt=""
            )
    
    except Exception as e:
        logger.error(f"Ses kaydı veya çeviri hatası: {str(e)}")
        cevaplar = [{"title": f"Hata: {str(e)}", "is_button": False}]
        return render_template('index.html',
            results=[],
            gemini_response_list=cevaplar,
            youtube_videos=[],
            precautions_videos=[],
            precautions_text=[],
            is_consultancy=False,
            chat_prompt=""
        )

@app.route('/stop-audio', methods=['POST'])
def stop_audio():
    try:
        logger.info("Ses kaydı durduruldu (otomatik durdurma kullanıldığı için işlem yok)")
        return jsonify({"status": "Ses kaydı durduruldu"})
    except Exception as e:
        logger.error(f"Ses kaydı durdurma hatası: {str(e)}")
        return jsonify({"error": f"Hata: {str(e)}"})

if __name__ == '__main__':
    app.run(debug=True)

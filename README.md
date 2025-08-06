## Proje Hakkında
Ürün Arama Asistanı, kullanıcıların Trendyol ve Hepsiburada’dan ürün aramalarını kolaylaştırmak için geliştirilmiş bir web uygulamasıdır. Gemini’nin yapay zeka yeteneklerini kullanarak ürünleri hızlıca tarar, fiyatları, puanları, yorum sayıları ve görselleri yan yana listeler. Ayrıca, YouTube’dan ürünle ilgili inceleme ve kullanım videoları önererek alışveriş deneyimini zenginleştirir. Mobil uyumlu arayüzü ve basit kullanımıyla, kullanıcıların zaman tasarrufu yapmasını ve en iyi fırsatları bulmasını sağlar.

### Amaç
- Alışveriş sürecini hızlandırmak ve basitleştirmek.
- Trendyol ve Hepsiburada’dan ürünleri karşılaştırmalı olarak sunmak.
- Gemini ile optimize edilmiş YouTube önerileriyle bilgi sağlamak.
- Güvenilir, hızlı ve kullanıcı dostu bir alışveriş asistanı sunmak.

## Özellikler
- **Çoklu Platform Desteği**: Trendyol ve Hepsiburada’dan aynı anda ürün tarama.
- **Sesli Bildirim**: Gemini tarafından yapılan yorumların çıktısı sesli olarak alınabiliyor.
- **Ürün Karşılaştırma**:
  - İlk 5 ürünü yan yana listeleme (Trendyol ve Hepsiburada için ayrı ayrı).
  - Fiyat, puan, yorum sayısı ve ürün görselleri gösterimi.
- **Gemini ile Yapay Zeka Desteği**:
  - Arama sorgularını optimize etme (örneğin, “halhal” → “Halhal Modelleri Halhal”).
  - YouTube’dan ilgili videolar önerisi.
- **Mobil Uyumlu Arayüz**: Yatay kaydırmalı kartlar, mobil ve masaüstü cihazlarda sorunsuz deneyim.
- **Hızlı ve Güvenilir**: Selenium ile dinamik web scraping, WebDriver Manager ile otomatik tarayıcı yönetimi.
- **Hata Yönetimi**: Ürün bulunamama veya scraper hatalarında kullanıcı dostu hata mesajları.

## Teknolojiler
- **Backend**: Python 3.8+, Flask
- **Web Scraping**: Selenium, WebDriver Manager
- **Frontend**: HTML, CSS (mobil uyumlu tasarım)
- **Yapay Zeka**: Gemini (arama optimizasyonu ve YouTube önerileri)
- **YouTube Entegrasyonu**: Google YouTube Data API (veya HTML scraping, scraper_youtube.py’ye bağlı)
- **Loglama**: Python logging modülü
- **Bağımlılık Yönetimi**: pip, requirements.txt

### Gereksinimler
- Python 3.8 veya üstü
- Google Chrome tarayıcı (Selenium için)
- İnternet bağlantısı (web scraping ve YouTube API için)

## Kurulum
Projenizi yerel makinenizde çalıştırmak için aşağıdaki adımları izleyin.

1. **Depoyu Klonlayın**:
   ```bash
   git clone https://github.com/BeratYumak/GeminiCommercialConsultant.git
   cd GeminiCommercialConsultant-master
2. Sanal Ortam Oluşturun:
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   venv\Scripts\activate     # Windows

3.Bağımlılıkları Yükleyin:
  pip install -r requirements.txt

4.Gerekli Dizinleri Oluşturun:
  mkdir -p static/audio

5.Uygulamayı Çalıştırın:
  python app.py
  
6. Uygulamaya Erişin:
  Tarayıcınızda http://localhost:5000 adresine gidin.



## Kullanım

**Arama Yapma:**

http://localhost:5000 adresine gidin.
Arama çubuğuna bir ürün adı yazın (örneğin, “iPhone 13” veya “halhal”).
“Ara” butonuna tıklayın.


Sonuçları Görüntüleme:

Trendyol: İlk 5 ürün, yatay kaydırmalı kartlarda listelenir.

Fiyatlar div.price-container span.price-normal-price seçicisinden çekilir.
Başlık, puan, yorum sayısı ve görsel gösterilir.


Hepsiburada: İlk 5 ürün, Trendyol’un altında yatay kaydırmalı kartlarda listelenir.

Fiyatlar [data-test-id='price'] veya diğer seçicilerden çekilir.
Reklam içeren linkler (adservice, sponsored, vb.) filtrelenir.


YouTube Önerileri: Ürünle ilgili videolar (örneğin, “iPhone 13 Modelleri iPhone 13”) en altta gösterilir.

DOSYA YAPISI:

GeminiCommercialConsultant/

├── app.py                    # Flask uygulaması, ana endpoint

├── scraper_trendyol.py       # Trendyol scraper’ı

├── scraper_hepsiburada.py    # Hepsiburada scraper’ı

├── scraper_youtube.py        # YouTube video scraper’ı

├── templates/
│   └── index.html            # Frontend HTML şablonu

├── static/
│   └── audio/                # Ses dosyaları için (isteğe bağlı)

├── requirements.txt          # Bağımlılıklar

├── gemini_cevaplar.txt       # Log dosyası

└── README.md                 # Bu dosya

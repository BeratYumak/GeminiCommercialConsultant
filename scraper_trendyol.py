# scraper_youtube.py
import requests
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def scrape_youtube(query, api_key, max_results=5):
    try:
        url = "https://www.googleapis.com/youtube/v3/search"
        params = {
            "part": "snippet",
            "q": query,
            "type": "video",
            "maxResults": max_results,
            "key": api_key,
            "order": "relevance"  # Daha alakalı sonuçlar için
        }
        response = requests.get(url, params=params)
        response.raise_for_status()  # HTTP hatalarını yakala
        items = response.json().get("items", [])
        videos = []
        for item in items:
            videos.append({
                "title": item["snippet"]["title"],
                "videoId": item["id"]["videoId"],
                "thumbnail": item["snippet"]["thumbnails"]["medium"]["url"],
                "url": f"https://www.youtube.com/watch?v={item['id']['videoId']}",
                "views": "N/A"  # İzlenme sayısı için ek API çağrısı gerekirse eklenebilir
            })
        logger.info(f"YouTube: '{query}' için {len(videos)} video bulundu")
        return videos
    except requests.exceptions.HTTPError as e:
        logger.error(f"YouTube API hatası: {e}")
        return [{"title": "Hata", "url": "", "thumbnail": "", "views": f"YouTube API hatası: {str(e)}"}]
    except Exception as e:
        logger.error(f"YouTube genel hatası: {e}")
        return [{"title": "Hata", "url": "", "thumbnail": "", "views": f"YouTube genel hatası: {str(e)}"}]

import os
import time
import wave
import numpy as np
import google.generativeai as genai
import pyaudio

# ANSI renk kodları
NEON_GREEN = "\033[92m"
BLUE = "\033[94m"
RED = "\033[91m"
RESET_COLOR = "\033[0m"

# Google Gemini API ayarları
GOOGLE_API_KEY = "AIzaSyB7ZvG_Fx5sOwIkEK2wkMajXEbTuwH5S5Y"
genai.configure(api_key=GOOGLE_API_KEY)

# Yapılandırma
CHUNK_DURATION_SEC = 5
TARGET_LANGUAGE = "Turkish"
SOURCE_LANGUAGE = "auto"

# Ses parametreleri
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
CHUNK = 1024
SILENCE_THRESHOLD = 30  # Sessizlik eşiği (düşürüldü, daha hassas)
SILENCE_DURATION = 2  # Sessizlik süresi (saniye)

def save_audio_as_wav(frames, filename):
    """Ses çerçevelerini WAV dosyası olarak kaydeder."""
    with wave.open(filename, 'wb') as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(2)
        wf.setframerate(RATE)
        wf.writeframes(b''.join(frames))
    return True

def translate_chunk(model_name, chunk_file):
    """Ses dosyasını çevirir."""
    try:
        if not os.path.exists(chunk_file) or os.path.getsize(chunk_file) < 100:
            print(f"{RED}Uyarı: Ses dosyası boş veya çok küçük{RESET_COLOR}")
            return ""

        with open(chunk_file, 'rb') as f:
            file_content = f.read()
        
        google_model = genai.GenerativeModel(model_name=model_name)
        transcription_prompt = """
        Transcribe the speech in this audio file. 
        Only return the transcribed text without any additional information or explanations.
        If there is no speech detected, return exactly "NO_SPEECH_DETECTED".
        """
        response = google_model.generate_content(
            contents=[
                {'text': transcription_prompt},
                {'inline_data': {'mime_type': 'audio/wav', 'data': file_content}}
            ]
        )
        transcription = response.text.strip()
        
        if transcription == "NO_SPEECH_DETECTED" or not transcription:
            return ""
            
        if SOURCE_LANGUAGE != "auto" and SOURCE_LANGUAGE.lower() != "english" and TARGET_LANGUAGE.lower() == "english":
            translation_prompt = f"Translate this from {SOURCE_LANGUAGE} to {TARGET_LANGUAGE}: {transcription}"
            translation_response = google_model.generate_content(translation_prompt)
            return translation_response.text.strip()
        
        return transcription
        
    except Exception as e:
        print(f"{RED}Çeviri hatası: {str(e)}{RESET_COLOR}")
        time.sleep(1)
        return ""

def record_audio():
    """Ses kaydeder, sessizlik algılanırsa otomatik durdurur."""
    p = pyaudio.PyAudio()
    frames = []
    
    try:
        stream = p.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            input=True,
            frames_per_buffer=CHUNK
        )
        
        print(f"{BLUE}Kayıt başlıyor...{RESET_COLOR}")
        
        # İlk 0.5 saniyeyi gürültü/sessizlik için atla
        for _ in range(0, int(RATE / CHUNK * 0.5)):
            stream.read(CHUNK, exception_on_overflow=False)
        
        silence_start = None
        while True:
            data = stream.read(CHUNK, exception_on_overflow=False)
            frames.append(data)
            
            # Ses verisini kontrol et
            audio_data = np.frombuffer(data, dtype=np.int16)
            rms = np.sqrt(np.mean(np.square(audio_data.astype(np.float32))))
            
            if rms < SILENCE_THRESHOLD:
                if silence_start is None:
                    silence_start = time.time()
                elif time.time() - silence_start > SILENCE_DURATION:
                    print(f"{BLUE}Sessizlik algılandı (RMS: {rms:.2f}), kayıt durduruluyor...{RESET_COLOR}")
                    break
            else:
                silence_start = None
            
            # Maksimum süre kontrolü
            if len(frames) * CHUNK / RATE > CHUNK_DURATION_SEC:
                print(f"{BLUE}Maksimum süre ({CHUNK_DURATION_SEC}s) aşıldı, kayıt durduruluyor...{RESET_COLOR}")
                break
        
        # Ses verisini kontrol et
        audio_data = np.frombuffer(b''.join(frames), dtype=np.int16)
        rms = np.sqrt(np.mean(np.square(audio_data.astype(np.float32))))
        
        if rms > SILENCE_THRESHOLD:
            return frames
        else:
            print(f"{BLUE}Sessizlik algılandı (RMS: {rms:.2f}), kayıt atlanıyor...{RESET_COLOR}")
            return None
    
    except Exception as e:
        print(f"{RED}Kayıt hatası: {str(e)}{RESET_COLOR}")
        return None
    
    finally:
        stream.stop_stream()
        stream.close()
        p.terminate()
        print(f"{BLUE}Kayıt tamamlandı.{RESET_COLOR}")

def translate_audio():
    """Tek bir ses kaydını yapar, çevirir ve sonucu döndürür."""
    chunk_file = "temp_chunk.wav"
    translation = ""
    
    try:
        # Ses kaydını yap
        frames = record_audio()
        
        if frames:
            # Ses parçasını kaydet
            save_audio_as_wav(frames, chunk_file)
            
            # Ses parçasını çevir
            translation = translate_chunk('gemini-2.5-pro', chunk_file)
            
            if translation and translation.strip():
                print(f"{NEON_GREEN}Çeviri: {translation}{RESET_COLOR}")
            else:
                print(f"{RED}Konuşma algılanmadı{RESET_COLOR}")
            
            # Geçici dosyayı sil
            try:
                os.remove(chunk_file)
            except:
                pass
            
        return translation, frames is not None
    
    except Exception as e:
        print(f"{RED}İşleme hatası: {str(e)}{RESET_COLOR}")
        return "", False
    
if __name__ == "__main__":
    translation, success = translate_audio()
    print(f"{BLUE}Çevrilen metin: {translation}{RESET_COLOR}")
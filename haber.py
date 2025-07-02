import requests
from bs4 import BeautifulSoup
import json
import os
import smtplib
from email.mime.text import MIMEText
from email.header import Header
import traceback
import time
import google.generativeai as genai

# --- YAPILANDIRMA (LÜTFEN BU ALANLARI DOLDURUN) ---

# 1. Gemini API Anahtarı
# Google AI Studio'dan aldığınız API anahtarınızı buraya yapıştırın.
GEMINI_API_KEY = "AIzaSyAhWRiGAgtvAG94eoH53F6XyA8f5zlvMUY"


# 2. Blog Sitenize POST yapılacak URL
# Oluşturduğumuz blog_ekle.php dosyasının tam URL'si.
BLOG_POST_URL = "https://kiyaslasana.com/blog_ekle.php"

# 3. E-posta Ayarları
SMTP_SERVER = "mail.kiyaslasana.com"
SMTP_PORT = 587
EMAIL_ADRESINIZ = "samet@kiyaslasana.com"
EMAIL_SIFRENIZ = "Galatasaray1!"
ALICI_EMAIL_ADRESI = "egenull0@gmail.com"

# 4. Site İçerik Seçicileri (Selectors)
# Her site için haber başlığı ve içeriğini çekecek HTML seçicileri.
SITE_CONFIGS = {
    "Webtekno": {
        "title_selector": "h1[itemprop=\"headline\"]",
        "content_selector": "div[itemprop=\"articleBody\"]"
    },
    "ShiftDelete.Net": {
        "title_selector": "h1.tdb-title-text",
        "content_selector": "div.td-post-content.tagdiv-type"
    },
    "DonanımHaber": {
        "title_selector": "h1.dh-title",
        "content_selector": "div.article-content"
    },
    "Donanım Arşivi": {
        "title_selector": "h1.zox-post-title",
        "content_selector": "div.zox-post-body"
    },
    "NTV": {
        "title_selector": "h1.category-detail-title",
        "content_selector": "div.category-detail-content"
    }
}

# --- YARDIMCI FONKSİYONLAR ---

def json_dosyasini_oku(dosya_yolu):
    if os.path.exists(dosya_yolu):
        try:
            with open(dosya_yolu, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return []
    return []

def json_dosyasina_yaz(dosya_yolu, veri):
    with open(dosya_yolu, 'w', encoding='utf-8') as f:
        json.dump(veri, f, ensure_ascii=False, indent=4)

def mail_gonder(baslik, icerik):
    if not all([SMTP_SERVER, EMAIL_ADRESINIZ, EMAIL_SIFRENIZ, ALICI_EMAIL_ADRESI]) or "ornek@gmail.com" in EMAIL_ADRESINIZ:
        print("\n--- E-POSTA GÖNDERİMİ ATLANDI (Yapılandırma Eksik) ---")
        return
    try:
        msg = MIMEText(icerik, 'plain', 'utf-8')
        msg['Subject'] = Header(baslik, 'utf-8')
        msg['From'] = EMAIL_ADRESINIZ
        msg['To'] = ALICI_EMAIL_ADRESI
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(EMAIL_ADRESINIZ, EMAIL_SIFRENIZ)
        server.sendmail(EMAIL_ADRESINIZ, [ALICI_EMAIL_ADRESI], msg.as_string())
        server.quit()
        print("E-posta başarıyla gönderildi.")
    except Exception as e:
        print(f"E-posta gönderilirken bir hata oluştu: {e}")

# --- OTOMASYON FONKSİYONLARI ---

def get_article_details(url, site_key):
    """Verilen URL'den başlık ve içeriği çeker."""
    config = SITE_CONFIGS.get(site_key)
    if not config:
        print(f"HATA: '{site_key}' için site yapılandırması eksik. Atlanıyor.")
        return None, None

    print(f"  -> Sayfa içeriği çekiliyor: {url}")
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=20)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'lxml')
        
        title_element = soup.select_one(config['title_selector'])
        content_element = soup.select_one(config['content_selector'])
        
        if title_element and content_element:
            for tag in content_element.select('script, style, .advertisement, .related-posts, .ads, .ad-wrapper, .zox-post-ad-wrap'):
                tag.decompose()
            
            title = title_element.get_text(strip=True)
            content = content_element.get_text(strip=True, separator='\n')
            print("  -> Başlık ve içerik başarıyla çekildi.")
            return title, content
        else:
            print("  -> HATA: Başlık veya içerik seçicileri bulunamadı. Lütfen SITE_CONFIGS'i kontrol edin.")
            debug_filename = f"debug_article_{site_key.replace(' ', '_')}.html"
            with open(debug_filename, 'w', encoding='utf-8') as f:
                f.write(soup.prettify())
            print(f"  -> DEBUG: Sayfanın HTML'i '{debug_filename}' dosyasına kaydedildi.")
            return None, None
    except requests.exceptions.RequestException as e:
        print(f"  -> HATA: Sayfa çekilirken hata oluştu: {e}")
    except Exception as e:
        print(f"  -> HATA: Sayfa işlenirken bir hata oluştu: {e}")
    return None, None

def generate_blog_post(title, content, site_name):
    """Verilen içerik için Gemini API kullanarak blog yazısı oluşturur."""
    if not GEMINI_API_KEY or "YOUR_GEMINI_API_KEY" in GEMINI_API_KEY:
        print("  -> HATA: Gemini API anahtarı ayarlanmamış. Atlanıyor.")
        return None

    print("  -> İçerik Gemini'ye gönderiliyor...")
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        prompt = f"""
        Orijinal Haber Başlığı: {title}
        Orijinal Haber Metni:
        ---
        {content}
        ---

        GÖREV:
        Yukarıdaki metni, tecrübeli bir teknoloji editörü olarak kiyaslasana.com için yazdığını düşün. Bu metni kaynak alarak, Türkçe dil kurallarına ve SEO prensiplerine uygun, özgün bir makale oluştur. Rakip firma isimleri kullanma, sadece kiyaslasana.com'dan bahset.

        İSTENEN ÇIKTI FORMATI:
        Yanıtın KESİNLİKLE SADECE ve SADECE aşağıda belirtilen yapıda bir JSON nesnesi olmalıdır. JSON dışında HİÇBİR metin, açıklama, giriş veya sonuç cümlesi eklemeyin.
        {{
          "baslik": "Buraya SEO uyumlu, ilgi çekici ve özgün yeni başlık gelecek.",
          "icerik": "Buraya senin tarafıdan, tüm kurallara uyarak yeniden yazılmış makalenin tam metni gelecek.",
          "etiketler": ["konuyla ilgili etiket 1", "etiket 2", "teknoloji", "{site_name}"]
        }}
        """

        response = model.generate_content(prompt)
        
        cleaned_response = response.text.strip().replace("```json", "").replace("```", "").strip()
        
        try:
            article_data = json.loads(cleaned_response)
        except json.JSONDecodeError:
            print(f"  -> HATA: Gemini'den gelen yanıt JSON formatında değil. Yanıt: {cleaned_response}")
            return None
        
        if 'baslik' in article_data and 'icerik' in article_data and 'etiketler' in article_data:
            print("  -> Gemini'den geçerli JSON yanıtı alındı.")
            return article_data
        else:
            print("  -> HATA: Gemini'den gelen JSON'da beklenen anahtarlar yok.")
            return None

    except Exception as e:
        if '429' in str(e):
            print("  -> BİLGİ: Gemini API kullanım limitine ulaşıldı. 1 dakika bekleniyor...")
            time.sleep(60)
            return generate_blog_post(title, content, site_name) # Tekrar dene
        print(f"  -> HATA: Gemini API ile iletişimde sorun oluştu: {e}")
        if 'response' in locals():
            print(f"  -> Gemini'den gelen ham yanıt: {response.text}")
        return None

def save_as_draft(article_data):
    """Oluşturulan yazıyı web sitesine taslak olarak gönderir."""
    if not BLOG_POST_URL or "siteniz.com" in BLOG_POST_URL:
        print("  -> HATA: BLOG_POST_URL yapılandırılmamış. Atlanıyor.")
        return False

    print(f"  -> '{article_data['baslik']}' başlıklı yazı taslak olarak siteye gönderiliyor...")
    
    try:
        tags_str = ",".join(article_data.get('etiketler', []))
        payload = {
            'baslik': article_data['baslik'],
            'icerik': article_data['icerik'],
            'etiketler': tags_str
        }

        response = requests.post(BLOG_POST_URL, data=payload, timeout=30)
        
        if response.status_code == 201 or response.status_code == 200:
            try:
                response_json = response.json()
                if response_json.get("status") == "success":
                    print(f"  -> BAŞARILI: Yazı taslak olarak eklendi. (Blog ID: {response_json.get('blog_id')})")
                    return True
                else:
                    print(f"  -> HATA: Web sitesi tarafında bir sorun oluştu: {response_json.get('message')}")
                    return False
            except json.JSONDecodeError:
                 print(f"  -> HATA: Web sitesinden gelen yanıt JSON formatında değil. Yanıt: {response.text}")
                 return False
        else:
            print(f"  -> HATA: Web sitesine bağlanırken hata: {response.status_code} {response.reason}")
            print(f"  -> Sunucu Yanıtı: {response.text}")
            return False

    except requests.exceptions.RequestException as e:
        print(f"  -> HATA: Web sitesine bağlanırken hata: {e}")
    return False

# --- SİTE KONTROL FONKSİYONLARI ---

def generic_site_kontrol_et(site_key, url, json_dosyasi, list_selector, link_selector, title_selector=None, url_prefix=""):
    """Tüm siteler için jenerik kontrol fonksiyonu."""
    print(f"\n{site_key} kontrol ediliyor...")
    time.sleep(10) # Site kontrolü öncesi 10 saniye bekle
    
    processed_links_data = json_dosyasini_oku(json_dosyasi)
    eski_haber_linkleri = [haber['link'] for haber in processed_links_data]
    mevcut_haberler = []
    yeni_haberler = []
    basariyla_islenenler = []

    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'lxml')
        haber_listesi = soup.select(list_selector)

        if not haber_listesi:
            print(f"-> HATA: Ana sayfada '{list_selector}' ile eşleşen haber listesi bulunamadı.")
            debug_filename = f"debug_homepage_{site_key.replace(' ', '_')}.html"
            with open(debug_filename, 'w', encoding='utf-8') as f:
                f.write(soup.prettify())
            print(f"-> DEBUG: Ana sayfa HTML'i '{debug_filename}' dosyasına kaydedildi.")
            return basariyla_islenenler

        for item in haber_listesi[:10]:
            link_tag = item.select_one(link_selector)
            
            if link_tag and link_tag.has_attr('href'):
                link = link_tag['href']
                if not link.startswith('http'):
                    link = (url_prefix or url).rstrip('/') + link
                
                # Kategori ve galeri linklerini atla
                if "galeri" in link or (site_key == "Webtekno" and not link.endswith(".html")):
                     continue

                title_tag = item.select_one(title_selector) if title_selector else link_tag
                title = title_tag.get_text(strip=True) if title_tag else "Başlık Bulunamadı"

                mevcut_haberler.append({'baslik': title, 'link': link})

    except requests.exceptions.RequestException as e:
        print(f"{site_key} sitesine bağlanırken bir hata oluştu: {e}")
        return basariyla_islenenler

    if not mevcut_haberler:
        print(f"-> {site_key} için haberler bulunamadı. Site yapısı değişmiş olabilir.")
        return basariyla_islenenler

    for haber in mevcut_haberler:
        if haber['link'] not in eski_haber_linkleri:
            yeni_haberler.append(haber)
    
    if not yeni_haberler:
        print(f"-> {site_key} kontrolü tamamlandı. Yeni haber bulunamadı.")
        return basariyla_islenenler

    print(f"-> {site_key} kontrolü tamamlandı. {len(yeni_haberler)} yeni haber bulundu. İşleniyor...")
    for haber in reversed(yeni_haberler):
        print(f"\n-> İşleme Alınan Haber: '{haber['baslik']}'")
        
        title, content = get_article_details(haber['link'], site_key)
        if not title or not content:
            continue

        article_data = generate_blog_post(title, content, site_key)
        if not article_data:
            continue

        success = save_as_draft(article_data)
        if success:
            basariyla_islenenler.append(haber)
            processed_links_data.append(haber)

    time.sleep(5)  # Her haber sonrası 5 saniye bekle

    json_dosyasina_yaz(json_dosyasi, processed_links_data)
    print(f"-> {site_key} kontrolü tamamlandı. Bir sonraki siteye geçmeden önce 10 saniye bekleniyor...")
    time.sleep(10)
    return basariyla_islenenler

# --- ANA KOD ---
if __name__ == "__main__":
    print("Haber otomasyon süreci başlatıldı.")
    print("="*40)
    
    tum_basarili_haberler = {}

    site_params = [
        {
            "site_key": "Webtekno", "url": "https://www.webtekno.com/", "json_dosyasi": "webtekno_haberler.json",
            "list_selector": "div.content-timeline__item", 
            "link_selector": "a.content-timeline__link",
            "title_selector": "h3.content-timeline__detail__title",
            "url_prefix": "https://www.webtekno.com"
        },
        {
            "site_key": "ShiftDelete.Net", "url": "https://shiftdelete.net/haberler", "json_dosyasi": "shiftdelete_haberler.json",
            "list_selector": "div.tdb_module_loop", 
            "link_selector": "h3.entry-title a",
            "title_selector": "h3.entry-title a"
        },
        {
            "site_key": "DonanımHaber", "url": "https://www.donanimhaber.com/", "json_dosyasi": "donanimhaber_haberler.json",
            "list_selector": "section.ekslayt a.ekoge", 
            "link_selector": ".",
            "title_selector": "span.baslik.previewTitle",
            "url_prefix": "https://www.donanimhaber.com"
        },
        {
            "site_key": "Donanım Arşivi", "url": "https://donanimarsivi.com/", "json_dosyasi": "donanimarsivi_haberler.json",
            "list_selector": "article.zox-art-wrap", 
            "link_selector": "a",
            "title_selector": "h2.zox-s-title2 a"
        },
        {
            "site_key": "NTV", "url": "https://www.ntv.com.tr/teknoloji", "json_dosyasi": "ntv_haberler.json",
            "list_selector": "div.card.card--md", 
            "link_selector": "a",
            "title_selector": "h3.card-text",
            "url_prefix": "https://www.ntv.com.tr"
        }
    ]

    for params in site_params:
        try:
            processed = generic_site_kontrol_et(**params)
            if processed:
                tum_basarili_haberler[params['site_key']] = processed
        except Exception as e:
            print(f"Ana döngüde '{params.get('site_key', 'Bilinmeyen')}' sitesi için bir hata oluştu: {e}")
            traceback.print_exc()

    print("\n" + "="*40)
    if tum_basarili_haberler:
        mail_basligi = "Otomasyon Raporu: Yeni Blog Taslakları Eklendi"
        mail_icerigi = "Aşağıdaki haberler başarıyla işlenerek sitenize taslak olarak eklendi:\n\n"
        for site, haberler in tum_basarili_haberler.items():
            mail_icerigi += f"--- {site} ---\n"
            for haber in haberler:
                mail_icerigi += f"- {haber['baslik']}\n  Orijinal Link: {haber['link']}\n"
            mail_icerigi += "\n"
        mail_icerigi += "Lütfen admin panelinize giderek yazıları kontrol edin, kapak görsellerini ekleyin ve yayınlayın."
        
        print("\n--- Gönderilecek Mail İçeriği ---\n")
        print(mail_icerigi)
        print("---------------------------------")
        mail_gonder(mail_basligi, mail_icerigi)
    else:
        print("\nTüm siteler kontrol edildi. İşlenecek yeni bir haber bulunamadı veya işlenemedi.")
    
    print("\n" + "="*40)
    print("Haber otomasyon süreci tamamlandı.")

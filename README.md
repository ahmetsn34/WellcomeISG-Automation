# Sea Fort RPA AI - Wellcome Automation Suite

<p align="center">
  <a href="README.md">🇹🇷 Türkçe</a> | 
  <a href="README_EN.md">🇺🇸 English</a>
</p>

---
# Sea Fort RPA AI - Wellcome Otomasyon Süiti

[![Python Version](https://img.shields.io/badge/python-3.8%20%7C%203.9%20%7C%203.10-blue)](https://www.python.org/)
[![Framework](https://img.shields.io/badge/UI-CustomTkinter-orange)](https://github.com/TomSchimansky/CustomTkinter)
[![Automation](https://img.shields.io/badge/Stealth-Undetected__Chromedriver-brightgreen)](https://github.com/ultrafunkamsterdam/undetected-chromedriver)
[![OCR](https://img.shields.io/badge/OCR-Tesseract-blueviolet)](https://github.com/UB-Mannheim/tesseract/wiki)

**Sea Fort RPA AI**, insan kaynakları ve İSG dökümantasyon süreçlerini otomatize etmek amacıyla geliştirilmiş, yapay zeka destekli kurumsal bir RPA (Robotic Process Automation) masaüstü yazılımıdır. 

Sistem, Excel/CSV dosyalarından okuduğu personel verilerini otomatik olarak sisteme kaydeder ve personellere ait 11 farklı zorunlu evrak tipini (Adli Sicil, Kimlik, İSG Talimatları, SGK Giriş vb.) akıllı OCR ve dosya adı baskınlık (Override) algoritmalarıyla teşhis ederek Wellcome (ISG) platformuna firesiz bir şekilde yükler.

---

## 🚀 Öne Çıkan Özellikler ve Çözülen Zorluklar (Engine Highlights)

Geliştirme sürecinde Selenium ve web mimarisinin getirdiği birçok kronik sorun **asgari zırh mimarileriyle** kökten çözülmüştür:

* **Dosya Adı Mutlak Baskınlığı (AI Override):** Evrak içeriklerinde geçen ortak kelimelerin (Örn: Adli Sicil belgesinin üstünde yazan "T.C. Kimlik No" ibaresinin Kimlik kategorisini tetiklemesi) yapay zekayı yanıltmasını engellemek için **Dosya Adı Baskınlığı** algoritması kurulmuştur. Dosya adında anahtar kelime yakalandığı an içerik taraması bypass edilerek %100 doğru kategori hedeflenir.
* **Stale Element ve Ajax Postback Kalkanı:** Wellcome platformunun arka planda yürüttüğü senkronize olmayan Ajax Postback işlemleri esnasında Selenium elementlerinin bayatlaması (`StaleElementReferenceException`) akıllı yeniden deneme kalkanıyla (`try-except` retry döngüsü) ekarte edilmiştir. Element bayatladığı an sistem 0.5 saniye içinde en taze DOM elemanını otomatik olarak söküp alır.
* **Sitedeki İmla Hatalarına Karşı Tam Senkronizasyon:** Sitenin dropdown listesinde yer alan `"Yapılacak İşen Özgü Talimatlar..."` gibi sinsi imla ve yazım hataları, ağırlık matrisine doğrudan entegre edilerek eşleşme kalitesinin kusursuz (10'da 10) olması sağlanmıştır.
* **Türkçe Karakter Kırıcı (Adaptive Layout):** Küçük/büyük harf dönüşümlerinde ve dosya isimlerinde yaşanan Türkçe karakter karmaşaları (`İ -> I`, `Ç -> C` vb.) özel bir ön işlem katmanıyla standartlaştırılmıştır.
* **Gelişmiş Enterprise UI:** `CustomTkinter` kütüphanesiyle inşa edilmiş karanlık tema destekli, KPI metriklerini (Başarılı, Kalan, ETA) anlık güncelleyen modern kontrol paneli.

---

## 🛠️ Kurulum ve Gereksinimler

Yazılımın çalışabilmesi için sisteminizde Python 3.8+ ve Google Chrome yüklü olmalıdır.

### 1. Tesseract OCR Kurulumu (Zorunlu)
Sistemin görsellerden ve dökümanlardan metin okuyabilmesi için Tesseract OCR motoruna ihtiyacı vardır:
1. [Tesseract OCR Windows Installer](https://github.com/UB-Mannheim/tesseract/wiki) sayfasından en güncel sürümü indirin ve kurun.
2. Varsayılan kurulum yolu olan `C:\Program Files\Tesseract-OCR\tesseract.exe` dizinini kontrol edin. Eğer farklı bir yere kurduysanız kodun en üstündeki `pytesseract.pytesseract.tesseract_cmd` yolunu güncelleyin.

### 2. Bağımlılıkların Yüklenmesi
Proje dizininde bir terminal açarak gerekli tüm kütüphaneleri tek seferde yükleyin:

```bash
pip install undetected-chromedriver pillow pytesseract pdfplumber pandas openpyxl customtkinter
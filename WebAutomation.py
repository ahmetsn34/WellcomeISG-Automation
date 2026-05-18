import imaplib
import email
import re
import time
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys

os.environ['WDM_LOG'] = '0'

# --- 1. DOSYADAN VERİ OKUMA ---
def txt_den_verileri_al(dosya_yolu):
    veriler = []
    try:
        with open(dosya_yolu, "r", encoding="utf-8") as dosya:
            for satir in dosya:
                temiz_satir = satir.strip()
                if temiz_satir:
                    parcalar = temiz_satir.split()
                    if len(parcalar) >= 3:
                        veriler.append({
                            "sirket": parcalar[0],
                            "kullanici": parcalar[1],
                            "sifre": parcalar[2]
                        })
        print(f"Toplam {len(veriler)} veri başarıyla ayıklandı.")
        return veriler
    except FileNotFoundError:
        print(f"Hata: {dosya_yolu} bulunamadı!")
        return []

# --- 2. MAİLDEN KOD ÇEKME ---
def mailden_kodu_al(mail_adresi, mail_sifresi, gonderici_adresi):
    print("Mail kutusu dinleniyor...")

    IMAP_SUNUCULARI = [
        ('imap.gmail.com', 993)
    ]

    mail_sunucusu = None
    for sunucu, port in IMAP_SUNUCULARI:
        try:
            print(f"  -> {sunucu} deneniyor...")
            mail_sunucusu = imaplib.IMAP4_SSL(sunucu, port)
            mail_sunucusu.login(mail_adresi, mail_sifresi)
            print(f"  -> Bağlantı başarılı: {sunucu}")
            break
        except Exception as e:
            print(f"  -> {sunucu} başarısız oldu. Hata: {e}")
            mail_sunucusu = None

    if mail_sunucusu is None:
        print("HATA: Hiçbir IMAP sunucusuna bağlanılamadı!")
        return None

    try:
        for deneme in range(12):  # 60 saniye bekler
            mail_sunucusu.select("inbox")
            
            # Sadece OKUNMAMIŞ (UNSEEN) mailleri listeliyoruz
            durum, veriler = mail_sunucusu.search(None, 'UNSEEN')
            mail_idleri = veriler[0].split()

            if mail_idleri:
                son_mail_id = mail_idleri[-1]
                durum, mail_verisi = mail_sunucusu.fetch(son_mail_id, '(RFC822)')

                for response_part in mail_verisi:
                    if isinstance(response_part, tuple):
                        mesaj = email.message_from_bytes(response_part[1])
                        
                        # Gönderici veya başlık kontrolü
                        gonderen = mesaj.get('From', '')
                        if gonderici_adresi.lower() in gonderen.lower() or "danteteknoloji" in gonderen.lower():
                            
                            icerik = ""
                            if mesaj.is_multipart():
                                for parca in mesaj.walk():
                                    if parca.get_content_type() in ("text/plain", "text/html"):
                                        try:
                                            icerik += parca.get_payload(decode=True).decode(
                                                parca.get_content_charset() or "utf-8", errors="ignore"
                                            )
                                        except:
                                            pass
                            else:
                                icerik = mesaj.get_payload(decode=True).decode(
                                    mesaj.get_content_charset() or "utf-8", errors="ignore"
                                )

                            # 4 VEYA 6 HANELİ ŞİFRELERİN TÜMÜNÜ HAVADA KAPAR
                            kod_eslesme = re.search(r'\b\d{4,6}\b', icerik)
                            if kod_eslesme:
                                dogrulama_kodu = kod_eslesme.group(0)
                                print(f"  -> Kod bulundu: {dogrulama_kodu}")
                                return dogrulama_kodu

            print(f"  -> Mail bekleniyor... ({(deneme+1)*5}/60 sn)")
            time.sleep(5)
            
    except Exception as e:
        print(f"Mail okuma hatası: {e}")
    finally:
        try:
            mail_sunucusu.logout()
        except:
            pass

    print("Uyarı: 60 saniye içinde mail gelmedi.")
    return None

# --- 3. ANA DÖNGÜ ---
def otomasyonu_baslat():
    dosya_yolu = r"C:\Users\DELL\Deneme.txt"
    hedef_veriler = txt_den_verileri_al(dosya_yolu)
    if not hedef_veriler:
        return

    mail_adresi = "denemehesapserver@gmail.com"
    mail_sifresi = "gzcgiofiqyenwztd"
    sitenin_mail_adresi = "wellcomebilgilendirme@danteteknoloji.com"

    chrome_options = Options()
    chrome_options.add_experimental_option("prefs", {"profile.managed_default_content_settings.images": 2})
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    bekleme = WebDriverWait(driver, 20)

    try:
        basarili_sayisi = 0

        for veri in hedef_veriler:
            print(f"\n--- Kullanıcı: {veri['kullanici']} için işlem başlatılıyor ---")
            try:
                driver.delete_all_cookies()
                driver.get("https://wellcome.azurewebsites.net/pnlwell/login/")
                print("Adım 1: Site yükleniyor (5 sn)...")
                time.sleep(5)

                # Şirket Kodu
                print("Adım 2: Şirket kodu yazılıyor...")
                sirket_kutusu = bekleme.until(EC.presence_of_element_located((By.ID, "FirmCode")))
                sirket_kutusu.clear()
                sirket_kutusu.send_keys(veri["sirket"])
                print("-> Şirket kodu yazıldı.")
                time.sleep(3)

                # Kullanıcı Adı
                print("Adım 3: Kullanıcı adı yazılıyor...")
                for _ in range(5):
                    try:
                        kullanici_kutusu = bekleme.until(EC.element_to_be_clickable((By.ID, "Username")))
                        kullanici_kutusu.clear()
                        kullanici_kutusu.send_keys(veri["kullanici"])
                        break
                    except Exception:
                        time.sleep(1)
                print("-> Kullanıcı adı yazıldı.")

                # Şifre
                print("Adım 4: Şifre yazılıyor...")
                for _ in range(5):
                    try:
                        sifre_kutusu = bekleme.until(EC.element_to_be_clickable((By.ID, "Password")))
                        sifre_kutusu.clear()
                        sifre_kutusu.send_keys(veri["sifre"])
                        break
                    except Exception:
                        time.sleep(1)
                print("-> Şifre yazıldı.")

                # Giriş Butonu
                print("Adım 5: Giriş butonuna tıklanıyor...")
                bekleme.until(EC.element_to_be_clickable((By.ID, "loginButton"))).click()

                # Doğrulama Kodu Bekleme Aşaması
                print("Adım 6: Mail'den doğrulama kodu bekleniyor...")
                dogrulama_kodu = mailden_kodu_al(mail_adresi, mail_sifresi, sitenin_mail_adresi)

                if dogrulama_kodu:
                    kod_kutusu = bekleme.until(EC.presence_of_element_located((By.ID, "VerificationCode")))
                    kod_kutusu.clear()
                    kod_kutusu.send_keys(dogrulama_kodu)
                    time.sleep(1)
                    
                    # --- GÜNCELLENEN ID'SİZ <A> ETİKETİ TIKLAMA AYARI ---
                    print("-> Doğrulama butonuna tıklanıyor...")
                    tıklandı = False
                    
                    # Alternatif 1: Gönderdiğin özel class yapısına göre CSS Seçici ile bulmayı dener
                    try:
                        css_seçici = "a.btn.btn-sms-verification.btn-block.btn-lg.btn-primary.text-uppercase"
                        yeşil_buton = bekleme.until(EC.element_to_be_clickable((By.CSS_SELECTOR, css_seçici)))
                        yeşil_buton.click()
                        tıklandı = True
                    except Exception:
                        pass
                        
                    # Alternatif 2: Eğer class'lar değişirse, buton metni üzerinden (Doğrula ve Giriş Yap) dener
                    if not tıklandı:
                        try:
                            yeşil_buton = bekleme.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'Doğrula ve Giriş Yap')]")))
                            yeşil_buton.click()
                            tıklandı = True
                        except Exception:
                            pass
                    
                    # Alternatif 3: Eğer yukarıdakilerin hiçbiri tıklayamazsa, son çare enter tuşlar
                    if not tıklandı:
                        kod_kutusu.send_keys(Keys.ENTER)
                    
                    time.sleep(5)  # Giriş başarılı olduktan sonra ana panelin yüklenmesini bekle
                    basarili_sayisi += 1
                    print(f"✅ Başarılı! {veri['kullanici']} sisteme tamamen giriş yaptı.")
                else:
                    print(f"⚠️ {veri['kullanici']} için mail kodu bulunamadı, atlanıyor.")

            except Exception as e:
                print(f"❌ Hata: {e}")
                continue

        print(f"\nToplam {len(hedef_veriler)} verinin {basarili_sayisi} tanesine başarıyla giriş yapıldı.")

    finally:
        input("\n[!] Tarayıcıyı kapatmak için ENTER'a bas...")
        driver.quit()

if __name__ == "__main__":
    otomasyonu_baslat()
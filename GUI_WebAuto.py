import imaplib
import email
import re
import time
import os
import threading
import tkinter as tk
from tkinter import filedialog
import customtkinter as ctk
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys

os.environ['WDM_LOG'] = '0'

# Arayüz Teması Ayarları
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

class WellcomeAutomationApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Wellcome Otomasyon Paneli v1.0")
        self.geometry("700x550")
        self.resizable(False, False)

        # Değişkenler
        self.dosya_yolu = tk.StringVar()
        self.is_running = False

        # --- ARAYÜZ TASARIMI ---
        self.title_label = ctk.CTkLabel(self, text="Wellcome Otomatik Giriş Sistemi", font=ctk.CTkFont(size=20, weight="bold"))
        self.title_label.pack(pady=20)

        self.file_frame = ctk.CTkFrame(self)
        self.file_frame.pack(pady=10, padx=20, fill="x")

        self.file_entry = ctk.CTkEntry(self.file_frame, textvariable=self.dosya_yolu, placeholder_text="Lütfen veri (.txt) dosyasını seçin...", width=450)
        self.file_entry.pack(side="left", padx=10, pady=10)

        self.file_button = ctk.CTkButton(self.file_frame, text="Dosya Seç", command=self.dosya_sec, width=100)
        self.file_button.pack(side="right", padx=10, pady=10)

        self.log_label = ctk.CTkLabel(self, text="Canlı İşlem Logları:", font=ctk.CTkFont(size=13, weight="bold"))
        self.log_label.pack(anchor="w", padx=30, pady=(10, 0))

        self.log_text = ctk.CTkTextbox(self, width=640, height=250, font=ctk.CTkFont(family="Consolas", size=12))
        self.log_text.pack(pady=5, padx=20)
        self.log_text.configure(state="disabled")

        self.start_button = ctk.CTkButton(self, text="Otomasyonu Başlat", fg_color="green", hover_color="darkgreen", command=self.thread_baslat, height=40, font=ctk.CTkFont(size=14, weight="bold"))
        self.start_button.pack(pady=20)

    # --- FONKSİYONLAR ---
    def dosya_sec(self):
        yol = filedialog.askopenfilename(filetypes=[("Text Files", "*.txt")])
        if yol:
            self.dosya_yolu.set(yol)
            self.log_yaz(f"[SİSTEM] Veri dosyası seçildi: {yol}\n")

    def log_yaz(self, mesaj):
        self.log_text.configure(state="normal")
        self.log_text.insert(tk.END, mesaj + "\n")
        self.log_text.see(tk.END)
        self.log_text.configure(state="disabled")

    def txt_den_verileri_al(self, dosya_yolu):
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
            self.log_yaz(f"[BİLGİ] Dosyadan {len(veriler)} kullanıcı başarıyla ayıklandı.")
            return veriler
        except Exception as e:
            self.log_yaz(f"[HATA] Dosya okunurken hata oluştu: {e}")
            return []

    def mailden_kodu_al(self, mail_adresi, mail_sifresi, gonderici_adresi):
        self.log_yaz("  -> Gmail kutusu dinleniyor...")
        try:
            # Gmail bağlantısını kuruyoruz
            mail_sunucusu = imaplib.IMAP4_SSL('imap.gmail.com', 993)
            mail_sunucusu.login(mail_adresi, mail_sifresi)
        except Exception as e:
            self.log_yaz(f"  -> [HATA] Gmail bağlantısı başarısız: {e}")
            return None

        try:
            for deneme in range(10):
                time.sleep(4)  # GÜNCELLEME: Gmail spam filtresine takılmamak için 4 saniye es veriyoruz
                mail_sunucusu.select("inbox")
                durum, veriler = mail_sunucusu.search(None, 'UNSEEN')
                mail_idleri = veriler[0].split()

                if mail_idleri:
                    son_mail_id = mail_idleri[-1]
                    durum, mail_verisi = mail_sunucusu.fetch(son_mail_id, '(RFC822)')

                    for response_part in mail_verisi:
                        if isinstance(response_part, tuple):
                            mesaj = email.message_from_bytes(response_part[1])
                            gonderen = mesaj.get('From', '')
                            
                            if gonderici_adresi.lower() in gonderen.lower() or "danteteknoloji" in gonderen.lower():
                                icerik = ""
                                if mesaj.is_multipart():
                                    for parca in mesaj.walk():
                                        if parca.get_content_type() in ("text/plain", "text/html"):
                                            try:
                                                icerik += parca.get_payload(decode=True).decode(parca.get_content_charset() or "utf-8", errors="ignore")
                                            except: pass
                                else:
                                    icerik = mesaj.get_payload(decode=True).decode(mesaj.get_content_charset() or "utf-8", errors="ignore")

                                kod_eslesme = re.search(r'\b\d{4,6}\b', icerik)
                                if kod_eslesme:
                                    dogrulama_kodu = kod_eslesme.group(0)
                                    self.log_yaz(f"  -> Kod Gmail'den çekildi: {dogrulama_kodu}")
                                    return dogrulama_kodu

                self.log_yaz(f"  -> Mail bekleniyor... ({(deneme+1)*4}/40 sn)")
        except Exception as e:
            self.log_yaz(f"  -> [HATA] Mail okuma esnasında hata: {e}")
        finally:
            # GÜNCELLEME: Bağlantının açık kalıp kilitlenmemesi için her durumda güvenli çıkış yapıyoruz
            try: 
                mail_sunucusu.logout()
                self.log_yaz("  -> Gmail bağlantısı güvenli kapatıldı.")
            except: pass
        return None

    def thread_baslat(self):
        if not self.dosya_yolu.get():
            self.log_yaz("[UYARI] Lütfen önce bir dosya seçin!")
            return
        
        if self.is_running:
            return

        self.is_running = True
        self.start_button.configure(state="disabled", text="Otomasyon Çalışıyor...", fg_color="gray")
        threading.Thread(target=self.otomasyonu_calistir, daemon=True).start()

    def otomasyonu_calistir(self):
        hedef_veriler = self.txt_den_verileri_al(self.dosya_yolu.get())
        if not hedef_veriler:
            self.is_running = False
            self.start_button.configure(state="normal", text="Otomasyonu Başlat", fg_color="green")
            return

        mail_adresi = "denemehesapserver@gmail.com"
        # DİKKAT: Buradaki şifreyi Google'dan yenisiyle değiştirmeyi unutma kanka!
        mail_sifresi = "fgdnpormmyqixbui" 
        sitenin_mail_adresi = "wellcomebilgilendirme@danteteknoloji.com"

        chrome_options = Options()
        chrome_options.add_experimental_option("prefs", {"profile.managed_default_content_settings.images": 2})

        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        bekleme = WebDriverWait(driver, 20)

        try:
            basarili_sayisi = 0

            for veri in hedef_veriler:
                self.log_yaz(f"\n--- Kullanıcı: {veri['kullanici']} Başlatıldı ---")
                try:
                    driver.delete_all_cookies()
                    driver.get("https://wellcome.azurewebsites.net/pnlwell/login/")
                    self.log_yaz("[1/6] Site yükleniyor...")
                    time.sleep(5)

                    # Şirket Kodu
                    self.log_yaz("[2/6] Şirket kodu yazılıyor...")
                    sirket_kutusu = bekleme.until(EC.presence_of_element_located((By.ID, "FirmCode")))
                    sirket_kutusu.clear()
                    sirket_kutusu.send_keys(veri["sirket"])
                    time.sleep(3)

                    # Kullanıcı Adı (Koruyucu Döngülü)
                    self.log_yaz("[3/6] Kullanıcı adı yazılıyor...")
                    for _ in range(5):
                        try:
                            kullanici_kutusu = bekleme.until(EC.element_to_be_clickable((By.ID, "Username")))
                            kullanici_kutusu.clear()
                            kullanici_kutusu.send_keys(veri["kullanici"])
                            break
                        except Exception:
                            time.sleep(1)

                    # Şifre (Koruyucu Döngülü)
                    self.log_yaz("[4/6] Şifre yazılıyor...")
                    for _ in range(5):
                        try:
                            sifre_kutusu = bekleme.until(EC.element_to_be_clickable((By.ID, "Password")))
                            sifre_kutusu.clear()
                            sifre_kutusu.send_keys(veri["sifre"])
                            break
                        except Exception:
                            time.sleep(1)

                    # Giriş Butonu
                    self.log_yaz("[5/6] Giriş butonuna tıklanıyor...")
                    bekleme.until(EC.element_to_be_clickable((By.ID, "loginButton"))).click()

                    # Doğrulama Kodu
                    self.log_yaz("[6/6] Mail onay kodu bekleniyor...")
                    dogrulama_kodu = self.mailden_kodu_al(mail_adresi, mail_sifresi, sitenin_mail_adresi)

                    if dogrulama_kodu:
                        kod_kutusu = bekleme.until(EC.presence_of_element_located((By.ID, "VerificationCode")))
                        kod_kutusu.clear()
                        kod_kutusu.send_keys(dogrulama_kodu)
                        time.sleep(1)
                        
                        # ID'siz <a> Butonuna Tıklama Alanı (Sınıf ve Metin Korumalı)
                        tıklandı = False
                        try:
                            css_seçici = "a.btn.btn-sms-verification.btn-block.btn-lg.btn-primary.text-uppercase"
                            yeşil_buton = bekleme.until(EC.element_to_be_clickable((By.CSS_SELECTOR, css_seçici)))
                            yeşil_buton.click()
                            tıklandı = True
                        except: pass
                            
                        if not tıklandı:
                            try:
                                yeşil_buton = bekleme.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'Doğrula ve Giriş Yap')]")))
                                yeşil_buton.click()
                                tıklandı = True
                            except: pass
                        
                        if not tıklandı:
                            kod_kutusu.send_keys(Keys.ENTER)
                        
                        time.sleep(5)
                        basarili_sayisi += 1
                        self.log_yaz(f"✅ BAŞARILI: {veri['kullanici']} içeri girdi.")
                    else:
                        self.log_yaz(f"⚠️ BAŞARISIZ: {veri['kullanici']} için kod bulunamadı.")

                except Exception as e:
                    self.log_yaz(f"❌ HATA: {veri['kullanici']} işleminde sorun çıktı: {e}")
                    continue

            self.log_yaz(f"\n[BİTTİ] Toplam {len(hedef_veriler)} veriden {basarili_sayisi} tanesi başarıyla açıldı.")

        finally:
            driver.quit()
            self.is_running = False
            self.start_button.configure(state="normal", text="Otomasyonu Başlat", fg_color="green")

if __name__ == "__main__":
    app = WellcomeAutomationApp()
    app.mainloop()
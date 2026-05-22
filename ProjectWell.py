import imaplib
import email
import re
import time
import os
import sys
import json
import threading
import queue
import logging
import winsound
import socket
import random
import shutil
from datetime import datetime
from typing import Optional, Dict, List

import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
import pandas as pd

# Akıllı PDF Okuma Kütüphanesi
import pdfplumber

import undetected_chromedriver as uc 
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import StaleElementReferenceException, TimeoutException, UnexpectedAlertPresentException

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

try:
    import config
    from logger_config import setup_logger
    logger = setup_logger()
except ImportError:
    class MockLogger:
        def info(self, msg): print(f"[INFO] {msg}")
        def error(self, msg): print(f"[ERROR] {msg}")
    logger = MockLogger()
    class MockConfig:
        DISABLE_IMAGES = False
        LOGIN_URL = "https://wellcome.azurewebsites.net/pnlwell/"
    config = MockConfig()

os.environ['WDM_LOG'] = '0'
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

# =====================================================================
# --- ÇOKLU DİL DESTEĞİ VE SÖZLÜK ---
# =====================================================================
LANG_PACK = {
    "TR": {
        "title": "Wellcome RPA - Kurumsal Zırhlı Yapay Zeka Otomasyonu",
        "select_folder": "OneDrive Klasörünü Seç",
        "placeholder": "Personel klasörlerinin bulunduğu ana dizini seçin...",
        "headless": "Tarayıcıyı Gizle (Arka Planda Çalıştır)",
        "demo_mode": "Simülasyon (Demo) Modu",
        "start": "GİRİŞ YAP VE OTOMASYONU BAŞLAT",
        "running": "İşlemler Sürüyor...",
        "pause": "DURAKLAT",
        "resume": "DEVAM ET",
        "stats": "✅ Başarılı: {}  |  ❌ Hatalı: {}  |  ⏳ Kalan: {}  |  ⏱️ ETA: {}",
        "no_folder": "Lütfen önce personel klasörlerinin bulunduğu ana dizini seçin!",
        "pre_flight_start": "[SİSTEM] Başlangıç sağlık kontrolleri yapılıyor...",
        "internet_ok": "  🌐 İnternet bağlantısı aktif.",
        "internet_err": "❌ KRİTİK HATA: İnternet bağlantısı yok!",
        "chrome_ok": "  🚗 Chrome görünmezlik altyapısı hazır.",
        "eta_calculating": "Hesaplanıyor...",
        "all_done": "Seçilen dizindeki tüm personel klasörleri başarıyla işlendi!",
        "demo_alert": "🤖 SİMÜLASYON MODU AKTİF: Gerçek tarayıcı açılmayacak, işlemler taklit ediliyor...",
        "login_wait": "🔐 Gömülü bilgilerle giriş yapılıyor, OTP kodu bekleniyor...",
        "process_folder": "📂 Klasör Analiz Ediliyor: {}",
        "read_success": "   📋 Okunan -> Ad Soyad: {}, TC: {}, Tel: {}",
        "img1_click": "   -> 'Çalışan Tanımla' sekmesine geçiliyor...",
        "img2_click": "   -> '+ Yeni Çalışan' form ekranı açılıyor...",
        "img3_fill": "   -> Form alanları ve kimlik bilgileri yazılıyor...",
        "gen_password": "   🔑 'Üret' butonuna basılarak rastgele şifre oluşturuluyor...",
        "submit_form": "   -> Bilgiler doğrulanıyor, 'Bilgileri Kontrol Et' butonuna basıldı.",
        "success_log": "✅ [BAŞARILI] {} sisteme başarıyla kaydedildi.",
        "error_log": "❌ [HATA] {} işlenirken sorun çıktı: {}",
        "checkpoint_title": "Kaldığı Yerden Devam",
        "checkpoint_msg": "Önceki oturumdan kalan {} adet işlenmiş klasör bulundu.\nKaldığınız yerden devam etmek ister misiniz?\n\nEvet: Sadece kalanları işler.\nHayır: Her şeye sıfırdan başlar.",
        "checkpoint_clean": "[SİSTEM] Eski hafıza temizlendi, sıfırdan başlanıyor...",
        "report_gen": "📊 Operasyon raporu OneDrive dizinine kaydedildi: {}",
        "sw_retry": "Hata Anında 3 Kez Yeniden Dene",
        "sw_alert": "Tarayıcı Uyarılarını (Alert) Otomatik Geç",
        "lbl_comp": "Şirket Kodu",
        "lbl_user": "Kullanıcı Adı",
        "lbl_pass": "Şifre",
        "otp_title": "🔐 OTP Güvenlik Kodu",
        "otp_prompt": "Telefonunuza veya e-postanıza gelen 6 haneli OTP kodunu giriniz:"
    },
    "EN": {
        "title": "Wellcome RPA - Enterprise Armored AI Automation",
        "select_folder": "Select OneDrive Folder",
        "placeholder": "Select the main directory containing personnel folders...",
        "headless": "Run Headless (Hide Browser)",
        "demo_mode": "Simulation (Demo) Mode",
        "start": "LOG IN & START AUTOMATION",
        "running": "Processing...",
        "pause": "PAUSE",
        "resume": "RESUME",
        "stats": "✅ Success: {}  |  ❌ Failed: {}  |  ⏳ Remaining: {}  |  ⏱️ ETA: {}",
        "no_folder": "Please select the main personnel directory first!",
        "pre_flight_start": "[SYSTEM] Running pre-flight health checks...",
        "internet_ok": "  🌐 Internet connection is active.",
        "internet_err": "❌ CRITICAL ERROR: No internet connection!",
        "chrome_ok": "  🚗 Chrome stealth infrastructure is ready.",
        "eta_calculating": "Calculating...",
        "all_done": "All personnel folders in the selected directory have been processed!",
        "demo_alert": "🤖 SIMULATION MODE ACTIVE: Browser will not open, actions are simulated...",
        "login_wait": "🔐 Logging in with embedded credentials, waiting for OTP...",
        "process_folder": "📂 Analyzing Folder: {}",
        "read_success": "   📋 Extracted -> Name: {}, ID: {}, Tel: {}",
        "img1_click": "   -> Navigating to 'Personnel Definitions'...",
        "img2_click": "   -> Opening '+ New Employee' form...",
        "img3_fill": "   -> Filling out form fields and identity data...",
        "gen_password": "   🔑 Clicking 'Generate' to create a random password...",
        "submit_form": "   -> Verifying details, clicking 'Check Information' button.",
        "success_log": "✅ [SUCCESS] {} registered successfully.",
        "error_log": "❌ [ERROR] Failed to process {}: {}",
        "checkpoint_title": "Resume Session",
        "checkpoint_msg": "Found {} processed folders from previous session.\nDo you want to resume where you left off?\n\nYes: Process remaining only.\nNo: Start from scratch.",
        "checkpoint_clean": "[SYSTEM] Old memory cleared, starting from scratch...",
        "report_gen": "📊 Operation report saved to OneDrive directory: {}",
        "sw_retry": "Retry 3 Times on Error", 
        "sw_alert": "Automatically Dismiss Browser Alerts",
        "lbl_comp": "Company Code",
        "lbl_user": "Username",
        "lbl_pass": "Password",
        "otp_title": "🔐 OTP Security Code",
        "otp_prompt": "Enter the 6-digit OTP code sent to your phone/email:"
    }
}


class WellcomeRPAApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()

        self.settings_file = "settings.json"
        self.checkpoint_file = "checkpoint.json"

        # Pencere Boyutu Sabitlendi
        self.geometry("640x720")

        # İç Durum Değişkenleri
        self.base_folder_path = tk.StringVar()
        self.company_code_var = tk.StringVar() 
        self.username_var = tk.StringVar()
        self.password_var = tk.StringVar()
        self.is_running = False
        
        # Zırh Switch Değişkenleri
        self.headless_var = tk.BooleanVar(value=False)
        self.demo_mode_var = tk.BooleanVar(value=False)
        self.retry_enabled = tk.BooleanVar(value=True)
        self.alert_dismiss_enabled = tk.BooleanVar(value=True)
        self.current_lang = "TR"
        
        self.pause_event = threading.Event()
        self.pause_event.set()  
        self.checkpoint_lock = threading.Lock()
        
        self.start_time = None
        self.processed_count_for_eta = 0

        self._load_settings() 
        self._build_ui()  
        self._update_ui_texts()
        logger.info("Application initialized with armored SaaS RPA architecture.")

    def _log(self, message: str, tag: str = "normal") -> None:
        def update_gui():
            self.log_text.configure(state="normal")
            self.log_text.insert(tk.END, f"{datetime.now().strftime('%H:%M:%S')} - {message}\n", tag)
            self.log_text.see(tk.END)
            self.log_text.configure(state="disabled")
        self.after(0, update_gui)

    def _build_ui(self) -> None:
        top_bar = ctk.CTkFrame(self, fg_color="transparent")
        top_bar.pack(side="top", fill="x", padx=10, pady=5)

        self.title_label = ctk.CTkLabel(top_bar, text="", font=ctk.CTkFont(size=18, weight="bold"))
        self.title_label.pack(side="left", padx=10, pady=10)

        self.lang_dropdown = ctk.CTkOptionMenu(top_bar, values=["TR", "EN"], command=self._on_lang_change, width=70)
        self.lang_dropdown.pack(side="right", padx=10, pady=10)

        container = ctk.CTkFrame(self, fg_color="transparent")
        container.pack(side="top", fill="x", padx=10, pady=5)

        # Gömülü Giriş Paneli
        login_frame = ctk.CTkFrame(container)
        login_frame.pack(pady=5, padx=10, fill="x")
        
        self.lbl_comp_txt = ctk.CTkLabel(login_frame, text="", font=ctk.CTkFont(size=11, weight="bold"))
        self.lbl_comp_txt.grid(row=0, column=0, padx=10, pady=(8, 2), sticky="w")
        self.company_entry = ctk.CTkEntry(login_frame, textvariable=self.company_code_var, placeholder_text="şirket kodu", width=150)
        self.company_entry.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="w")

        self.lbl_user_txt = ctk.CTkLabel(login_frame, text="", font=ctk.CTkFont(size=11, weight="bold"))
        self.lbl_user_txt.grid(row=0, column=1, padx=10, pady=(8, 2), sticky="w")
        self.username_entry = ctk.CTkEntry(login_frame, textvariable=self.username_var, placeholder_text="username", width=170)
        self.username_entry.grid(row=1, column=1, padx=10, pady=(0, 10), sticky="w")

        self.lbl_pass_txt = ctk.CTkLabel(login_frame, text="", font=ctk.CTkFont(size=11, weight="bold"))
        self.lbl_pass_txt.grid(row=0, column=2, padx=10, pady=(8, 2), sticky="w")
        self.password_entry = ctk.CTkEntry(login_frame, textvariable=self.password_var, placeholder_text="••••••••", show="*", width=170)
        self.password_entry.grid(row=1, column=2, padx=10, pady=(0, 10), sticky="w")

        # Klasör Seçim Alanı
        folder_frame = ctk.CTkFrame(container)
        folder_frame.pack(pady=5, padx=10, fill="x")

        self.folder_entry = ctk.CTkEntry(folder_frame, textvariable=self.base_folder_path, placeholder_text="", width=400)
        self.folder_entry.pack(side="left", padx=10, pady=10, expand=True, fill="x")

        self.folder_button = ctk.CTkButton(folder_frame, text="", command=self._select_folder, width=120)
        self.folder_button.pack(side="right", padx=10, pady=10)

        # Kontrol Switchleri
        config_frame = ctk.CTkFrame(container)
        config_frame.pack(pady=5, padx=10, fill="x")

        self.cb_headless = ctk.CTkCheckBox(config_frame, text="", variable=self.headless_var)
        self.cb_headless.grid(row=0, column=0, padx=20, pady=8, sticky="w")

        self.cb_demo_mode = ctk.CTkCheckBox(config_frame, text="", variable=self.demo_mode_var, fg_color="#e67e22", hover_color="#d35400")
        self.cb_demo_mode.grid(row=0, column=1, padx=20, pady=8, sticky="w")

        self.sw_retry_cb = ctk.CTkSwitch(config_frame, text="", variable=self.retry_enabled, progress_color="#2ecc71")
        self.sw_retry_cb.grid(row=1, column=0, padx=20, pady=8, sticky="w")

        self.sw_alert_cb = ctk.CTkSwitch(config_frame, text="", variable=self.alert_dismiss_enabled, progress_color="#2ecc71")
        self.sw_alert_cb.grid(row=1, column=1, padx=20, pady=8, sticky="w")

        # İstatistik Paneli
        stats_frame = ctk.CTkFrame(container)
        stats_frame.pack(pady=5, padx=10, fill="x")

        self.stats_label = ctk.CTkLabel(stats_frame, text="", font=ctk.CTkFont(size=12, weight="bold"))
        self.stats_label.pack(pady=(5, 5))

        self.progress_bar = ctk.CTkProgressBar(stats_frame, height=14)
        self.progress_bar.set(0)
        self.progress_bar.pack(fill="x", padx=20, pady=(0, 10))

        # Buton Çerçevesi
        button_frame = ctk.CTkFrame(container, fg_color="transparent")
        button_frame.pack(pady=5, fill="x")

        self.start_button = ctk.CTkButton(button_frame, text="", fg_color="#27ae60", hover_color="#219653", command=self._start_automation, height=44, width=220, font=ctk.CTkFont(size=13, weight="bold"))
        self.start_button.pack(side="left", expand=True, padx=10)

        self.pause_button = ctk.CTkButton(button_frame, text="", fg_color="#f39c12", hover_color="#e67e22", command=self._toggle_pause, height=44, width=110, state="disabled", font=ctk.CTkFont(size=13, weight="bold"))
        self.pause_button.pack(side="left", expand=True, anchor="w", padx=10)

        # Çakılı Sabit Konsol Ekranı
        log_frame = ctk.CTkFrame(self)
        log_frame.pack(side="top", pady=10, padx=20, fill="both", expand=True)

        self.log_textInput = tk.Text(log_frame, bg="#111111", fg="#deff9a", font=("Consolas", 10), wrap="word", bd=0, highlightthickness=0)
        self.log_textInput.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        self.log_text = self.log_textInput 

        self.log_text.tag_config("normal", foreground="#ffffff")
        self.log_text.tag_config("system", foreground="#5dade2")
        self.log_text.tag_config("success", foreground="#2ecc71", font=("Consolas", 10, "bold"))
        self.log_text.tag_config("error", foreground="#e74c3c", font=("Consolas", 10, "bold"))
        self.log_text.tag_config("warning", foreground="#f1c40f")
        self.log_text.configure(state="disabled")

    def _on_lang_change(self, choice: str) -> None:
        self.current_lang = choice
        self._update_ui_texts()
        self._save_settings()

    def _update_ui_texts(self) -> None:
        lg = LANG_PACK[self.current_lang]
        self.title(lg["title"])
        self.title_label.configure(text=lg["title"])
        self.folder_button.configure(text=lg["select_folder"])
        self.folder_entry.configure(placeholder_text=lg["placeholder"])
        self.cb_headless.configure(text=lg["headless"])
        self.cb_demo_mode.configure(text=lg["demo_mode"])
        self.sw_retry_cb.configure(text=lg["sw_retry"])
        self.sw_alert_cb.configure(text=lg["sw_alert"])
        self.lbl_comp_txt.configure(text=lg["lbl_comp"]) 
        self.lbl_user_txt.configure(text=lg["lbl_user"])
        self.lbl_pass_txt.configure(text=lg["lbl_pass"])
        self.pause_button.configure(text=lg["pause"] if self.pause_event.is_set() else lg["resume"])
        
        if not self.is_running:
            self.start_button.configure(text=lg["start"])
            self.stats_label.configure(text=lg["stats"].format(0, 0, 0, "--:--"))
        else:
            self.start_button.configure(text=lg["running"])
        self.lang_dropdown.set(self.current_lang)

    def _load_settings(self) -> None:
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, "r") as f:
                    settings = json.load(f)
                    self.current_lang = settings.get("lang", "TR")
                    self.base_folder_path.set(settings.get("base_folder_path", ""))
                    self.company_code_var.set(settings.get("company_code", "")) 
                    self.username_var.set(settings.get("username", ""))
                    self.password_var.set(settings.get("password", ""))
                    self.headless_var.set(settings.get("headless", False))
                    self.demo_mode_var.set(settings.get("demo_mode", False))
                    self.retry_enabled.set(settings.get("retry_enabled", True))
                    self.alert_dismiss_enabled.set(settings.get("alert_dismiss_enabled", True))
            except Exception: pass

    def _save_settings(self) -> None:
        settings = {
            "lang": self.current_lang,
            "base_folder_path": self.base_folder_path.get(),
            "company_code": self.company_code_var.get(), 
            "username": self.username_var.get(),
            "password": self.password_var.get(),
            "headless": self.headless_var.get(),
            "demo_mode": self.demo_mode_var.get(),
            "retry_enabled": self.retry_enabled.get(),
            "alert_dismiss_enabled": self.alert_dismiss_enabled.get()
        }
        try:
            with open(self.settings_file, "w") as f: json.dump(settings, f)
        except Exception: pass

    def _select_folder(self) -> None:
        path = filedialog.askdirectory()
        if path:
            self.base_folder_path.set(path)
            self._log(f"[SYSTEM] Ana dizin bağlandı: {path}", "system")
            self._save_settings()

    def _clean_phone_number(self, phone_str: str) -> str:
        if not phone_str: return ""
        digits = re.sub(r'\D', '', phone_str)
        if digits.startswith("90") and len(digits) > 10: digits = digits[2:]
        elif digits.startswith("0") and len(digits) == 11: digits = digits[1:]
        return digits

    def _read_personel_txt(self, folder_path: str) -> Dict[str, str]:
        klasor_adi = os.path.basename(folder_path.strip().rstrip('\\/'))
        veriler = {
            "tc": "00000000000", 
            "isim_soyisim": klasor_adi.replace("_", " "), 
            "gorev": "Personel",
            "telefon": "",
            "eposta": ""
        }
        
        if os.path.exists(folder_path):
            pdf_dosyalari = [f for f in os.listdir(folder_path) if f.upper().endswith('.PDF')]
            if pdf_dosyalari:
                try:
                    pdf_path = os.path.join(folder_path, pdf_dosyalari[0])
                    with pdfplumber.open(pdf_path) as pdf:
                        full_text = ""
                        for page in pdf.pages:
                            text = page.extract_text()
                            if text: full_text += text
                    
                    tc_match = re.search(r'\b\d{11}\b', full_text)
                    if tc_match:
                        veriler["tc"] = tc_match.group(0)
                        self._log(f"🤖 [AI-OCR] PDF içinden T.C. çekildi: {veriler['tc']}", "success")
                    else:
                        self._log(f"⚠️ {klasor_adi} belgesinde T.C. numarası bulunamadı!", "warning")

                    phone_match = re.search(r'(?:\+?90|\b0)?\s*([5]\d{2})\s*(\d{3})\s*(\d{2})\s*(\d{2})\b', full_text)
                    if phone_match:
                        raw_phone = "".join(phone_match.groups())
                        veriler["telefon"] = self._clean_phone_number(raw_phone)
                        self._log(f"🤖 [AI-OCR] PDF içinden Telefon başarıyla çekildi: {veriler['telefon']}", "success")
                    else:
                        alt_phone = re.search(r'\b(?:0|\+?90)?(5\d{9})\b', full_text)
                        if alt_phone:
                            veriler["telefon"] = self._clean_phone_number(alt_phone.group(1))
                            self._log(f"🤖 [AI-OCR] PDF içinden Telefon çekildi: {veriler['telefon']}", "success")
                        else:
                            self._log(f"⚠️ {klasor_adi} belgesinde Telefon numarası bulunamadı!", "warning")
                            
                except Exception as pdf_err:
                    self._log(f"⚠️ Evrak okuma motoru hatası: {str(pdf_err)[:40]}", "warning")
                    
        return veriler

    def _request_otp_from_user(self) -> str:
        lg = LANG_PACK[self.current_lang]
        otp_box = ctk.CTkInputDialog(text=lg["otp_prompt"], title=lg["otp_title"])
        otp_code = otp_box.get_input()
        return otp_code if otp_code else ""

    def _create_driver(self) -> Optional[uc.Chrome]:
        if self.demo_mode_var.get(): return None
        chrome_options = uc.ChromeOptions()
        chrome_options.add_experimental_option("prefs", {"profile.managed_default_content_settings.images": config.DISABLE_IMAGES})
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        return uc.Chrome(options=chrome_options, headless=self.headless_var.get(), version_main=148)

    def _handle_embedded_login(self, driver: uc.Chrome, bekleme: WebDriverWait) -> bool:
        lg = LANG_PACK[self.current_lang]
        try:
            self._log("🔐 Giriş alanları dolduruluyor...", "system")
            time.sleep(1.5) 

            if self.company_code_var.get():
                comp_input = bekleme.until(EC.presence_of_element_located((By.ID, "FirmCode")))
                comp_input.clear()
                comp_input.send_keys(self.company_code_var.get())
                
                self._log("⚡ Şirket kodu gönderildi, AJAX Postback tetikleniyor...", "system")
                comp_input.send_keys(Keys.ENTER)
                
                self._log("⏳ Sayfa Postback oluyor, yeni alanların canlanması bekleniyor...", "warning")
                time.sleep(4.5) 
                
                bekleme = WebDriverWait(driver, 20)

            self._log("👁️ Alanlar taranıyor, Username kutusu bekleniyor...", "system")
            user_box = bekleme.until(EC.element_to_be_clickable((By.ID, "Username")))
            pass_box = driver.find_element(By.ID, "Password")
            
            driver.execute_script("arguments[0].value = arguments[1];", user_box, self.username_var.get())
            driver.execute_script("arguments[0].value = arguments[1];", pass_box, self.password_var.get())
            time.sleep(0.5)

            login_btn = bekleme.until(EC.element_to_be_clickable((By.ID, "loginButton")))
            driver.execute_script("arguments[0].click();", login_btn) 
            
            self._log(lg["login_wait"], "warning")
            time.sleep(3.5) 
            
            otp_done_event = threading.Event()
            otp_code_container = [""]

            def ask_gui():
                otp_code_container[0] = self._request_otp_from_user()
                otp_done_event.set()

            self.after(0, ask_gui)
            otp_done_event.wait() 

            user_otp = otp_code_container[0]
            if user_otp:
                self._log("🔐 OTP kodu siteye enjekte ediliyor...", "system")
                otp_input = bekleme.until(EC.presence_of_element_located((By.ID, "VerificationCode")))
                driver.execute_script("arguments[0].value = arguments[1];", otp_input, user_otp)
                time.sleep(0.5)
                
                self._log("🚀 'Doğrula ve Giriş Yap' butonuna basılıyor...", "success")
                otp_submit_btn = bekleme.until(EC.element_to_be_clickable((
                    By.XPATH, "//a[contains(@class, 'btn-sms-verification') or text()='Doğrula ve Giriş Yap']"
                )))
                driver.execute_script("arguments[0].click();", otp_submit_btn) 
                time.sleep(3.0)
            return True
        except Exception as e:
            # --- ZIRH KORUMASI: HATA BURADA YAKALANIYOR ---
            self._log(f"❌ KRİTİK GİRİŞ HATASI: Giriş elemanları doldurulamadı! Detay: {str(e)[:50]}", "error")
            try: winsound.MessageBeep(winsound.MB_ICONHAND)
            except: pass
            return False

    def _process_single_folder(self, driver: Optional[uc.Chrome], folder_name: str, base_path: str) -> str:
        lg = LANG_PACK[self.current_lang]
        folder_path = os.path.join(base_path, folder_name) if base_path else folder_name
        
        self.pause_event.wait()
        personel_bilgisi = self._read_personel_txt(folder_path)
        self._log(lg["process_folder"].format(folder_name), "system")
        self._log(lg["read_success"].format(personel_bilgisi['isim_soyisim'], personel_bilgisi['tc'], personel_bilgisi['telefon']), "normal")

        if self.demo_mode_var.get():
            time.sleep(0.8)
            self._log(lg["img1_click"], "normal")
            self._log(lg["img2_click"], "normal")
            self._log(lg["img3_fill"], "normal")
            self._log(lg["gen_password"], "normal")
            self._log(lg["submit_form"], "normal")
            self._log(lg["success_log"].format(folder_name.replace("_", " ")), "success")
            with self.checkpoint_lock: self._save_to_checkpoint(folder_name)
            return "Success"

        deneme_siniri = 3 if self.retry_enabled.get() else 1
        for deneme in range(1, deneme_siniri + 1):
            try:
                bekleme = WebDriverWait(driver, 12)

                if self.alert_dismiss_enabled.get():
                    try:
                        alert = driver.switch_to.alert
                        self._log(f"⚠️ Sinsi Alert yakalandı ve temizlendi: {alert.text}", "warning")
                        alert.accept()
                    except Exception: pass

                # SÜREÇ 1: Çalışan Tanımla Sekmesi
                self._log(lg["img1_click"], "normal")
                calisan_tanimla_btn = bekleme.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(@href, '/files/workgroup/')]")))
                calisan_tanimla_btn.click()

                # SÜREÇ 2: + Yeni Çalışan Butonu
                self._log(lg["img2_click"], "normal")
                yeni_calisan_btn = bekleme.until(EC.element_to_be_clickable((By.ID, "ContentPlaceHolder1_btnNewUserPanel")))
                yeni_calisan_btn.click()

                # SÜREÇ 3: Kayıt Alanları Formu
                self._log(lg["img3_fill"], "normal")
                isim_input = bekleme.until(EC.presence_of_element_located((By.ID, "NameSurname")))
                isim_input.clear()
                isim_input.send_keys(personel_bilgisi["isim_soyisim"])

                tc_input = driver.find_element(By.ID, "kimlikno")
                tc_input.clear()
                tc_input.send_keys(personel_bilgisi["tc"])

                gorev_input = driver.find_element(By.ID, "yetkinlik")
                gorev_input.clear()
                gorev_input.send_keys(personel_bilgisi["gorev"])

                self._log(lg["gen_password"], "normal")
                uret_btn = driver.find_element(By.XPATH, "//a[contains(@onclick, 'rndPassword') or @title='Random Şifre Türet ']")
                uret_btn.click()

                if personel_bilgisi["telefon"]:
                    tel_input = driver.find_element(By.ID, "telefon")
                    tel_input.clear()
                    tel_input.send_keys(personel_bilgisi["telefon"])

                if personel_bilgisi["eposta"]:
                    mail_input = driver.find_element(By.ID, "eposta")
                    mail_input.clear()
                    mail_input.send_keys(personel_bilgisi["eposta"])

                time.sleep(1)
                self._log(lg["submit_form"], "normal")
                
                kaydet_btn = driver.find_element(By.XPATH, "//a[contains(@onclick, 'CheckInfo') or contains(@class, 'checkUser')]")
                kaydet_btn.click()
                
                if self.alert_dismiss_enabled.get():
                    time.sleep(1.0)
                    try:
                        alert = driver.switch_to.alert
                        alert_msg = alert.text
                        self._log(f"❌ Site Kayıt Başarısız Pop-up Uyarısı: {alert_msg}", "error")
                        alert.accept()
                        return f"Site Engeli: {alert_msg}"
                    except Exception: pass

                insansi_bekleme = random.uniform(2.6, 5.4)  
                time.sleep(insansi_bekleme)
                
                self._log(lg["success_log"].format(folder_name), "success")
                with self.checkpoint_lock: self._save_to_checkpoint(folder_name)
                return "Success"

            except (TimeoutException, UnexpectedAlertPresentException, OSError):
                self._log(f"⚠️ Deneme {deneme}/{deneme_siniri} başarısız oldu (Ağ/Timeout). Yeniden yönlendiriliyor...", "warning")
                time.sleep(5.0)
                try: driver.get("https://wellcome.azurewebsites.net/pnlwell/")
                except Exception: pass
                if deneme == deneme_siniri: return f"Error: Network Timeout after {deneme_siniri} retries."
            except Exception as e:
                error_msg = str(e)[:40]
                self._log(lg["error_log"].format(folder_name, error_msg), "error")
                return f"Error: {error_msg}"
        return "Failed"

    def _toggle_pause(self) -> None:
        lg = LANG_PACK[self.current_lang]
        if self.pause_event.is_set():
            self.pause_event.clear()  
            self.pause_button.configure(text=lg["resume"], fg_color="#27ae60", hover_color="#219653")
            self._log(f"[SYSTEM] {lg['pause']} - Otomasyon duraklatıldı. Kontrol yapabilirsiniz.", "warning")
        else:
            self.pause_event.set()  
            self.pause_button.configure(text=lg["pause"], fg_color="#f39c12", hover_color="#e67e22")
            self._log(f"[SYSTEM] {lg['resume']} - Otomasyon kaldığı yerden devam ediyor...", "system")

    def _save_to_checkpoint(self, folder_name: str) -> None:
        try:
            processed = []
            if os.path.exists(self.checkpoint_file):
                with open(self.checkpoint_file, "r") as f: processed = json.load(f)
            if folder_name not in processed: processed.append(folder_name)
            with open(self.checkpoint_file, "w") as f: json.dump(processed, f)
        except Exception: pass

    def _generate_report(self, results: List[Dict[str, str]], base_path: str) -> None:
        lg = LANG_PACK[self.current_lang]
        try:
            directory = base_path if base_path and os.path.exists(base_path) else os.getcwd()
            filename = f"Wellcome_RPA_AI_Raporu_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            full_path = os.path.join(directory, filename)
            pd.DataFrame(results).to_excel(full_path, index=False)
            self._log(lg["report_gen"].format(full_path), "success")
        except Exception as e: self._log(f"\n❌ Rapor oluşturulamadı: {e}", "error")

    def _start_automation(self) -> None:
        lg = LANG_PACK[self.current_lang]
        if not self.base_folder_path.get() and not self.demo_mode_var.get():
            messagebox.showwarning("Warning", lg["no_folder"])
            return
        if self.is_running: return

        self._log(lg["pre_flight_start"], "system")
        try: socket.create_connection(("8.8.8.8", 53), timeout=3)
        except OSError:
            self._log(lg["internet_err"], "error")
            return

        base_path = self.base_folder_path.get()
        if self.demo_mode_var.get():
            personel_folders = ["KANIVAR_TOKAY", "MEHMET_YILMAZ", "AYSE_DEMIR"]
        else:
            if not os.path.exists(base_path):
                messagebox.showwarning("Warning", lg["no_folder"])
                return
            personel_folders = [f for f in os.listdir(base_path) if os.path.isdir(os.path.join(base_path, f))]

        processed_folders = []
        if os.path.exists(self.checkpoint_file):
            try:
                with open(self.checkpoint_file, "r") as f: processed_folders = json.load(f)
            except Exception: pass

        if processed_folders:
            resume = messagebox.askyesno(lg["checkpoint_title"], lg["checkpoint_msg"].format(len(processed_folders)))
            if resume: personel_folders = [f for f in personel_folders if f not in processed_folders]
            else:
                with open(self.checkpoint_file, "w") as f: json.dump([], f)

        if not personel_folders:
            messagebox.showinfo("Bilgi", "İşlenecek yeni personel klasörü bulunamadı.")
            return

        self.is_running = True
        self.start_button.configure(state="disabled", text=lg["running"], fg_color="gray")
        self.pause_button.configure(state="normal")
        self.pause_event.set()  
        self.start_time = time.time()
        self.processed_count_for_eta = 0
        self._save_settings()

        threading.Thread(target=self._run_automation_loop, args=(personel_folders, base_path), daemon=True).start()

    def _calculate_eta(self, remaining_count: int) -> str:
        if self.processed_count_for_eta == 0 or self.start_time is None: return LANG_PACK[self.current_lang]["eta_calculating"]
        elapsed_time = time.time() - self.start_time
        avg_time_per_folder = elapsed_time / self.processed_count_for_eta
        remaining_seconds = int(avg_time_per_folder * remaining_count)
        return f"{remaining_seconds // 60:02d}m {remaining_seconds % 60:02d}s"

    def _run_automation_loop(self, folders: list, base_path: str) -> None:
        lg = LANG_PACK[self.current_lang]
        driver = None
        results_report: List[Dict[str, str]] = []
        
        try:
            total_folders = len(folders)
            success_count = 0
            error_count = 0
            self.after(0, lambda: self.progress_bar.set(0))

            if not self.demo_mode_var.get():
                driver = self._create_driver()
                driver.get(config.LOGIN_URL)
                bekleme = WebDriverWait(driver, 15)
                
                if self.username_var.get() and self.password_var.get():
                    # --- 🛑 YENİ MİMARİ BURADA KİLİTLİYOR 🛑 ---
                    login_success = self._handle_embedded_login(driver, bekleme)
                    if not login_success:
                        self._log("⚠️ [KRİTİK DURDURMA] Giriş başarısız olduğu için işlem tamamen iptal edildi. Klasörler ellenmedi.", "error")
                        if driver: driver.quit()
                        return # Klasör döngüsüne girmeden sistemi tamamen durdurur!
                else:
                    messagebox.showinfo("Giriş Onayı", "Giriş bilgileri boş! Lütfen tarayıcıdan giriş yapıp OK basın.")
            else:
                self._log(lg["demo_alert"], "warning")

            # Giriş başarılıysa döngü güvenle başlar
            for index, folder in enumerate(folders):
                if not self.is_running: break
                status_res = self._process_single_folder(driver, folder, base_path)
                
                if status_res == "Success" and not self.demo_mode_var.get():
                    try:
                        arsiv_dizini = os.path.join(base_path, "[BASARILI_ARSIV]")
                        if not os.path.exists(arsiv_dizini): os.makedirs(arsiv_dizini)
                        shutil.move(os.path.join(base_path, folder), os.path.join(arsiv_dizini, folder))
                        self._log(f"🗂️ {folder} başarıyla [BASARILI_ARSIV] dizinine arşivlendi.", "system")
                    except Exception as archive_err:
                        self._log(f"⚠️ Arşivleme hatası ({folder}): {str(archive_err)[:40]}", "warning")
                
                personel_data = self._read_personel_txt(os.path.join(base_path, folder) if base_path else folder)
                results_report.append({
                    "Klasör Adı": folder,
                    "Personel Ad Soyad": personel_data["isim_soyisim"],
                    "TC Kimlik No": personel_data["tc"],
                    "İşlem Durumu": "Başarılı" if status_res == "Success" else "Hata/Engel",
                    "Detay": "" if status_res == "Success" else status_res,
                    "Zaman": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })

                if status_res == "Success": success_count += 1
                else: error_count += 1
                
                self.processed_count_for_eta += 1
                kalan = total_folders - (index + 1)
                eta_str = self._calculate_eta(kalan) if kalan > 0 else "00:00"
                stats_text = lg["stats"].format(success_count, error_count, kalan, eta_str)
                self.after(0, lambda p=(index + 1) / total_folders, s=stats_text: (self.progress_bar.set(p), self.stats_label.configure(text=s)))

            if results_report and self.is_running:
                self._generate_report(results_report, base_path)
                with open(self.checkpoint_file, "w") as f: json.dump([], f)

        except Exception as main_err: self._log(f"[CRITICAL] Ana döngü hatası: {main_err}", "error")
        finally:
            if driver:
                try: driver.quit()
                except Exception: pass
            self.after(0, lambda: (setattr(self, 'is_running', False), self.start_button.configure(state="normal", text=lg["start"], fg_color="#27ae60"), self.pause_button.configure(state="disabled")))


if __name__ == "__main__":
    try:
        app = WellcomeRPAApp()
        app.mainloop()
    except KeyboardInterrupt: os._exit(0)
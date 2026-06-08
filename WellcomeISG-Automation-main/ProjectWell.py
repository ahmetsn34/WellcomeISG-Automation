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
import io
import urllib.request
from datetime import datetime
from typing import Optional, Dict, List, Tuple

import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
import pandas as pd

# Akıllı PDF ve OCR Kütüphaneleri
import pdfplumber
from pdf2image import convert_from_path
import pytesseract
from PIL import Image

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import StaleElementReferenceException, TimeoutException, UnexpectedAlertPresentException

# Konuşma Protokolü için Ses Kütüphanesi
try:
    import pyttsx3
except ImportError:
    pyttsx3 = None

# =====================================================================
# --- TESSERACT OCR WINDOWS YOLU YAPILANDIRMASI ---
# =====================================================================
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
# =====================================================================

# =====================================================================
# --- MONKEY PATCH: WinError 6 Kirliliğini Kökten Yok Etme Zırhı ---
# =====================================================================
try:
    original_del = uc.Chrome.__del__
    def safe_del(self):
        try:
            original_del(self)
        except Exception: pass
    uc.Chrome.__del__ = safe_del
except Exception: pass

os.environ['WDM_LOG'] = '0'
ctk.set_appearance_mode("Dark")

# =====================================================================
# --- LOGGER VE CONFIG COZUMU ---
# =====================================================================
class MockLogger:
    def info(self, msg): print(f"[INFO] {msg}")
    def error(self, msg): print(f"[ERROR] {msg}")

class MockConfig:
    DISABLE_IMAGES = False
    LOGIN_URL = "https://wellcome.azurewebsites.net/pnlwell/"

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
    logger = MockLogger()
    config = MockConfig()

# =====================================================================
# --- DİL PAKETİ ---
# =====================================================================
LANG_PACK = {
    "TR": {
        "title": "WELLCOME // AUTOMATION SUITE",
        "subtitle": "Enterprise RPA Control Panel v3.4 AI Final Stable",
        "select_file": "Excel Seç",
        "select_folder": "Klasör Seç",
        "placeholder_file": "Excel/CSV dosyası veya OneDrive Linki bağlayın...",
        "placeholder_folder": "Evrak klasör yolu veya OneDrive linki girin...",
        "headless": "Arka Plan (Headless)",
        "start": "OTOMASYONU BAŞLAT",
        "running": "İŞLEMLER SÜRÜYOR...",
        "pause": "DURAKLAT",
        "resume": "DEVAM ET",
        "kpi_success": "BAŞARILI KAYIT",
        "kpi_failed": "HATALI / KALAN",
        "kpi_eta": "TAHMİNİ BİTİŞ (ETA)",
        "no_data": "Lütfen önce Excel veri kaynağını ve Evrak klasörünü belirtin!",
        "pre_flight_start": "[SİSTEM] Altyapı ve veri taraması yapılıyor...",
        "internet_ok": "  🌐 İnternet bağlantısı aktif.",
        "internet_err": "❌ KRİTİK HATA: İnternet bağlantısı yok!",
        "chrome_ok": "  🚗 Chrome görünmezlik altyapısı hazır.",
        "eta_calculating": "Hesaplanıyor...",
        "all_done": "Seçilen dosyadaki tüm personeller ve evrakları başarıyla işlendi!",
        "login_wait": "🔐 Gömülü bilgilerle giriş yapılıyor, OTP kodu bekleniyor...",
        "process_folder": "👤 Personel İşleniyor: {}",
        "read_success": "    📋 Okunan -> Ad Soyad: {}, TC: {}, Tel: {}",
        "submit_form": "-> Bilgiler doğrulanıyor, 'Kullanıcıyı Oluştur' butonuna çift tıklanıyor...",
        "success_log": "✅ [BAŞARILI] {} sisteme kaydedildi. Tokenli evrak linkine zıplanıyor...",
        "error_log": "❌ [HATA] {} işlenirken sorun çıktı: {}",
        "report_gen": "📊 Operasyon raporu harici dizine kaydedildi: {}",
        "sw_retry": "Akıllı Adım Tekrarı",
        "lbl_comp": "Şirket Kodu",
        "lbl_user": "Kullanıcı Adı",
        "lbl_pass": "Şifre",
        "otp_title": "🔐 OTP Güvenlik Kodu",
        "otp_prompt": "Telefonunuza veya e-postanıza gelen 6 haneli OTP kodunu giriniz:",
        "lbl_throttle": "Gecikme Girdisi: {}s",
        "lbl_range": "Filtre Sektör Aralığı"
    },
    "EN": {
        "title": "WELLCOME // AUTOMATION SUITE",
        "subtitle": "Enterprise RPA Control Panel v3.4 AI Final Stable",
        "select_file": "Browse Excel",
        "select_folder": "Browse Folder",
        "placeholder_file": "Select Excel/CSV file or paste OneDrive Link...",
        "placeholder_folder": "Select main folder path or paste OneDrive link...",
        "headless": "Headless Mode",
        "start": "START AUTOMATION",
        "running": "PROCESSING...",
        "pause": "PAUSE",
        "resume": "RESUME",
        "kpi_success": "SUCCESS LOGS",
        "kpi_failed": "FAILED / REMAINING",
        "kpi_eta": "ESTIMATED TIME (ETA)",
        "no_data": "Please select both data source and documents folder first!",
        "pre_flight_start": "[SYSTEM] Running pre-flight infrastructure checks...",
        "internet_ok": "  🌐 Internet connection is active.",
        "internet_err": "❌ CRITICAL ERROR: No internet connection!",
        "chrome_ok": "  🚗 Chrome stealth infrastructure is ready.",
        "eta_calculating": "Calculating...",
        "all_done": "All personnel records and documents have been processed!",
        "login_wait": "🔐 Logging in with embedded credentials, waiting for OTP...",
        "process_folder": "👤 Processing Personnel: {}",
        "read_success": "    📋 Extracted -> Name: {}, ID: {}, Tel: {}",
        "submit_form": "-> Verifying details, double clicking 'Create User' button...",
        "success_log": "✅ [SUCCESS] {} registered successfully. Jumping to tokenized link...",
        "error_log": "❌ [ERROR] Failed to process {}: {}",
        "report_gen": "📊 Report saved: {}",
        "sw_retry": "Smart Step Retry", 
        "lbl_comp": "Company Code",
        "lbl_user": "Username",
        "lbl_pass": "Password",
        "otp_title": "🔐 OTP Security Code",
        "otp_prompt": "Enter the 6-digit OTP code sent to your phone/email:",
        "lbl_throttle": "Throttle Delay: {}s",
        "lbl_range": "Range Indices"
    }
}


class WellcomeRPAApp(ctk.CTk):

    def _update_ui_texts(self) -> None:
        lg = LANG_PACK[self.current_lang]
        self.title(lg["title"])
        self.title_label.configure(text=lg["title"])
        self.subtitle_label.configure(text=lg["subtitle"])
        
        self.excel_file_button.configure(text=lg["select_file"])
        self.excel_file_entry.configure(placeholder_text=lg["placeholder_file"])
        self.docs_folder_button.configure(text=lg["select_folder"])
        self.docs_folder_entry.configure(placeholder_text=lg["placeholder_folder"])
        
        self.cb_headless.configure(text=lg["headless"])
        self.sw_retry_cb.configure(text=lg["sw_retry"])
        
        self.lbl_comp_txt.configure(text=lg["lbl_comp"]) 
        self.lbl_user_txt.configure(text=lg["lbl_user"])
        self.lbl_pass_txt.configure(text=lg["lbl_pass"])
        
        self.kpi_lbl_succ.configure(text=lg["kpi_success"])
        self.kpi_lbl_fail.configure(text=lg["kpi_failed"])
        self.kpi_lbl_eta.configure(text=lg["kpi_eta"])
        
        self.throttle_label.configure(text=lg["lbl_throttle"].format(round(self.throttle_speed.get(), 1)))
        self.lbl_range_txt.configure(text=lg["lbl_range"])
        
        self.pause_button.configure(text=lg["pause"] if self.pause_event.is_set() else lg["resume"])
        
        if not self.is_running:
            self.start_button.configure(text=lg["start"])
        else:
            self.start_button.configure(text=lg["running"])
        self.lang_dropdown.set(self.current_lang)

    def _speak(self, text: str):
        if pyttsx3:
            def run_speech():
                try:
                    engine = pyttsx3.init()
                    engine.setProperty('rate', 150)
                    engine.say(text)
                    engine.runAndWait()
                    del engine
                except: pass
            threading.Thread(target=run_speech, daemon=True).start()

    def _generate_report(self, results: List[Dict[str, str]], center_path: str) -> None:
        try:
            if not self.current_report_path:
                filename = f"Sea_Fort_RPA_AI_Raporu_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                self.current_report_path = os.path.join(center_path, filename)
            pd.DataFrame(results).to_excel(self.current_report_path, index=False)
        except PermissionError:
            self._log("⚠️ Rapor Excel dosyası şu an açık! Önbelleğe yazıldı.", "warning")
        except Exception as e: 
            self._log(f"⚠️ Raporlama arızası: {e}", "warning")

    def _load_settings(self) -> None:
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, "r") as f:
                    settings = json.load(f)
                    self.current_lang = settings.get("lang", "TR")
                    self.excel_file_path.set(settings.get("excel_file_path", ""))
                    self.docs_folder_path.set(settings.get("docs_folder_path", ""))
                    self.company_code_var.set(settings.get("company_code", "")) 
                    self.username_var.set(settings.get("username", ""))
                    self.password_var.set(settings.get("password", ""))
                    self.headless_var.set(settings.get("headless", False))
                    self.retry_enabled.set(settings.get("retry_enabled", True))
                    self.alert_dismiss_enabled.set(settings.get("alert_dismiss_enabled", True))
            except Exception: pass

    def _save_settings(self) -> None:
        settings = {
            "lang": self.current_lang,
            "excel_file_path": self.excel_file_path.get(),
            "docs_folder_path": self.docs_folder_path.get(),
            "company_code": self.company_code_var.get(), 
            "username": self.username_var.get(),
            "password": self.password_var.get(),
            "headless": self.headless_var.get(),
            "retry_enabled": self.retry_enabled.get(),
            "alert_dismiss_enabled": self.alert_dismiss_enabled.get()
        }
        try:
            with open(self.settings_file, "w") as f: json.dump(settings, f)
        except Exception: pass

    def _toggle_pause(self) -> None:
        lg = LANG_PACK[self.current_lang]
        if self.pause_event.is_set():
            self.pause_event.clear()  
            self.pause_button.configure(text=lg["resume"], fg_color="#22C55E", hover_color="#16A34A")
            self._log(f"[SİSTEM] {lg['pause']} - Otomasyon duraklatıldı.", "warning")
        else:
            self.pause_event.set()  
            self.pause_button.configure(text=lg["pause"], fg_color="#64748B", hover_color="#475569")
            self._log(f"[SİSTEM] {lg['resume']} - Otomasyon kaldığı yerden devam ediyor...", "system")

    def _log(self, message: str, tag: str = "normal") -> None:
        def update_gui():
            try:
                self.log_text.configure(state="normal")
                line_count = int(self.log_text.index('end-1c').split('.')[0])
                if line_count > 150:
                    self.log_text.delete("1.0", "20.0")
                self.log_text.insert(tk.END, f"{datetime.now().strftime('%H:%M:%S')} - {message}\n", tag)
                self.log_text.see(tk.END)
                self.log_text.configure(state="disabled")
            except Exception: pass
        self.after(0, update_gui)

    def _on_lang_change(self, choice: str) -> None:
        self.current_lang = choice
        self._update_ui_texts()
        self._save_settings()

    def _select_excel_file(self) -> None:
        path = filedialog.askopenfilename(
            title="WellcomeRPA Veri Dosyasını Seçin",
            filetypes=[("Excel ve CSV Dosyaları", "*.xlsx *.xls *.csv")]
        )
        if path:
            self.excel_file_path.set(path)
            self._log(f"[SİSTEM] Veri Excel'i Bağlandı: {os.path.basename(path)}", "system")
            self._save_settings()

    def _select_docs_folder(self) -> None:
        path = filedialog.askdirectory(title="Personel PDF Klasörlerinin Bulunduğu Ana Dizini Seçin")
        if path:
            self.docs_folder_path.set(path)
            self._log(f"[SİSTEM] PDF Evrak Klasörü Bağlandı: {path}", "system")
            self._save_settings()

    def _clean_phone_number(self, phone_str: str) -> str:
        if not phone_str: return ""
        digits = re.sub(r'\D', '', str(phone_str))
        if digits.startswith("90") and len(digits) > 10: digits = digits[2:]
        elif digits.startswith("0") and len(digits) == 11: digits = digits[1:]
        return digits

    def _mask_sensitive_data(self, value: str, is_tc: bool = True) -> str:
        if not value or value == "00000000000": return "---"
        value = str(value).split('.')[0]
        if is_tc and len(value) == 11:
            return f"{value[:3]}******{value[-2:]}"
        elif not is_tc and len(value) >= 7:
            return f"{value[:3]}***{value[-2:]}"
        return value

    def _validate_tc_kn(self, tc_str: str) -> bool:
        if not tc_str or len(tc_str) != 11 or not tc_str.isdigit(): return False
        if tc_str[0] == '0': return False
        
        digits = [int(d) for d in tc_str]
        if digits[10] % 2 != 0: return False
        
        tekler = sum(digits[0:9:2])
        ciftler = sum(digits[1:8:2])
        if ((tekler * 7) - ciftler) % 10 != digits[9]: return False
        if sum(digits[0:10]) % 10 != digits[10]: return False
        
        return True

    def _request_otp_from_user(self) -> str:
        lg = LANG_PACK[self.current_lang]
        self._speak("Lütfen telefonunuza gelen altı haneli güvenlik kodunu ekrana giriniz.")
        otp_box = ctk.CTkInputDialog(text=lg["otp_prompt"], title=lg["otp_title"])
        otp_code = otp_box.get_input()
        return otp_code if otp_code else ""

    def _is_blacklisted(self, folder_name: str) -> bool:
        if os.path.exists(self.blacklist_file):
            try:
                with open(self.blacklist_file, "r") as f:
                    return folder_name in json.load(f)
            except Exception: pass
        return False

    def _add_to_blacklist(self, folder_name: str) -> None:
        blacklist = []
        if os.path.exists(self.blacklist_file):
            try:
                with open(self.blacklist_file, "r") as f: blacklist = json.load(f)
            except Exception: pass
        if folder_name not in blacklist:
            blacklist.append(folder_name)
            try:
                with open(self.blacklist_file, "w") as f: json.dump(blacklist, f)
            except Exception: pass

    def _calculate_eta(self, remaining: int) -> str:
        if self.start_time is None or self.processed_count_for_eta == 0:
            return LANG_PACK[self.current_lang]["eta_calculating"]
        elapsed = time.time() - self.start_time
        avg_time = elapsed / self.processed_count_for_eta
        total_seconds = int(avg_time * remaining)
        mins, secs = divmod(total_seconds, 60)
        return f"{mins:02d}:{secs:02d}"

    def _clean_turkish_chars(self, text: str) -> str:
        mapping = {'İ': 'I', 'I': 'I', 'Ş': 'S', 'Ğ': 'G', 'Ç': 'C', 'Ü': 'U', 'Ö': 'O', 'ı': 'i', 'ş': 's', 'ğ': 'g', 'ç': 'c', 'ü': 'u', 'ö': 'o'}
        for tr_char, eng_char in mapping.items():
            text = text.replace(tr_char, eng_char)
        return text.upper()

    def __init__(self) -> None:
        super().__init__()

        self.settings_file = "settings.json"
        self.checkpoint_file = "checkpoint.json"
        self.blacklist_file = "blacklist.json"

        self.excel_file_path = tk.StringVar()
        self.docs_folder_path = tk.StringVar()
        self.company_code_var = tk.StringVar() 
        self.username_var = tk.StringVar()
        self.password_var = tk.StringVar()
        
        self.range_start_var = tk.StringVar(value="")
        self.range_end_var = tk.StringVar(value="")
        self.throttle_speed = tk.DoubleVar(value=2.0)
        
        self.is_running = False
        self.headless_var = tk.BooleanVar(value=False)
        self.retry_enabled = tk.BooleanVar(value=True)
        self.alert_dismiss_enabled = tk.BooleanVar(value=True)
        self.current_lang = "TR"
        
        self.pause_event = threading.Event()
        self.pause_event.set()  
        self.checkpoint_lock = threading.Lock()
        
        self.start_time = None
        self.processed_count_for_eta = 0
        self.current_report_path = None
        self.current_full_df = None

        self._load_settings() 
        self._build_ui()  
        self._update_ui_texts()
        
        self.geometry("720x750")
        logger.info("Application re-initialized with normal load strategy.")

    def _read_personel_from_row(self, row: pd.Series) -> Dict[str, str]:
        ad_soyadi = str(row.get('ADI SOYADI', 'Bilinmeyen Personel')).strip()
        tc_raw = str(row.get('T.C. Kimlik Numarası', ''))
        tc_clean = tc_raw.split('.')[0].strip()
        
        tel_raw = str(row.get('TELEFON NUMARASI', ''))
        tel_clean = self._clean_phone_number(tel_raw)
        
        gorev_clean = str(row.get('GÖREVİ', 'Personel')).strip()
        if gorev_clean == 'nan' or not gorev_clean:
            gorev_clean = 'Personel'

        veriler = {
            "tc": tc_clean if tc_clean != 'nan' else '00000000000', 
            "isim_soyisim": ad_soyadi, 
            "gorev": gorev_clean,
            "telefon": tel_clean,
            "eposta": "",
            "valid_record": True
        }

        if not self._validate_tc_kn(veriler["tc"]):
            self._log(f"❌ [ALGORİTMA HATASI] {ad_soyadi} -> T.C. doğrulamayı geçemedi!", "error")
            veriler["valid_record"] = False
            
        if not veriler["telefon"]:
            self._log(f"❌ [VERİ EKSİK] {ad_soyadi} -> Telefon numarası tespit edilemedi!", "error")
            veriler["valid_record"] = False

        cleaned_name = "".join([c for c in self._clean_turkish_chars(veriler["isim_soyisim"]).lower() if c.isalnum() or c.isspace()])
        veriler["eposta"] = f"{cleaned_name.replace(' ', '.')}@seafortservice.com"

        return veriler

    def _create_driver(self) -> Optional[uc.Chrome]:
        os.system("taskkill /f /im chromedriver.exe >nul 2>&1")
        os.system("taskkill /f /im chrome.exe >nul 2>&1")
        time.sleep(1)

        chrome_options = uc.ChromeOptions()
        chrome_options.add_experimental_option("prefs", {
            "profile.managed_default_content_settings.images": config.DISABLE_IMAGES,
            "profile.default_content_setting_values.notifications": 2
        })
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--ignore-certificate-errors")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--window-size=1280,720")
        
        chrome_options.page_load_strategy = 'normal'
        chrome_options.set_capability("unhandledPromptBehavior", "accept")
        
        try:
            return uc.Chrome(options=chrome_options, headless=self.headless_var.get(), use_subprocess=True)
        except Exception as e:
            self._log(f"⚠️ Sürücü uyuşmazlığı yakalandı. Bağımsız v148 kilit zırhı tetikleniyor...", "warning")
            os.system("taskkill /f /im chromedriver.exe >nul 2>&1")
            time.sleep(0.5)
            
            backup_options = uc.ChromeOptions()
            backup_options.add_experimental_option("prefs", {
                "profile.managed_default_content_settings.images": config.DISABLE_IMAGES,
                "profile.default_content_setting_values.notifications": 2
            })
            backup_options.add_argument("--no-sandbox")
            backup_options.add_argument("--disable-dev-shm-usage")
            backup_options.add_argument("--disable-gpu")
            backup_options.add_argument("--ignore-certificate-errors")
            backup_options.add_argument("--window-size=1280,720")
            backup_options.page_load_strategy = 'normal'
            backup_options.set_capability("unhandledPromptBehavior", "accept")
            
            try:
                return uc.Chrome(options=backup_options, headless=self.headless_var.get(), version_main=148, use_subprocess=False)
            except Exception as backup_err:
                self._log(f"❌ KRİTİK: Sürücü katmanı ayağa kaldırılamadı: {backup_err}", "error")
                raise backup_err

    def _handle_embedded_login(self, driver: uc.Chrome, bekleme: WebDriverWait) -> bool:
        lg = LANG_PACK[self.current_lang]
        try:
            self._log("🔐 Giriş alanları dolduruluyor...", "system")
            time.sleep(1.5) 

            if self.company_code_var.get():
                comp_input = bekleme.until(EC.presence_of_element_located((By.ID, "FirmCode")))
                comp_input.clear()
                comp_input.send_keys(self.company_code_var.get())
                comp_input.send_keys(Keys.ENTER)
                time.sleep(4.5) 
                bekleme = WebDriverWait(driver, 20)

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
                otp_input = bekleme.until(EC.presence_of_element_located((By.ID, "VerificationCode")))
                driver.execute_script("arguments[0].value = arguments[1];", otp_input, user_otp)
                time.sleep(0.5)
                
                otp_submit_btn = bekleme.until(EC.presence_of_element_located((By.XPATH, "//a[contains(@class, 'btn-sms-verification') or text()='Doğrula ve Giriş Yap']")))
                driver.execute_script("arguments[0].click();", otp_submit_btn) 
                time.sleep(3.0)
            return True
        except Exception as e:
            self._log(f"❌ KRİTİK GİRİŞ HATASI: Detay: {str(e)[:50]}", "error")
            return False

    # =====================================================================
    # --- ULTRA KARARLI AI TAHMİN / OCR SIFIR HATA MOTORU ---
    # =====================================================================
    def _analyze_document_content_ai(self, file_path: str) -> Optional[str]:
        text_content = ""
        filename_raw = os.path.basename(file_path).upper()
        filename_clean = self._clean_turkish_chars(filename_raw)
        
        # --- [YALIN ÖZGÜ TAAHHÜT BYPASS KİLİDİ] ---
        if "YAPILACAK" in filename_clean and "OZGU" in filename_clean and "TAAHHUT" in filename_clean:
            return "Yapılacak İşen Özgü Talimatlar ve Taahhütnameler"

        if "IS SAGLIGI VE GUVENLIGI.PDF" in filename_clean or "IS_SAGLIGI_VE_GUVENLIGI.PDF" in filename_clean or filename_clean == "IS SAGLIGI VE GUVENLIGI.PDF":
            return "İş Sağlığı ve Güvenliği Talimat ve Taahhütnamesi"

        evrak_ai_weights = {
            "Adli Sicil Belgesi": ["ADLI SICIL", "SABIKA KAYDI", "ARSIV KAYDI", "SICIL", "SABIKA", "ADLI-SICIL"],
            "Geçici Görevlendirme Belgesi": ["GOREVLENDIRME", "GECICI", "GEÇİCİ GÖREVLENDİRME", "GOREVLENDIRME FORMU"],
            "Kişisel Koruyucu Donanım Zimmet Formu": ["DONANIM ZIMMET", "KKD ZIMMET", "ZIMMET FORMU", "TESLIM FORMU", "KORUYUCU DONANIM", "DONANIM", "KKD", "KKBDONANIM", "KKB"],
            "Nüfus Cüzdanı Sadece Ön Yüz": ["TC KIMLIK KARTI", "NUFUS CUZDANI", "DOGUM TARIHI", "SERI NO", "KIMLIK NUMARASI", "KIMLIK KARTI", "KIMLIK", "KİMLİK"],
            "Sürücü Belgesi": ["SURUCU BELGESI", "EHLIYET", "KULLANILDIGI ARACLAR", "BELGE NO", "SURUCU"],
            "SGK İşe Giriş bildiğresi / SGK Bağ-Kur Kaydı Belgesi /Emekli Durum Belgesi": ["SIGORTALI ISE GIRIS", "BILDIRGESI", "4A", "İŞE GİRİŞ BİLDİRGESİ", "GIRIS BILDIRGESI", "SGK", "ISE GIRIS", "İGB"],
            "İş Yeri Hekimi Kanaat Raporu / OGUK": ["SAGLIK RAPORU", "ISYERI HEKIMI", "KANAAT", "FIZIKSEL MUAYENE", "ISE UYGUNDUR", "MUAYENE FORMU", "HEKIMI KANAAT", "EK-2", "EK 2", "OGUK"],
            "Temel İş Sağlığı ve Güvenliği Eğitim Sertifikası": ["TEMEL EGITIM", "TEMEL EGITIM SERTIFIKASI", "16 SAAT", "ISG EGITIM", "ISG SERTIFIKASI"],
            "Yapılacak İşin Gerekliliği Olan Mesleki Yeterlilik Belgesi (MYK,EKAT, operatörlük belgesi vb.)": ["MESLEKI YETERLILIK", "MYK", "YETERLILIK BELGESI", "MESLEK KODU", "MUAFIYET", "MESLEKİ YETERLİLİK BELGESİ", "MUAFİYET"],
            "İş Sağlığı ve Güvenliği Talimat ve Taahhütnamesi": ["TALIMAT VE TAAHHUTNAMESI", "TAAHHUTNAME", "MADDELERINI", "TEBELLUG", "TALIMATNAME", "İŞ SAĞLIĞI VE GÜVENLİĞİ", "TALIMAT MADDELERI", "ISG TAAHHUT", "ISG TAAHUT"],
            "Yapılacak İşen Özgü Talimatlar ve Taahhütnameler": ["OZGU TALIMATNAME", "YAPILACAK ISEN OZGU", "OZGU TALIMATLAR", "YAPILACAK ISE OZGU TALIMATNAME", "OZGU TALIMAT", "ISEN OZGU", "İŞEN ÖZGÜ", "OZGU TAAHHUT", "MESLEGE OZGU"],
            "Yapılacak İşe Özgü Eğitim Sertifikası (yüksekte çalışma, kapalı alanlarda çalışma vb.)": ["YUKSEKTE CALISMA", "KAPALI ALAN", "OZGU EGITIM", "YÜKSEKTE ÇALIŞMA BELGESI", "YUKSEKTE", "CALISMABELGESI", "EGITIM SERTIFIKASI"]
        }

        if "EK-2" in filename_clean or "EK 2" in filename_clean:
            return "İş Yeri Hekimi Kanaat Raporu / OGUK"
            
        for evrak_tipi, anahtar_kelimeler in evrak_ai_weights.items():
            for kelime in anahtar_kelimeler:
                if kelime in filename_clean:
                    return evrak_tipi

        if file_path.lower().endswith('.pdf'):
            try:
                with pdfplumber.open(file_path) as pdf:
                    for page in pdf.pages[:2]:
                        text_content += (page.extract_text() or "")
            except Exception: pass

        text_content = self._clean_turkish_chars(text_content)

        is_image = file_path.lower().endswith(('.jpg', '.jpeg', '.png'))
        if is_image or file_path.lower().endswith('.pdf'):
            try:
                if is_image:
                    ocr_text = pytesseract.image_to_string(Image.open(file_path), lang='tur+eng')
                    text_content += (ocr_text or "")
                else:
                    images = convert_from_path(file_path, first_page=1, last_page=2)
                    for img in images:
                        ocr_text = pytesseract.image_to_string(img, lang='tur+eng')
                        text_content += (ocr_text or "")
            except Exception: pass

        text_content = self._clean_turkish_chars(text_content)

        if "IS SAGLIGI VE GUVENLIGI" in text_content and not any(k in text_content for k in ["TEMEL", "EGITIM", "SERTIFIKA", "16 SAAT"]):
            return "İş Sağlığı ve Güvenliği Talimat ve Taahhütnamesi"

        if ("TEMEL" in text_content or "EGITIM" in text_content or "SERTIFIKA" in text_content) and "IS SAGLIGI" in text_content:
            return "Temel İş Sağlığı ve Güvenliği Eğitim Sertifikası"

        best_match = None
        max_score = 0

        for evrak_tipi, anahtar_kelimeler in evrak_ai_weights.items():
            score = 0
            for kelime in anahtar_kelimeler:
                if text_content and kelime in text_content:
                    score += text_content.count(kelime) * 20

            if score > max_score:
                max_score = score
                best_match = evrak_tipi

        if max_score >= 20:
            return best_match
            
        return None

    # =====================================================================
    # --- GÜVENLİ BORU HATTI VE SELECTION KİLİTLEME SİSTEMİ ---
    # =====================================================================
    def _execute_document_upload_pipeline(self, driver: uc.Chrome, bekleme: WebDriverWait, row: pd.Series, docs_folder: str) -> bool:
        ad_soyadi = str(row.get('ADI SOYADI', '')).strip()
        tc_no = str(row.get('T.C. Kimlik Numarası', '')).split('.')[0].strip()
        user_delay = self.throttle_speed.get()
        
        personel_klasor_yolu = None
        target_name_clean = self._clean_turkish_chars(ad_soyadi).replace(" ", "")
        
        tarama_dizinleri = []
        if os.path.exists(docs_folder) and os.path.isdir(docs_folder):
            tarama_dizinleri.append(docs_folder)
        tarama_dizinleri.append(os.getcwd())
        
        for ana_dizin in tarama_dizinleri:
            try:
                for alt_oge in os.listdir(ana_dizin):
                    tam_yol = os.path.join(ana_dizin, alt_oge)
                    if os.path.isdir(tam_yol):
                        current_dir_clean = self._clean_turkish_chars(alt_oge).replace(" ", "")
                        if target_name_clean in current_dir_clean or current_dir_clean in target_name_clean:
                            personel_klasor_yolu = tam_yol
                            break
            except Exception: pass
            if personel_klasor_yolu: break

        if not personel_klasor_yolu:
            self._log(f"⚠️ {ad_soyadi} için evrak klasörü bulunamadı. İşlem atlanıyor.", "warning")
            return False
            
        mevcut_dosyalar = os.listdir(personel_klasor_yolu)
        if not mevcut_dosyalar:
            self._log(f"⚠️ {ad_soyadi} klasörünün içi boş, evrak yüklenemedi.", "warning")
            return False

        while True:
            try:
                try:
                    driver.execute_script("window.onbeforeunload = null; window.alert = function() {}; window.confirm = function() {return true;};")
                except Exception: pass

                self._log("🚀 Tokenli evrak yükleme linkine güvenli bağlantı kuruluyor...", "system")
                driver.get("https://wellcome.azurewebsites.net/pnlwell/files/documents/?v=CyGOrRq/t88nmeL78K/hmA==&dcode=ce")
                
                WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.ID, "drpEvrak")))
                time.sleep(5.5 + user_delay)
                
                bekleme = WebDriverWait(driver, 25)
                evrak_select_el = driver.find_element(By.ID, "drpEvrak")
                select_obj = Select(evrak_select_el)
                sitedeki_opsiyonlar = [(opt.get_attribute("value"), opt.text.strip()) for opt in select_obj.options if opt.text.strip() != ""]
                break
            except Exception:
                self._log(f"⚠️ [SİTE SAPITTI]: Ekstra alan veya yükleme donması algılandı! Çözülene kadar sayfa yenileniyor (Refresh)...", "error")
                try: driver.execute_script("window.stop();")
                except: pass
                time.sleep(3.0)

        try:
            for dosya in mevcut_dosyalar:
                if dosya.startswith('.') or os.path.isdir(os.path.join(personel_klasor_yolu, dosya)):
                    continue
                    
                tam_dosya_yolu = os.path.abspath(os.path.join(personel_klasor_yolu, dosya))
                
                self._log(f"🧠 AI Hibrit Analiz Yapıyor -> {dosya}...", "system")
                tahmin_edilen_tip = self._analyze_document_content_ai(tam_dosya_yolu)
                
                if not tahmin_edilen_tip:
                    self._log(f"❓ AI Belgeyi Tanıyamadı veya Havuz Dışı Kaldı: {dosya} (Pas geçiliyor)", "warning")
                    continue
                    
                self._log(f"🎯 AI Belge Türünü Teşhes Etti: [ {tahmin_edilen_tip[:40]}... ]", "success")

                # --- [KİLİTLENEMEDİ HATASINI YOK EDEN SELECTION ZIRHI] ---
                success_match = False
                for attempt in range(4):
                    try:
                        # Postback temizliği bekletmesi
                        driver.execute_script("if(typeof jQuery !== 'undefined') { jQuery('.select2-container--open').remove(); }")
                        time.sleep(1.0)
                        
                        bekleme = WebDriverWait(driver, 25)
                        select2_container = bekleme.until(EC.visibility_of_element_located((By.XPATH, "//*[contains(@class, 'select2-selection') and @aria-labelledby='select2-drpWorker-container']")))
                        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", select2_container)
                        time.sleep(0.5)

                        actions = ActionChains(driver)
                        actions.move_to_element_with_offset(select2_container, -50, 0).click().perform()
                        time.sleep(1.0)

                        select2_search = bekleme.until(EC.presence_of_element_located((By.CLASS_NAME, "select2-search__field")))
                        driver.execute_script("arguments[0].click();", select2_search)
                        driver.execute_script("arguments[0].focus();", select2_search)
                        time.sleep(0.3)
                        
                        select2_search.clear()
                        for char in ad_soyadi:
                            select2_search.send_keys(char)
                            time.sleep(0.05)
                        time.sleep(2.0)

                        js_worker_injector = """
                            var target_text_1 = arguments[0];
                            var target_text_2 = arguments[1];
                            var select_el = document.getElementById('drpWorker');
                            if(!select_el) return false;
                            
                            for (var i = 0; i < select_el.options.length; i++) {
                                var opt = select_el.options[i];
                                if (opt.text.indexOf(target_text_1) !== -1 || opt.text.indexOf(target_text_2) !== -1) {
                                    select_el.value = opt.value;
                                    if(typeof jQuery !== 'undefined') {
                                        jQuery(select_el).trigger('change');
                                    } else {
                                        var event = document.createEvent('HTMLEvents');
                                        event.initEvent('change', true, true);
                                        select_el.dispatchEvent(event);
                                    }
                                    return true;
                                }
                            }
                            return false;
                        """
                        success_match = driver.execute_script(js_worker_injector, tc_no, ad_soyadi)
                        time.sleep(1.5)
                        if success_match:
                            break
                    except Exception:
                        time.sleep(1.5)

                if not success_match:
                    self._log(f"⚠️ {ad_soyadi} seçimi postback sonrası kilitlenemedi, pas geçiliyor.", "warning")
                    continue

                hedef_value = None
                hedef_görünür_metin = ""
                
                tahmin_clean = self._clean_turkish_chars(tahmin_edilen_tip).strip()
                for val, text in sitedeki_opsiyonlar:
                    text_clean = self._clean_turkish_chars(text).strip()
                    if tahmin_clean in text_clean or text_clean in tahmin_clean:
                        hedef_value = val
                        hedef_görünür_metin = text
                        break
                        
                if not hedef_value:
                    kisa_kok = tahmin_clean.split()[0]
                    for val, text in sitedeki_opsiyonlar:
                        text_clean = self._clean_turkish_chars(text).strip()
                        if kisa_kok in text_clean:
                            hedef_value = val
                            hedef_görünür_metin = text
                            break

                if not hedef_value:
                    self._log(f"❌ Sitede '{tahmin_edilen_tip}' ibaresini içeren hiçbir evrak tipi bulunamadı! Pas geçildi.", "error")
                    continue

                try:
                    js_dropdown_force = """
                        var sel = document.getElementById('drpEvrak');
                        var val_to_set = arguments[0];
                        if(sel) {
                            sel.value = val_to_set;
                            if(typeof jQuery !== 'undefined') {
                                jQuery(sel).trigger('change');
                            } else {
                                var event = document.createEvent('HTMLEvents');
                                event.initEvent('change', true, true);
                                sel.dispatchEvent(event);
                            }
                            return true;
                        }
                        return false;
                    """
                    driver.execute_script(js_dropdown_force, hedef_value)
                    time.sleep(1.5)
                except Exception:
                    continue

                try:
                    file_upload_input = driver.find_element(By.ID, "ContentPlaceHolder1_FileUpload1")
                    driver.execute_script("arguments[0].style.display = 'block'; arguments[0].style.visibility = 'visible';", file_upload_input)
                    time.sleep(0.5)
                    
                    file_upload_input.send_keys(tam_dosya_yolu)
                    time.sleep(1.0)
                    
                    evrak_yukle_btn = driver.find_element(By.ID, "ContentPlaceHolder1_btnEvrakKaydet") if driver.find_elements(By.ID, "ContentPlaceHolder1_btnEvrakKaydet") else driver.find_element(By.XPATH, "//a[contains(@onclick, 'fncOtherClick')]")
                    driver.execute_script("arguments[0].click();", evrak_yukle_btn)
                    
                    self._log(f"📁 [AI YÜKLEDİ] -> Tür: '{hedef_görünür_metin[:20]}' -> Dosya: {dosya}", "success")
                    time.sleep(5.0 + user_delay)
                except Exception as upload_inner_err:
                    self._log(f"⚠️ Belge yükleme katmanında beklenmeyen hata: {upload_inner_err}", "warning")
                    
            return True

        except Exception as e:
            self._log(f"❌ [KRİTİK BORU HATTI HATASI]: {str(e)}", "error")
            return False

    def _process_single_row(self, driver: Optional[uc.Chrome], row: pd.Series, docs_folder: str) -> Tuple[str, Dict[str, str]]:
        lg = LANG_PACK[self.current_lang]
        
        self.pause_event.wait()
        personel_bilgisi = self._read_personel_from_row(row)
        personel_ismi = personel_bilgisi["isim_soyisim"]
        
        if not personel_bilgisi["valid_record"]:
            return "Mükerrer veya Hatalı Veri", personel_bilgisi

        self._log(lg["process_folder"].format(personel_ismi), "system")
        user_delay = self.throttle_speed.get()

        for deneme in range(1, 4):
            try:
                bekleme = WebDriverWait(driver, 15)

                try:
                    driver.execute_script("window.alert = function() {}; window.confirm = function() {return true;};")
                except Exception: pass

                driver.get("https://wellcome.azurewebsites.net/pnlwell/")
                time.sleep(2.0)

                calisan_tanimla_btn = bekleme.until(EC.presence_of_element_located((By.XPATH, "//a[contains(@href, '/files/workgroup/')]")))
                driver.execute_script("arguments[0].click();", calisan_tanimla_btn)
                time.sleep(user_delay + random.uniform(1.0, 2.0))

                yeni_calisan_btn = bekleme.until(EC.presence_of_element_located((By.ID, "ContentPlaceHolder1_btnNewUserPanel")))
                driver.execute_script("arguments[0].click();", yeni_calisan_btn)
                time.sleep(user_delay + random.uniform(0.5, 1.0))

                isim_input = bekleme.until(EC.presence_of_element_located((By.ID, "NameSurname")))
                isim_input.clear()
                isim_input.send_keys(personel_bilgisi["isim_soyisim"])

                tc_input = driver.find_element(By.ID, "kimlikno")
                tc_input.clear()
                tc_input.send_keys(personel_bilgisi["tc"])

                gorev_input = driver.find_element(By.ID, "yetkinlik")
                gorev_input.clear()
                gorev_input.send_keys(personel_bilgisi["gorev"])

                uret_btn = driver.find_element(By.XPATH, "//a[contains(@onclick, 'rndPassword') or @title='Random Şifre Türet ']")
                driver.execute_script("arguments[0].click();", uret_btn)
                
                time.sleep(0.8)
                try:
                    username_field = driver.find_element(By.ID, "Username")
                    site_generated_username = username_field.get_attribute("value")
                    if site_generated_username:
                        personel_bilgisi["eposta"] = f"{site_generated_username.strip()}@seafortservice.com"
                except Exception: pass

                if personel_bilgisi["telefon"]:
                    tel_input = driver.find_element(By.ID, "telefon")
                    tel_input.clear()
                    tel_input.send_keys(personel_bilgisi["telefon"])

                if personel_bilgisi["eposta"]:
                    mail_input = driver.find_element(By.ID, "eposta")
                    mail_input.clear()
                    mail_input.send_keys(personel_bilgisi["eposta"])

                time.sleep(1.5)
                self._log(lg["submit_form"], "normal")
                
                kaydet_btn = bekleme.until(EC.presence_of_element_located((By.XPATH, "//a[contains(@onclick, 'AddNewUser') or contains(@class, 'createUser') or @id='ContentPlaceHolder1_btnSave']")))
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", kaydet_btn)
                time.sleep(0.5)
                
                driver.execute_script("arguments[0].click();", kaydet_btn)
                time.sleep(4.0 + user_delay) 
                
                try:
                    alert = driver.switch_to.alert
                    alert_msg = alert.text
                    alert.accept()
                    self._log(f"🔔 Site Uyarısı Yakalandı: {alert_msg}", "system")
                    if "zaten" in alert_msg.lower() or "mevcut" in alert_msg.lower() or "kayitli" in alert_msg.lower():
                        self._log(f"🔄 Personel Zaten Kayıtlı. Doğrudan Evrak Yükleme Adımına Geçiliyor -> {personel_ismi}", "warning")
                        self._add_to_blacklist(personel_ismi)
                        self._execute_document_upload_pipeline(driver, bekleme, row, docs_folder)
                        return "Success", personel_bilgisi
                except Exception: pass

                pipeline_res = self._execute_document_upload_pipeline(driver, bekleme, row, docs_folder)
                
                if pipeline_res:
                    return "Success", personel_bilgisi
                else:
                    return "Failed_Docs", personel_bilgisi

            except Exception as loop_err:
                time.sleep(3.0)
                try: driver.get("https://wellcome.azurewebsites.net/pnlwell/")
                except Exception: pass
                if deneme == 3: return f"Error: Operational Timeout.", personel_bilgisi
        return "Failed", personel_bilgisi

    def _run_automation_loop(self, df_data: pd.DataFrame, file_path: str, docs_folder: str) -> None:
        lg = LANG_PACK[self.current_lang]
        driver = None
        results_report: List[Dict[str, str]] = []
        
        if file_path.lower().startswith("http"):
            base_path = os.getcwd()
        else:
            base_path = os.path.dirname(os.path.abspath(file_path))
            
        center_directory = os.path.join(base_path, "Sea_Fort_RPA_Operasyon_Merkezi")
        
        if not os.path.exists(center_directory):
            try: os.makedirs(center_directory)
            except Exception: center_directory = base_path

        try:
            try:
                start_idx = int(self.range_start_var.get()) if self.range_start_var.get().isdigit() else 0
                end_idx = int(self.range_end_var.get()) if self.range_end_var.get().isdigit() else len(df_data)
                df_data = df_data.iloc[start_idx:end_idx]
            except Exception: pass

            total_records = len(df_data)
            success_count = 0
            error_count = 0
            
            self.after(0, lambda: (self.progress_bar.set(0), self.val_success.configure(text="0"), self.val_pending.configure(text=f"0 / {total_records}")))

            driver = self._create_driver()
            driver.get(config.LOGIN_URL)
            bekleme = WebDriverWait(driver, 15)
            
            if self.username_var.get() and self.password_var.get():
                if not self._handle_embedded_login(driver, bekleme): return 
            else:
                messagebox.showinfo("Giriş Onayı", "Giriş bilgileri boş! Lütfen giriş yapıp OK basın.")

            for index, (real_idx, row) in enumerate(df_data.iterrows()):
                if not self.is_running: break
                
                personel_ismi = str(row.get('ADI SOYADI', '')).strip()
                if self._is_blacklisted(personel_ismi): continue

                status_res, personel_data = self._process_single_row(driver, row, docs_folder)
                
                if status_res == "Mükerrer veya Hatalı Veri":
                    error_count += 1
                    results_report.append({
                        "Personel Ad Soyad": personel_data["isim_soyisim"] if "isim_soyisim" in personel_data else "Bilinmeyen",
                        "TC Kimlik No": self._mask_sensitive_data(personel_data["tc"], is_tc=True),
                        "Telefon No": self._mask_sensitive_data(personel_data["telefon"], is_tc=False),
                        "İşlem Durumu": "Bozuk / Eksik Evrak", "Detay": "Zorunlu telefon veya TC doğrulaması geçemedi.",
                        "Zaman": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    })
                    self._generate_report(results_report, center_directory)
                    continue

                results_report.append({
                    "Personel Ad Soyad": personel_data["isim_soyisim"] if "isim_soyisim" in personel_data else "Bilinmeyen",
                    "TC Kimlik No": self._mask_sensitive_data(personel_data["tc"], is_tc=True),
                    "Telefon No": self._mask_sensitive_data(personel_data["telefon"], is_tc=False),
                    "İşlem Durumu": "Başarılı" if status_res == "Success" else "Hata/Engel",
                    "Detay": "" if status_res == "Success" else status_res,
                    "Zaman": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })
                self._generate_report(results_report, center_directory)

                if status_res == "Success":
                    success_count += 1
                    if self.current_full_df is not None:
                        self.current_full_df.at[real_idx, 'YÜKLEME_DURUMU'] = 0
                        if not file_path.lower().startswith("http"):
                            try:
                                if file_path.lower().endswith('.csv'):
                                    self.current_full_df.to_csv(file_path, index=False)
                                else:
                                    self.current_full_df.to_excel(file_path, index=False)
                            except Exception as write_err:
                                self._log(f"⚠️ Orijinal Excel güncellenirken hata: {write_err}", "warning")
                else: 
                    error_count += 1
                
                self.processed_count_for_eta += 1
                kalan = total_records - (index + 1)
                
                time.sleep(0.05)
                self.after(0, lambda p=((index + 1) / total_records), s=str(success_count), d=f"{error_count} / {kalan}", e=(self._calculate_eta(kalan) if kalan > 0 else "00:00"): (
                    self.progress_bar.set(p), self.val_success.configure(text=s), self.val_pending.configure(text=d), self.val_eta.configure(text=e)
                ))
                time.sleep(1.8)

            if results_report and self.is_running:
                if self.current_report_path:
                    self._log(lg["report_gen"].format(os.path.basename(self.current_report_path)), "success")
                    self._speak("Tüm operasyon başarıyla tamamlandı, raporunuz kaydedildi.")

        except Exception as main_err: 
            self._log(f"[KRİTİK] Sistem hatası: {main_err}", "error")
        finally:
            self.after(0, lambda: (setattr(self, 'is_running', False), self.start_button.configure(state="normal", text=LANG_PACK[self.current_lang]["start"], fg_color="#22C55E"), self.pause_button.configure(state="disabled")))

    def _start_automation(self) -> None:
        lg = LANG_PACK[self.current_lang]
        if self.is_running: return
        
        excel_p = self.excel_file_path.get().strip()
        docs_p = self.docs_folder_path.get().strip()
        
        if not excel_p or not docs_p:
            messagebox.showerror("Eksik Seçim", lg["no_data"])
            return
            
        self._log(lg["pre_flight_start"], "system")
        
        try:
            if excel_p.lower().startswith("http"):
                self._log("🌐 Bulut Bağlantısı Algılandı. Excel verisi uzaktan çekiliyor...", "warning")
                req = urllib.request.Request(excel_p, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req) as response:
                    file_data = response.read()
                if "csv" in excel_p.lower():
                    df = pd.read_csv(io.BytesIO(file_data))
                else:
                    df = pd.read_excel(io.BytesIO(file_data))
            else:
                if excel_p.lower().endswith('.csv'):
                    df = pd.read_csv(excel_p)
                else:
                    df = pd.read_excel(excel_p)
        except Exception as e:
            self._log(f"❌ Dosya okunurken kritik Hata oluştu: {str(e)[:60]}", "error")
            return

        df.columns = df.columns.str.strip()
        
        if 'YÜKLEME_DURUMU' not in df.columns:
            self._log("❌ HATA: Dosyada 'YÜKLEME_DURUMU' adında bir sütun bulunamadı!", "error")
            return

        df['YÜKLEME_DURUMU'] = pd.to_numeric(df['YÜKLEME_DURUMU'].astype(str).str.strip(), errors='coerce')
        
        self.current_full_df = df.copy()
        filtrelenmis_df = df[df['YÜKLEME_DURUMU'] == 1]
        
        if filtrelenmis_df.empty:
            self._log("⚠️ 'YÜKLEME_DURUMU' sütunu '1' olan hiçbir kayıt bulunamadı!", "warning")
            return

        self._log(f"📊 Toplam Kayıt: {len(df)} | Filtrelenmiş Yüklenecek Kayıt: {len(filtrelenmis_df)}", "system")

        self.is_running = True
        self.start_button.configure(state="disabled", text=lg["running"])
        self.pause_button.configure(state="normal")
        self.start_time = time.time()
        self.processed_count_for_eta = 0
        self.current_report_path = None 
        self._save_settings()

        threading.Thread(target=self._run_automation_loop, args=(filtrelenmis_df, excel_p, docs_p), daemon=True).start()

    def _build_ui(self) -> None:
        top_bar = ctk.CTkFrame(self, fg_color="#1E293B", corner_radius=6, height=60)
        top_bar.pack(side="top", fill="x", padx=15, pady=(10, 5))
        top_bar.pack_propagate(False)

        title_frame = ctk.CTkFrame(top_bar, fg_color="transparent")
        title_frame.pack(side="left", padx=15, pady=8)
        self.title_label = ctk.CTkLabel(title_frame, text="", font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"), text_color="#F8FAFC")
        self.title_label.pack(anchor="w")
        self.subtitle_label = ctk.CTkLabel(title_frame, text="", font=ctk.CTkFont(family="Segoe UI", size=10), text_color="#3B82F6")
        self.subtitle_label.pack(anchor="w")

        self.lang_dropdown = ctk.CTkOptionMenu(top_bar, values=["TR", "EN"], command=self._on_lang_change, width=70, height=26, fg_color="#0F172A", button_color="#3B82F6")
        self.lang_dropdown.pack(side="right", padx=15, pady=17)

        main_container = ctk.CTkFrame(self, fg_color="transparent")
        main_container.pack(side="top", fill="both", expand=True, padx=15, pady=0)

        login_card = ctk.CTkFrame(main_container, fg_color="#1E293B", corner_radius=6)
        login_card.pack(pady=4, fill="x")
        login_card.grid_columnconfigure((0,1,2), weight=1)

        comp_frame = ctk.CTkFrame(login_card, fg_color="transparent")
        comp_frame.grid(row=0, column=0, padx=10, pady=8, sticky="ew")
        self.lbl_comp_txt = ctk.CTkLabel(comp_frame, text="", font=ctk.CTkFont(size=10, weight="bold"), text_color="#94A3B8")
        self.lbl_comp_txt.pack(anchor="w")
        self.company_entry = ctk.CTkEntry(comp_frame, textvariable=self.company_code_var, height=28, fg_color="#0F172A")
        self.company_entry.pack(fill="x")

        user_frame = ctk.CTkFrame(login_card, fg_color="transparent")
        user_frame.grid(row=0, column=1, padx=10, pady=8, sticky="ew")
        self.lbl_user_txt = ctk.CTkLabel(user_frame, text="", font=ctk.CTkFont(size=10, weight="bold"), text_color="#94A3B8")
        self.lbl_user_txt.pack(anchor="w")
        self.username_entry = ctk.CTkEntry(user_frame, textvariable=self.username_var, height=28, fg_color="#0F172A")
        self.username_entry.pack(fill="x")

        pass_frame = ctk.CTkFrame(login_card, fg_color="transparent")
        pass_frame.grid(row=0, column=2, padx=10, pady=8, sticky="ew")
        self.lbl_pass_txt = ctk.CTkLabel(pass_frame, text="", font=ctk.CTkFont(size=10, weight="bold"), text_color="#94A3B8")
        self.lbl_pass_txt.pack(anchor="w")
        self.password_entry = ctk.CTkEntry(pass_frame, textvariable=self.password_var, show="*", height=28, fg_color="#0F172A")
        self.password_entry.pack(fill="x")

        excel_card = ctk.CTkFrame(main_container, fg_color="#1E293B", corner_radius=6)
        excel_card.pack(pady=4, fill="x")
        self.excel_file_entry = ctk.CTkEntry(excel_card, textvariable=self.excel_file_path, height=32, fg_color="#0F172A")
        self.excel_file_entry.pack(side="left", padx=10, pady=10, expand=True, fill="x")
        self.excel_file_button = ctk.CTkButton(excel_card, text="", command=self._select_excel_file, width=100, height=32, fg_color="#3B82F6")
        self.excel_file_button.pack(side="right", padx=10, pady=10)

        docs_card = ctk.CTkFrame(main_container, fg_color="#1E293B", corner_radius=6)
        docs_card.pack(pady=4, fill="x")
        self.docs_folder_entry = ctk.CTkEntry(docs_card, textvariable=self.docs_folder_path, height=32, fg_color="#0F172A")
        self.docs_folder_entry.pack(side="left", padx=10, pady=10, expand=True, fill="x")
        self.docs_folder_button = ctk.CTkButton(docs_card, text="", command=self._select_docs_folder, width=100, height=32, fg_color="#EAB308", hover_color="#CA8A04")
        self.docs_folder_button.pack(side="right", padx=10, pady=10)

        adv_panel = ctk.CTkFrame(main_container, fg_color="#1E293B", corner_radius=6)
        adv_panel.pack(pady=4, fill="x")
        adv_panel.grid_columnconfigure((0,1,2), weight=1, uniform="equal_cols")

        sw_frame = ctk.CTkFrame(adv_panel, fg_color="transparent")
        sw_frame.grid(row=0, column=0, padx=15, pady=10, sticky="nw")
        self.cb_headless = ctk.CTkCheckBox(sw_frame, text="", variable=self.headless_var, fg_color="#3B82F6", checkbox_width=16, checkbox_height=16)
        self.cb_headless.pack(anchor="w", pady=3)
        self.sw_retry_cb = ctk.CTkSwitch(sw_frame, text="", variable=self.retry_enabled, progress_color="#3B82F6", switch_width=34, switch_height=16)
        self.sw_retry_cb.pack(anchor="w", pady=3)

        range_frame = ctk.CTkFrame(adv_panel, fg_color="transparent")
        range_frame.grid(row=0, column=1, padx=10, pady=10, sticky="n")
        self.lbl_range_txt = ctk.CTkLabel(range_frame, text="", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), text_color="#94A3B8")
        self.lbl_range_txt.pack(anchor="center")
        range_box_frame = ctk.CTkFrame(range_frame, fg_color="transparent")
        range_box_frame.pack(anchor="center", pady=4)
        self.entry_start = ctk.CTkEntry(range_box_frame, textvariable=self.range_start_var, placeholder_text="Start", width=55, height=26, fg_color="#0F172A")
        self.entry_start.pack(side="left", padx=(0, 4))
        self.entry_end = ctk.CTkEntry(range_box_frame, textvariable=self.range_end_var, placeholder_text="End", width=55, height=26, fg_color="#0F172A")
        self.entry_end.pack(side="left")

        throttle_frame = ctk.CTkFrame(adv_panel, fg_color="#1E293B", corner_radius=6)
        throttle_frame.grid(row=0, column=2, padx=15, pady=10, sticky="ne")
        self.throttle_label = ctk.CTkLabel(throttle_frame, text="", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), text_color="#94A3B8")
        self.throttle_label.pack(anchor="e")
        self.speed_slider = ctk.CTkSlider(throttle_frame, from_=0.5, to=8.0, number_of_steps=15, variable=self.throttle_speed, progress_color="#3B82F6", height=14, width=150, command=lambda e: self._update_ui_texts())
        self.speed_slider.pack(anchor="e", pady=6)

        kpi_container = ctk.CTkFrame(main_container, fg_color="transparent")
        kpi_container.pack(pady=4, fill="x")
        kpi_container.grid_columnconfigure((0,1,2), weight=1)

        card_success = ctk.CTkFrame(kpi_container, fg_color="#1E293B", border_color="#22C55E", border_width=1, corner_radius=6, height=65)
        card_success.grid(row=0, column=0, padx=(0, 6), sticky="ew")
        card_success.pack_propagate(False)
        self.kpi_lbl_succ = ctk.CTkLabel(card_success, text="", font=ctk.CTkFont(size=9, weight="bold"), text_color="#94A3B8")
        self.kpi_lbl_succ.pack(pady=(6, 0), padx=10, anchor="w")
        self.val_success = ctk.CTkLabel(card_success, text="0", font=ctk.CTkFont(size=18, weight="bold"), text_color="#22C55E")
        self.val_success.pack(pady=(0, 6), padx=10, anchor="w")

        card_pending = ctk.CTkFrame(kpi_container, fg_color="#1E293B", border_color="#3B82F6", border_width=1, corner_radius=6, height=65)
        card_pending.grid(row=0, column=1, padx=2, sticky="ew")
        card_pending.pack_propagate(False)
        self.kpi_lbl_fail = ctk.CTkLabel(card_pending, text="", font=ctk.CTkFont(size=9, weight="bold"), text_color="#94A3B8")
        self.kpi_lbl_fail.pack(pady=(6, 0), padx=10, anchor="w")
        self.val_pending = ctk.CTkLabel(card_pending, text="0 / 0", font=ctk.CTkFont(size=16, weight="bold"), text_color="#3B82F6")
        self.val_pending.pack(pady=(2, 6), padx=10, anchor="w")

        card_eta = ctk.CTkFrame(kpi_container, fg_color="#1E293B", border_color="#EAB308", border_width=1, corner_radius=6, height=65)
        card_eta.grid(row=0, column=2, padx=(6, 0), sticky="ew")
        card_eta.pack_propagate(False)
        self.kpi_lbl_eta = ctk.CTkLabel(card_eta, text="", font=ctk.CTkFont(size=9, weight="bold"), text_color="#94A3B8")
        self.kpi_lbl_eta.pack(pady=(6, 0), padx=10, anchor="w")
        self.val_eta = ctk.CTkLabel(card_eta, text="--:--", font=ctk.CTkFont(size=16, weight="bold"), text_color="#EAB308")
        self.val_eta.pack(pady=(2, 6), padx=10, anchor="w")

        self.progress_bar = ctk.CTkProgressBar(main_container, height=6, progress_color="#3B82F6", fg_color="#1E293B")
        self.progress_bar.set(0)
        self.progress_bar.pack(fill="x", pady=6)

        button_frame = ctk.CTkFrame(main_container, fg_color="transparent")
        button_frame.pack(pady=4, fill="x")
        button_frame.grid_columnconfigure(0, weight=3)
        button_frame.grid_columnconfigure(1, weight=1)

        self.start_button = ctk.CTkButton(button_frame, text="", fg_color="#3B82F6", hover_color="#2563EB", command=self._start_automation, height=38)
        self.start_button.grid(row=0, column=0, padx=(0, 8), sticky="ew")
        self.pause_button = ctk.CTkButton(button_frame, text="", fg_color="#64748B", command=self._toggle_pause, height=38, state="disabled")
        self.pause_button.grid(row=0, column=1, sticky="ew")

        log_card = ctk.CTkFrame(main_container, fg_color="#1E293B", corner_radius=6)
        log_card.pack(pady=6, fill="both", expand=True)
        self.log_textInput = tk.Text(log_card, bg="#0F172A", fg="#E2E8F0", font=("Consolas", 10), wrap="word", bd=0, highlightthickness=0)
        self.log_textInput.pack(fill="both", expand=True, padx=8, pady=8)
        self.log_text = self.log_textInput 
        self.log_text.tag_config("normal", foreground="#E2E8F0")    
        self.log_text.tag_config("system", foreground="#3B82F6") 
        self.log_text.tag_config("success", foreground="#22C55E", font=("Consolas", 10, "bold")) 
        self.log_text.tag_config("error", foreground="#EF4444", font=("Consolas", 10, "bold")) 
        self.log_text.tag_config("warning", foreground="#F59E0B") 
        self.log_text.configure(state="disabled")


if __name__ == "__main__":
    try:
        app = WellcomeRPAApp()
        app.mainloop()
    except KeyboardInterrupt: os._exit(0)
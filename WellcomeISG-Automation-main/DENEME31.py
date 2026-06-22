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
from selenium.common.exceptions import (
    StaleElementReferenceException,
    TimeoutException,
    UnexpectedAlertPresentException,
    NoSuchElementException
)

# =====================================================================
# --- TESSERACT OCR WINDOWS YOLU YAPILANDIRMASI ---
# =====================================================================
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# =====================================================================
# --- MONKEY PATCH: WinError 6 Kirliliğini Kökten Yok Etme Zırhı ---
# =====================================================================
try:
    original_del = uc.Chrome.__del__
    def safe_del(self):
        try:
            original_del(self)
        except Exception:
            pass
    uc.Chrome.__del__ = safe_del
except Exception:
    pass

os.environ['WDM_LOG'] = '0'
ctk.set_appearance_mode("Dark")


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
# --- DİL PAKETİ (v3.6) ---
# =====================================================================
LANG_PACK = {
    "TR": {
        "title": "WELLCOME // AUTOMATION SUITE",
        "subtitle": "Enterprise RPA Control Panel v3.6 Stable",
        "select_file": "Excel Seç",
        "select_folder": "Klasör Seç",
        "placeholder_file": "Excel/CSV dosyası veya OneDrive Linki bağlayın...",
        "placeholder_folder": "Evrak klasör yolu veya OneDrive linki girin...",
        "headless": "Arka Plan (Headless)",
        "start": "OTOMASYONU BAŞLAT",
        "upload_only": "SADECE EVRAK YÜKLE",
        "running": "İŞLEMLER SÜRÜYOR...",
        "pause": "DURAKLAT",
        "resume": "DEVAM ET",
        "kpi_success": "BAŞARILI KAYIT",
        "kpi_failed": "HATALI / KALAN",
        "kpi_eta": "TAHMİNİ BİTİŞ (ETA)",
        "no_data": "Lütfen önce Excel veri kaynağını ve Evrak klasörünü belirtin!",
        "pre_flight_start": "[SİSTEM] Altyapı ve veri taraması yapılıyor...",
        "internet_ok": "🌐 İnternet bağlantısı aktif.",
        "internet_err": "❌ KRİTİK HATA: İnternet bağlantısı yok!",
        "chrome_ok": "🚗 Chrome görünmezlik altyapısı hazır.",
        "eta_calculating": "Hesaplanıyor...",
        "all_done": "Seçilen dosyadaki tüm personeller ve evrakları başarıyla işlendi!",
        "login_wait": "🔐 Gömülü bilgilerle giriş yapılıyor, OTP kodu bekleniyor...",
        "process_folder": "👤 Personel İşleniyor: {}",
        "read_success": "📋 Okunan -> Ad Soyad: {}, TC: {}, Tel: {}",
        "submit_form": "-> Bilgiler doğrulanıyor, 'Kullanıcıyı Oluştur' butonuna tıklanıyor...",
        "success_log": "✅ [BAŞARILI] {} sisteme kaydedildi. Evrak adımına geçiliyor...",
        "error_log": "❌ [HATA] {} işlenirken sorun çıktı: {}",
        "report_gen": "📊 Operasyon raporu harici dizine kaydedildi: {}",
        "sw_retry": "Akıllı Adım Tekrarı",
        "sw_ocr": "AI & OCR Hibrit Analiz",
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
        "subtitle": "Enterprise RPA Control Panel v3.6 Stable",
        "select_file": "Browse Excel",
        "select_folder": "Browse Folder",
        "placeholder_file": "Select Excel/CSV file or paste OneDrive Link...",
        "placeholder_folder": "Select main folder path or paste OneDrive link...",
        "headless": "Headless Mode",
        "start": "START AUTOMATION",
        "upload_only": "UPLOAD DOCUMENTS ONLY",
        "running": "PROCESSING...",
        "pause": "PAUSE",
        "resume": "RESUME",
        "kpi_success": "SUCCESS LOGS",
        "kpi_failed": "FAILED / REMAINING",
        "kpi_eta": "ESTIMATED TIME (ETA)",
        "no_data": "Please select both data source and documents folder first!",
        "pre_flight_start": "[SYSTEM] Running pre-flight infrastructure checks...",
        "internet_ok": "🌐 Internet connection is active.",
        "internet_err": "❌ CRITICAL ERROR: No internet connection!",
        "chrome_ok": "🚗 Chrome stealth infrastructure is ready.",
        "eta_calculating": "Calculating...",
        "all_done": "All personnel records and documents have been processed!",
        "login_wait": "🔐 Logging in with embedded credentials, waiting for OTP...",
        "process_folder": "👤 Processing Personnel: {}",
        "read_success": "📋 Extracted -> Name: {}, ID: {}, Tel: {}",
        "submit_form": "-> Verifying details, clicking 'Create User' button...",
        "success_log": "✅ [SUCCESS] {} registered successfully. Transferring to documents...",
        "error_log": "❌ [ERROR] Failed to process {}: {}",
        "report_gen": "📊 Report saved: {}",
        "sw_retry": "Smart Step Retry",
        "sw_ocr": "AI & OCR Hybrid Engine",
        "lbl_comp": "Company Code",
        "lbl_user": "Username",
        "lbl_pass": "Password",
        "otp_title": "🔐 OTP Security Code",
        "otp_prompt": "Enter the 6-digit OTP code sent to your phone/email:",
        "lbl_throttle": "Throttle Delay: {}s",
        "lbl_range": "Range Indices"
    }
}

try:
    import pyttsx3
except ImportError:
    pyttsx3 = None

# =====================================================================
# --- EVRAK HARİTASI SABİT SIRA (HTML KAYNAK KODUNA GÖRE BİREBİR) ---
# =====================================================================
DEFAULT_EVRAK_MAP = {
    "1":  "Adli Sicil Belgesi",
    "2":  "Geçici Görevlendirme Belgesi",
    "3":  "İş Sağlığı ve Güvenliği Talimat ve Taahhütnamesi",
    "4":  "İş Yeri Hekimi Kanaat Raporu / OGUK",
    "5":  "Kişisel Koruyucu Donanım Zimmet Formu",
    "6":  "Nüfus Cüzdanı Sadece Ön Yüz",
    "7":  "SGK İşe Giriş bildirgesi / SGK Bağ-Kur Kaydı Belgesi /Emekli Durum Belgesi",
    "8":  "Temel İş Sağlığı ve Güvenliği Eğitim Sertifikası",
    "9":  "Yapılacak İşe Özgü Eğitim Sertifikası (yüksekte çalışma, kapalı alanlarda çalışma vb.)",
    "10": "Yapılacak İşe Özgü Talimatlar ve Taahhütnameler",
    "11": "Yapılacak İşin Gerekliliği Olan Mesleki Yeterlilik Belgesi (MYK,EKAT, operatörlük belgesi vb.)",
    "12": "Sürücü Belgesi",
    "13": "E-devlet’ten Alınacak ve Son Beş (5) Yıla ait, Sürücü Ceza Bilgisi ve Sürücü Trafik Kazası Barkodlu",
    "14": "Psikoteknik",
    "15": "SRC Belgesi",
    "16": "SRC-5 (Tehlikeli Madde Taşımacılık için)"
}


class WellcomeRPAApp(ctk.CTk):

    def __init__(self) -> None:
        super().__init__()

        self.settings_file   = "settings.json"
        self.checkpoint_file = "checkpoint.json"
        self.blacklist_file  = "blacklist.json"
        self.map_file        = "evrak_map.json"

        self.excel_file_path   = tk.StringVar()
        self.docs_folder_path  = tk.StringVar()
        self.company_code_var  = tk.StringVar()
        self.username_var      = tk.StringVar()
        self.password_var      = tk.StringVar()

        self.range_start_var = tk.StringVar(value="")
        self.range_end_var   = tk.StringVar(value="")
        self.throttle_speed  = tk.DoubleVar(value=2.0)

        self.new_evrak_num  = tk.StringVar()
        self.new_evrak_name = tk.StringVar()

        self.is_running             = False
        self.headless_var           = tk.BooleanVar(value=False)
        self.retry_enabled          = tk.BooleanVar(value=True)
        self.alert_dismiss_enabled  = tk.BooleanVar(value=True)
        self.ocr_enabled            = tk.BooleanVar(value=False)
        self.current_lang           = "TR"
        self.mode_upload_only       = False

        self.pause_event      = threading.Event()
        self.pause_event.set()
        self.checkpoint_lock  = threading.Lock()

        self.start_time                 = None
        self.processed_count_for_eta    = 0
        self.current_report_path        = None
        self.current_full_df            = None

        self._load_evrak_map()
        self._load_settings()
        self._build_ui()
        self._update_ui_texts()
        self._refresh_map_listbox()

        self.geometry("1100x780")
        logger.info("WellcomeRPA v3.6 başlatıldı.")

    # =====================================================================
    # --- EVRAK HARİTASI YÖNETİMİ ---
    # =====================================================================

    def _load_evrak_map(self) -> None:
        # JSON dosyasındaki olası bozulmaları tamamen ezmek için 
        # sadece orijinal listeyi yüklüyoruz.
        self.evrak_numara_haritasi = dict(DEFAULT_EVRAK_MAP)
        self._save_evrak_map()

    def _save_evrak_map(self) -> None:
        try:
            with open(self.map_file, "w", encoding="utf-8") as f:
                json.dump(self.evrak_numara_haritasi, f, ensure_ascii=False, indent=4)
        except Exception:
            pass

    def _add_custom_evrak(self) -> None:
        num  = self.new_evrak_num.get().strip()
        name = self.new_evrak_name.get().strip()
        if not num or not name:
            messagebox.showwarning("Eksik Veri", "Lütfen hem numara hem de evrak adı girin!")
            return
        self.evrak_numara_haritasi[num] = name
        self._save_evrak_map()
        self._refresh_map_listbox()
        self.new_evrak_num.set("")
        self.new_evrak_name.set("")
        self._log(f"➕ Yeni Evrak Tipi Haritaya Eklendi -> {num}: {name}", "success")

    def _refresh_map_listbox(self) -> None:
        try:
            self.map_textbox.configure(state="normal")
            self.map_textbox.delete("1.0", tk.END)
            sorted_map = sorted(
                self.evrak_numara_haritasi.items(),
                key=lambda x: int(x[0]) if x[0].isdigit() else 999
            )
            for num, name in sorted_map:
                self.map_textbox.insert(tk.END, f" [{num:>2}] → {name}\n")
            self.map_textbox.configure(state="disabled")
        except Exception:
            pass

    # =====================================================================
    # --- UI METİN / AYAR ---
    # =====================================================================

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
        self.sw_ocr_cb.configure(text=lg["sw_ocr"])
        self.lbl_comp_txt.configure(text=lg["lbl_comp"])
        self.lbl_user_txt.configure(text=lg["lbl_user"])
        self.lbl_pass_txt.configure(text=lg["lbl_pass"])
        self.kpi_lbl_succ.configure(text=lg["kpi_success"])
        self.kpi_lbl_fail.configure(text=lg["kpi_failed"])
        self.kpi_lbl_eta.configure(text=lg["kpi_eta"])
        self.throttle_label.configure(
            text=lg["lbl_throttle"].format(round(self.throttle_speed.get(), 1))
        )
        self.lbl_range_txt.configure(text=lg["lbl_range"])
        self.pause_button.configure(
            text=lg["pause"] if self.pause_event.is_set() else lg["resume"]
        )
        if not self.is_running:
            self.start_button.configure(text=lg["start"])
            self.upload_only_button.configure(text=lg["upload_only"])
        else:
            self.start_button.configure(text=lg["running"])
            self.upload_only_button.configure(text=lg["running"])
        self.lang_dropdown.set(self.current_lang)

    def _speak(self, text: str) -> None:
        if pyttsx3:
            def run_speech():
                try:
                    engine = pyttsx3.init()
                    engine.setProperty('rate', 150)
                    engine.say(text)
                    engine.runAndWait()
                    del engine
                except Exception:
                    pass
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
                    s = json.load(f)
                    self.current_lang = s.get("lang", "TR")
                    self.excel_file_path.set(s.get("excel_file_path", ""))
                    self.docs_folder_path.set(s.get("docs_folder_path", ""))
                    self.company_code_var.set(s.get("company_code", ""))
                    self.username_var.set(s.get("username", ""))
                    self.password_var.set(s.get("password", ""))
                    self.headless_var.set(s.get("headless", False))
                    self.retry_enabled.set(s.get("retry_enabled", True))
                    self.alert_dismiss_enabled.set(s.get("alert_dismiss_enabled", True))
                    self.ocr_enabled.set(s.get("ocr_enabled", False))
            except Exception:
                pass

    def _save_settings(self) -> None:
        try:
            with open(self.settings_file, "w") as f:
                json.dump({
                    "lang": self.current_lang,
                    "excel_file_path": self.excel_file_path.get(),
                    "docs_folder_path": self.docs_folder_path.get(),
                    "company_code": self.company_code_var.get(),
                    "username": self.username_var.get(),
                    "password": self.password_var.get(),
                    "headless": self.headless_var.get(),
                    "retry_enabled": self.retry_enabled.get(),
                    "alert_dismiss_enabled": self.alert_dismiss_enabled.get(),
                    "ocr_enabled": self.ocr_enabled.get()
                }, f)
        except Exception:
            pass

    def _toggle_pause(self) -> None:
        lg = LANG_PACK[self.current_lang]
        if self.pause_event.is_set():
            self.pause_event.clear()
            self.pause_button.configure(text=lg["resume"], fg_color="#22C55E", hover_color="#16A34A")
            self._log(f"[SİSTEM] Otomasyon duraklatıldı.", "warning")
        else:
            self.pause_event.set()
            self.pause_button.configure(text=lg["pause"], fg_color="#64748B", hover_color="#475569")
            self._log(f"[SİSTEM] Otomasyon devam ediyor...", "system")

    def _log(self, message: str, tag: str = "normal") -> None:
        def update_gui():
            try:
                self.log_text.configure(state="normal")
                if int(self.log_text.index('end-1c').split('.')[0]) > 150:
                    self.log_text.delete("1.0", "20.0")
                self.log_text.insert(tk.END, f"{datetime.now().strftime('%H:%M:%S')} - {message}\n", tag)
                self.log_text.see(tk.END)
                self.log_text.configure(state="disabled")
            except Exception:
                pass
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

    # =====================================================================
    # --- YARDIMCI FONKSİYONLAR ---
    # =====================================================================

    def _clean_turkish_chars(self, text: str) -> str:
        mapping = {
            'İ': 'I', 'Ş': 'S', 'Ğ': 'G', 'Ç': 'C',
            'Ü': 'U', 'Ö': 'O', 'ı': 'i', 'ş': 's',
            'ğ': 'g', 'ç': 'c', 'ü': 'u', 'ö': 'o'
        }
        for tr, en in mapping.items():
            text = text.replace(tr, en)
        return text.upper()

    def _normalize_string(self, text: str) -> str:
        """Kelimeleri karşılaştırmak için tüm özel karakterleri ve boşlukları temizler."""
        if not text: 
            return ""
        t = self._clean_turkish_chars(str(text))
        t = re.sub(r'[^A-Z0-9]', ' ', t)
        return ' '.join(t.split())

    def _clean_phone_number(self, phone_str: str) -> str:
        if not phone_str:
            return ""
        digits = re.sub(r'\D', '', str(phone_str))
        if digits.startswith("90") and len(digits) > 10:
            digits = digits[2:]
        elif digits.startswith("0") and len(digits) == 11:
            digits = digits[1:]
        return digits

    def _mask_sensitive_data(self, value: str, is_tc: bool = True) -> str:
        if not value or value == "00000000000":
            return "---"
        value = str(value).split('.')[0]
        if is_tc and len(value) == 11:
            return f"{value[:3]}******{value[-2:]}"
        elif not is_tc and len(value) >= 7:
            return f"{value[:3]}***{value[-2:]}"
        return value

    def _validate_tc_kn(self, tc_str: str) -> bool:
        if not tc_str or len(tc_str) != 11 or not tc_str.isdigit():
            return False
        if tc_str[0] == '0':
            return False
        digits = [int(d) for d in tc_str]
        if digits[10] % 2 != 0:
            return False
        if ((sum(digits[0:9:2]) * 7) - sum(digits[1:8:2])) % 10 != digits[9]:
            return False
        if sum(digits[0:10]) % 10 != digits[10]:
            return False
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
            except Exception:
                pass
        return False

    def _add_to_blacklist(self, folder_name: str) -> None:
        blacklist = []
        if os.path.exists(self.blacklist_file):
            try:
                with open(self.blacklist_file, "r") as f:
                    blacklist = json.load(f)
            except Exception:
                pass
        if folder_name not in blacklist:
            blacklist.append(folder_name)
            try:
                with open(self.blacklist_file, "w") as f:
                    json.dump(blacklist, f)
            except Exception:
                pass

    def _calculate_eta(self, remaining: int) -> str:
        if self.start_time is None or self.processed_count_for_eta == 0:
            return LANG_PACK[self.current_lang]["eta_calculating"]
        elapsed  = time.time() - self.start_time
        avg_time = elapsed / self.processed_count_for_eta
        mins, secs = divmod(int(avg_time * remaining), 60)
        return f"{mins:02d}:{secs:02d}"

    def _read_personel_from_row(self, row: pd.Series) -> Dict[str, str]:
        ad_soyadi   = str(row.get('ADI SOYADI', 'Bilinmeyen Personel')).strip()
        tc_raw      = str(row.get('T.C. Kimlik Numarası', ''))
        tc_clean    = tc_raw.split('.')[0].strip()
        tel_raw     = str(row.get('TELEFON NUMARASI', ''))
        tel_clean   = self._clean_phone_number(tel_raw)
        gorev_clean = str(row.get('GÖREVİ', 'Personel')).strip()
        if gorev_clean in ('nan', ''):
            gorev_clean = 'Personel'

        veriler = {
            "tc":            tc_clean if tc_clean != 'nan' else '00000000000',
            "isim_soyisim":  ad_soyadi,
            "gorev":         gorev_clean,
            "telefon":       tel_clean,
            "eposta":        "",
            "valid_record":  True,
        }

        if not self._validate_tc_kn(veriler["tc"]):
            self._log(f"❌ [TC HATA] {ad_soyadi} -> T.C. doğrulamayı geçemedi!", "error")
            veriler["valid_record"] = False

        if not veriler["telefon"]:
            self._log(f"❌ [TEL EKSİK] {ad_soyadi} -> Telefon bulunamadı!", "error")
            veriler["valid_record"] = False

        cleaned_name = "".join([
            c for c in self._clean_turkish_chars(ad_soyadi).lower()
            if c.isalnum() or c.isspace()
        ])
        veriler["eposta"] = f"{cleaned_name.replace(' ', '.')}@seafortservice.com"
        return veriler

    # =====================================================================
    # --- SELENIUM YARDIMCILARI ---
    # =====================================================================

    def _safe_wait_and_click(self, driver, by, value, timeout=15, retries=3) -> bool:
        for _ in range(retries):
            try:
                el = WebDriverWait(driver, timeout).until(EC.element_to_be_clickable((by, value)))
                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
                time.sleep(0.3)
                el.click()
                return True
            except (StaleElementReferenceException, NoSuchElementException):
                time.sleep(1.0)
            except Exception:
                try:
                    driver.execute_script("arguments[0].click();", driver.find_element(by, value))
                    return True
                except Exception:
                    pass
        return False

    def _safe_send_keys(self, driver, by, value, text, timeout=15, retries=3) -> bool:
        for _ in range(retries):
            try:
                el = WebDriverWait(driver, timeout).until(EC.presence_of_element_located((by, value)))
                el.clear()
                el.send_keys(text)
                return True
            except (StaleElementReferenceException, NoSuchElementException):
                time.sleep(1.0)
        return False

    def _create_driver(self) -> Optional[uc.Chrome]:
        os.system("taskkill /f /im chromedriver.exe >nul 2>&1")
        os.system("taskkill /f /im chrome.exe >nul 2>&1")
        time.sleep(1)

        def make_opts():
            opts = uc.ChromeOptions()
            opts.add_experimental_option("prefs", {
                "profile.managed_default_content_settings.images": config.DISABLE_IMAGES,
                "profile.default_content_setting_values.notifications": 2
            })
            for arg in ["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu",
                        "--ignore-certificate-errors", "--disable-extensions", "--window-size=1280,720"]:
                opts.add_argument(arg)
            opts.page_load_strategy = 'normal'
            opts.set_capability("unhandledPromptBehavior", "accept")
            return opts

        try:
            return uc.Chrome(options=make_opts(), headless=self.headless_var.get(), use_subprocess=True)
        except Exception:
            self._log("⚠️ Sürücü uyuşmazlığı, v148 kilidi tetikleniyor...", "warning")
            os.system("taskkill /f /im chromedriver.exe >nul 2>&1")
            time.sleep(0.5)
            try:
                return uc.Chrome(options=make_opts(), headless=self.headless_var.get(),
                                 version_main=148, use_subprocess=False)
            except Exception as err:
                self._log(f"❌ KRİTİK: Sürücü başlatılamadı: {err}", "error")
                raise

    # =====================================================================
    # --- GİRİŞ MOTORU ---
    # =====================================================================

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
                time.sleep(5.0)
                bekleme = WebDriverWait(driver, 25)

            user_box = bekleme.until(EC.element_to_be_clickable((By.ID, "Username")))
            pass_box = driver.find_element(By.ID, "Password")
            driver.execute_script("arguments[0].value = arguments[1];", user_box, self.username_var.get())
            driver.execute_script("arguments[0].value = arguments[1];", pass_box, self.password_var.get())
            time.sleep(0.8)

            login_btn = bekleme.until(EC.element_to_be_clickable((By.ID, "loginButton")))
            ActionChains(driver).move_to_element(login_btn).click().perform()
            self._log(lg["login_wait"], "warning")
            time.sleep(4.0)

            otp_fields = driver.find_elements(By.ID, "VerificationCode")
            if otp_fields:
                otp_done  = threading.Event()
                otp_holder = [""]
                def ask_gui():
                    otp_holder[0] = self._request_otp_from_user()
                    otp_done.set()
                self.after(0, ask_gui)
                otp_done.wait()
                if otp_holder[0]:
                    otp_input = bekleme.until(EC.presence_of_element_located((By.ID, "VerificationCode")))
                    driver.execute_script("arguments[0].value = arguments[1];", otp_input, otp_holder[0])
                    time.sleep(0.5)
                    otp_btn = bekleme.until(EC.presence_of_element_located((
                        By.XPATH,
                        "//a[contains(@class,'btn-sms-verification') or text()='Doğrula ve Giriş Yap']"
                    )))
                    driver.execute_script("arguments[0].click();", otp_btn)
                    time.sleep(3.5)

            time.sleep(3.0)
            driver.get("https://wellcome.azurewebsites.net/pnlwell/")
            time.sleep(2.5)
            self._log("✅ Giriş başarıyla tamamlandı.", "success")
            return True
        except Exception as e:
            self._log(f"❌ GİRİŞ HATASI: {str(e)[:60]}", "error")
            return False

    # =====================================================================
    # --- HİBRİT BELGE TANIMA MOTORU ---
    # =====================================================================

    def _analyze_document_content_ai(self, file_path: str) -> Optional[str]:
        filename_raw   = os.path.basename(file_path)
        filename_clean = self._clean_turkish_chars(filename_raw)

        # --- 1. Kesin Numara Eşleştirmesi (Örn: 1.pdf, 01.pdf) ---
        all_nums = re.findall(r'\d+', filename_clean)
        for num in sorted(all_nums, key=lambda x: int(x), reverse=True):
            clean_num = str(int(num))
            if clean_num in self.evrak_numara_haritasi:
                matched = self.evrak_numara_haritasi[clean_num]
                self._log(f"🔢 İsimden Yakalandı ({clean_num}) → {matched[:35]}...", "system")
                return matched

        # --- 2. OCR / AI Fallback ---
        if not self.ocr_enabled.get():
            return None

        quick_map = [
            (["ADLI SICIL", "SABIKA", "SICIL"], "1"),
            (["GOREVLENDIRME", "GECICI"], "2"),
            (["IS SAGLIGI VE GUVENLIGI TALIMAT", "TAAHHUTNAME"], "3"),
            (["EK-2", "EK 2", "HEKIMI", "KANAAT", "OGUK"], "4"),
            (["ZIMMET", "KKD", "KORUYUCU DONANIM"], "5"),
            (["NUFUS CUZDANI", "ON YUZ", "KIMLIK"], "6"),
            (["SGK", "ISE GIRIS", "BAG-KUR", "EMEKLİ DURUM"], "7"),
            (["TEMEL EGITIM", "16 SAAT", "TEMEL IS SAGLIGI"], "8"),
            (["OZGU EGITIM", "YUKSEKTE", "KAPALI ALAN"], "9"),
            (["OZGU TALIMAT", "OZGU TAAHHUT", "MESLEGE OZGU", "TALIMATNAME", "TAAHHUTNAMELER"], "10"),
            (["MESLEKI YETERLILIK", "MYK", "EKAT", "OPERATORLUK"], "11"),
        ]
        
        for keywords, num in quick_map:
            if any(kw in filename_clean for kw in keywords):
                matched = self.evrak_numara_haritasi.get(num)
                if matched:
                    return matched

        text_content = ""
        if file_path.lower().endswith('.pdf'):
            try:
                with pdfplumber.open(file_path) as pdf:
                    for page in pdf.pages[:2]:
                        text_content += (page.extract_text() or "")
            except Exception:
                pass

        is_image = file_path.lower().endswith(('.jpg', '.jpeg', '.png'))
        if is_image or file_path.lower().endswith('.pdf'):
            try:
                if is_image:
                    text_content += pytesseract.image_to_string(Image.open(file_path), lang='tur+eng') or ""
                else:
                    images = convert_from_path(file_path, first_page=1, last_page=2)
                    for img in images:
                        text_content += pytesseract.image_to_string(img, lang='tur+eng') or ""
            except Exception:
                pass

        text_content = self._clean_turkish_chars(text_content)

        weight_table = {
            "1":  ["ADLI SICIL", "SABIKA KAYDI", "ARSIV KAYDI"],
            "2":  ["GECICI GOREVLENDIRME", "GOREVLENDIRME BELGESI"],
            "3":  ["IS SAGLIGI VE GUVENLIGI", "TALIMAT VE TAAHHUTNAME"],
            "4":  ["ISYERI HEKIMI", "KANAAT RAPORU", "OGUK", "EK 2"],
            "5":  ["KKD", "ZIMMET FORMU", "KISISEL KORUYUCU"],
            "6":  ["NUFUS CUZDANI", "TC KIMLIK"],
            "7":  ["ISE GIRIS BILDIRGESI", "SGK BILDIRGESI", "BAG-KUR", "EMEKLİ"],
            "8":  ["TEMEL IS SAGLIGI", "TEMEL EGITIM SERTIFIKASI"],
            "9":  ["YUKSEKTE CALISMA", "KAPALI ALANLARDA", "OZGU EGITIM SERTIFIKASI"],
            "10": ["OZGU TALIMATLAR", "OZGU TAAHHUTNAMELER", "MESLEGE OZGU", "TALIMATNAME"],
            "11": ["MESLEKI YETERLILIK", "MYK BELGESI", "EKAT", "OPERATORLUK"],
        }
        best_num   = None
        max_score  = 0
        for num, keywords in weight_table.items():
            score = sum(text_content.count(kw) * 20 for kw in keywords if kw in text_content)
            if score > max_score:
                max_score = score
                best_num  = num

        if max_score >= 20 and best_num:
            return self.evrak_numara_haritasi.get(best_num)

        return None

    # =====================================================================
    # --- TOKEN KONTROL & KURTARMA YARDIMCISI ---
    # =====================================================================

    def _ensure_on_upload_page(self, driver: uc.Chrome, tokenli_url: str,
                                ad_soyadi: str, user_delay: float) -> Tuple[bool, List]:
        for deneme in range(1, 5):
            try:
                try:
                    driver.execute_script(
                        "window.onbeforeunload=null;"
                        "window.alert=function(){};"
                        "window.confirm=function(){return true;};"
                    )
                except Exception:
                    pass

                current_url = driver.current_url.lower()
                if "documents" not in current_url or "dcode=ce" not in current_url:
                    self._log(f"🚨 Token kayması! Sayfa yeniden yükleniyor (Deneme {deneme}/4)...", "warning")
                    driver.get(tokenli_url)

                WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.ID, "drpEvrak")))
                time.sleep(2.5 + user_delay)

                evrak_el = driver.find_element(By.ID, "drpEvrak")
                opsiyonlar = [
                    (opt.get_attribute("value"), opt.text.strip())
                    for opt in Select(evrak_el).options
                    if opt.text.strip()
                ]
                return True, opsiyonlar

            except Exception as e:
                self._log(f"⚠️ Sayfa kurtarma denemesi {deneme}/4 başarısız: {str(e)[:40]}", "error")
                try:
                    driver.execute_script("window.stop();")
                except Exception:
                    pass
                time.sleep(4.0)

        self._log(f"❌ {ad_soyadi} için yükleme sayfası 4 denemede açılamadı.", "error")
        return False, []

    # =====================================================================
    # --- ÇALIŞAN SEÇİM YARDIMCISI ---
    # =====================================================================

    def _select_worker_on_page(self, driver: uc.Chrome, ad_soyadi: str,
                                tc_no: str, user_delay: float) -> bool:
        for attempt in range(1, 5):
            try:
                driver.execute_script(
                    "if(typeof jQuery!=='undefined'){jQuery('.select2-container--open').remove();}"
                )
                time.sleep(0.8)

                bekleme = WebDriverWait(driver, 20)
                container = bekleme.until(EC.visibility_of_element_located((
                    By.XPATH,
                    "//*[contains(@class,'select2-selection') and "
                    "@aria-labelledby='select2-drpWorker-container']"
                )))
                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", container)
                time.sleep(0.4)
                ActionChains(driver).move_to_element_with_offset(container, -50, 0).click().perform()
                time.sleep(0.8)

                search_box = bekleme.until(EC.presence_of_element_located((By.CLASS_NAME, "select2-search__field")))
                driver.execute_script("arguments[0].click(); arguments[0].focus();", search_box)
                time.sleep(0.3)
                search_box.clear()
                for ch in ad_soyadi:
                    search_box.send_keys(ch)
                    time.sleep(0.04)
                time.sleep(2.0)

                selected = driver.execute_script("""
                    var tc   = arguments[0];
                    var isim = arguments[1];
                    var sel  = document.getElementById('drpWorker');
                    if(!sel) return false;
                    for(var i=0;i<sel.options.length;i++){
                        var t = sel.options[i].text;
                        if(t.indexOf(tc)!==-1 || t.indexOf(isim)!==-1){
                            sel.value = sel.options[i].value;
                            var ev = document.createEvent('HTMLEvents');
                            ev.initEvent('change',true,true);
                            sel.dispatchEvent(ev);
                            if(typeof jQuery!=='undefined') jQuery(sel).trigger('change');
                            return true;
                        }
                    }
                    return false;
                """, tc_no, ad_soyadi)

                if selected:
                    self._log(f"👤 Çalışan kilitlendi: {ad_soyadi}", "system")
                    time.sleep(3.0 + user_delay)
                    WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.ID, "drpEvrak")))
                    return True

                self._log(f"⚠️ Çalışan JS ile seçilemedi (Deneme {attempt}/4), tekrar...", "warning")
                time.sleep(1.5)

            except StaleElementReferenceException:
                self._log("⚠️ Stale element, yeniden deneniyor...", "warning")
                time.sleep(1.0)
            except Exception:
                time.sleep(1.5)

        return False

    # =====================================================================
    # --- EVRAK YÜKLEME BORU HATTI ---
    # =====================================================================

    def _execute_document_upload_pipeline(
        self, driver: uc.Chrome, bekleme: WebDriverWait,
        row: pd.Series, docs_folder: str
    ) -> bool:
        ad_soyadi   = str(row.get('ADI SOYADI', '')).strip()
        tc_no       = str(row.get('T.C. Kimlik Numarası', '')).split('.')[0].strip()
        user_delay  = self.throttle_speed.get()
        tokenli_url = (
            "https://wellcome.azurewebsites.net/pnlwell/files/documents/"
            "?v=CyGOrRq/t88nmeL78K/hmA==&dcode=ce"
        )

        personel_klasor_yolu  = None
        target_clean          = self._clean_turkish_chars(ad_soyadi).replace(" ", "")

        tarama_dizinleri = []
        if os.path.exists(docs_folder) and os.path.isdir(docs_folder):
            tarama_dizinleri.append(docs_folder)
        tarama_dizinleri.append(os.getcwd())

        for ana_dir in tarama_dizinleri:
            try:
                for entry in os.listdir(ana_dir):
                    full = os.path.join(ana_dir, entry)
                    if os.path.isdir(full):
                        entry_clean = self._clean_turkish_chars(entry).replace(" ", "")
                        if target_clean in entry_clean or entry_clean in target_clean:
                            personel_klasor_yolu = full
                            break
            except Exception:
                pass
            if personel_klasor_yolu:
                break

        if not personel_klasor_yolu:
            self._log(f"⚠️ {ad_soyadi} için klasör bulunamadı, atlanıyor.", "warning")
            return False

        raw_files = [
            f for f in os.listdir(personel_klasor_yolu)
            if not f.startswith('.') and
               os.path.isfile(os.path.join(personel_klasor_yolu, f))
        ]
        if not raw_files:
            self._log(f"⚠️ {ad_soyadi} klasörü boş, yükleme yapılamadı.", "warning")
            return False

        def dosya_sira_key(fname):
            nums = re.findall(r'\d+', fname)
            if nums:
                return int(nums[0])
            
            f_upper = self._clean_turkish_chars(fname)
            if any(k in f_upper for k in ["SABIKA", "ADLI SICIL", "SICIL"]): return 1
            if any(k in f_upper for k in ["GECICI", "GOREVLENDIRME"]): return 2
            if any(k in f_upper for k in ["TALIMAT VE TAAHHUT", "ISG TALIMAT"]): return 3
            if any(k in f_upper for k in ["EK 2", "EK-2", "HEKIMI", "OGUK"]): return 4
            if any(k in f_upper for k in ["ZIMMET", "KKD"]): return 5
            if any(k in f_upper for k in ["NUFUS", "KIMLIK", "ON YUZ"]): return 6
            if any(k in f_upper for k in ["SGK", "ISE GIRIS", "BAG-KUR", "EMEKLİ"]): return 7
            if any(k in f_upper for k in ["TEMEL EGITIM", "16 SAAT"]): return 8
            if any(k in f_upper for k in ["OZGU EGITIM", "YUKSEKTE", "KAPALI ALAN"]): return 9
            if any(k in f_upper for k in ["OZGU TALIMAT", "MESLEGE OZGU", "TALIMATNAME"]): return 10
            if any(k in f_upper for k in ["MESLEKI", "MYK", "EKAT", "OPERATORLUK"]): return 11
            return 999

        siralı_dosyalar = sorted(raw_files, key=dosya_sira_key)
        self._log(
            f"📂 {ad_soyadi}: {len(siralı_dosyalar)} dosya sıralı yüklenecek "
            f"→ {[f[:20] for f in siralı_dosyalar]}", "system"
        )

        driver.get(tokenli_url)
        page_ok, sitedeki_opsiyonlar = self._ensure_on_upload_page(
            driver, tokenli_url, ad_soyadi, user_delay
        )
        if not page_ok:
            return False

        tümü_başarılı = True

        for dosya in siralı_dosyalar:
            tam_dosya_yolu = os.path.abspath(os.path.join(personel_klasor_yolu, dosya))

            self._log(f"🔍 [{dosya}] teşhis ediliyor...", "system")
            tahmin_edilen_tip = self._analyze_document_content_ai(tam_dosya_yolu)

            if not tahmin_edilen_tip:
                self._log(f"❓ [{dosya}] eşleşme bulunamadı → atlanıyor.", "warning")
                continue

            self._log(f"🎯 [{dosya}] → {tahmin_edilen_tip[:45]}", "success")

            page_ok, sitedeki_opsiyonlar = self._ensure_on_upload_page(
                driver, tokenli_url, ad_soyadi, user_delay
            )
            if not page_ok:
                self._log(f"❌ Token kurtarma başarısız, {dosya} atlanıyor.", "error")
                tümü_başarılı = False
                continue

            worker_ok = self._select_worker_on_page(driver, ad_soyadi, tc_no, user_delay)
            if not worker_ok:
                self._log(f"⚠️ {ad_soyadi} seçilemedi, {dosya} atlanıyor.", "warning")
                tümü_başarılı = False
                driver.get(tokenli_url)
                time.sleep(2.5)
                continue

            # ── AGRESİF METİN TEMİZLEME (NORMALIZE) İLE %100 EŞLEŞTİRME ──
            tahmin_norm = self._normalize_string(tahmin_edilen_tip)
            hedef_value  = None
            hedef_metin  = ""

            # 1. Agresif Karşılaştırma
            for val, text in sitedeki_opsiyonlar:
                text_norm = self._normalize_string(text)
                if tahmin_norm == text_norm or tahmin_norm in text_norm:
                    hedef_value = val
                    hedef_metin = text
                    break

            # 2. Akıllı Kelime Kesişimi
            if hedef_value is None:
                tahmin_words = set(tahmin_norm.split())
                best_score = 0
                for val, text in sitedeki_opsiyonlar:
                    text_norm = self._normalize_string(text)
                    text_words = set(text_norm.split())
                    
                    overlap = len(tahmin_words.intersection(text_words))
                    if overlap > best_score and overlap >= 2:
                        best_score = overlap
                        hedef_value = val
                        hedef_metin = text

            if hedef_value is None:
                self._log(f"❌ [{dosya}] için sitedeki listede karşılık bulunamadı → atlanıyor.", "error")
                tümü_başarılı = False
                continue

            try:
                driver.execute_script("""
                    var sel = document.getElementById('drpEvrak');
                    if(sel){
                        sel.value = arguments[0];
                        var ev = document.createEvent('HTMLEvents');
                        ev.initEvent('change',true,true);
                        sel.dispatchEvent(ev);
                        if(typeof jQuery!=='undefined') jQuery(sel).trigger('change');
                    }
                """, hedef_value)
                time.sleep(1.5)
            except Exception as e:
                self._log(f"⚠️ Dropdown set edilemedi: {e}", "warning")
                continue

            try:
                upload_input = driver.find_element(By.ID, "ContentPlaceHolder1_FileUpload1")
                driver.execute_script(
                    "arguments[0].style.display='block';"
                    "arguments[0].style.visibility='visible';",
                    upload_input
                )
                time.sleep(0.4)
                upload_input.send_keys(tam_dosya_yolu)
                time.sleep(1.0)

                btns = driver.find_elements(By.ID, "ContentPlaceHolder1_btnEvrakKaydet")
                kaydet_btn = btns[0] if btns else driver.find_element(
                    By.XPATH, "//a[contains(@onclick,'fncOtherClick')]"
                )
                driver.execute_script("arguments[0].click();", kaydet_btn)

                self._log(
                    f"📁 [YÜKLENDİ] → '{hedef_metin[:30]}' ← {dosya}", "success"
                )
                time.sleep(5.5 + user_delay)

                try:
                    alert = driver.switch_to.alert
                    alert_msg = alert.text
                    alert.accept()
                    self._log(f"🔔 Site uyarısı: {alert_msg}", "system")
                    time.sleep(1.0)
                except Exception:
                    pass

            except Exception as upload_err:
                self._log(f"⚠️ Yükleme hatası [{dosya}]: {str(upload_err)[:60]}", "warning")
                tümü_başarılı = False
                try:
                    driver.get(tokenli_url)
                    time.sleep(2.5)
                except Exception:
                    pass
                continue

        return tümü_başarılı

    # =====================================================================
    # --- TEK SATIR İŞLEME ---
    # =====================================================================

    def _process_single_row(
        self, driver: uc.Chrome, row: pd.Series, docs_folder: str
    ) -> Tuple[str, Dict[str, str]]:
        lg = LANG_PACK[self.current_lang]
        self.pause_event.wait()
        personel_bilgisi = self._read_personel_from_row(row)
        personel_ismi    = personel_bilgisi["isim_soyisim"]

        if not personel_bilgisi["valid_record"]:
            return "Mükerrer veya Hatalı Veri", personel_bilgisi

        self._log(lg["process_folder"].format(personel_ismi), "system")
        user_delay = self.throttle_speed.get()

        for deneme in range(1, 4):
            try:
                bekleme = WebDriverWait(driver, 15)
                try:
                    driver.execute_script(
                        "window.alert=function(){}; window.confirm=function(){return true;};"
                    )
                except Exception:
                    pass

                self._log("📋 Pre-check: sistemde kayıt aranıyor...", "system")
                driver.get("https://wellcome.azurewebsites.net/pnlwell/")
                time.sleep(2.0)

                calisan_btn = bekleme.until(
                    EC.presence_of_element_located((By.XPATH, "//a[contains(@href,'/files/workgroup/')]"))
                )
                driver.execute_script("arguments[0].click();", calisan_btn)
                time.sleep(2.5)

                search_field = bekleme.until(EC.presence_of_element_located((
                    By.XPATH,
                    "//input[@type='search' or contains(@class,'form-control-sm') or contains(@placeholder,'Ara')]"
                )))
                search_field.clear()
                search_field.send_keys(personel_bilgisi["tc"])
                time.sleep(2.0)

                if (personel_bilgisi["tc"] in driver.page_source
                        or personel_bilgisi["isim_soyisim"] in driver.page_source):
                    self._log(f"🔄 {personel_ismi} zaten kayıtlı → doğrudan evrak yükleniyor.", "warning")
                    self._execute_document_upload_pipeline(driver, bekleme, row, docs_folder)
                    return "Success", personel_bilgisi

                self._log("✨ Yeni kayıt! Form dolduruluyor...", "success")
                yeni_btn = bekleme.until(EC.presence_of_element_located((By.ID, "ContentPlaceHolder1_btnNewUserPanel")))
                driver.execute_script("arguments[0].click();", yeni_btn)
                time.sleep(user_delay + random.uniform(0.5, 1.0))

                self._safe_send_keys(driver, By.ID, "NameSurname", personel_bilgisi["isim_soyisim"])
                self._safe_send_keys(driver, By.ID, "kimlikno",    personel_bilgisi["tc"])
                self._safe_send_keys(driver, By.ID, "yetkinlik",   personel_bilgisi["gorev"])

                uret_btn = driver.find_element(
                    By.XPATH, "//a[contains(@onclick,'rndPassword') or @title='Random Şifre Türet ']"
                )
                driver.execute_script("arguments[0].click();", uret_btn)
                time.sleep(0.8)

                try:
                    site_user = driver.find_element(By.ID, "Username").get_attribute("value")
                    if site_user:
                        personel_bilgisi["eposta"] = f"{site_user.strip()}@seafortservice.com"
                except Exception:
                    pass

                tel_no = personel_bilgisi["telefon"]
                if tel_no:
                    self._safe_send_keys(driver, By.ID, "telefon", tel_no)

                if personel_bilgisi["eposta"]:
                    self._safe_send_keys(driver, By.ID, "eposta", personel_bilgisi["eposta"])

                time.sleep(1.5)
                self._log(lg["submit_form"], "normal")

                kaydet_btn = bekleme.until(EC.presence_of_element_located((
                    By.XPATH,
                    "//a[contains(@onclick,'AddNewUser') or "
                    "contains(@class,'createUser') or "
                    "@id='ContentPlaceHolder1_btnSave']"
                )))
                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", kaydet_btn)
                time.sleep(0.5)
                driver.execute_script("arguments[0].click();", kaydet_btn)
                time.sleep(4.0 + user_delay)

                try:
                    alert     = driver.switch_to.alert
                    alert_msg = alert.text
                    alert.accept()
                    self._log(f"🔔 Site Uyarısı: {alert_msg}", "system")
                    if any(k in alert_msg.lower() for k in ["zaten", "mevcut", "kayitli"]):
                        self._execute_document_upload_pipeline(driver, bekleme, row, docs_folder)
                        return "Success", personel_bilgisi
                except Exception:
                    pass

                pipeline_ok = self._execute_document_upload_pipeline(driver, bekleme, row, docs_folder)
                return ("Success" if pipeline_ok else "Failed_Docs"), personel_bilgisi

            except Exception as loop_err:
                self._log(
                    f"⚠️ Adım hatası (Deneme {deneme}/3): {str(loop_err)[:60]}", "warning"
                )
                time.sleep(3.0)
                try:
                    driver.get("https://wellcome.azurewebsites.net/pnlwell/")
                except Exception:
                    pass
                if deneme == 3:
                    return "Error: Operational Timeout.", personel_bilgisi

        return "Failed", personel_bilgisi

    # =====================================================================
    # --- ANA OTOMASYON DÖNGÜSÜ ---
    # =====================================================================

    def _run_automation_loop(
        self, df_data: pd.DataFrame, file_path: str, docs_folder: str
    ) -> None:
        lg      = LANG_PACK[self.current_lang]
        driver  = None
        results: List[Dict[str, str]] = []

        base_path = os.getcwd() if file_path.lower().startswith("http") else \
                    os.path.dirname(os.path.abspath(file_path))
        center_dir = os.path.join(base_path, "Sea_Fort_RPA_Operasyon_Merkezi")
        os.makedirs(center_dir, exist_ok=True)

        try:
            try:
                s = int(self.range_start_var.get()) if self.range_start_var.get().isdigit() else 0
                e = int(self.range_end_var.get())   if self.range_end_var.get().isdigit()   else len(df_data)
                df_data = df_data.iloc[s:e]
            except Exception:
                pass

            total = len(df_data)
            if total == 0:
                self._log("❌ İşlenecek kayıt yok!", "error")
                self.after(0, lambda: messagebox.showerror("Veri Hatası", "Filtrelenmiş kayıt bulunamadı!"))
                return

            success_count = error_count = 0
            self.after(0, lambda: (
                self.progress_bar.set(0),
                self.val_success.configure(text="0"),
                self.val_pending.configure(text=f"0 / {total}")
            ))

            driver  = self._create_driver()
            driver.get(config.LOGIN_URL)
            bekleme = WebDriverWait(driver, 15)

            if self.username_var.get().strip() and self.password_var.get().strip():
                if not self._handle_embedded_login(driver, bekleme):
                    self._log("❌ Giriş başarısız, otomasyon durduruluyor.", "error")
                    return
            else:
                self._log("⚠️ Giriş bilgileri boş, manuel giriş bekleniyor...", "warning")
                self.after(0, lambda: messagebox.showinfo("Giriş Onayı", "Giriş yapıp OK basın."))
                time.sleep(3.0)

            for index, (real_idx, row) in enumerate(df_data.iterrows()):
                if not self.is_running:
                    break

                personel_ismi = str(row.get('ADI SOYADI', '')).strip()
                if self._is_blacklisted(personel_ismi):
                    self._log(f"⚠️ Kara listede: {personel_ismi} → atlandı.", "warning")
                    continue

                self.pause_event.wait()

                if self.mode_upload_only:
                    personel_bilgisi = self._read_personel_from_row(row)
                    self._log(f"👤 Sadece Evrak: {personel_ismi}", "system")
                    ok         = self._execute_document_upload_pipeline(driver, bekleme, row, docs_folder)
                    status_res = "Success" if ok else "Failed_Docs"
                else:
                    status_res, personel_bilgisi = self._process_single_row(driver, row, docs_folder)

                if status_res == "Mükerrer veya Hatalı Veri":
                    error_count += 1
                    results.append({
                        "Personel Ad Soyad": personel_bilgisi.get("isim_soyisim", "?"),
                        "TC Kimlik No":  self._mask_sensitive_data(personel_bilgisi.get("tc", ""), True),
                        "Telefon No":    self._mask_sensitive_data(personel_bilgisi.get("telefon", ""), False),
                        "İşlem Durumu":  "Bozuk / Eksik Veri",
                        "Detay":         "TC veya telefon doğrulaması geçemedi.",
                        "Zaman":         datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    })
                    self._generate_report(results, center_dir)
                    continue

                results.append({
                    "Personel Ad Soyad": personel_ismi,
                    "TC Kimlik No":  self._mask_sensitive_data(personel_bilgisi["tc"], True),
                    "Telefon No":    self._mask_sensitive_data(personel_bilgisi["telefon"], False),
                    "İşlem Durumu":  "Başarılı" if status_res == "Success" else "Hata/Engel",
                    "Detay":         "" if status_res == "Success" else status_res,
                    "Zaman":         datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                })
                self._generate_report(results, center_dir)

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
                            except Exception as we:
                                self._log(f"⚠️ Excel güncelleme hatası: {we}", "warning")
                else:
                    error_count += 1

                self.processed_count_for_eta += 1
                kalan = total - (index + 1)
                time.sleep(0.05)
                self.after(0, lambda
                    p=((index + 1) / total),
                    s=str(success_count),
                    d=f"{error_count} / {kalan}",
                    e=self._calculate_eta(kalan) if kalan > 0 else "00:00": (
                        self.progress_bar.set(p),
                        self.val_success.configure(text=s),
                        self.val_pending.configure(text=d),
                        self.val_eta.configure(text=e),
                    )
                )
                time.sleep(1.8)

            if results and self.is_running and self.current_report_path:
                self._log(lg["report_gen"].format(os.path.basename(self.current_report_path)), "success")
                self._speak("Tüm operasyon başarıyla tamamlandı, raporunuz kaydedildi.")

        except Exception as main_err:
            self._log(f"[KRİTİK] Döngü hatası: {main_err}", "error")
        finally:
            if driver:
                try:
                    driver.quit()
                except Exception:
                    pass
            self._log("🏁 Otomasyon sonlandı.", "system")
            self.after(0, lambda: (
                setattr(self, 'is_running', False),
                self.start_button.configure(state="normal", text=LANG_PACK[self.current_lang]["start"], fg_color="#3B82F6"),
                self.upload_only_button.configure(state="normal", text=LANG_PACK[self.current_lang]["upload_only"], fg_color="#10B981"),
                self.pause_button.configure(state="disabled"),
            ))

    # =====================================================================
    # --- BAŞLATICI ---
    # =====================================================================

    def _start_automation_wrapper(self, upload_only: bool = False) -> None:
        lg = LANG_PACK[self.current_lang]
        if self.is_running:
            return

        excel_p = self.excel_file_path.get().strip()
        docs_p  = self.docs_folder_path.get().strip()
        if not excel_p or not docs_p:
            messagebox.showerror("Eksik Seçim", lg["no_data"])
            return

        self._log(lg["pre_flight_start"], "system")
        try:
            if excel_p.lower().startswith("http"):
                self._log("🌐 OneDrive bağlantısı, veri çekiliyor...", "warning")
                req = urllib.request.Request(excel_p, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req) as resp:
                    data = resp.read()
                df = pd.read_csv(io.BytesIO(data)) if "csv" in excel_p.lower() else pd.read_excel(io.BytesIO(data))
            else:
                df = pd.read_csv(excel_p) if excel_p.lower().endswith('.csv') else pd.read_excel(excel_p)
        except Exception as e:
            self._log(f"❌ Dosya okuma hatası: {str(e)[:60]}", "error")
            return

        df.columns = df.columns.str.strip()
        if 'YÜKLEME_DURUMU' not in df.columns:
            self._log("❌ 'YÜKLEME_DURUMU' sütunu bulunamadı!", "error")
            return

        df['YÜKLEME_DURUMU'] = pd.to_numeric(df['YÜKLEME_DURUMU'].astype(str).str.strip(), errors='coerce')
        self.current_full_df = df.copy()
        filtre_df = df[df['YÜKLEME_DURUMU'] == 1]

        if filtre_df.empty:
            self._log("⚠️ YÜKLEME_DURUMU=1 olan kayıt yok!", "warning")
            self.after(0, lambda: messagebox.showwarning("Veri Uyarısı", "YÜKLEME_DURUMU=1 olan kayıt bulunamadı!"))
            return

        self._log(f"📊 Toplam: {len(df)} | Yüklenecek: {len(filtre_df)}", "system")

        self.is_running       = True
        self.mode_upload_only = upload_only
        self.start_button.configure(state="disabled", text=lg["running"])
        self.upload_only_button.configure(state="disabled", text=lg["running"])
        self.pause_button.configure(state="normal")
        self.start_time              = time.time()
        self.processed_count_for_eta = 0
        self.current_report_path     = None
        self._save_settings()

        threading.Thread(
            target=self._run_automation_loop,
            args=(filtre_df, excel_p, docs_p),
            daemon=True
        ).start()

    def _start_automation(self)  -> None: self._start_automation_wrapper(upload_only=False)
    def _start_upload_only(self) -> None: self._start_automation_wrapper(upload_only=True)

    # =====================================================================
    # --- UI İNŞA ---
    # =====================================================================

    def _build_ui(self) -> None:
        top_bar = ctk.CTkFrame(self, fg_color="#1E293B", corner_radius=6, height=60)
        top_bar.pack(side="top", fill="x", padx=15, pady=(10, 5))
        top_bar.pack_propagate(False)

        tf = ctk.CTkFrame(top_bar, fg_color="transparent")
        tf.pack(side="left", padx=15, pady=8)
        self.title_label    = ctk.CTkLabel(tf, text="", font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"), text_color="#F8FAFC")
        self.title_label.pack(anchor="w")
        self.subtitle_label = ctk.CTkLabel(tf, text="", font=ctk.CTkFont(family="Segoe UI", size=10), text_color="#3B82F6")
        self.subtitle_label.pack(anchor="w")

        self.lang_dropdown = ctk.CTkOptionMenu(top_bar, values=["TR", "EN"], command=self._on_lang_change,
                                               width=70, height=26, fg_color="#0F172A", button_color="#3B82F6")
        self.lang_dropdown.pack(side="right", padx=15, pady=17)

        master = ctk.CTkFrame(self, fg_color="transparent")
        master.pack(side="top", fill="both", expand=True, padx=15, pady=5)

        left = ctk.CTkFrame(master, fg_color="transparent")
        left.pack(side="left", fill="both", expand=True, padx=(0, 10))

        lc = ctk.CTkFrame(left, fg_color="#1E293B", corner_radius=6)
        lc.pack(pady=4, fill="x")
        lc.grid_columnconfigure((0,1,2), weight=1)

        for col, (attr_lbl, attr_entry, var, show) in enumerate([
            ("lbl_comp_txt",  "company_entry",  self.company_code_var, ""),
            ("lbl_user_txt",  "username_entry", self.username_var,     ""),
            ("lbl_pass_txt",  "password_entry", self.password_var,     "*"),
        ]):
            fr = ctk.CTkFrame(lc, fg_color="transparent")
            fr.grid(row=0, column=col, padx=10, pady=8, sticky="ew")
            lbl = ctk.CTkLabel(fr, text="", font=ctk.CTkFont(size=10, weight="bold"), text_color="#94A3B8")
            lbl.pack(anchor="w")
            setattr(self, attr_lbl, lbl)
            kw  = {"show": show} if show else {}
            ent = ctk.CTkEntry(fr, textvariable=var, height=28, fg_color="#0F172A", **kw)
            ent.pack(fill="x")
            setattr(self, attr_entry, ent)

        for fg, attr_btn, attr_ent, var, cmd in [
            ("#3B82F6", "excel_file_button",  "excel_file_entry",  self.excel_file_path,  self._select_excel_file),
            ("#EAB308", "docs_folder_button", "docs_folder_entry", self.docs_folder_path, self._select_docs_folder),
        ]:
            card = ctk.CTkFrame(left, fg_color="#1E293B", corner_radius=6)
            card.pack(pady=4, fill="x")
            ent = ctk.CTkEntry(card, textvariable=var, height=32, fg_color="#0F172A")
            ent.pack(side="left", padx=10, pady=10, expand=True, fill="x")
            setattr(self, attr_ent, ent)
            btn = ctk.CTkButton(card, text="", command=cmd, width=100, height=32,
                                fg_color=fg, hover_color="#CA8A04" if fg=="#EAB308" else "#2563EB")
            btn.pack(side="right", padx=10, pady=10)
            setattr(self, attr_btn, btn)

        adv = ctk.CTkFrame(left, fg_color="#1E293B", corner_radius=6)
        adv.pack(pady=4, fill="x")
        adv.grid_columnconfigure((0,1,2), weight=1, uniform="eq")

        sw_fr = ctk.CTkFrame(adv, fg_color="transparent")
        sw_fr.grid(row=0, column=0, padx=15, pady=10, sticky="nw")
        self.cb_headless  = ctk.CTkCheckBox(sw_fr, text="", variable=self.headless_var,  fg_color="#3B82F6", checkbox_width=16, checkbox_height=16)
        self.cb_headless.pack(anchor="w", pady=2)
        self.sw_retry_cb  = ctk.CTkSwitch(sw_fr, text="", variable=self.retry_enabled,   progress_color="#3B82F6", switch_width=34, switch_height=16)
        self.sw_retry_cb.pack(anchor="w", pady=2)
        self.sw_ocr_cb    = ctk.CTkSwitch(sw_fr, text="", variable=self.ocr_enabled,     progress_color="#10B981", switch_width=34, switch_height=16, command=self._save_settings)
        self.sw_ocr_cb.pack(anchor="w", pady=2)

        rng_fr = ctk.CTkFrame(adv, fg_color="transparent")
        rng_fr.grid(row=0, column=1, padx=10, pady=10, sticky="n")
        self.lbl_range_txt = ctk.CTkLabel(rng_fr, text="", font=ctk.CTkFont(size=11, weight="bold"), text_color="#94A3B8")
        self.lbl_range_txt.pack(anchor="center")
        rb = ctk.CTkFrame(rng_fr, fg_color="transparent")
        rb.pack(anchor="center", pady=4)
        self.entry_start = ctk.CTkEntry(rb, textvariable=self.range_start_var, placeholder_text="Start", width=55, height=26, fg_color="#0F172A")
        self.entry_start.pack(side="left", padx=(0, 4))
        self.entry_end   = ctk.CTkEntry(rb, textvariable=self.range_end_var,   placeholder_text="End",   width=55, height=26, fg_color="#0F172A")
        self.entry_end.pack(side="left")

        thr_fr = ctk.CTkFrame(adv, fg_color="#1E293B", corner_radius=6)
        thr_fr.grid(row=0, column=2, padx=15, pady=10, sticky="ne")
        self.throttle_label = ctk.CTkLabel(thr_fr, text="", font=ctk.CTkFont(size=11, weight="bold"), text_color="#94A3B8")
        self.throttle_label.pack(anchor="e")
        self.speed_slider   = ctk.CTkSlider(thr_fr, from_=0.5, to=8.0, number_of_steps=15,
                                            variable=self.throttle_speed, progress_color="#3B82F6",
                                            height=14, width=150, command=lambda _: self._update_ui_texts())
        self.speed_slider.pack(anchor="e", pady=6)

        kpi = ctk.CTkFrame(left, fg_color="transparent")
        kpi.pack(pady=4, fill="x")
        kpi.grid_columnconfigure((0,1,2), weight=1)

        for col, (border, val_attr, lbl_attr, val_txt, val_color) in enumerate([
            ("#22C55E", "val_success", "kpi_lbl_succ", "0",    "#22C55E"),
            ("#3B82F6", "val_pending", "kpi_lbl_fail", "0/0",  "#3B82F6"),
            ("#EAB308", "val_eta",     "kpi_lbl_eta",  "--:--","#EAB308"),
        ]):
            card = ctk.CTkFrame(kpi, fg_color="#1E293B", border_color=border, border_width=1, corner_radius=6, height=65)
            card.grid(row=0, column=col, padx=(0 if col==0 else 6, 6 if col==2 else 0), sticky="ew")
            card.pack_propagate(False)
            lbl = ctk.CTkLabel(card, text="", font=ctk.CTkFont(size=9, weight="bold"), text_color="#94A3B8")
            lbl.pack(pady=(6,0), padx=10, anchor="w")
            setattr(self, lbl_attr, lbl)
            val = ctk.CTkLabel(card, text=val_txt, font=ctk.CTkFont(size=18 if col==0 else 16, weight="bold"), text_color=val_color)
            val.pack(pady=(0,6), padx=10, anchor="w")
            setattr(self, val_attr, val)

        self.progress_bar = ctk.CTkProgressBar(left, height=6, progress_color="#3B82F6", fg_color="#1E293B")
        self.progress_bar.set(0)
        self.progress_bar.pack(fill="x", pady=6)

        bf = ctk.CTkFrame(left, fg_color="transparent")
        bf.pack(pady=4, fill="x")
        bf.grid_columnconfigure((0,1), weight=2, uniform="eb")
        bf.grid_columnconfigure(2, weight=1)

        self.start_button       = ctk.CTkButton(bf, text="", fg_color="#3B82F6", hover_color="#2563EB", command=self._start_automation, height=38)
        self.start_button.grid(row=0, column=0, padx=(0,4), sticky="ew")
        self.upload_only_button = ctk.CTkButton(bf, text="", fg_color="#10B981", hover_color="#059669", command=self._start_upload_only, height=38)
        self.upload_only_button.grid(row=0, column=1, padx=(4,4), sticky="ew")
        self.pause_button       = ctk.CTkButton(bf, text="", fg_color="#64748B", command=self._toggle_pause, height=38, state="disabled")
        self.pause_button.grid(row=0, column=2, padx=(4,0), sticky="ew")

        log_card = ctk.CTkFrame(left, fg_color="#1E293B", corner_radius=6)
        log_card.pack(pady=6, fill="both", expand=True)
        self.log_text = tk.Text(log_card, bg="#0F172A", fg="#E2E8F0", font=("Consolas", 10),
                                wrap="word", bd=0, highlightthickness=0)
        self.log_text.pack(fill="both", expand=True, padx=8, pady=8)
        self.log_text.tag_config("normal",  foreground="#E2E8F0")
        self.log_text.tag_config("system",  foreground="#3B82F6")
        self.log_text.tag_config("success", foreground="#22C55E", font=("Consolas", 10, "bold"))
        self.log_text.tag_config("error",   foreground="#EF4444", font=("Consolas", 10, "bold"))
        self.log_text.tag_config("warning", foreground="#F59E0B")
        self.log_text.configure(state="disabled")

        # ===== SAĞ PANEL: EVRAK SÖZLÜĞÜ =====
        right = ctk.CTkFrame(master, fg_color="#1E293B", corner_radius=6, width=390)
        right.pack(side="right", fill="both", padx=(5, 0))
        right.pack_propagate(False)

        ctk.CTkLabel(right, text="📋 Evrak Numaralandırma Sözlüğü",
                     font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                     text_color="#F8FAFC").pack(pady=10, padx=15, anchor="w")

        self.map_textbox = tk.Text(right, bg="#0F172A", fg="#94A3B8",
                                   font=("Consolas", 9), wrap="word", bd=0, highlightthickness=0)
        self.map_textbox.pack(fill="both", expand=True, padx=15, pady=(0, 6))
        self.map_textbox.configure(state="disabled")

        add = ctk.CTkFrame(right, fg_color="#0F172A", corner_radius=6)
        add.pack(fill="x", padx=15, pady=12)

        ctk.CTkLabel(add, text="➕ Yeni Dosya/Evrak Ekle",
                     font=ctk.CTkFont(size=11, weight="bold"), text_color="#3B82F6"
                     ).grid(row=0, column=0, columnspan=2, padx=10, pady=5, sticky="w")

        ctk.CTkLabel(add, text="Dosya No:", font=ctk.CTkFont(size=10), text_color="#94A3B8"
                     ).grid(row=1, column=0, padx=10, sticky="w")
        self.entry_new_num = ctk.CTkEntry(add, textvariable=self.new_evrak_num,
                                          placeholder_text="Örn: 13", height=26, width=60, fg_color="#1E293B")
        self.entry_new_num.grid(row=1, column=1, padx=10, pady=4, sticky="w")

        ctk.CTkLabel(add, text="Sitedeki Adı:", font=ctk.CTkFont(size=10), text_color="#94A3B8"
                     ).grid(row=2, column=0, padx=10, sticky="w")
        self.entry_new_name = ctk.CTkEntry(add, textvariable=self.new_evrak_name,
                                           placeholder_text="Sitedeki tam dropdown metni...",
                                           height=26, width=240, fg_color="#1E293B")
        self.entry_new_name.grid(row=2, column=1, padx=10, pady=4, sticky="w")

        ctk.CTkButton(add, text="Sözlüğe Kaydet ve Güncelle",
                      font=ctk.CTkFont(size=11, weight="bold"),
                      fg_color="#3B82F6", hover_color="#2563EB",
                      command=self._add_custom_evrak, height=30
                      ).grid(row=3, column=0, columnspan=2, padx=10, pady=10, sticky="ew")


if __name__ == "__main__":
    try:
        app = WellcomeRPAApp()
        app.mainloop()
    except KeyboardInterrupt:
        os._exit(0)
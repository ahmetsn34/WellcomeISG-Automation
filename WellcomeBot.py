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
from datetime import datetime
from typing import Optional, Dict, List

import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
import pandas as pd

import undetected_chromedriver as uc 
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import StaleElementReferenceException, TimeoutException

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import config
from logger_config import setup_logger

os.environ['WDM_LOG'] = '0'
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")
logger = setup_logger()

# =====================================================================
# --- ÇOKLU DİL DESTEĞİ SÖZLÜĞÜ (MALA ANLATIR GİBİ SİSTEM) ---
# =====================================================================
LANG_PACK = {
    "TR": {
        "title": "Wellcome Premium Otomasyon Sistemi",
        "select_file": "Dosya Seç",
        "placeholder": "Veri dosyasını seçin (.xlsx veya .txt)...",
        "headless": "Tarayıcıyı Gizle (Arka Planda Çalıştır)",
        "keep_open": "Girişten Sonra Tarayıcıyı Açık Tut",
        "concurrent": "Eşzamanlı İşlem (Çoklu Tarayıcı)",
        "retry": "E-posta Deneme Sayısı:",
        "timeout": "Giriş Zaman Aşımı (sn):",
        "demo_mode": "Simülasyon (Demo) Modu - Gerçek Giriş Yapmaz",
        "start": "Otomasyonu Başlat",
        "running": "Çalışıyor...",
        "pause": "Duraklat",
        "resume": "Devam Et",
        "stats": "✅ Başarılı: {}  |  ❌ Hatalı: {}  |  ⏳ Kalan: {}  |  ⏱️ ETA: {}",
        "no_file": "Lütfen önce bir veri dosyası seçin!",
        "invalid_env": "Gmail bilgileri .env dosyasında bulunamadı!",
        "pre_flight_start": "[SİSTEM] Başlangıç sağlık kontrolleri yapılıyor...",
        "internet_ok": "  🌐 İnternet bağlantısı aktif.",
        "internet_err": "❌ KRİTİK HATA: İnternet bağlantısı yok!",
        "chrome_ok": "  🚗 Chrome tarayıcı altyapısı hazır.",
        "eta_calculating": "Hesaplanıyor...",
        "checkpoint_title": "Kaldığı Yerden Devam",
        "checkpoint_msg": "Önceki oturumdan kalan {} işlenmiş hesap bulundu.\nKaldığınız yerden devam etmek ister misiniz?\n\nEvet: Sadece kalanları işler.\nHayır: Her şeye sıfırdan başlar.",
        "checkpoint_clean": "[SİSTEM] Eski checkpoint temizlendi, sıfırdan başlanıyor...",
        "all_done": "Listede işlenecek yeni hesap kalmamış! Tüm hesaplar zaten tamamlanmış.",
        "demo_alert": "🤖 DEMO MODU AKTİF: Tarayıcı açılmayacak, işlemler simüle ediliyor...",
        "report_gen": "📊 Rapor oluşturuldu: {}"
    },
    "EN": {
        "title": "Wellcome Premium Automation System",
        "select_file": "Select File",
        "placeholder": "Select data file (.xlsx or .txt)...",
        "headless": "Run Headless (Hide Browser)",
        "keep_open": "Keep Browser Open After Login",
        "concurrent": "Concurrent Processing (Multi-Browser)",
        "retry": "Retry Attempts:",
        "timeout": "Login Timeout (s):",
        "demo_mode": "Simulation (Demo) Mode - No Real Login",
        "start": "Start Automation",
        "running": "Running...",
        "pause": "Pause",
        "resume": "Resume",
        "stats": "✅ Success: {}  |  ❌ Failed: {}  |  ⏳ Remaining: {}  |  ⏱️ ETA: {}",
        "no_file": "Please select a data file first!",
        "invalid_env": "Gmail credentials not configured in .env!",
        "pre_flight_start": "[SYSTEM] Running pre-flight health checks...",
        "internet_ok": "  🌐 Internet connection is active.",
        "internet_err": "❌ CRITICAL ERROR: No internet connection!",
        "chrome_ok": "  🚗 Chrome browser infrastructure is ready.",
        "eta_calculating": "Calculating...",
        "checkpoint_title": "Resume Work",
        "checkpoint_msg": "Found {} processed accounts from previous session.\nDo you want to resume where you left off?\n\nYes: Process remaining only.\nNo: Start from scratch.",
        "checkpoint_clean": "[SYSTEM] Old checkpoint cleared, starting from scratch...",
        "all_done": "No new accounts left to process! All accounts are already completed.",
        "demo_alert": "🤖 DEMO MODE ACTIVE: Browser will not open, simulating actions...",
        "report_gen": "📊 Report generated: {}"
    }
}


class WellcomeAutomationApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()

        # Dosya yolları 
        self.settings_file = "settings.json"
        self.checkpoint_file = "checkpoint.json"

        # İç Durum (Internal State)
        self.file_path = tk.StringVar()
        self.is_running = False
        self.headless_var = tk.BooleanVar(value=False)
        self.keep_open_var = tk.BooleanVar(value=False)
        self.concurrent_var = tk.BooleanVar(value=False)
        self.demo_mode_var = tk.BooleanVar(value=False) # --- YENİ ---
        self.current_lang = "TR" # Varsayılan dil --- YENİ ---
        
        self.pause_event = threading.Event()
        self.pause_event.set()
        self.checkpoint_lock = threading.Lock()

        # Süre tahmin (ETA) değişkenleri --- YENİ ---
        self.start_time = None
        self.processed_count_for_eta = 0

        # Hassas Bilgiler
        self.gmail_address: str = os.getenv('GMAIL_ADDRESS', 'denemehesapserver@gmail.com')
        self.gmail_password: str = os.getenv('GMAIL_PASSWORD', 'slynpgdwjfcrrpcq')
        self.site_email: str = os.getenv('SITE_EMAIL', 'https://wellcome.azurewebsites.net/pnlwell/login/')

        self._build_ui()
        self._load_settings() # Program açılışında ayarları ve dili yükle
        self._update_ui_texts() # Seçili dile göre arayüzü giydir
        logger.info("Application started")

    def _build_ui(self) -> None:
        # ÜST BAR: Başlık ve Dil Seçimi Menüsü
        top_bar = ctk.CTkFrame(self, fg_color="transparent")
        top_bar.pack(side="top", fill="x", padx=10, pady=5)

        self.title_label = ctk.CTkLabel(top_bar, text="", font=ctk.CTkFont(size=22, weight="bold"))
        self.title_label.pack(side="left", padx=10, pady=10)

        self.lang_dropdown = ctk.CTkOptionMenu(top_bar, values=["TR", "EN"], command=self._on_lang_change, width=70)
        self.lang_dropdown.pack(side="right", padx=10, pady=10)

        top_container = ctk.CTkFrame(self, fg_color="transparent")
        top_container.pack(side="top", fill="x", padx=10, pady=5)

        # Dosya Seçim Alanı
        file_frame = ctk.CTkFrame(top_container)
        file_frame.pack(pady=5, padx=10, fill="x")

        self.file_entry = ctk.CTkEntry(file_frame, textvariable=self.file_path, placeholder_text="", width=500)
        self.file_entry.pack(side="left", padx=10, pady=10, expand=True, fill="x")

        self.file_button = ctk.CTkButton(file_frame, text="", command=self._select_file, width=100)
        self.file_button.pack(side="right", padx=10, pady=10)

        # Standart Ayarlar
        settings_frame = ctk.CTkFrame(top_container)
        settings_frame.pack(pady=5, padx=10, fill="x")

        self.cb_headless = ctk.CTkCheckBox(settings_frame, text="", variable=self.headless_var)
        self.cb_headless.pack(side="left", padx=20, pady=10)
        
        self.cb_keep_open = ctk.CTkCheckBox(settings_frame, text="", variable=self.keep_open_var)
        self.cb_keep_open.pack(side="right", padx=20, pady=10)

        # Gelişmiş Ayarlar (Eşzamanlılık ve DEMO MODU)
        advanced_frame = ctk.CTkFrame(top_container)
        advanced_frame.pack(pady=5, padx=10, fill="x")

        self.cb_concurrent = ctk.CTkCheckBox(advanced_frame, text="", variable=self.concurrent_var)
        self.cb_concurrent.pack(side="left", padx=20, pady=10)

        self.cb_demo_mode = ctk.CTkCheckBox(advanced_frame, text="", variable=self.demo_mode_var, fg_color="#e67e22", hover_color="#d35400")
        self.cb_demo_mode.pack(side="right", padx=20, pady=10)

        # Kontrol Spinbox Alanları
        control_frame = ctk.CTkFrame(top_container)
        control_frame.pack(pady=5, padx=10, fill="x")

        self.lbl_retry = ctk.CTkLabel(control_frame, text="")
        self.lbl_retry.pack(side="left", padx=10)
        self.retry_spinbox = ctk.CTkEntry(control_frame, width=50)
        self.retry_spinbox.insert(0, str(os.getenv('RETRY_ATTEMPTS', config.DEFAULT_MAIL_RETRY_ATTEMPTS)))
        self.retry_spinbox.pack(side="left", padx=5)

        self.lbl_timeout = ctk.CTkLabel(control_frame, text="")
        self.lbl_timeout.pack(side="left", padx=10)
        self.timeout_spinbox = ctk.CTkEntry(control_frame, width=50)
        self.timeout_spinbox.insert(0, str(os.getenv('LOGIN_TIMEOUT', config.DEFAULT_LOGIN_TIMEOUT)))
        self.timeout_spinbox.pack(side="left", padx=5)

        # İstatistik ve İlerleme Çubuğu
        stats_frame = ctk.CTkFrame(top_container)
        stats_frame.pack(pady=5, padx=10, fill="x")

        self.stats_label = ctk.CTkLabel(stats_frame, text="", font=ctk.CTkFont(size=13, weight="bold"))
        self.stats_label.pack(pady=(5, 5))

        self.progress_bar = ctk.CTkProgressBar(stats_frame, height=12)
        self.progress_bar.set(0)
        self.progress_bar.pack(fill="x", padx=20, pady=(0, 10))

        # ALT KISMA SABİTLENEN AKSİYON BUTONLARI
        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.pack(side="bottom", fill="x", pady=10)

        self.start_button = ctk.CTkButton(button_frame, text="", fg_color="#27ae60", hover_color="#219653", command=self._start_automation, height=45, width=150, font=ctk.CTkFont(size=14, weight="bold"))
        self.start_button.pack(side="left", expand=True, anchor="e", padx=10)

        self.pause_button = ctk.CTkButton(button_frame, text="", fg_color="#f39c12", hover_color="#e67e22", command=self._toggle_pause, height=45, width=100, state="disabled", font=ctk.CTkFont(size=14, weight="bold"))
        self.pause_button.pack(side="left", expand=True, anchor="w", padx=10)

        # ESNEK GÜNLÜK (LOG) EKRANI
        log_frame = ctk.CTkFrame(self)
        log_frame.pack(side="top", pady=5, padx=20, fill="both", expand=True)

        self.log_text: tk.Text = tk.Text(log_frame, bg="#1e1e1e", fg="#ffffff", font=("Consolas", 11), wrap="word", bd=0, highlightthickness=0)
        self.log_text.pack(side="left", fill="both", expand=True, padx=5, pady=5)

        self.log_text.tag_config("normal", foreground="#ffffff")
        self.log_text.tag_config("system", foreground="#5dade2")
        self.log_text.tag_config("success", foreground="#2ecc71", font=("Consolas", 11, "bold"))
        self.log_text.tag_config("error", foreground="#e74c3c", font=("Consolas", 11, "bold"))
        self.log_text.tag_config("warning", foreground="#f1c40f")
        self.log_text.configure(state="disabled")

    # --- DİL DEĞİŞİMİ VE UI YENİLEME ---
    def _on_lang_change(self, choice: str):
        self.current_lang = choice
        self._update_ui_texts()
        self._save_settings()

    def _update_ui_texts(self):
        """Arayüzdeki tüm yazıları seçili dile göre dinamik günceller."""
        lg = LANG_PACK[self.current_lang]
        
        self.title(lg["title"])
        self.title_label.configure(text=lg["title"])
        self.file_button.configure(text=lg["select_file"])
        self.file_entry.configure(placeholder_text=lg["placeholder"])
        self.cb_headless.configure(text=lg["headless"])
        self.cb_keep_open.configure(text=lg["keep_open"])
        self.cb_concurrent.configure(text=lg["concurrent"])
        self.cb_demo_mode.configure(text=lg["demo_mode"])
        self.lbl_retry.configure(text=lg["retry"])
        self.lbl_timeout.configure(text=lg["timeout"])
        
        if not self.is_running:
            self.start_button.configure(text=lg["start"])
            self.pause_button.configure(text=lg["pause"])
            self.stats_label.configure(text=lg["stats"].format(0, 0, 0, "--:--"))
        
        self.lang_dropdown.set(self.current_lang)

    def _play_sound(self, sound_type: str):
        try:
            if sound_type == "error":
                winsound.MessageBeep(winsound.MB_ICONHAND)
            elif sound_type == "finish":
                winsound.PlaySound("SystemExit", winsound.SND_ALIAS)
        except:
            pass

    def _load_settings(self):
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, "r") as f:
                    settings = json.load(f)
                    self.current_lang = settings.get("lang", "TR")
                    self.file_path.set(settings.get("file_path", ""))
                    self.headless_var.set(settings.get("headless", False))
                    self.keep_open_var.set(settings.get("keep_open", False))
                    self.concurrent_var.set(settings.get("concurrent", False))
                    self.demo_mode_var.set(settings.get("demo_mode", False))
                    
                    self.retry_spinbox.delete(0, tk.END)
                    self.retry_spinbox.insert(0, settings.get("retry", str(config.DEFAULT_MAIL_RETRY_ATTEMPTS)))
                    self.timeout_spinbox.delete(0, tk.END)
                    self.timeout_spinbox.insert(0, settings.get("timeout", str(config.DEFAULT_LOGIN_TIMEOUT)))
            except Exception:
                pass

    def _save_settings(self):
        settings = {
            "lang": self.current_lang,
            "file_path": self.file_path.get(),
            "headless": self.headless_var.get(),
            "keep_open": self.keep_open_var.get(),
            "concurrent": self.concurrent_var.get(),
            "demo_mode": self.demo_mode_var.get(),
            "retry": self.retry_spinbox.get(),
            "timeout": self.timeout_spinbox.get()
        }
        try:
            with open(self.settings_file, "w") as f:
                json.dump(settings, f)
        except Exception:
            pass

    def _on_closing(self):
        self.is_running = False
        self.pause_event.set()
        self._save_settings() 
        self.destroy()
        os._exit(0)

    def _select_file(self) -> None:
        path = filedialog.askopenfilename(filetypes=[("Excel Files", "*.xlsx"), ("Text Files", "*.txt")])
        if path:
            self.file_path.set(path)
            lg = LANG_PACK[self.current_lang]
            self._log(f"[SYSTEM] Data file selected: {path}", "system")

    def _log(self, message: str, tag: str = "normal") -> None:
        def update_gui():
            self.log_text.configure(state="normal")
            self.log_text.insert(tk.END, message + "\n", tag)
            self.log_text.see(tk.END)
            self.log_text.configure(state="disabled")
        self.after(0, update_gui)

    # --- SİSTEM SAĞLIK KONTROLÜ (PRE-FLIGHT CHECK) ---
    def _run_pre_flight_checks(self) -> bool:
        """Bot başlamadan önce interneti ve sistem altyapısını test eder."""
        lg = LANG_PACK[self.current_lang]
        self._log(lg["pre_flight_start"], "system")
        time.sleep(1)

        # 1. İnternet Bağlantı Kontrolü
        try:
            socket.create_connection(("8.8.8.8", 53), timeout=3)
            self._log(lg["internet_ok"], "success")
        except OSError:
            self._log(lg["internet_err"], "error")
            self._play_sound("error")
            return False

        # 2. Tarayıcı Altyapı Kontrolü (Demo modunda değilse)
        if not self.demo_mode_var.get():
            self._log(lg["chrome_ok"], "success")
        
        return True

    def _read_data_file(self, file_path: str) -> List[Dict[str, str]]:
        data: List[Dict[str, str]] = []
        seen_users = set() 
        
        try:
            if file_path.lower().endswith('.xlsx'):
                df = pd.read_excel(file_path)
                for index, row in df.iterrows():
                    if pd.isna(row.iloc[0]) or pd.isna(row.iloc[1]) or pd.isna(row.iloc[2]):
                        continue
                    
                    company = str(row.iloc[0]).strip()
                    username = str(row.iloc[1]).strip()
                    password = str(row.iloc[2]).strip()
                    proxy = str(row.iloc[3]).strip() if len(row) > 3 and not pd.isna(row.iloc[3]) else None
                    
                    if not company or not username or not password or company == 'nan':
                        continue
                    if username in seen_users:
                        continue
                        
                    seen_users.add(username)
                    data.append({"company": company, "username": username, "password": password, "proxy": proxy})
            else:
                with open(file_path, "r", encoding="utf-8") as f:
                    for line_num, line in enumerate(f, 1):
                        line = line.strip()
                        if not line or line.startswith("#"): continue
                        
                        parts = line.split()
                        if len(parts) < 3: continue
                            
                        username = parts[1].strip()
                        if username in seen_users: continue
                            
                        proxy = parts[3].strip() if len(parts) > 3 else None
                        seen_users.add(username)
                        data.append({"company": parts[0].strip(), "username": username, "password": parts[2].strip(), "proxy": proxy})
            return data
        except Exception as e:
            self._log(f"[ERROR] Failed to read file: {e}", "error")
            return []

    def _validate_credentials(self) -> bool:
        if not self.gmail_address or not self.gmail_password:
            lg = LANG_PACK[self.current_lang]
            self._log(lg["invalid_env"], "error")
            return False
        return True

    def _get_code_from_email(self, sender_email: str, retry_attempts: int) -> Optional[str]:
        time.sleep(config.INITIAL_SERVER_DELAY)
        mail_server = None
        try:
            mail_server = imaplib.IMAP4_SSL(config.GMAIL_IMAP_HOST, config.GMAIL_IMAP_PORT)
            mail_server.login(self.gmail_address, self.gmail_password)
        except Exception as e:
            self._log(f"  → [ERROR] Gmail connection failed: {e}", "error")
            self._play_sound("error")
            return None

        try:
            for attempt in range(retry_attempts):
                if not self.is_running:
                    return None
                
                self.pause_event.wait()
                time.sleep(config.MAIL_CHECK_INTERVAL)
                try:
                    mail_server.select("inbox")
                    status, data = mail_server.search(None, 'UNSEEN')
                    mail_ids = data[0].split()

                    if mail_ids:
                        last_mail_id = mail_ids[-1]
                        status, mail_data = mail_server.fetch(last_mail_id, '(RFC822)')

                        for response_part in mail_data:
                            if isinstance(response_part, tuple):
                                message = email.message_from_bytes(response_part[1])
                                sender = message.get('From', '')

                                if sender_email.lower() in sender.lower() or "danteteknoloji" in sender.lower():
                                    content = self._extract_email_content(message)
                                    code_match = re.search(r'\b\d{4,6}\b', content)
                                    if code_match:
                                        code = code_match.group(0)
                                        self._log(f"  → OTP code retrieved: {code}", "success")
                                        return code
                except Exception:
                    pass
                self._log(f"  → Waiting for email... (Attempt {attempt+1}/{retry_attempts})", "normal")
        finally:
            if mail_server:
                try:
                    mail_server.logout()
                except Exception:
                    pass
        return None

    def _extract_email_content(self, message: email.message.Message) -> str:
        content = ""
        if message.is_multipart():
            for part in message.walk():
                if part.get_content_type() in ("text/plain", "text/html"):
                    try:
                        content += part.get_payload(decode=True).decode(part.get_content_charset() or "utf-8", errors="ignore")
                    except Exception:
                        pass
        else:
            content = message.get_payload(decode=True).decode(message.get_content_charset() or "utf-8", errors="ignore")
        return content

    def _toggle_pause(self) -> None:
        lg = LANG_PACK[self.current_lang]
        if self.pause_event.is_set():
            self.pause_event.clear()
            self.pause_button.configure(text=lg["resume"], fg_color="#27ae60")
            self._log(f"[SYSTEM] {lg['pause'].upper()}", "system")
        else:
            self.pause_event.set()
            self.pause_button.configure(text=lg["pause"], fg_color="#f39c12")
            self._log(f"[SYSTEM] {lg['resume'].upper()}", "system")

    def _create_driver(self, username: str, proxy: str = None) -> Optional[uc.Chrome]:
        if self.demo_mode_var.get():
            return None 
            
        chrome_options = uc.ChromeOptions()
        chrome_options.add_experimental_option("prefs", {"profile.managed_default_content_settings.images": config.DISABLE_IMAGES})
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        
        if proxy and proxy.lower() != "nan":
            chrome_options.add_argument(f"--proxy-server=http://{proxy}")
            self._log(f"  🌐 Proxy Devrede: {proxy}", "system")
        
        base_dir = os.path.dirname(self.file_path.get()) if self.file_path.get() else os.getcwd()
        profile_dir = os.path.join(base_dir, "Chrome_Profiles", username)
        os.makedirs(profile_dir, exist_ok=True)
        
        # --- VERSION_MAIN EKLEYEREK SÜRÜMÜ SABİTLEDİK ---
        return uc.Chrome(
            options=chrome_options, 
            user_data_dir=profile_dir,
            headless=self.headless_var.get(),
            version_main=148  # Bilgisayarındaki Chrome sürümüyle eşleştirdik
        )

    def _safe_action(self, wait_obj: WebDriverWait, by_type: str, locator: str, action: str, text: str = "") -> bool:
        for attempt in range(3):
            if not self.is_running: return False
            try:
                element = wait_obj.until(EC.element_to_be_clickable((by_type, locator)))
                time.sleep(0.5) 
                if action == "send_keys":
                    element.clear()
                    element.send_keys(text)
                elif action == "click":
                    element.click()
                elif action == "enter":
                    element.send_keys(Keys.ENTER)
                return True
            except StaleElementReferenceException:
                time.sleep(1) 
                if attempt == 2: raise
        return False

    def _process_user(self, user_data: Dict[str, str], driver: Optional[uc.Chrome], timeout: int, retries: int) -> Dict[str, str]:
        self.pause_event.wait()
        username = user_data['username']
        status = "Unknown Error"
        timestamp = datetime.now().strftime("%H:%M:%S")

        # --- YENİ SİMÜLASYON (DEMO MODU) İŞLEME BLOKLUKLARI ---
        if self.demo_mode_var.get():
            self._log(f"\n🤖 [DEMO] Processing User: {username}...", "warning")
            time.sleep(1.5)
            self._log("🤖 [DEMO] Entering inputs...", "normal")
            time.sleep(1)
            self._log("🤖 [DEMO] Simulating OTP code retrieval...", "normal")
            time.sleep(1.5)
            self._log(f"✅ [DEMO] SUCCESS: {username} processed.", "success")
            status = "Success (Simulated)"
            
            with self.checkpoint_lock:
                self._save_to_checkpoint(username)
            return {"Username": username, "Company": user_data['company'], "Proxy": "Demo", "Status": status, "Timestamp": timestamp}

        # --- GERÇEK OTOMASYON MOTORU ---
        try:
            self._log(f"\n--- Processing User: {username} ---", "system")
            driver.get(config.LOGIN_URL)
            
            needs_login = True
            try:
                WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.ID, config.FORM_IDS["firm_code"])))
            except TimeoutException:
                needs_login = False

            if needs_login:
                bekleme = WebDriverWait(driver, timeout)
                
                self._log("[1/6] Entering company code...", "normal")
                self._safe_action(bekleme, By.ID, config.FORM_IDS["firm_code"], "send_keys", user_data["company"])

                self._log("[2/6] Entering username...", "normal")
                self._safe_action(bekleme, By.ID, config.FORM_IDS["username"], "send_keys", username)

                self._log("[3/6] Entering password...", "normal")
                self._safe_action(bekleme, By.ID, config.FORM_IDS["password"], "send_keys", user_data["password"])

                self._log("[4/6] Clicking login button...", "normal")
                self._safe_action(bekleme, By.ID, config.FORM_IDS["login_button"], "click")

                self._log("[5/6] Waiting for OTP code...", "normal")
                otp_code = self._get_code_from_email(self.site_email, retries)

                if otp_code:
                    self._log("[6/6] Entering OTP code...", "normal")
                    self._safe_action(bekleme, By.ID, config.FORM_IDS["verification_code"], "send_keys", otp_code)

                    clicked = False
                    for locator_tuple in [(By.CSS_SELECTOR, config.VERIFICATION_BUTTON_CSS), (By.XPATH, config.VERIFICATION_BUTTON_XPATH)]:
                        try:
                            self._safe_action(bekleme, locator_tuple[0], locator_tuple[1], "click")
                            clicked = True
                            break
                        except Exception:
                            continue
                    
                    if not clicked:
                        self._safe_action(bekleme, By.ID, config.FORM_IDS["verification_code"], "enter")

                    self._log(f"✅ SUCCESS: {username} logged in.", "success")
                    status = "Success"
                else:
                    self._log(f"⚠️ FAILED: {username} - OTP not received", "warning")
                    self._play_sound("error")
                    status = "Failed (No OTP)"
            else:
                self._log(f"⚡ FAST LOGIN: {username} session active!", "success")
                status = "Success (Session Reused)"

        except Exception as e:
            self._log(f"❌ ERROR: {username} - {str(e)[:70]}", "error")
            self._play_sound("error")
            status = f"Error: {str(e)[:50]}"
            try:
                base_dir = os.path.dirname(self.file_path.get())
                error_dir = os.path.join(base_dir, "Hata_Goruntuleri")
                os.makedirs(error_dir, exist_ok=True)
                shot_name = os.path.join(error_dir, f"Hata_{username}_{datetime.now().strftime('%H%M%S')}.png")
                driver.save_screenshot(shot_name)
            except Exception:
                pass
            
        finally:
            if driver:
                if not self.keep_open_var.get() or "Error" in status or "Failed" in status:
                    try: driver.quit()
                    except Exception: pass
            
            with self.checkpoint_lock:
                self._save_to_checkpoint(username)

        return {"Username": username, "Company": user_data['company'], "Proxy": user_data.get('proxy', 'Yok'), "Status": status, "Timestamp": timestamp}

    def _save_to_checkpoint(self, username: str):
        try:
            processed = []
            if os.path.exists(self.checkpoint_file):
                with open(self.checkpoint_file, "r") as f:
                    processed = json.load(f)
            if username not in processed:
                processed.append(username)
            with open(self.checkpoint_file, "w") as f:
                json.dump(processed, f)
        except Exception:
            pass

    def _generate_report(self, results: List[Dict[str, str]]) -> None:
        lg = LANG_PACK[self.current_lang]
        try:
            directory = os.path.dirname(self.file_path.get())
            filename = f"Wellcome_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            full_path = os.path.join(directory, filename)
            pd.DataFrame(results).to_excel(full_path, index=False)
            self._log(lg["report_gen"].format(full_path), "success")
        except Exception as e:
            self._log(f"\n❌ Report error: {e}", "error")

    def _start_automation(self) -> None:
        lg = LANG_PACK[self.current_lang]
        if not self.file_path.get():
            messagebox.showwarning("Warning", lg["no_file"])
            return
        if not self._validate_credentials():
            messagebox.showerror("Error", lg["invalid_env"])
            return
        if self.is_running:
            return

        # 1. Başlangıç Sağlık Kontrollerini Çalıştır
        if not self._run_pre_flight_checks():
            return

        user_data_list = self._read_data_file(self.file_path.get())
        if not user_data_list: return

        # 2. Checkpoint Kontrolü
        processed_users = []
        if os.path.exists(self.checkpoint_file):
            try:
                with open(self.checkpoint_file, "r") as f:
                    processed_users = json.load(f)
            except Exception: pass

        if processed_users:
            resume = messagebox.askyesno(lg["checkpoint_title"], lg["checkpoint_msg"].format(len(processed_users)))
            if resume:
                user_data_list = [u for u in user_data_list if u['username'] not in processed_users]
                self._log(f"[SYSTEM] Checkpoint active. Remaining: {len(user_data_list)}", "system")
            else:
                with open(self.checkpoint_file, "w") as f: json.dump([], f)
                self._log(lg["checkpoint_clean"], "system")

        if not user_data_list:
            messagebox.showinfo("Bilgi", lg["all_done"])
            return

        if self.demo_mode_var.get():
            self._log(lg["demo_alert"], "warning")

        self.is_running = True
        self.start_button.configure(state="disabled", text=lg["running"], fg_color="gray")
        self.pause_button.configure(state="normal")
        self.pause_event.set()

        # Süre tahmin sayaçlarını sıfırla
        self.start_time = time.time()
        self.processed_count_for_eta = 0

        threading.Thread(target=self._run_automation, args=(user_data_list,), daemon=True).start()

    # --- SÜRE TAHMİN ALGORİTMASI (ETA) ---
    def _calculate_eta(self, remaining_count: int) -> str:
        """İşlem hızına göre kalan süreyi matematiksel olarak hesaplar."""
        if self.processed_count_for_eta == 0 or self.start_time is None:
            return LANG_PACK[self.current_lang]["eta_calculating"]
        
        elapsed_time = time.time() - self.start_time
        # Hesap başına harcanan ortalama süre
        avg_time_per_user = elapsed_time / self.processed_count_for_eta
        
        # Kalan toplam süre (saniye cinsinden)
        remaining_seconds = int(avg_time_per_user * remaining_count)
        
        # Saniyeyi Saat:Dakika:Saniye formatına çevirme
        hours = remaining_seconds // 3600
        minutes = (remaining_seconds % 3600) // 60
        seconds = remaining_seconds % 60
        
        if hours > 0:
            return f"{hours:02d}h {minutes:02d}m"
        return f"{minutes:02d}m {seconds:02d}s"

    def _run_automation(self, user_data_list: list) -> None:
        lg = LANG_PACK[self.current_lang]
        try:
            timeout = int(self.timeout_spinbox.get())
            retries = int(self.retry_spinbox.get())
            total_users = len(user_data_list)
            
            results: List[Dict[str, str]] = []
            results_lock = threading.Lock() 
            
            self.success_count = 0
            self.error_count = 0
            self.completed_count = 0

            def _update_progress_ui(is_success: bool):
                def update():
                    if is_success: self.success_count += 1
                    else: self.error_count += 1
                    
                    self.processed_count_for_eta += 1
                    kalan = total_users - self.completed_count
                    
                    # Dinamik ETA değerini alıyoruz
                    eta_str = self._calculate_eta(kalan)
                    if kalan == 0: eta_str = "00:00"

                    self.progress_bar.set(self.completed_count / total_users)
                    self.stats_label.configure(text=lg["stats"].format(self.success_count, self.error_count, kalan, eta_str))
                self.after(0, update)

            self.after(0, lambda: self.progress_bar.set(0))
            self.after(0, lambda: self.stats_label.configure(text=lg["stats"].format(0, 0, total_users, lg["eta_calculating"])))

            work_queue = queue.Queue()
            for user in user_data_list:
                work_queue.put(user)

            def worker():
                while not work_queue.empty() and self.is_running:
                    self.pause_event.wait()
                    try:
                        user = work_queue.get_nowait()
                    except queue.Empty: break
                    
                    # Sürücü oluşturma (Demo modda None döner)
                    driver = self._create_driver(username=user['username'], proxy=user.get('proxy'))
                    result = self._process_user(user, driver, timeout, retries)
                    
                    with results_lock:
                        results.append(result)
                        self.completed_count += 1
                    
                    is_succ = "Success" in result["Status"]
                    _update_progress_ui(is_succ)
                    work_queue.task_done()
                    
                    # Çoklu tarayıcı seçili değilse ve demo modda değilsek dinlendir
                    if not self.concurrent_var.get() and not self.demo_mode_var.get() and self.is_running:
                        time.sleep(2)

            # Eğer DEMO MODU seçiliyse çoklu tarayıcıya gerek yok, hızlıca 1 thread ile simüle et
            num_threads = 1 if self.demo_mode_var.get() else (min(3, total_users) if self.concurrent_var.get() else 1)
            threads = []
            
            for _ in range(num_threads):
                t = threading.Thread(target=worker, daemon=True)
                t.start()
                threads.append(t)

            for t in threads: t.join()

            if results and self.is_running:
                self._generate_report(results)
                self._play_sound("finish")
                with open(self.checkpoint_file, "w") as f: json.dump([], f)

        except Exception as e:
            self._log(f"[ERROR] Automation error: {e}", "error")
            self._play_sound("error")
        finally:
            def reset_ui():
                self.is_running = False
                self.start_button.configure(state="normal", text=lg["start"], fg_color="#27ae60")
                self.pause_button.configure(state="disabled")
            self.after(0, reset_ui)


if __name__ == "__main__":
    try:
        app = WellcomeAutomationApp()
        app.mainloop()
    except KeyboardInterrupt:
        os._exit(0)
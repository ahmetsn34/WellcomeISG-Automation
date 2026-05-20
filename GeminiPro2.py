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
import winsound  # --- SES SİSTEMİ İÇİN EKLENDİ ---
from datetime import datetime
from typing import Optional, Dict, List
from concurrent.futures import ThreadPoolExecutor, as_completed

import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
import pandas as pd

# --- UNDETECTED CHROMEDRIVER (GÖRÜNMEZLİK PELERİNİ) EKLENDİ ---
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


class WellcomeAutomationApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()

        self.title(config.TITLE)
        self.geometry(f"{config.WINDOW_WIDTH}x{config.WINDOW_HEIGHT + 100}")
        self.minsize(800, 680) 
        self.resizable(True, True) 
        self.protocol("WM_DELETE_WINDOW", self._on_closing)

        # Dosya yolları 
        self.settings_file = "settings.json"
        self.checkpoint_file = "checkpoint.json"

        # İç Durum (Internal State)
        self.file_path = tk.StringVar()
        self.is_running = False
        self.headless_var = tk.BooleanVar(value=False)
        self.keep_open_var = tk.BooleanVar(value=False)
        self.concurrent_var = tk.BooleanVar(value=False)
        self.pause_event = threading.Event()
        self.pause_event.set()
        self.checkpoint_lock = threading.Lock()

        # Hassas Bilgiler
        self.gmail_address: str = os.getenv('GMAIL_ADDRESS', 'denemehesapserver@gmail.com')
        self.gmail_password: str = os.getenv('GMAIL_PASSWORD', 'slynpgdwjfcrrpcq')
        self.site_email: str = os.getenv('SITE_EMAIL', 'https://wellcome.azurewebsites.net/pnlwell/login/')

        self._build_ui()
        self._load_settings() 
        logger.info("Application started")

    def _build_ui(self) -> None:
        top_container = ctk.CTkFrame(self, fg_color="transparent")
        top_container.pack(side="top", fill="x", padx=10, pady=5)

        title_label = ctk.CTkLabel(top_container, text="Wellcome Premium Automation", font=ctk.CTkFont(size=22, weight="bold"))
        title_label.pack(pady=10)

        file_frame = ctk.CTkFrame(top_container)
        file_frame.pack(pady=5, padx=10, fill="x")

        self.file_entry = ctk.CTkEntry(file_frame, textvariable=self.file_path, placeholder_text="Select data file (.xlsx or .txt)...", width=500)
        self.file_entry.pack(side="left", padx=10, pady=10, expand=True, fill="x")

        file_button = ctk.CTkButton(file_frame, text="Select File", command=self._select_file, width=100)
        file_button.pack(side="right", padx=10, pady=10)

        settings_frame = ctk.CTkFrame(top_container)
        settings_frame.pack(pady=5, padx=10, fill="x")

        ctk.CTkCheckBox(settings_frame, text="Run Headless (Hide Browser)", variable=self.headless_var).pack(side="left", padx=20, pady=10)
        ctk.CTkCheckBox(settings_frame, text="Keep Browser Open After Login", variable=self.keep_open_var).pack(side="right", padx=20, pady=10)

        advanced_frame = ctk.CTkFrame(top_container)
        advanced_frame.pack(pady=5, padx=10, fill="x")

        ctk.CTkCheckBox(advanced_frame, text="Concurrent Processing (Multi-Browser)", variable=self.concurrent_var).pack(side="left", padx=20, pady=10)

        control_frame = ctk.CTkFrame(top_container)
        control_frame.pack(pady=5, padx=10, fill="x")

        ctk.CTkLabel(control_frame, text="Retry Attempts:").pack(side="left", padx=10)
        self.retry_spinbox = ctk.CTkEntry(control_frame, width=50)
        self.retry_spinbox.insert(0, str(os.getenv('RETRY_ATTEMPTS', config.DEFAULT_MAIL_RETRY_ATTEMPTS)))
        self.retry_spinbox.pack(side="left", padx=5)

        ctk.CTkLabel(control_frame, text="Login Timeout (s):").pack(side="left", padx=10)
        self.timeout_spinbox = ctk.CTkEntry(control_frame, width=50)
        self.timeout_spinbox.insert(0, str(os.getenv('LOGIN_TIMEOUT', config.DEFAULT_LOGIN_TIMEOUT)))
        self.timeout_spinbox.pack(side="left", padx=5)

        stats_frame = ctk.CTkFrame(top_container)
        stats_frame.pack(pady=5, padx=10, fill="x")

        self.stats_label = ctk.CTkLabel(stats_frame, text="✅ Başarılı: 0  |  ❌ Hatalı: 0  |  ⏳ Kalan: 0", font=ctk.CTkFont(size=13, weight="bold"))
        self.stats_label.pack(pady=(5, 5))

        self.progress_bar = ctk.CTkProgressBar(stats_frame, height=12)
        self.progress_bar.set(0)
        self.progress_bar.pack(fill="x", padx=20, pady=(0, 10))

        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.pack(side="bottom", fill="x", pady=10)

        self.start_button = ctk.CTkButton(button_frame, text="Start Automation", fg_color="#27ae60", hover_color="#219653", command=self._start_automation, height=45, width=150, font=ctk.CTkFont(size=14, weight="bold"))
        self.start_button.pack(side="left", expand=True, anchor="e", padx=10)

        self.pause_button = ctk.CTkButton(button_frame, text="Pause", fg_color="#f39c12", hover_color="#e67e22", command=self._toggle_pause, height=45, width=100, state="disabled", font=ctk.CTkFont(size=14, weight="bold"))
        self.pause_button.pack(side="left", expand=True, anchor="w", padx=10)

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

    def _play_sound(self, sound_type: str):
        """İşlemlere göre Windows uyarı sesleri çalar."""
        try:
            if sound_type == "error":
                winsound.MessageBeep(winsound.MB_ICONHAND) # Kritik Hata sesi
            elif sound_type == "success":
                pass # Her hesapta çalması rahatsız edebilir diye boş bıraktık
            elif sound_type == "finish":
                winsound.PlaySound("SystemExit", winsound.SND_ALIAS) # Bitiş sesi
        except:
            pass

    def _load_settings(self):
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, "r") as f:
                    settings = json.load(f)
                    self.file_path.set(settings.get("file_path", ""))
                    self.headless_var.set(settings.get("headless", False))
                    self.keep_open_var.set(settings.get("keep_open", False))
                    self.concurrent_var.set(settings.get("concurrent", False))
                    
                    self.retry_spinbox.delete(0, tk.END)
                    self.retry_spinbox.insert(0, settings.get("retry", str(config.DEFAULT_MAIL_RETRY_ATTEMPTS)))
                    self.timeout_spinbox.delete(0, tk.END)
                    self.timeout_spinbox.insert(0, settings.get("timeout", str(config.DEFAULT_LOGIN_TIMEOUT)))
                self._log("[SYSTEM] Eski ayarlar başarıyla yüklendi.", "system")
            except Exception:
                pass

    def _save_settings(self):
        settings = {
            "file_path": self.file_path.get(),
            "headless": self.headless_var.get(),
            "keep_open": self.keep_open_var.get(),
            "concurrent": self.concurrent_var.get(),
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
            self._log(f"[SYSTEM] Data file selected: {path}", "system")

    def _log(self, message: str, tag: str = "normal") -> None:
        def update_gui():
            self.log_text.configure(state="normal")
            self.log_text.insert(tk.END, message + "\n", tag)
            self.log_text.see(tk.END)
            self.log_text.configure(state="disabled")
        self.after(0, update_gui)

    # --- YENİ EKLENEN PROXY OKUMA SİSTEMİ ---
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
                    # 4. Sütun varsa Proxy olarak al, yoksa None yap
                    proxy = str(row.iloc[3]).strip() if len(row) > 3 and not pd.isna(row.iloc[3]) else None
                    
                    if not company or not username or not password or company == 'nan':
                        continue
                        
                    if username in seen_users:
                        continue
                        
                    seen_users.add(username)
                    data.append({"company": company, "username": username, "password": password, "proxy": proxy})
                    
                self._log(f"[SYSTEM] Excel'den {len(data)} hesap okundu (Proxy destekli).", "system")
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
                self._log(f"[SYSTEM] Text dosyasından {len(data)} hesap okundu (Proxy destekli).", "system")
            return data
        except Exception as e:
            self._log(f"[ERROR] Failed to read file: {e}", "error")
            return []

    def _validate_credentials(self) -> bool:
        if not self.gmail_address or not self.gmail_password:
            self._log("[ERROR] Gmail credentials not found. Check your .env file.", "error")
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
        if self.pause_event.is_set():
            self.pause_event.clear()
            self.pause_button.configure(text="Resume", fg_color="#27ae60")
            self._log("[SYSTEM] Automation paused", "system")
        else:
            self.pause_event.set()
            self.pause_button.configure(text="Pause", fg_color="#f39c12")
            self._log("[SYSTEM] Automation resumed", "system")

    # --- YENİ MİMARİ: UNDETECTED CHROMEDRIVER & PROXY ---
    def _create_driver(self, username: str, proxy: str = None) -> uc.Chrome:
        chrome_options = uc.ChromeOptions()
        chrome_options.add_experimental_option("prefs", {"profile.managed_default_content_settings.images": config.DISABLE_IMAGES})
        
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        
        # PROXY ENTEGRASYONU
        if proxy and proxy.lower() != "nan":
            chrome_options.add_argument(f"--proxy-server=http://{proxy}")
            self._log(f"  🌐 Proxy Devrede: {proxy}", "system")
        
        base_dir = os.path.dirname(self.file_path.get()) if self.file_path.get() else os.getcwd()
        profile_dir = os.path.join(base_dir, "Chrome_Profiles", username)
        os.makedirs(profile_dir, exist_ok=True)
        
        # uc.Chrome, webdriver_manager'a ihtiyaç duymadan kendini günceller ve gizler
        return uc.Chrome(
            options=chrome_options, 
            user_data_dir=profile_dir,
            headless=self.headless_var.get()
        )

    def _safe_action(self, wait_obj: WebDriverWait, by_type: str, locator: str, action: str, text: str = "") -> bool:
        for attempt in range(3):
            if not self.is_running:
                return False
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
                if attempt == 2:
                    raise
        return False

    def _process_user(self, user_data: Dict[str, str], driver: uc.Chrome, timeout: int, retries: int) -> Dict[str, str]:
        self.pause_event.wait()
        username = user_data['username']
        status = "Unknown Error"
        timestamp = datetime.now().strftime("%H:%M:%S")

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

                    self._log(f"✅ SUCCESS: {username} logged in and session saved.", "success")
                    status = "Success"
                else:
                    self._log(f"⚠️ FAILED: {username} - OTP not received", "warning")
                    self._play_sound("error")
                    status = "Failed (No OTP)"
            else:
                self._log(f"⚡ FAST LOGIN: {username} session active! Otomatik giriş yapıldı.", "success")
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
                self._log(f"📸 Hata görüntüsü kaydedildi.", "warning")
            except Exception:
                pass
            
        finally:
            if not self.keep_open_var.get() or "Error" in status or "Failed" in status:
                try:
                    driver.quit()
                except Exception:
                    pass
            
            with self.checkpoint_lock:
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

        return {"Username": username, "Company": user_data['company'], "Proxy": user_data.get('proxy', 'Yok'), "Status": status, "Timestamp": timestamp}

    def _generate_report(self, results: List[Dict[str, str]]) -> None:
        try:
            directory = os.path.dirname(self.file_path.get())
            filename = f"Wellcome_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            full_path = os.path.join(directory, filename)
            pd.DataFrame(results).to_excel(full_path, index=False)
            self._log(f"\n📊 Report generated: {full_path}", "success")
        except Exception as e:
            self._log(f"\n❌ Report generation error: {e}", "error")

    def _start_automation(self) -> None:
        if not self.file_path.get():
            messagebox.showwarning("Warning", "Please select a data file first!")
            return
        if not self._validate_credentials():
            messagebox.showerror("Error", "Gmail credentials not configured. Fix your .env file.")
            return
        if self.is_running:
            return

        user_data_list = self._read_data_file(self.file_path.get())
        if not user_data_list:
            return

        processed_users = []
        if os.path.exists(self.checkpoint_file):
            try:
                with open(self.checkpoint_file, "r") as f:
                    processed_users = json.load(f)
            except Exception:
                pass

        if processed_users:
            resume = messagebox.askyesno("Kaldığı Yerden Devam", f"Önceki oturumdan kalan {len(processed_users)} işlenmiş hesap bulundu.\nKaldığınız yerden devam etmek ister misiniz?\n\nEvet: Sadece kalanları işler.\nHayır: Her şeye sıfırdan başlar.")
            if resume:
                user_data_list = [u for u in user_data_list if u['username'] not in processed_users]
                self._log(f"[SYSTEM] Checkpoint devrede: Kalan {len(user_data_list)} kullanıcı işleniyor...", "system")
            else:
                with open(self.checkpoint_file, "w") as f:
                    json.dump([], f)
                self._log("[SYSTEM] Eski checkpoint temizlendi, sıfırdan başlanıyor...", "system")

        if not user_data_list:
            messagebox.showinfo("Bilgi", "Listede işlenecek yeni hesap kalmamış. Tüm hesaplar zaten tamamlanmış!")
            return

        self.is_running = True
        self.start_button.configure(state="disabled", text="Running...", fg_color="gray")
        self.pause_button.configure(state="normal")
        self.pause_event.set()

        threading.Thread(target=self._run_automation, args=(user_data_list,), daemon=True).start()

    def _run_automation(self, user_data_list: list) -> None:
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
                    if is_success:
                        self.success_count += 1
                    else:
                        self.error_count += 1
                    
                    kalan = total_users - self.completed_count
                    self.progress_bar.set(self.completed_count / total_users)
                    self.stats_label.configure(text=f"✅ Başarılı: {self.success_count}  |  ❌ Hatalı: {self.error_count}  |  ⏳ Kalan: {kalan}")
                self.after(0, update)

            self.after(0, lambda: self.progress_bar.set(0))
            self.after(0, lambda: self.stats_label.configure(text=f"✅ Başarılı: 0  |  ❌ Hatalı: 0  |  ⏳ Kalan: {total_users}"))

            self._log("[SYSTEM] Initializing Undetected ChromeDriver...", "system")

            work_queue = queue.Queue()
            for user in user_data_list:
                work_queue.put(user)

            def worker():
                while not work_queue.empty() and self.is_running:
                    self.pause_event.wait()
                    
                    try:
                        user = work_queue.get_nowait()
                    except queue.Empty:
                        break
                    
                    # --- UC ile Driver Başlatma ---
                    driver = self._create_driver(username=user['username'], proxy=user.get('proxy'))
                    
                    result = self._process_user(user, driver, timeout, retries)
                    
                    with results_lock:
                        results.append(result)
                        self.completed_count += 1
                    
                    is_succ = "Success" in result["Status"]
                    _update_progress_ui(is_succ)
                    
                    work_queue.task_done()
                    
                    if not self.concurrent_var.get() and self.is_running:
                        time.sleep(2)

            num_threads = min(3, total_users) if self.concurrent_var.get() else 1
            threads = []
            
            for _ in range(num_threads):
                t = threading.Thread(target=worker, daemon=True)
                t.start()
                threads.append(t)

            for t in threads:
                t.join()

            if results and self.is_running:
                self._generate_report(results)
                # BİTİŞ SESİ VE CHECKPOINT SIFIRLAMA
                self._play_sound("finish")
                with open(self.checkpoint_file, "w") as f:
                    json.dump([], f)

        except Exception as e:
            self._log(f"[ERROR] Automation error: {e}", "error")
            self._play_sound("error")
        finally:
            def reset_ui():
                self.is_running = False
                self.start_button.configure(state="normal", text="Start Automation", fg_color="#27ae60")
                self.pause_button.configure(state="disabled")
            self.after(0, reset_ui)


if __name__ == "__main__":
    try:
        app = WellcomeAutomationApp()
        app.mainloop()
    except KeyboardInterrupt:
        os._exit(0)
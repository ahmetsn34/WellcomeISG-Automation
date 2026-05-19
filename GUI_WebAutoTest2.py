"""
Wellcome Advanced Automation GUI v3.0

A secure, feature-rich web automation tool for Wellcome login processes with:
- Environment-based credential management
- Configurable retry logic and timeouts
- File-based logging
- Progress tracking
- Input validation
"""

import imaplib
import email
import re
import time
import os
import threading
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

import config
from logger_config import setup_logger

# Load environment variables
if load_dotenv:
    load_dotenv()

os.environ['WDM_LOG'] = '0'
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

logger = setup_logger()


class WellcomeAutomationApp(ctk.CTk):
    """Main GUI application for Wellcome automation."""

    def __init__(self) -> None:
        """Initialize the application."""
        super().__init__()

        self.title(config.TITLE)
        self.geometry(f"{config.WINDOW_WIDTH}x{config.WINDOW_HEIGHT}")
        self.resizable(False, False)

        # Internal State
        self.file_path: tk.StringVar = tk.StringVar()
        self.is_running: bool = False
        self.headless_var: tk.BooleanVar = tk.BooleanVar(value=False)
        self.keep_open_var: tk.BooleanVar = tk.BooleanVar(value=False)
        self.concurrent_var: tk.BooleanVar = tk.BooleanVar(value=False)
        self.pause_event: threading.Event = threading.Event()
        self.pause_event.set()  # Start in "not paused" state

        # Configuration
        self.retry_attempts: int = int(os.getenv('RETRY_ATTEMPTS', config.DEFAULT_MAIL_RETRY_ATTEMPTS))
        self.login_timeout: int = int(os.getenv('LOGIN_TIMEOUT', config.DEFAULT_LOGIN_TIMEOUT))
        self.mail_timeout: int = int(os.getenv('MAIL_WAIT_TIMEOUT', config.DEFAULT_MAIL_WAIT_TIMEOUT))

        # Gmail credentials from environment
        self.gmail_address: str = os.getenv('GMAIL_ADDRESS', 'denemehesapserver@gmail.com')
        self.gmail_password: str = os.getenv('GMAIL_PASSWORD', 'slynpgdwjfcrrpcq')
        self.site_email: str = os.getenv('SITE_EMAIL', 'https://wellcome.azurewebsites.net/pnlwell/login/')

        self._build_ui()
        logger.info("Application started")

    def _build_ui(self) -> None:
        """Build the user interface."""
        # Title
        title_label = ctk.CTkLabel(
            self,
            text="Wellcome Advanced Automation System",
            font=ctk.CTkFont(size=22, weight="bold")
        )
        title_label.pack(pady=15)

        # File Selection Frame
        file_frame = ctk.CTkFrame(self)
        file_frame.pack(pady=10, padx=20, fill="x")

        self.file_entry = ctk.CTkEntry(
            file_frame,
            textvariable=self.file_path,
            placeholder_text="Select data file (.txt)...",
            width=500
        )
        self.file_entry.pack(side="left", padx=10, pady=10)

        file_button = ctk.CTkButton(file_frame, text="Select File", command=self._select_file, width=100)
        file_button.pack(side="right", padx=10, pady=10)

        # Settings Frame
        settings_frame = ctk.CTkFrame(self)
        settings_frame.pack(pady=10, padx=20, fill="x")

        ctk.CTkCheckBox(
            settings_frame,
            text="Run Headless (Hide Browser)",
            variable=self.headless_var
        ).pack(side="left", padx=20, pady=10)

        ctk.CTkCheckBox(
            settings_frame,
            text="Keep Browser Open After Login",
            variable=self.keep_open_var
        ).pack(side="right", padx=20, pady=10)

        # Advanced Settings Frame
        advanced_frame = ctk.CTkFrame(self)
        advanced_frame.pack(pady=10, padx=20, fill="x")

        ctk.CTkCheckBox(
            advanced_frame,
            text="Concurrent Processing",
            variable=self.concurrent_var
        ).pack(side="left", padx=20, pady=10)

        # Retry/Timeout Controls
        control_frame = ctk.CTkFrame(self)
        control_frame.pack(pady=5, padx=20, fill="x")

        ctk.CTkLabel(control_frame, text="Retry Attempts:").pack(side="left", padx=10)
        retry_spinbox = ctk.CTkEntry(control_frame, width=50)
        retry_spinbox.insert(0, str(self.retry_attempts))
        retry_spinbox.pack(side="left", padx=5)

        ctk.CTkLabel(control_frame, text="Login Timeout (s):").pack(side="left", padx=10)
        timeout_spinbox = ctk.CTkEntry(control_frame, width=50)
        timeout_spinbox.insert(0, str(self.login_timeout))
        timeout_spinbox.pack(side="left", padx=5)

        # Live Log Display
        log_label = ctk.CTkLabel(self, text="Live Execution Logs:", font=ctk.CTkFont(size=13, weight="bold"))
        log_label.pack(anchor="w", padx=30, pady=(5, 0))

        log_frame = ctk.CTkFrame(self)
        log_frame.pack(pady=5, padx=20, fill="both", expand=True)

        self.log_text: tk.Text = tk.Text(
            log_frame,
            bg="#1e1e1e",
            fg="#ffffff",
            font=("Consolas", 11),
            wrap="word",
            bd=0,
            highlightthickness=0
        )
        self.log_text.pack(side="left", fill="both", expand=True, padx=5, pady=5)

        # Configure log tags
        self.log_text.tag_config("normal", foreground="#ffffff")
        self.log_text.tag_config("system", foreground="#5dade2")
        self.log_text.tag_config("success", foreground="#2ecc71", font=("Consolas", 11, "bold"))
        self.log_text.tag_config("error", foreground="#e74c3c", font=("Consolas", 11, "bold"))
        self.log_text.tag_config("warning", foreground="#f1c40f")
        self.log_text.configure(state="disabled")

        # Control Buttons Frame
        button_frame = ctk.CTkFrame(self)
        button_frame.pack(pady=15)

        self.start_button = ctk.CTkButton(
            button_frame,
            text="Start Automation",
            fg_color="#27ae60",
            hover_color="#219653",
            command=self._start_automation,
            height=45,
            width=150,
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.start_button.pack(side="left", padx=10)

        self.pause_button = ctk.CTkButton(
            button_frame,
            text="Pause",
            fg_color="#f39c12",
            hover_color="#e67e22",
            command=self._toggle_pause,
            height=45,
            width=100,
            state="disabled",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.pause_button.pack(side="left", padx=10)

    def _select_file(self) -> None:
        """Open file dialog to select data file."""
        path = filedialog.askopenfilename(filetypes=[("Text Files", "*.txt")])
        if path:
            self.file_path.set(path)
            self._log(f"[SYSTEM] Data file selected: {path}", "system")
            logger.info(f"File selected: {path}")

    def _log(self, message: str, tag: str = "normal") -> None:
        """Log message to GUI text widget."""
        self.log_text.configure(state="normal")
        self.log_text.insert(tk.END, message + "\n", tag)
        self.log_text.see(tk.END)
        self.log_text.configure(state="disabled")

    def _read_data_file(self, file_path: str) -> List[Dict[str, str]]:
        """
        Read user data from text file.

        Format: COMPANY_CODE USERNAME PASSWORD (space-separated)

        Args:
            file_path: Path to data file

        Returns:
            List of dictionaries with 'company', 'username', 'password' keys
        """
        data: List[Dict[str, str]] = []
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue

                    parts = line.split()
                    if len(parts) < 3:
                        self._log(f"[WARNING] Line {line_num}: Invalid format (skipped)", "warning")
                        logger.warning(f"Line {line_num} has invalid format: {line}")
                        continue

                    data.append({
                        "company": parts[0],
                        "username": parts[1],
                        "password": parts[2]
                    })

            self._log(f"[INFO] Successfully loaded {len(data)} users from file", "system")
            logger.info(f"Loaded {len(data)} users from {file_path}")
            return data
        except Exception as e:
            self._log(f"[ERROR] Failed to read file: {e}", "error")
            logger.error(f"Error reading file: {e}")
            return []

    def _validate_credentials(self) -> bool:
        """Validate Gmail credentials are available."""
        if not self.gmail_address or not self.gmail_password:
            self._log(
                "[ERROR] Gmail credentials not found. Set GMAIL_ADDRESS and GMAIL_PASSWORD in .env file",
                "error"
            )
            logger.error("Gmail credentials missing")
            return False
        return True

    def _get_code_from_email(
        self,
        gmail_address: str,
        gmail_password: str,
        sender_email: str,
        retry_attempts: int
    ) -> Optional[str]:
        """
        Retrieve OTP code from Gmail inbox.

        Args:
            gmail_address: Gmail account address
            gmail_password: Gmail app password
            sender_email: Expected sender email address
            retry_attempts: Number of retry attempts

        Returns:
            OTP code if found, None otherwise
        """
        self._log("  → Waiting for server security delay (3s)...", "normal")
        time.sleep(config.INITIAL_SERVER_DELAY)

        self._log("  → Connecting to Gmail inbox...", "normal")
        mail_server = None
        try:
            mail_server = imaplib.IMAP4_SSL(config.GMAIL_IMAP_HOST, config.GMAIL_IMAP_PORT)
            mail_server.login(gmail_address, gmail_password)
        except Exception as e:
            self._log(f"  → [ERROR] Gmail connection failed: {e}", "error")
            logger.error(f"Gmail login failed: {e}")
            return None

        try:
            for attempt in range(retry_attempts):
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
                                        logger.info(f"OTP code found: {code}")
                                        return code
                except Exception as e:
                    logger.debug(f"Error during mail check attempt {attempt + 1}: {e}")

                elapsed = (attempt + 1) * config.MAIL_CHECK_INTERVAL
                self._log(f"  → Waiting for email... ({elapsed}/{self.mail_timeout}s)", "normal")

        except Exception as e:
            self._log(f"  → [ERROR] Mail reading error: {e}", "error")
            logger.error(f"Mail reading error: {e}")
        finally:
            if mail_server:
                try:
                    mail_server.logout()
                    self._log("  → Gmail connection closed securely", "system")
                except Exception:
                    pass

        return None

    def _extract_email_content(self, message: email.message.Message) -> str:
        """Extract text content from email message."""
        content = ""
        try:
            if message.is_multipart():
                for part in message.walk():
                    if part.get_content_type() in ("text/plain", "text/html"):
                        try:
                            content += part.get_payload(decode=True).decode(
                                part.get_content_charset() or "utf-8",
                                errors="ignore"
                            )
                        except Exception:
                            pass
            else:
                content = message.get_payload(decode=True).decode(
                    message.get_content_charset() or "utf-8",
                    errors="ignore"
                )
        except Exception as e:
            logger.debug(f"Error extracting email content: {e}")
        return content

    def _toggle_pause(self) -> None:
        """Toggle pause state during automation."""
        if self.pause_event.is_set():
            self.pause_event.clear()
            self.pause_button.configure(text="Resume", fg_color="#27ae60")
            self._log("[SYSTEM] Automation paused", "system")
            logger.info("Automation paused")
        else:
            self.pause_event.set()
            self.pause_button.configure(text="Pause", fg_color="#f39c12")
            self._log("[SYSTEM] Automation resumed", "system")
            logger.info("Automation resumed")

    def _process_user(
        self,
        user_data: Dict[str, str],
        driver: webdriver.Chrome,
        timestamp: str
    ) -> Dict[str, str]:
        """
        Process single user login.

        Args:
            user_data: Dictionary with company, username, password
            driver: Selenium WebDriver instance
            timestamp: Current timestamp

        Returns:
            Dictionary with login result information
        """
        self.pause_event.wait()  # Wait if paused

        username = user_data['username']
        status = "Unknown Error"

        try:
            self._log(f"\n--- Processing User: {username} ---", "system")

            # Clear cookies and navigate
            driver.delete_all_cookies()
            driver.get(config.LOGIN_URL)
            self._log("[1/6] Page loading...", "normal")
            time.sleep(config.PAGE_LOAD_TIMEOUT)

            # Enter company code
            self._log("[2/6] Entering company code...", "normal")
            bekleme = WebDriverWait(driver, self.login_timeout)
            firm_input = bekleme.until(
                EC.presence_of_element_located((By.ID, config.FORM_IDS["firm_code"]))
            )
            firm_input.clear()
            firm_input.send_keys(user_data["company"])
            time.sleep(3)

            # Enter username with retry
            self._log("[3/6] Entering username...", "normal")
            for _ in range(config.ELEMENT_INTERACTION_RETRIES):
                try:
                    username_input = bekleme.until(
                        EC.element_to_be_clickable((By.ID, config.FORM_IDS["username"]))
                    )
                    username_input.clear()
                    username_input.send_keys(user_data["username"])
                    break
                except Exception:
                    time.sleep(config.ELEMENT_INTERACTION_DELAY)

            # Enter password with retry
            self._log("[4/6] Entering password...", "normal")
            for _ in range(config.ELEMENT_INTERACTION_RETRIES):
                try:
                    password_input = bekleme.until(
                        EC.element_to_be_clickable((By.ID, config.FORM_IDS["password"]))
                    )
                    password_input.clear()
                    password_input.send_keys(user_data["password"])
                    break
                except Exception:
                    time.sleep(config.ELEMENT_INTERACTION_DELAY)

            # Click login button
            self._log("[5/6] Clicking login button...", "normal")
            bekleme.until(
                EC.element_to_be_clickable((By.ID, config.FORM_IDS["login_button"]))
            ).click()

            # Wait for OTP code
            self._log("[6/6] Waiting for OTP code...", "normal")
            otp_code = self._get_code_from_email(
                self.gmail_address,
                self.gmail_password,
                self.site_email,
                self.retry_attempts
            )

            if otp_code:
                code_input = bekleme.until(
                    EC.presence_of_element_located((By.ID, config.FORM_IDS["verification_code"]))
                )
                code_input.clear()
                code_input.send_keys(otp_code)
                time.sleep(1)

                # Try to click verification button
                clicked = False
                try:
                    verify_btn = bekleme.until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, config.VERIFICATION_BUTTON_CSS))
                    )
                    verify_btn.click()
                    clicked = True
                except Exception:
                    pass

                if not clicked:
                    try:
                        verify_btn = bekleme.until(
                            EC.element_to_be_clickable((By.XPATH, config.VERIFICATION_BUTTON_XPATH))
                        )
                        verify_btn.click()
                        clicked = True
                    except Exception:
                        pass

                if not clicked:
                    code_input.send_keys(Keys.ENTER)

                if self.keep_open_var.get():
                    self._log(f"✅ SUCCESS: {username} logged in. Browser kept open.", "success")
                    status = "Success (Browser Open)"
                else:
                    time.sleep(5)
                    self._log(f"✅ SUCCESS: {username} logged in.", "success")
                    status = "Success"
            else:
                self._log(f"⚠️ FAILED: {username} - OTP code not received", "warning")
                status = "Failed (No OTP)"

        except Exception as e:
            self._log(f"❌ ERROR: {username} - {str(e)[:100]}", "error")
            logger.error(f"Error processing {username}: {e}")
            status = f"Error: {str(e)[:50]}"

        return {
            "Username": user_data['username'],
            "Company": user_data['company'],
            "Status": status,
            "Timestamp": timestamp
        }

    def _generate_report(self, results: List[Dict[str, str]]) -> None:
        """
        Generate Excel report of results.

        Args:
            results: List of result dictionaries
        """
        try:
            directory = os.path.dirname(self.file_path.get())
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"Wellcome_Report_{timestamp}.xlsx"
            full_path = os.path.join(directory, filename)

            df = pd.DataFrame(results)
            df.to_excel(full_path, index=False)

            self._log(f"\n📊 Report generated: {full_path}", "success")
            logger.info(f"Report saved: {full_path}")
        except Exception as e:
            self._log(f"\n❌ Report generation error: {e}", "error")
            logger.error(f"Report generation failed: {e}")

    def _start_automation(self) -> None:
        """Start the automation process."""
        if not self.file_path.get():
            messagebox.showwarning("Warning", "Please select a data file first!")
            self._log("[WARNING] No data file selected", "warning")
            return

        if not self._validate_credentials():
            messagebox.showerror("Error", "Gmail credentials not configured. See .env file.")
            return

        if self.is_running:
            return

        self.is_running = True
        self.start_button.configure(state="disabled", text="Running...", fg_color="gray")
        self.pause_button.configure(state="normal")
        self.pause_event.set()

        threading.Thread(target=self._run_automation, daemon=True).start()

    def _run_automation(self) -> None:
        """Execute the automation process."""
        try:
            user_data_list = self._read_data_file(self.file_path.get())
            if not user_data_list:
                return

            timestamp = datetime.now().strftime("%H:%M:%S")
            chrome_options = Options()
            chrome_options.add_experimental_option(
                "prefs",
                {"profile.managed_default_content_settings.images": config.DISABLE_IMAGES}
            )

            if self.headless_var.get():
                chrome_options.add_argument("--headless")
                chrome_options.add_argument("--window-size=1920,1080")
                self._log("[SYSTEM] Running in headless mode", "system")
                logger.info("Headless mode enabled")

            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)

            results: List[Dict[str, str]] = []

            try:
                if self.concurrent_var.get() and len(user_data_list) > 1:
                    self._log("[SYSTEM] Concurrent processing enabled", "system")
                    logger.info("Using concurrent processing")
                    # Sequential fallback for safety (concurrent drivers can be unstable)
                    for i, user in enumerate(user_data_list, 1):
                        self.pause_event.wait()
                        self._log(f"\n[Progress] Processing user {i}/{len(user_data_list)}", "system")
                        result = self._process_user(user, driver, timestamp)
                        results.append(result)
                else:
                    for i, user in enumerate(user_data_list, 1):
                        self.pause_event.wait()
                        self._log(f"\n[Progress] Processing user {i}/{len(user_data_list)}", "system")
                        result = self._process_user(user, driver, timestamp)
                        results.append(result)
                        if self.keep_open_var.get() and result["Status"].startswith("Success"):
                            break

                if results:
                    self._generate_report(results)

            finally:
                if not self.keep_open_var.get():
                    driver.quit()

        except Exception as e:
            self._log(f"[ERROR] Automation error: {e}", "error")
            logger.error(f"Critical error in automation: {e}")
        finally:
            self.is_running = False
            self.start_button.configure(state="normal", text="Start Automation", fg_color="#27ae60")
            self.pause_button.configure(state="disabled")
            logger.info("Automation completed")

if __name__ == "__main__":
    app = WellcomeAutomationApp()
    app.mainloop()

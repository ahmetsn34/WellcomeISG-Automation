# WellcomeRPA AI: Enterprise OHS Document Automation Suite

<p align="center">
  <a href="README.md">🇹🇷 Türkçe</a> | 
  <a href="README_EN.md">🇺🇸 English</a>
</p>

---

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/)
[![License: Proprietary](https://img.shields.io/badge/License-Proprietary-red.svg)](https://github.com/)
[![Framework: CustomTkinter](https://img.shields.io/badge/UI-CustomTkinter-orange.svg)](https://github.com/TomSchimansky/CustomTkinter)
[![Automation: Selenium Stealth](https://img.shields.io/badge/Automation-Undetected__Chromedriver-green.svg)](https://github.com/ultrafunkamsterdam/undetected-chromedriver)

## 📋 Overview

**Wellcome RPA AI** is a professional, GUI-based desktop automation suite engineered to eliminate high-volume, repetitive human workflows. It automatically parses local data sources (Excel/CSV) and securely executes end-to-end personnel registration and mandatory Occupational Health and Safety (OHS) document filing on the **Wellcome (Azure-based) portal**.

By integrating advanced **PDF parsing (pdfplumber)**, an intelligent **classification engine**, and robust browser safety shields, this application reduces human error rates to zero and slashes administrative overhead by up to 90%.

---

## 📜 Dev Note: The "Vibe Coding" Chronicles

Let’s be honest for a second. As an old-school minded developer at heart, I’ve spent years believing that "real software" is only crafted by typing every single line of code manually, staring at compiler errors until your eyes bleed.

But times change, and staying stubborn doesn't pay the bills or keep up with the speed of business.

This entire project was built using pure **Vibe Coding**. Instead of getting bogged down in boilerplate code, I sat down, orchestrated the architecture, guided the high-level logic, and let an LLM assistant do the heavy lifting of spitting out thousands of lines of precise UI and automation scripts. 

Is it hand-crafted artisan code? *Nope.* 
Does it perfectly solve a tedious corporate problem that used to take hours, executing with 100% precision? *Absolutely.*

Welcome to the new era, where being an efficient engineer means vibing with the right AI tools to deliver bulletproof software at lightning speed.

---

## 🚀 Engine Highlights & Technical Shields

Geliştirme sürecinde Selenium ve web mimarisinin getirdiği kronik web portal kararsızlıkları şu asgari zırhlarla kökten çözülmüştür:

### 🧠 Intelligent Classification (AI Override Engine)
A common problem in document processing is cross-contamination (e.g., a Criminal Record being misidentified as an ID because it contains a "TR Identity Number" string). 
*   **The Shield:** The engine implements a custom scoring matrix with **Absolute Filename Dominance (+1000 weight)**. If specific patterns exist in the filename, content scanning is safely bypassed to guarantee 100% classification accuracy.

### 🛡️ Postback & Stale Element Mitigation
The Wellcome platform utilizes heavy asynchronous Ajax postbacks that constantly cause active browser elements to expire or detach from the live DOM.
*   **The Shield:** A **"Stale Element Armor"** retry infrastructure. The pipeline catches `StaleElementReferenceException` in real-time, pauses for 0.5s, and re-fetches the freshest active DOM node seamlessly without losing pipeline progress.

### 🔤 Adaptive Turkish Character Handler
Case conversions and special character mismatches (such as `İ, Ş, Ğ`) frequently break search and filter inputs within Form element containers.
*   **The Shield:** A pre-processing character-agnostic abstraction layer standardizes all text metrics before executing Select2 injection queries, ensuring correct record-locking every single time.

---

## 🛠️ Built With

*   **GUI Mimarisi:** CustomTkinter / Tkinter (Modern desktop workspace)
*   **Automation Infrastructure:** Undetected Chromedriver & Selenium WebDriver
*   **Data Katmanı:** Pandas (Excel and CSV ingestion engine)
*   **OCR & Extraction:** PDFPlumber & Pytesseract Engine

---

## 📦 Getting Started & Deployment

### Run Pre-Compiled Binary (No Installation Required)
For non-technical operational staff, a pre-compiled standalone executable is provided for immediate deployment.

## 📦 Getting Started & Deployment

### Run Pre-Compiled Binary (No Installation Required)
For non-technical operational staff, a pre-compiled standalone executable is provided for immediate deployment.

1.  Navigate to the **[Latest Releases](https://github.com/ahmetsn34/WellcomeISG.exe)** page.
2.  Download the compiled `.exe` file.
3.  Launch the application and follow the operational instructions below.

### Developer Environment Setup
If you wish to run or modify the source code locally:

```bash
# Install environment dependencies
pip install undetected-chromedriver pillow pytesseract pdfplumber pandas openpyxl customtkinter

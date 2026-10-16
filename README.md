# Wellcome ISG Automation

![Python](https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white)
![CustomTkinter](https://img.shields.io/badge/UI-CustomTkinter-2563EB?style=flat-square)
![Selenium](https://img.shields.io/badge/Automation-Selenium-43B02A?style=flat-square&logo=selenium&logoColor=white)
![Windows](https://img.shields.io/badge/Platform-Windows-0078D4?style=flat-square)

A Python desktop application for personnel registration and occupational health and safety (OHS / ISG) document workflows on the Wellcome portal. It combines a CustomTkinter interface, spreadsheet processing, browser automation, and document text extraction.

## What it does

- Reads personnel records from Excel or CSV and selects rows marked for processing.
- Validates Turkish identity numbers and normalizes phone numbers and Turkish characters.
- Matches personnel to local document folders by name.
- Classifies documents using filename rules, PDF text extraction, and OCR for PDFs and images.
- Automates portal forms and document uploads through Selenium and `undetected-chromedriver`.
- Provides Turkish and English interface text, progress reporting, pause controls, and Excel result reports.

Document classification uses keyword rules; its accuracy depends on the files and naming conventions. Portal automation also depends on the current portal layout and account permissions.

## Run from source

The documented entry point is [`ProjectWell.py`](WellcomeISG-Automation-main/ProjectWell.py). The other Python scripts in that directory are separate variants.

### Prerequisites

- Windows, Python with Tkinter, and Google Chrome.
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) with the `tur` and `eng` language data. The script currently expects `C:\Program Files\Tesseract-OCR\tesseract.exe`; adjust that assignment in `ProjectWell.py` if needed.
- Poppler command-line tools available on `PATH` for PDF-to-image conversion. See the [pdf2image installation guide](https://pdf2image.readthedocs.io/en/latest/installation.html).
- Access to the intended Wellcome environment and permission to manage the relevant personnel records.

### Install and launch

Run these commands in PowerShell:

```powershell
git clone https://github.com/ahmetsn34/WellcomeISG-Automation.git
cd WellcomeISG-Automation
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install customtkinter pandas openpyxl selenium undetected-chromedriver pdfplumber pdf2image pytesseract Pillow
cd WellcomeISG-Automation-main
..\.venv\Scripts\python.exe ProjectWell.py
```

Optional packages: `pyttsx3` enables spoken notifications; `python-dotenv` enables the script's `.env` loading hook.

Before connecting, review `config.py`, the deployment-specific defaults in `ProjectWell.py`, and the local settings. The browser fallback currently specifies Chrome major version `148`; it may need adjustment for your installed browser. Dependency versions are not pinned in this repository.

## Prepare the input

Use an `.xlsx` or `.csv` file with these column names:

| Column | Purpose |
| --- | --- |
| `ADI SOYADI` | Full name, also used to match the document folder |
| `T.C. Kimlik Numarası` | Turkish identity number |
| `TELEFON NUMARASI` | Phone number |
| `GÖREVİ` | Job role; defaults to `Personel` if empty |
| `YÜKLEME_DURUMU` | Set to `1` for rows to process |

Keep each person's documents in a separate folder named to match `ADI SOYADI`, under the selected document directory. Use descriptive filenames to help the keyword classifier identify document types.

1. Select the spreadsheet and document directory in the application.
2. Enter the intended account details, then start processing.
3. Complete login or verification when prompted.
4. Check the application log, generated report, and uploaded records.

For local input files, successful rows are written back with `YÜKLEME_DURUMU` set to `0`. Keep a working copy of the spreadsheet. The application saves connection details, including the password, in a local `settings.json`; keep this file and personnel documents out of version control.

## Project status

This repository contains the source implementation and several development variants. Setup depends on local OCR tools and the target portal environment. Check the configuration and uploaded records in your environment; portal changes can require updates to the browser automation.


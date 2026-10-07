@echo off
REM ============================================================
REM  SAFETY AUDITOR — Windows Quickstart Script
REM  Run this ONCE to set up and get your paper results
REM  Usage: Double-click quickstart.bat OR run from cmd
REM ============================================================

setlocal enabledelayedexpansion
cd /d "%~dp0"

echo.
echo ============================================================
echo  Neuro-Symbolic Safety Auditing Framework — Quickstart
echo  Amrita Vishwa Vidyapeetham M.Tech Research
echo ============================================================
echo.

REM ── STEP 1: Python check ────────────────────────────────────
echo [1/7] Checking Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python not found. Install Python 3.11+ from https://python.org
    pause & exit /b 1
)
python --version
echo OK

REM ── STEP 2: Install dependencies ───────────────────────────
echo.
echo [2/7] Installing Python dependencies...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo ERROR: pip install failed. Check requirements.txt and your internet connection.
    pause & exit /b 1
)
echo OK

REM ── STEP 3: Tesseract check ─────────────────────────────────
echo.
echo [3/7] Checking Tesseract OCR...
if exist "C:\Program Files\Tesseract-OCR\tesseract.exe" (
    echo OK - Tesseract found at C:\Program Files\Tesseract-OCR\
) else (
    echo WARNING: Tesseract not found at default path.
    echo Download from: https://github.com/UB-Mannheim/tesseract/wiki
    echo P^&ID OCR will be skipped if Tesseract is missing.
)

REM ── STEP 4: Ollama check ────────────────────────────────────
echo.
echo [4/7] Checking Ollama and Qwen 2.5...
ollama list >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Ollama not running.
    echo  1. Download Ollama from https://ollama.ai
    echo  2. Start Ollama (it runs in the system tray)
    echo  3. Run this script again
    pause & exit /b 1
)
echo Ollama is running. Pulling qwen2.5 model...
ollama pull qwen2.5
echo OK

REM ── STEP 5: Generate benchmark ──────────────────────────────
echo.
echo [5/7] Generating 50 synthetic benchmark packages...
python run_pipeline.py benchmark --n 50 --output benchmark/corpus --seed 42
if %errorlevel% neq 0 (
    echo ERROR: Benchmark generation failed. Check error above.
    pause & exit /b 1
)
echo OK - 50 packages created in benchmark\corpus\

REM ── STEP 6: Run evaluation ──────────────────────────────────
echo.
echo [6/7] Running full evaluation + ablation study...
echo This will take a while (LLM runs on each package). Go get coffee.
echo.
python run_pipeline.py evaluate --corpus benchmark/corpus --output evaluation/results --ablation
if %errorlevel% neq 0 (
    echo ERROR: Evaluation failed. Check error above.
    pause & exit /b 1
)
echo OK

REM ── STEP 7: Show results ────────────────────────────────────
echo.
echo [7/7] YOUR RESULTS:
echo ============================================================
if exist "evaluation\results\main\metrics_table.csv" (
    type evaluation\results\main\metrics_table.csv
) else (
    echo metrics_table.csv not found - check evaluation\results\
)
echo.
if exist "evaluation\results\ablation_conclusion.txt" (
    echo ABLATION STUDY:
    type evaluation\results\ablation_conclusion.txt
)
echo ============================================================
echo.
echo ============================================================
echo  NEXT STEPS TO PUBLISH IN IEEE:
echo ============================================================
echo.
echo  1. FILL IN THE PAPER:
echo     Open paper\main.tex in any LaTeX editor.
echo     Search for \RESULT{ and replace each placeholder with your numbers above.
echo.
echo  2. RUN ON SCHNEIDER ELECTRIC DATA:
echo     Drop your PDF in data\schneider_electric\
echo     Run: python run_pipeline.py audit --input data\schneider_electric\YOUR.pdf --real-data
echo     Open output\YOUR\audit_report.html to see findings.
echo     Add these findings to Section V-D of the paper.
echo.
echo  3. COMPILE THE PAPER:
echo     Install MiKTeX or TeX Live: https://miktex.org/download
echo     Open paper\ in TeXstudio or VS Code with LaTeX Workshop
echo     Compile: pdflatex main.tex then bibtex main then pdflatex twice
echo.
echo  4. FILL AUTHOR INFO:
echo     Open paper\main.tex and replace:
echo       [YOUR EMAIL] with your student email
echo       [SURNAME]    with Dr. Raviteja's surname
echo       [GUIDE EMAIL] with Dr. Raviteja's email
echo     All literature references are already complete.
echo.
echo  5. SUBMIT:
echo     Read paper\HOW_TO_SUBMIT.md for the IEEE submission checklist.
echo.
echo  6. GET GUIDE APPROVAL:
echo     Send paper draft to Dr. Raviteja BEFORE submitting.
echo.
pause

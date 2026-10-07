@echo off
REM ============================================================
REM  Compile IEEE LaTeX paper (run from project root or paper/)
REM  Requires: MiKTeX or TeX Live — https://miktex.org/download
REM ============================================================
setlocal
cd /d "%~dp0"

echo [1/4] Running pdflatex (pass 1)...
pdflatex -interaction=nonstopmode main.tex
if %errorlevel% neq 0 (
    echo ERROR: pdflatex pass 1 failed. Check main.tex for errors.
    pause & exit /b 1
)

echo [2/4] Running bibtex...
bibtex main
if %errorlevel% neq 0 (
    echo WARNING: bibtex returned an error. Check for missing [TODO] fields in references.bib
)

echo [3/4] Running pdflatex (pass 2)...
pdflatex -interaction=nonstopmode main.tex >nul 2>&1

echo [4/4] Running pdflatex (pass 3 - resolves cross-references)...
pdflatex -interaction=nonstopmode main.tex >nul 2>&1

echo.
echo ============================================================
if exist "main.pdf" (
    echo  SUCCESS: main.pdf generated.
    echo  Open main.pdf and search for "FILL:" to find unfilled placeholders.
    echo  If any are found, fill them in and run this script again.
) else (
    echo  ERROR: main.pdf was not created. Review the LaTeX error above.
)
echo ============================================================
pause

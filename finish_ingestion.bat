@echo off
echo ===================================================
echo 🚀 LAW-GPT: RESUMING FULL KAGGLE INGESTION (26k PDFs)
echo ===================================================
echo This process will extract and embed 20,000+ judgments.
echo It may take 1-2 hours. Do not close this window.
echo ===================================================

python scripts/resume_ingestion.py

echo.
echo ✅ Done! Run 'python scripts/advanced_legal_test.py' to verify accuracy.
pause

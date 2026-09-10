@echo off
echo ============================================================
echo  AI-Assisted Box Selection System — Setup and Test Runner
echo ============================================================

echo.
echo [1/4] Installing dependencies...
pip install -r requirements.txt
if %errorlevel% neq 0 (echo ERROR: pip install failed & exit /b 1)

echo.
echo [2/4] Running database migrations...
python manage.py makemigrations shipping
python manage.py migrate
if %errorlevel% neq 0 (echo ERROR: migrations failed & exit /b 1)

echo.
echo [3/4] Running test suite...
python manage.py test shipping --verbosity=2 2>&1 | tee TEST_OUTPUT.md
if %errorlevel% neq 0 (echo ERROR: tests failed & exit /b 1)

echo.
echo [4/4] All done! Starting dev server...
echo.
echo API available at: http://127.0.0.1:8000/api/
echo Admin panel at:   http://127.0.0.1:8000/admin/
echo.
python manage.py runserver

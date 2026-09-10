@echo off
echo Running migrations...
python manage.py makemigrations shipping
python manage.py migrate

echo.
echo Running tests with verbosity=2...
python manage.py test shipping --verbosity=2

echo.
echo Done. Paste the output above into TEST_OUTPUT.md

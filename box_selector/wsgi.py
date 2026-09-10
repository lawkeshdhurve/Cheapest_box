"""WSGI config for box_selector project."""

import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "box_selector.settings")
application = get_wsgi_application()

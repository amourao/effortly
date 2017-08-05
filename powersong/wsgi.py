"""
WSGI config for powersong project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/1.10/howto/deployment/wsgi/
"""

import os
import site
import sys

site.addsitedir('/home/amourao/powersong/')
site.addsitedir('/home/amourao/powersong/powersong')
site.addsitedir('/home/amourao/anaconda3/lib/python3.6/site-packages')

sys.path.append('/home/amourao/powersong/')
sys.path.append('/home/amourao/powersong/powersong')
sys.path.append('/home/amourao/anaconda3/lib/python3.6/site-packages')

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "powersong.settings")

application = get_wsgi_application()

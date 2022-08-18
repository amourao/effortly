"""
WSGI config for careceiver_server project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/2.1/howto/deployment/wsgi/
"""

import os
import site
import sys


site.addsitedir('/home/amourao/effortly/effortly/')
site.addsitedir('/home/amourao/effortly/effortly/lib/python3.10/site-packages/')

sys.path.append('/home/amourao/effortly/')
sys.path.append('/home/amourao/effortly/effortly/bin')


from django.core.wsgi import get_wsgi_application

os.environ["DJANGO_SETTINGS_MODULE"] = 'powersong.settings'

import django.core.handlers.wsgi

application = get_wsgi_application()

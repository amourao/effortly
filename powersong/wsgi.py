"""
WSGI config for powersong project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/1.10/howto/deployment/wsgi/
"""

import os
import site
import sys


site.addsitedir('/home/amourao/veffortly/')
site.addsitedir('/home/amourao/veffortly/lib/python3.8/site-packages/')

sys.path.append('/home/amourao/powersong')


from django.core.wsgi import get_wsgi_application

os.environ["DJANGO_SETTINGS_MODULE"] = "powersong.settings"

application = get_wsgi_application()

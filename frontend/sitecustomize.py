# install the apport exception handler if available
try:
    import apport_python_hook
except ImportError:
    pass
else:
    apport_python_hook.install()

import os, sys

os.environ['DJANGO_SETTINGS_MODULE'] = 'server.settings'
sys.path = ['/var/ntropy/ui/web', '/var/ntropy/ui/web/server'] + sys.path
if 'ntropy' in os.getcwd():
    from django.core.management import setup_environ
    import settings
    setup_environ(settings)

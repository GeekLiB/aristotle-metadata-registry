# MariaDB settings
# Includes conneciton age to account fot Travis-CI wierdness
# https://github.com/mozilla/kitsune/pull/2453/commits/229db28973f00dfc4fa7b386f266caf3417966a0

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql', 
        'NAME': 'aristotle_test_db',
        'USER': 'travis',
        'PASSWORD': '',
        'HOST': 'localhost',   # Or an IP Address that your DB is hosted on
        'PORT': '3306',
        'CONN_MAX_AGE': 600
    }
}

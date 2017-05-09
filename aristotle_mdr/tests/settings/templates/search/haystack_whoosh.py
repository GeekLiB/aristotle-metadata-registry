import os
import tempfile

HAYSTACK_CONNECTIONS = {
    'default': {
        'ENGINE': 'haystack.backends.whoosh_backend.WhooshEngine',
        'PATH': tempfile.mkdtemp(),
        'INCLUDE_SPELLING': True,
    },
}

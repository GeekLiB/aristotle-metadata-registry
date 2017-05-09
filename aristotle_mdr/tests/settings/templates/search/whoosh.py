import os
import tempfile

HAYSTACK_CONNECTIONS = {
    'default': {
        #'ENGINE': 'haystack.backends.whoosh_backend.WhooshEngine',
        'ENGINE': 'aristotle_mdr.contrib.search_backends.facetted_whoosh.FixedWhooshEngine',
        'PATH': tempfile.mkdtemp(),
        'INCLUDE_SPELLING': True,
    },
}

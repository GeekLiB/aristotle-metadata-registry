default_app_config = 'aristotle_mdr.apps.AristotleMDRConfig'


__version_info__ = {
    'major': 1,
    'minor': 5,
    'micro': 2,
    'releaselevel': 'final',
    'serial': 0
}


def get_version(release_level=True):
    """
    Return the formatted version information
    """
    vers = ["%(major)i.%(minor)i.%(micro)i" % __version_info__]
    if release_level and __version_info__['releaselevel'] != 'final':
        vers.append('%(releaselevel)s%(serial)i' % __version_info__)
    return ''.join(vers)


__version__ = get_version()

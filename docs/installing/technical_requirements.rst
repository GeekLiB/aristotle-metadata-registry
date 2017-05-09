Technical requirements
======================

The Aristotle Metadata Registry is built on the django framework which supports a wide range of
operating systems and databases. While Aristotle-MDR should support most of these
only a small set of configurations have been thoroughly tested on the
`Travis-CI <https://travis-ci.org/aristotle-mdr/aristotle-metadata-registry/>`_
or `Appveyor <https://ci.appveyor.com/project/LegoStormtroopr/aristotle-metadata-registry-361e5>`_
continuous integration systems as "supported infrastucture".

Operating system support
------------------------

* Ubuntu Linux 12.04 LTS (verification courtesy of Travis-CI)
* Windows Server 2016 (verification courtesy of Appveyor)

Travis-CI does not yet have containerised support for the Ubuntu 14.04 or 16.04
long-term support releases.

Python
------
Only the latest releases of Python are supported. New users are recommended to use Python 3.

* Python 2.7
* Python 3.5+

Django
------

* Django version 1.8 LTS
* Django version 1.10


Database support
----------------

* SQLite
* Postgres
* Microsoft SQL Server 2016 (Windows deployments only)
* MariaDB

Note, MySQL has issues incompatible with Aristotle that prevent it from being used.
Consider using an alternative like MariaDB if you need MySQL-like support.

Search index support
--------------------

* Elasticsearch 2.4+ (Only tested on Linux)
* Whoosh (Linux and Windows)

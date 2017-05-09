"""
Aristotle Easy Installer

This script guides you through the setup of the Aristotle Metadata Registry.

Command line options:
 -d --dry   -- Dry run: Run as normal, configures settings and requirements, but
               does not install them
 -f --force -- Forces install of requirements without confirmation
 -h --help  -- Prints this message
 -n --name  -- The system name for your registry
               eg. --name=registry or -nregistry
"""
from __future__ import unicode_literals, print_function


import getopt
import os
import pip
import re
import sys
from subprocess import call
from random import getrandbits
import hashlib


BASE_DIR = os.path.dirname(os.path.dirname(__file__))
name = "newly created"  # Forward-declaration placeholder
PIP_MSG = "You can finish installing by running - pip install -r requirements.txt - from the %s directory" % name


optional_modules = [
    ("Aristotle Glossary Extension", "#!aristotle_glossary!"),
    ("Aristotle Dataset Extensions", "#!aristotle_dse!"),
    ("Aristotle DDI Downloaders", "#!aristotle_ddi_utils!"),
    ("Aristotle MDR API", "#!aristotle_mdr_api!")
]


def valid_input(prompt, match):

    try:
        # Ensure input compatability across Python 2/3
        input_func = vars(__builtins__).get('raw_input', input)
    except:
        pass
    for i in range(5):
        check = input_func(prompt)
        if re.match(match, check):
            return check
    raise Exception


def setup_mdr(name="", extensions=[], force_install=False, dry_install=False):
    name_regex = '^[a-z][a-z_]*$'
    if not re.match(name_regex, name):
        name = valid_input("Enter the system name for your registry (lowercase letters and underscores ONLY): ", name_regex)

    try:
        download_example_mdr()
    except:
        print("Downloading of example settings failed, this script requires subversion to be installed and executable from the command line.")
        print("Try running the script again, if this continues to fail, try:")
        print("   1. manually downloading the folder to this directory and ALL its contents from github: https://github.com/aristotle-mdr/aristotle-metadata-registry/tree/master/example_mdr")
        print("   2. creating a new project using the django-admin tools and manually setting up a project")
        raise

    rename_example_mdr(name)

    yn = '^[YyNn]?$'  # yes/no regex
    if not extensions:
        do_install = valid_input("Do you wish to install any additional Aristotle modules? (y/n): ", yn).lower()
        if do_install == 'y':
            print("Select extensions to install (y/n)")
            for display, ext_token in optional_modules:
                do_ext = valid_input("  %s: " % display, yn).lower()
                if do_ext == 'y':
                    extensions.append(ext_token)
    if extensions:
        find_and_remove(name, extensions)

    # Update the settings key
    generate_secret_key(name)

    if dry_install:
        print("Performing dry run, no requirements installed.")
        print(PIP_MSG)
        return 0
    elif force_install:
        print("Installing from requirements.txt")
    else:
        do_install = 'y' == valid_input("Ready to install requirements? (y/n): ", yn).lower()
        if not do_install:
            print("Performing dry run, no requirements installed.")
            print(PIP_MSG)
            return 0
    try:
        install_reqs(name)
    except:
        print("Installing requirements failed.")
        print(PIP_MSG)
        raise

    if not dry_install and do_install:
        print("Running django command to fetch all required static files")
        collect_static(name)

        print("You can now locally test your installed registry by running the command './manage.py runserver'")


def generate_secret_key(name):
    key = "Change-this-key-as-soon-as-you-can"
    # This is probably not cryptographically secure, not for production.
    gen_key = hashlib.sha224(str(getrandbits(128)).encode('utf-8')).hexdigest()
    fname = './%s/%s/settings.py' % (name, name)
    with open(fname) as f:
        s = f.read()
    s = s.replace(key, gen_key)
    with open(fname, "w") as f:
        f.write(s)


def rename_example_mdr(name):
    os.rename('example_mdr', name)
    os.rename(os.path.join(name, 'example_mdr'), os.path.join(name, name))
    find_and_replace(name, 'example_mdr', name)


def install_reqs(name):
    # pip.main(['install', package])
    call(["pip", 'install', '-r%s/requirements.txt' % name])
    return call


def collect_static(name):
    call(["./%s/manage.py" % name, 'migrate'])
    call(["./%s/manage.py" % name, 'collectstatic'])
    return call


def download_example_mdr():
    print("Attempting to retrieve example registry")
    command = "export"
    arg = "https://github.com/aristotle-mdr/aristotle-metadata-registry/trunk/aristotle_mdr/install/example_mdr/"
    call(["svn", command, arg])
    return call


def find_and_replace(mydir, old, new):
    """Really naive find and replace lovingly borrowed from stack overflow - http://stackoverflow.com/a/4205918/764357"""
    for dname, dirs, files in os.walk(mydir):
        for fname in files:
            if fname.endswith(('py', 'txt', 'rst')):
                fpath = os.path.join(dname, fname)
                with open(fpath) as f:
                    s = f.read()
                s = s.replace(old, new)
                with open(fpath, "w") as f:
                    f.write(s)


def find_and_remove(mydir, extensions):
    for dname, dirs, files in os.walk(mydir):
        for fname in files:
            if fname.endswith(('py', 'txt', 'rst')):
                fpath = os.path.join(dname, fname)
                with open(fpath) as f:
                    s = f.read()
                for ext in extensions:
                    s = s.replace(ext, '')
                with open(fpath, "w") as f:
                    f.write(s)


class Usage(Exception):
    def __init__(self, msg):
        self.msg = msg


def is_opt(opts, *args):
    for a in args:
        if a in opts.keys():
            return True
    return False


def main(argv=None):
    if argv is None:
        argv = sys.argv
    try:
        try:
            opts, args = getopt.getopt(argv[1:], "n:dfh", ["dry", "force", "help", "name=", ])
            opts = dict(opts)
        except getopt.error as msg:
            raise Usage(msg)
        # more code, unchanged
    except Usage as err:
        print(err.msg, file=sys.stderr)
        print("for help use --help", file=sys.stderr)
        return 2
    if is_opt(opts, '-h', '--help'):
        print(__doc__)
        return 0
    kwargs = {}
    if is_opt(opts, '-n', '--name'):
        kwargs['name']=opts.get('-n', opts.get('--name'))
    if is_opt(opts, '-d', '--dry'):
        kwargs['dry_install']=True
    if is_opt(opts, '-f', '--force'):
        kwargs['force_install']=True

    return setup_mdr(**kwargs)


if __name__ == "__main__":
    sys.exit(main())

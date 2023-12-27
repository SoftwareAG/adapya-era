#!/usr/bin/env python
# requires Python V2.7 or V3.5 or higher
from __future__ import print_function          # PY3

import os,sys

try:
    from setuptools import setup
except:
    print('no setuptools found, trying distutils.core')
    from distutils.core import setup  # noqa

pver=sys.version[0]
prel=sys.version[2]

print('Active runtime:',sys.version, pver, prel)

extra = {}
#   extra['install_requires'] = ['uuid']

install_requires = [
    'adapya-base>=1.3.0',
    'adapya-adabas>=1.3.0',
    'adapya-entirex>=1.3.0',
]

README = open(os.path.join(os.path.dirname(__file__), 'README.rst')).read()

setup(  name='adapya-era',
    version='1.3.0',
    author='mmueller',
    author_email='mm@softwareag.com',
    description='adapya-era - services library of the Event Replicator for Adabas',
    license='Apache License 2.0',
    url='https://github.com/SoftwareAG/adapya-era',
    classifiers = [
        'Development Status :: 5 - Production/Stable',
        'License :: OSI Approved :: Apache Software License',
         'Intended Audience :: Developers',
         'Natural Language :: English',
         'Operating System :: Microsoft :: Windows',
         'Operating System :: POSIX :: AIX',
         'Operating System :: POSIX :: HP-UX',
         'Operating System :: POSIX :: SunOS/Solaris',
         'Operating System :: POSIX :: Linux',
         'Programming Language :: Python',
         'Programming Language :: Python :: 2.7',
         'Programming Language :: Python :: 3.5',
         'Programming Language :: Python :: 3.6',
         'Programming Language :: Python :: 3.7',
         'Programming Language :: Python :: 3.8',
         'Programming Language :: Python :: 3.9',
         'Programming Language :: Python :: 3.10',
         'Programming Language :: Python :: 3.11',
         'Topic :: Database'
         ],
    keywords='softwareag adabas event replication',
    long_description=README,
    zip_safe=False,
    scripts = ['adapya/era/scripts/inq.py','adapya/era/scripts/outq.py',
        'adapya/era/scripts/readris.py',],
    packages=['adapya', 'adapya.era'],
    install_requires=install_requires,
    namespace_packages=['adapya'],
    #extras_require={ 'dev': [ 'coverage','nose','pytest','pytest-pep8','pytest-cov' ]},

    platforms='any',
    **extra
)

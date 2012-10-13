#!/usr/bin/env python
#:coding=utf-8:

from setuptools import setup, find_packages
 
setup(
    name='namake',
    version='0.1',
    description='A lazy-loaded WebOb based WSGI micro-framework',
    author='Ian Lewis',
    author_email='ianmlewis@gmail.com',
    url='https://github.com/IanLewis/namake',
    classifiers=[
      'Development Status :: 3 - Alpha',
      'Intended Audience :: Developers',
      'License :: OSI Approved :: BSD License',
      'Programming Language :: Python',
    ],
    packages=find_packages(),
    install_requires=[
        'WebOb>=1.1.1',
        # Jinja2>=2.6 (Recommended)
    ],
)

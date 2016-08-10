# -*- coding: utf-8 -*-

import io
import re

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

version = ''
with io.open('typo/_version.py', 'r') as fd:
    version = re.search(r'^__version__\s*=\s*[\'"]([^\'"]*)[\'"]',
                        fd.read(), re.MULTILINE).group(1)

setup(
    name='typo',
    version=version,
    description='Runtime type checking for functions with type annotations',
    author='Ivan Smirnov',
    author_email='i.s.smirnov@gmail.com',
    url='https://github.com/aldanor/typo',
    license='MIT',
    packages=['typo'],
    classifiers=(
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
    ),
    keywords='typing type checking annotations',
    extras_require={
        ':python_version == "3.3"': 'typing >= 3.5',
        ':python_version == "3.4"': 'typing >= 3.5'
    }
)

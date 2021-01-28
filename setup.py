#!/usr/bin/env python
from os.path import join

from setuptools import setup, find_packages


# CONSTANTS
MODULE_NAME = 'django-json-api'         # package name used to install via pip 
MODULE_NAME_IMPORT = 'django_json_api'  # this is how this module is imported in Python 
REPO_NAME = 'django-json-api'           # repository name


# DEPENDENCIES
def requirements_from_pip(filename):
    with open(filename, 'r') as pip:
        return [l.strip() for l in pip if not l.startswith('#') and l.strip()]

core_deps = requirements_from_pip('requirements.txt')
test_deps = requirements_from_pip('requirements_test.txt')
all_deps = test_deps


# DESCRIPTION
with open('README.md', 'r', encoding='utf-8') as fh:
    long_description = fh.read()


setup(
    author='Sharework',
    description='JSON API specification for Django services',
    extras_require={'all': all_deps, 'test': test_deps},
    install_requires=core_deps,
    long_description=long_description,
    long_description_content_type="text/markdown",
    name="{:s}-share-work".format(MODULE_NAME), # Replace with your own username
    packages=find_packages(),
    python_requires='>=3.8',
    url='https://github.com/share-work/{:s}'.format(REPO_NAME),
    version=open(join(MODULE_NAME_IMPORT, 'resources', 'VERSION')).read().strip(),
    classifiers=[
        "Programming Language :: Python :: 3.8",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)

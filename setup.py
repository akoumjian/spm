from distribute_setup import use_setuptools
use_setuptools()

from setuptools import setup

setup_kwargs = {
    'name': 'spm',
    'version': '0.0.1',
    'packages': ['spm'],

    # metadata for upload to PyPI
    'author': 'Alec Koumjian',
    'author_email': 'akoumjian@gmail.com',
    'description': 'A package manager for Saltstack',
    'license': 'MIT',
    'keywords': 'salt saltstack package manager spm spam',
    # url: "http://example.com/HelloWorld/",   # project home page, if any

    'entry_points': {
        'console_scripts': [
            'spm = spm.scripts:run',
        ],
    }
}

setup(**setup_kwargs)

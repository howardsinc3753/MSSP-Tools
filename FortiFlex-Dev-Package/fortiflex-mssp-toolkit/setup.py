#!/usr/bin/env python3
"""
FortiFlex MSSP Toolkit Setup
"""

from setuptools import setup, find_packages
import os

# Read README for long description
def read_file(filename):
    with open(os.path.join(os.path.dirname(__file__), filename), encoding='utf-8') as f:
        return f.read()

setup(
    name='fortiflex-mssp-toolkit',
    version='1.0.0',
    description='Complete Python toolkit for managing FortiFlex MSSP operations',
    long_description=read_file('README.md') if os.path.exists('README.md') else '',
    long_description_content_type='text/markdown',
    author='Fortinet MSSP SE Team',
    author_email='noreply@fortinet.com',
    url='https://github.com/yourusername/fortiflex-mssp-toolkit',
    license='MIT',

    packages=find_packages(where='src'),
    package_dir={'': 'src'},

    install_requires=[
        'requests>=2.31.0',
        'urllib3>=2.0.0',
    ],

    extras_require={
        'database': ['psycopg2-binary>=2.9.0'],
        'dev': [
            'pytest>=7.4.0',
            'black>=23.0.0',
            'flake8>=6.0.0',
        ]
    },

    python_requires='>=3.7',

    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: System Administrators',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Topic :: System :: Monitoring',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],

    keywords='fortinet fortiflex mssp api automation',

    project_urls={
        'Documentation': 'https://docs.fortinet.com/document/flex-vm/',
        'Source': 'https://github.com/yourusername/fortiflex-mssp-toolkit',
        'Tracker': 'https://github.com/yourusername/fortiflex-mssp-toolkit/issues',
    },
)

"""Setup script for Orion Video Player."""

from setuptools import setup, find_packages

setup(
    name='orion-player',
    version='1.0.0',
    description='A powerful, modern video player for Linux with GNOME-style design',
    author='Orion Project',
    license='GPL-3.0',
    packages=find_packages(),
    python_requires='>=3.10',
    install_requires=[
        'PyGObject>=3.42',
    ],
    entry_points={
        'console_scripts': [
            'orion=orion.app:main',
        ],
    },
    data_files=[
        ('share/applications', ['orion.desktop']),
    ],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: X11 Applications :: GTK',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Programming Language :: Python :: 3',
        'Topic :: Multimedia :: Video',
    ],
)

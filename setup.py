#!/usr/bin/env python3

from setuptools import find_packages, setup

setup(name='tap-harvest-forecast',
      version="1.2.1",
      description='Singer.io tap for extracting data from the Harvest Forecast api',
      author='Robert Benjamin',
      url='https://github.com/singer-io/tap-harvest-forecast',
      classifiers=['Programming Language :: Python :: 3 :: Only'],
      py_modules=['tap_harvest_forecast'],
      install_requires=[
          'singer-python==6.8.0',
          'requests==2.33.0',
          'backoff==2.2.1'
      ],
      extras_require={
        "dev": [
            "pytest",
            "coverage",
        ]
    },
      entry_points='''
          [console_scripts]
          tap-harvest-forecast=tap_harvest_forecast:main
      ''',
      packages=find_packages(),
      package_data = {
          'tap_harvest_forecast': ['schemas/*.json'],
      },
      include_package_data=True
)

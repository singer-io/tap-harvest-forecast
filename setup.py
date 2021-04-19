#!/usr/bin/env python3

from setuptools import setup

setup(name='tap-harvest-forecast',
      version="1.1.1",
      description='Singer.io tap for extracting data from the Harvest Forecast api',
      author='Robert Benjamin',
      url='https://github.com/singer-io/tap-harvest-forecast',
      classifiers=['Programming Language :: Python :: 3 :: Only'],
      py_modules=['tap_harvest_forecast'],
      install_requires=[
          'singer-python==5.1.5',
          'requests==2.20.0',
          'backoff==1.3.2'
      ],
      entry_points='''
          [console_scripts]
          tap-harvest-forecast=tap_harvest_forecast:main
      ''',
      packages=['tap_harvest_forecast'],
      package_data = {
          'tap_harvest_forecast/schemas': [
            "assignments.json",
            "clients.json",
            "milestones.json",
            "people.json",
            "projects.json",
            "roles.json"
          ],
      },
      include_package_data=True
)

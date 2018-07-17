#!/usr/bin/env python

from setuptools import setup

setup(name='tap-harvest-forecast',
      version="0.0.1",
      description='Singer.io tap for extracting data from the Harvest Forecast api',
      author='Robert Benjamin',
      url='http://singer.io',
      classifiers=['Programming Language :: Python :: 3 :: Only'],
      py_modules=['tap_harvest_forecast'],
      install_requires=[
          'singer-python==5.0.4',
          'requests==2.13.0',
          'pendulum==1.2.0',
          'backoff==1.3.2'
      ],
      entry_points='''
          [console_scripts]
          tap-harvest=tap_harvest:main
      ''',
      packages=['tap_harvest'],
      package_data = {
          'tap_harvest/schemas': [
            "assignments.json",
            "clients.json",
            "milestones.json",
            "people.json",
            "projects.json"
          ],
      },
      include_package_data=True,
)

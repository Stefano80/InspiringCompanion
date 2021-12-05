from setuptools import setup, find_packages


with open('README.rst') as f:
    readme = f.read()

with open('LICENSE') as f:
    license = f.read()

setup(
    name='Role Inspire',
    version='0.1.0',
    description='Discord bot for inspiring awesome dungeon master',
    long_description=readme,
    author='Stefano Cardanobile',
    author_email='stefano.cardanobile@gmail.com',
    url='',
    license=license,
    packages=find_packages(exclude=('test', 'resources'))
)
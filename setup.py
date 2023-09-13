from setuptools import setup

with open('README.md') as f:
    readme = f.read()

with open('LICENSE') as f:
    license = f.read()

setup(
    name='napkin',
    version='0.1.0',
    description='Back-of-the-envelope calculations on a napkin',
    long_description=readme,
    author='Robert Escriva',
    author_email='robert@rescrv.net',
    license=license,
    url='https://github.com/rescrv/napkin',
    packages=['napkin'],
    entry_points = {
        'console_scripts': ['napkin = napkin:main']
    }
)

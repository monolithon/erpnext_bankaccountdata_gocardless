# ERPNext Gocardless Bank © 2024
# Author:  Ameen Ahmed
# Company: Level Up Marketing & Software Development Services
# Licence: Please refer to LICENSE file


from setuptools import setup, find_packages
from erpnext_gocardless_bank import __version__ as version


with open('requirements.txt') as f:
    install_requires = f.read().strip().split('\n')


setup(
    name='erpnext_gocardless_bank',
    version=version,
    description='Gocardless open banking services integration for ERPNext.',
    author='Ameen Ahmed (Level Up)',
    author_email='levelupye@gmail.com',
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    install_requires=install_requires
)
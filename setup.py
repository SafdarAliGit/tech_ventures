from setuptools import setup, find_packages

with open("requirements.txt") as f:
	install_requires = f.read().strip().split("\n")

# get version from __version__ variable in tech_ventures/__init__.py
from tech_ventures import __version__ as version

setup(
	name="tech_ventures",
	version=version,
	description="this is Tech Ventures",
	author="VUT",
	author_email="safdar211@gmail.com",
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=install_requires
)

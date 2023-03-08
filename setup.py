from setuptools import setup, find_packages


with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name='snbtlib',
    version='0.0.4',
    keywords='minecraft',
    description='a formatter for snbt from minecraft',
    long_description=long_description,
    license='MIT License',
    url='',
    author='Tryanks',
    author_email='tryanks@outlook.com',
    packages=find_packages(),
    include_package_data=True,
    platforms='any',
)

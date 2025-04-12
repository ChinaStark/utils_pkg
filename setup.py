# -- coding: utf-8 --
# @Author : ZhiliangLong
# @File : setup.py
# @Time : 2025/4/12 11:57
# setup.py

from setuptools import setup, find_packages

setup(
    name='utils_pkg',
    version='0.1.0',
    packages=find_packages(),
    install_requires=[
        'requests',
    ],
    python_requires='>=3.9',
    description='A small tool library from CStark',
    long_description=open('README.md').read(),
    author='CStark',
    author_email='CStark@Stark.com',
    url='https://github.com/CStark',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.8',
    ],
)
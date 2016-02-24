from setuptools import setup, find_packages

base_requirements = [
    'six>=1.10'
]

setup(
    name="helpful",
    description="Helpful tools for Python",
    author='Cal Leeming',
    author_email='cal@iops.io',
    url='https://github.com/imsofly/python-helpful',
    keywords=['helpful', 'useful'],
    version="0.8.1",
    py_modules=['helpful'],
    setup_requires=[
        'pytest-runner>=2.6',
        'yanc>=0.3'
    ],
    install_requires=base_requirements,
    classifiers=[
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.4'
    ]
)
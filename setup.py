from setuptools import setup, find_packages

setup(
    name="aura_maintainer",
    version="0.1",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'click',
        'pyyaml',
        'docker',
        'psycopg[binary]',
    ],
    entry_points={
        'console_scripts': [
            'aura-maintainer=src.main:cli'
        ],
    },
)
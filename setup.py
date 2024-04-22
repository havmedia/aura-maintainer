from setuptools import setup, find_packages

setup(
    name="aura_maintainer",
    version="0.3",
    python_requires='>=3.9',
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
            'aura-maintainer=src.main:cli_secure'
        ],
    },
)

from setuptools import setup, find_packages

# Read requirements files for dependencies
with open('requirements/base.txt', 'r') as f:
    install_requires = [line.strip() for line in f if line.strip() and not line.startswith('#')]

# Read long description from README
with open('README.md', 'r') as f:
    long_description = f.read()

setup(
    name='circle-core-framework',
    version='0.1.0',
    author='Circle Data & IT Solutions Ltd',
    author_email='hello@circle-labs.co.uk',
    description='Core framework for Circle Core ecosystem',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/ol-s-cloud/circle-core-framework',
    packages=find_packages(where='src'),
    package_dir={'': 'src'},
    install_requires=install_requires,
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: Other/Proprietary License',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
    ],
    python_requires='>=3.8',
    extras_require={
        'dev': ['black', 'isort', 'mypy', 'flake8', 'bandit', 'pre-commit'],
        'test': ['pytest', 'pytest-cov', 'pytest-mock', 'pytest-asyncio'],
        'docs': ['sphinx', 'sphinx-rtd-theme', 'myst-parser'],
    },
)

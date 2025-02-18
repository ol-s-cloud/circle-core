from setuptools import setup, find_packages

setup(
    name='circle-core-framework',
    version='0.1.0',
    packages=find_packages(),
    install_requires=[
        'requests>=2.25.0',
        'pyyaml>=5.4.0',
    ],
    author='Circle Core Team',
    author_email='support@circle-core.io',
    description='Core framework for Circle Core ecosystem',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/ol-s-cloud/circle-core-framework',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: Other/Proprietary License',
        'Programming Language :: Python :: 3.8',
    ],
    python_requires='>=3.8',
)
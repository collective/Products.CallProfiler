from setuptools import find_packages
from setuptools import setup

version = '1.5.3dev'

long_description = (
    open('README.rst').read()
    + '\n' +
    'Contributors\n'
    '============\n'
    + '\n' +
    open('CONTRIBUTORS.txt').read()
    + '\n' +
    open('CHANGES.txt').read()
    + '\n')

setup(
    name='Products.CallProfiler',
    version=version,
    description="Call Profiler monitors the chain of DTML, ZSQL, ZPT, Python "
                "method and Python Script",
    long_description=long_description,
    classifiers=[
        "Programming Language :: Python",
    ],
    keywords='',
    author='Richard Jones',
    author_email='product-developers@lists.plone.org',
    url='http://github.com/collective/Products.CallProfiler',
    license='gpl',
    packages=find_packages('src'),
    package_dir={'': 'src'},
    namespace_packages=['Products'],
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        'setuptools',
        # -*- Extra requirements: -*-
    ],
    extras_require={'test': ['plone.app.testing']},
    entry_points="""
    # -*- Entry points: -*-
    [z3c.autoinclude.plugin]
    target = plone
    """,
)

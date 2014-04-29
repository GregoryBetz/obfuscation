#!/usr/bin/env python2

from setuptools import setup, Extension, find_packages

__name__ = 'ind_obfuscation'
__author__ = 'Alex J. Malozemoff'
__version__ = '0.5'

obfuscator = Extension(
    'indobf._obfuscator',
    libraries = [
        'gmp',
        'gomp',
    ],
    extra_compile_args = [
        '-fopenmp',
        '-O3',
        '-Wall',
    ],
    sources = [
        'src/_obfuscator.cpp',
        'src/mpn_pylong.cpp',
        'src/mpz_pylong.cpp'
    ]
)

setup(name = __name__,
      version = __version__,
      author = __author__,
      description = 'Indistinguishability obfuscation',
      url = 'https://github.com/amaloz/ind-obfuscation',
      package_data = {'circuits': ['*.circ']},
      packages = ['indobf', 'circuits'],
      ext_modules = [obfuscator],
      test_suite = 'unittests',
      classifiers = [
          'Topic :: Security :: Cryptography',
          'Environment :: Console',
          'Development Status :: 3 - Alpha',
          'Intended Audience :: Science/Research',
          'Operating System :: Unix',
          'License :: OSI Approved :: Free For Educational Use',
          'Programming Language :: C',
          'Programming Language :: Sage',
      ],
)

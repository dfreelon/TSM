from setuptools import setup

dependencies = open('requirements-dev.txt').read().split()

setup(name='TSM',
      version='1.0',
      description='TSM - Twitter Subgraph Manipulator',
      url='http://github.com/dfreelon/tsm',
      author='Deen Freelon',
      author_email='dfreelon@gmail.com',
      license='BSD',
      install_requires=dependencies,
      zip_safe=False)

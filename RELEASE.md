### How to release

#. update `__version__` in `oscpy/__init__.py`
#. update `CHANGELOG.md`
#. call `git commit oscpy/__init__.py CHANGELOG.md`
#. call `git tag --sign [version]`
#. call `rm dist/*; python setup.py sdist bdist_wheel`
#. call `twine check oscpy/*`
#. call `twine upload oscpy/*`
#. call `git push --tags`

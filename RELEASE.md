### How to release

1. Update `__version__` in `oscpy/__init__.py`
1. Update `CHANGELOG.md`
1. Call `git commit oscpy/__init__.py CHANGELOG.md`
1. Call `git tag --sign [version]`
1. Call `git push --tags`

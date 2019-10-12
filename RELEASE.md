### How to release

For test releases, use a -test suffix to the tag, for example "v0.6.0-test",
for actual releases, just use the normal version name, for example "v0.6.0".

1. Update `__version__` in `oscpy/__init__.py`
1. Update `CHANGELOG.md`
1. Call `git commit oscpy/__init__.py CHANGELOG.md`
1. Call `git tag --sign [version]`
1. Call `git push --tags`

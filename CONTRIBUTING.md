# Contribution Guidelines

OSCPy is part of the [Kivy](https://kivy.org) ecosystem - a large group of
products used by many thousands of developers for free, but it
is built entirely by the contributions of volunteers. We welcome (and rely on) 
users who want to give back to the community by contributing to the project.

Contributions can come in many forms. See the latest 
[Contribution Guidelines](https://github.com/kivy/kivy/blob/master/CONTRIBUTING.md)
for how you can help us.

.. warning::
   The OSCPy process differs in small but important ways from the
   Kivy framework's process. See below.

# oscpy Contribution Hints

- Avoid lowering the test coverage. It's hard to achieve 100%, but staying as
  close to it as possible is a good way to improve quality by catching bugs as
  early as possible.
 
  Tests are automatically run in GitHub on a Pull Request, and the coverage is
  evaluated by Coveralls, so you'll get a report about your contribution
  breaking any test, and the evolution of coverage. You can also check that
  locally before sending the contribution, by using:

      pytest --cov-report term-missing --cov oscpy

  To get get an html report that you can open in your browser:

      pytest --cov-report html --cov  oscpy

- Please keep performance in mind when editing the code.

- You can install the package in `editable` mode, with the `dev` option,
  to easily have all the required tools to check your edits.

      pip install --editable .[dev]

- You can make sure the tests are run before pushing by using the git hook.

      cp tools/hooks/pre-commit .git/hooks/

- If you are unsure of the meaning of the pycodestyle output, you can use the
  `--show-pep8` flag to learn more about the errors.

      pycodestyle --show-pep8

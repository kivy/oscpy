### CONTRIBUTING

This software is open source and welcomes open contributions, there are just
a few guidelines, if you are unsure about them, please ask and guidance will be
provided.

- The code is [hosted on GitHub](https://github.com/kivy/oscpy) and
  development happens here, using the tools provided by the platform.
  Contributions are accepted in the form of Pull Requests. Bugs are to be
  reported in the issue tracker provided there.

- Please follow [PEP8](https://www.python.org/dev/peps/pep-0008/), hopefully
  your editor can be configured to automatically enforce it, but you can also
  install (using pip) and run `pycodestyle` from the command line,
  to get a report about it.

- Avoid lowering the test coverage, it's hard to achieve 100%, but staying as
  close to it as possible is a good way to improve quality by catching bugs as
  early as possible. Tests are ran by Travis, and the coverage is
  evaluated by Coveralls, so you'll get a report about your contribution
  breaking any test, and the evolution of coverage, but you can also check that
  locally before sending the contribution, by using `pytest --cov-report
  term-missing --cov oscpy`, you can also use `pytest --cov-report html --cov
  oscpy` to get an html report that you can open in your browser.

- Please try to conform to the style of the codebase, if you have a question,
  just ask.

- Please keep performance in mind when editing the code, if you
  see room for improvement, share your suggestions by opening an issue,
  or open a pull request direcly.

- Please keep in mind that the code you contribute will be subject to the MIT
  license, don't include code if it's not under a compatible license, and you
  are not the copyright holder.

#### Tips

You can install the package in `editable` mode, with the `dev` option,
to easily have all the required tools to check your edits.

    pip install --editable .[dev]

You can make sure the tests are ran before pushing by using the git hook.

    cp tools/hooks/pre-commit .git/hooks/

If you are unsure of the meaning of the pycodestyle output, you can use the
--show-pep8 flag to learn more about the errors.

    pycodestyle --show-pep8

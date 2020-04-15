# Contributing to NBViewer


Welcome! As a [Jupyter](https://jupyter.org) project,
you can follow the [Jupyter contributor guide](https://jupyter.readthedocs.io/en/latest/contributor/content-contributor.html).

Make sure to also follow [Project Jupyter's Code of Conduct](https://github.com/jupyter/governance/blob/master/conduct/code_of_conduct.md)
for a friendly and welcoming collaborative environment.

## Setting up a development environment

See the instructions for local development or local installation first. Next, set up pre-commit hooks for automatic code formatting, etc.

    ```bash
    pre-commit install
    ```

    You can also invoke the pre-commit hook manually at any time with

    ```bash
    pre-commit run
    ```

NBViewer has adopted automatic code formatting so you shouldn't
need to worry too much about your code style.
As long as your code is valid,
the pre-commit hook should take care of how it should look.
You can invoke the pre-commit hook by hand at any time with:

```bash
pre-commit run
```

which should run any autoformatting on your code
and tell you about any errors it couldn't fix automatically.
You may also install [black integration](https://github.com/ambv/black#editor-integration)
into your text editor to format code automatically.

#### Running the Tests

It's a good idea to write tests to exercise any new features,
or that trigger any bugs that you have fixed to catch regressions. `nose` is used to run the test suite. The tests currently make calls to
external APIs such as GitHub, so it is best to use your Github API Token when
running:

```shell
$ cd <path to repo>
$ pip install -r requirements-dev.txt
$ GITHUB_API_TOKEN=<your token> python setup.py test
```

You can run the tests with:

```bash
nosetests -v
```

in the repo directory.

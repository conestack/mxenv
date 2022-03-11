from mxdev import Hook
from mxdev import State
import abc
import logging
import os

logger = logging.getLogger('mxenv')

NAMESPACE = 'mxenv-'


###############################################################################
# utils
###############################################################################

def venv_folder():
    return os.environ.get('MXENV_VENV_FOLDER', os.path.join('venv'))


def scripts_folder():
    return os.environ.get('MXENV_SCRIPTS_FOLDER', os.path.join('venv', 'bin'))


def config_folder():
    return os.environ.get('MXENV_CONFIG_FOLDER', os.path.join('cfg'))


def ns_name(name):
    return f'{NAMESPACE}{name}'


def list_value(value):
    if not value:
        return list()
    return [v.strip() for v in value.replace('\n', ' ').strip().split(' ')]


###############################################################################
# template basics
###############################################################################

class template:
    _registry = dict()

    def __init__(self, name):
        self.name = name

    def __call__(self, ob):
        ob.name = self.name
        self._registry[self.name] = ob
        return ob

    @classmethod
    def lookup(cls, name):
        return cls._registry.get(name)


class Template(abc.ABC):
    name = None

    def __init__(self, config):
        self.config = config

    @property
    def settings(self):
        return self.config.hooks.get(ns_name(self.name), {})

    def ensure_directory(self, path):
        os.makedirs(path, exist_ok=True)

    @abc.abstractmethod
    def write(self):
        """Write script to filesystem."""


###############################################################################
# script template basics
###############################################################################

SCRIPT_TEMPLATE = """\
#!/bin/bash
#
# THIS SCRIPT IS GENERATED BY MXENV.
# CHANGES MADE IN THIS FILE MAY BE LOST.
#
{description}
{content}
exit 0
"""


def render_script(description, content):
    return SCRIPT_TEMPLATE.format(
        description='\n'.join([f'# {line}' for line in description.split('\n')]),
        content=content
    )


ENV_TEMPLATE = """\
{setenv}
{content}
{unsetenv}
"""


def render_env(env, content):
    return ENV_TEMPLATE.format(
        setenv='\n'.join([f'export {k}="{v}"' for k, v in env.items()]),
        content=content,
        unsetenv='\n'.join([f'unset {k}' for k in env])
    )


class ScriptTemplate(Template):

    @property
    def env(self):
        env_name = self.settings.get('environment')
        return self.config.hooks.get(ns_name(env_name), {}) if env_name else {}

    def write(self):
        scripts = scripts_folder()
        self.ensure_directory(scripts)
        script_path = os.path.join(scripts, f'{self.name}.sh')
        with open(script_path, 'w') as f:
            f.write(render_script(
                self.description,
                render_env(self.env, self.render())
            ))
        os.chmod(script_path, 0o750)


###############################################################################
# test script template
###############################################################################

TEST_TEMPLATE = """
{venv}/bin/zope-testrunner --auto-color --auto-progress \\
{testpaths}
    --module=$1
"""


@template('run-tests')
class TestScript(ScriptTemplate):
    description = 'Run tests'

    def package_paths(self, attr):
        paths = list()
        for name, package in self.config.packages.items():
            if attr not in package:
                continue
            path = f"{package['target']}/{name}/{package[attr]}".rstrip('/')
            paths.append(path)
        return paths

    def render(self):
        paths = self.package_paths(ns_name('test-path'))
        return TEST_TEMPLATE.format(
            venv=venv_folder(),
            testpaths='\n'.join([f'    --test-path={p} \\' for p in paths])
        )


###############################################################################
# coverage script template
###############################################################################

COVERAGE_TEMPLATE = """
sources=(
{sourcepaths}
)

sources=$(printf ",%s" "${{sources[@]}}")
sources=${{sources:1}}

{venv}/bin/coverage run \\
    --source=$sources \\
    -m zope.testrunner --auto-color --auto-progress \\
{testpaths}

{venv}/bin/coverage report
{venv}/bin/coverage html
"""


@template('run-coverage')
class CoverageScript(TestScript):
    description = 'Run coverage'

    def render(self):
        tpaths = self.package_paths(ns_name('test-path'))
        spaths = self.package_paths(ns_name('source-path'))
        return COVERAGE_TEMPLATE.format(
            venv=venv_folder(),
            sourcepaths='\n'.join([f'    {p}' for p in spaths]),
            testpaths='\n'.join(
                [f'    --test-path={p} \\' for p in tpaths]
            ).rstrip(' \\')
        )


###############################################################################
# mxdev hook
###############################################################################

class MxEnv(Hook):
    namespace = NAMESPACE

    def __init__(self):
        logger.info('mxenv: hook initialized')

    def write(self, state: State) -> None:
        config = state.configuration
        templates = list_value(config.settings.get(ns_name('templates')))
        if not templates:
            logger.info('mxenv: No templates defined')
            return
        for name in templates:
            factory = template.lookup(name)
            if not factory:
                msg = f'mxenv: No template registered under name {name}'
                logger.warning(msg)
                continue
            factory(config).write()

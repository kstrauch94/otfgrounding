from setuptools import setup

setup(
    version = '0.0.1',
    name = 'otfgrounding',
    description = 'System that creates propagator for constraints automatically.',
    author = 'Klaus Strauch',
    license = 'MIT',
    packages = ['otfgrounding', 'otfgrounding.propagator'],
    #test_suite = 'untimed.tests',
    zip_safe = False,
    entry_points = {
        'console_scripts': [
            'otfgrounding=otfgrounding:main',
            'otfcompile=otfgrounding.compile_propagators:compile'
        ]
    }
)

from setuptools import setup

setup(
    version = '0.0.1',
    name = 'otfgrounding',
    description = 'System to solve temporals programs with special handling of temporal constraints.',
    author = 'Klaus Strauch',
    license = 'MIT',
    packages = ['otfgrounding', 'otfgrounding.propagator', 'otfgrounding.theory'],
    #test_suite = 'untimed.tests',
    zip_safe = False,
    entry_points = {
        'console_scripts': [
            'otfgrounding=otfgrounding:main',
        ]
    }
)
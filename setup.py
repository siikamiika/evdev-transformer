from setuptools import setup

setup(
    name='evdev_transformer',
    version='0.0.1',
    url='https://github.com/siikamiika/evdev_transformer.git',
    author='siikamiika',
    description='evdev transformer',
    packages=['evdev_transformer'],
    install_requires=[
        'libevdev',
        'pyudev',
        'python_libinput @ git+https://github.com/siikamiika/python-libinput@master'
    ],
)

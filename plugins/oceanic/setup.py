#
# Oceanic, a Deluge plugin of the magnetics chain, core only: no GTK and no web part. Built on dev with
#   cd plugins/oceanic && /opt/projects/deluge_source_project/venv/bin/python3 setup.py bdist_egg
# into dist/Oceanic-0.4-py3.12.egg, which is installed from deluge-gtk's Preferences, Plugins, Install Plugin.
#

from setuptools import find_packages, setup

__plugin_name__ = 'Oceanic'
__author__ = 'sermin'
__version__ = '0.4'
__license__ = 'Unlicense'
__description__ = "hears the daemon's alerts and events and runs one command per hearing"

setup(
    name=__plugin_name__,
    version=__version__,
    description=__description__,
    author=__author__,
    license=__license__,
    long_description=__description__,
    packages=find_packages(),
    entry_points=f'''
    [deluge.plugin.core]
    {__plugin_name__} = deluge_{__plugin_name__.lower()}:CorePlugin
    ''',
)

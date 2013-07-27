import argparse
from spm.commands import install, remove, list_pkgs
import logging
import sys


class SpmCommand(object):

    def __init__(self):
        # Parse the command arguments
        parser = argparse.ArgumentParser(description='The Salt Package Manager')
        parser.add_argument('command', help="spm command to run: ['install']")
        parser.add_argument('pkg', nargs='?', default='', help="package to run operation on")
        parser.add_argument('--develop', action='store_true', help="Link package files directly from local folder")
        parser.add_argument('-l', '--loglevel', help="Set log output level")
        self.args = parser.parse_args()
        self.command = self.args.command
        self.pkg = self.args.pkg

        # Setup logging
        self.logger = logging.getLogger('spm')
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(self.args.loglevel or 'INFO')
        formatter = logging.Formatter('%(asctime)s [%(name)s] [%(levelname)s] %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

    def run(self):
        if self.command == 'install':
            return install(self.pkg, self.args)
        elif self.command == 'remove':
            return remove(self.pkg, self.args)
        elif self.command == 'list':
            return list_pkgs()
        else:
            self.logger.warning('No such command {0}'.format(self.command))

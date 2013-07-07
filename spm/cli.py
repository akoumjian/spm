import argparse
from spm.commands import install
import logging
import sys


class SpmCommand(object):

    def __init__(self):
        # Parse the command arguments
        parser = argparse.ArgumentParser(description='The Salt Package Manager')
        parser.add_argument('command', help="spm command to run: ['install']")
        parser.add_argument('pkg', help="package to run operation on")
        parser.add_argument('-l', '--loglevel', help="Set log output level")
        args = parser.parse_args()
        self.command = args.command
        self.pkg = args.pkg

        # Setup logging
        logger = logging.getLogger('spm')
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(args.loglevel)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    def run(self):
        if self.command == 'install':
            install(self.pkg)

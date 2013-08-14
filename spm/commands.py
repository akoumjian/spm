import os
import shutil
import yaml
import tempfile
import salt.config
import salt.client

import logging

logger = logging.getLogger('spm')

SPM_DIR = os.environ.get('SPM_CONFIG', '/etc/salt/spm')
PKGS_DIR = os.path.join(SPM_DIR, 'pkgs')
INSTALLED = os.path.join(SPM_DIR, 'installed')
CLIENT = os.path.join(SPM_DIR, 'client')


def _get_pkgs_dir():
    # TODO: Programmatic way to determine where to store these?
    src_dir = PKGS_DIR
    if not os.path.exists(src_dir):
        os.makedirs(src_dir)
    return src_dir


def _initialize_localclient_config():
    if not os.path.exists(CLIENT):
        with open(CLIENT, 'w') as f:
            f.write('master: localhost\nfile_client: local')
    return CLIENT


def fetch_pkg(pkg_name, url):
    """
    Grab a package from a remote url
    """
    caller = salt.client.Caller(CLIENT)
    src_dir = _get_pkgs_dir()

    url_pieces = url.split('/')
    pkg = url_pieces[-1]
    pkg_pieces = pkg.split('.')
    pkg_ext = '.'.join(pkg_pieces[1:])
    pkg_dir = os.path.join(src_dir, pkg_name)

    if pkg_ext == 'git':
        caller.function('git.clone', pkg_dir, url)
    else:
        # TODO: Add support for tarballs and zips
        raise Exception('Non git packages are not yet supported')

    return pkg_dir


def _read_manifest(manifest_path):
    with open(manifest_path, 'r') as f:
        manifest_str = f.read()

    manifest = yaml.load(manifest_str)
    return manifest


def _link_file(src, dest):
    # Normalizing paths makes sure directories
    # are also split correctly.
    # /etc/mypackage/ -> /etc/mypackage
    # os.path.split('/etc/mypackage') -> ('/etc', 'mypackage')
    src = os.path.normpath(src)
    dest = os.path.normpath(dest)

    # Create parent directories if they do not exist
    dest_dir, dest_link = os.path.split(dest)
    if not os.path.exists(dest_dir):
        os.makedirs(dest_dir)

    logger.info('Linking {0} -> {1}'.format(src, dest))
    # symlink the file or directory
    os.symlink(src, dest)

    # Return destination path so we have a record of created file
    return dest


def _expand_path(pkg_root, rel_path):
    return os.path.join(pkg_root, rel_path)


def _link_files(pkg_module_home, pkg_root, path_list):
    """
    Link the modules in path_list inside of module_home

    pkg_module_home: ie: '/srv/salt/_states/pkg-name/'
    """
    created_links = []
    for mod_path in path_list:
        rel_src = os.path.normpath(mod_path)

        # Get the full path to the origin file
        abs_src = _expand_path(pkg_root, rel_src)
        # Create the path to the symlink target
        abs_dir, target = os.path.split(abs_src)
        abs_dest = os.path.join(pkg_module_home, target)
        # Create symlink
        link = _link_file(abs_src, abs_dest)
        created_links.append(link)
    # Return list of created files
    return created_links


def _initialize_module_folder(module_home, pkg_name):
    pkg_module_dir = os.path.join(module_home, pkg_name)
    if not os.path.exists(pkg_module_dir):
        os.makedirs(pkg_module_dir)
    return pkg_module_dir


def _fetch_salt_config():
    master_path = os.environ.get('SALT_MASTER_CONFIG', '/etc/salt/master')
    minion_path = os.environ.get('SALT_MINION_CONFIG', '/etc/salt/minion')
    if os.path.exists(master_path):
        opts = salt.config.master_config(master_path)
    elif os.path.exists(minion_path):
        opts = salt.config.minion_config(minion_path)
    else:
        opts = salt.config.load_config(None)
    return opts


def _gen_mod_roots(config):
    """
    Get the locations to store different types of modules
    """
    mod_roots = {}
    file_root = config['file_roots']['base'][0]
    pillar_root = config['pillar_roots']['base'][0]

    mod_roots['modules'] = os.path.join(file_root, '_modules')
    mod_roots['states'] = os.path.join(file_root, '_states')
    mod_roots['runners'] = os.path.join(file_root, '_runners')
    mod_roots['grains'] = os.path.join(file_root, '_grains')
    mod_roots['formulas'] = file_root
    mod_roots['pillar'] = pillar_root

    logger.info(mod_roots)

    return mod_roots


def _mark_installed(pkg_name, url, files):
    with open(INSTALLED, 'r') as f:
        installed = f.read()
    installed = yaml.load(installed) or {}

    pkg_dict = {
        'url': url,
        'files': files
    }

    installed.update({pkg_name: pkg_dict})
    with open(INSTALLED, 'w') as f:
        f.write(yaml.dump(installed))


def _determine_package_name(url):
    url_pieces = url.split('/')
    pkg = url_pieces[-1]
    pkg_pieces = pkg.split('.')
    pkg_name = pkg_pieces[0]
    return pkg_name


def _get_installed():
    with open(INSTALLED, 'r') as f:
        installed = f.read()

    installed = yaml.load(installed) or {}
    return installed


def _initialize_spm():
    for folder in [SPM_DIR, PKGS_DIR]:
        if not os.path.exists(folder):
            os.makedirs(folder)

    if not os.path.exists(CLIENT):
        _initialize_localclient_config()

    if not os.path.exists(INSTALLED):
        with open(INSTALLED, 'a+') as f:
            f.write('')

    return True


def remove(pkg_name, opts):
    _initialize_spm()

    installed = _get_installed()

    if pkg_name in installed:
        logger.info('Removing package {0}'.format(pkg_name))
        src_dir = _get_pkgs_dir()
        pkg_dir = os.path.join(src_dir, pkg_name)


        # Fetch salt configuration settings
        config = _fetch_salt_config()
        mod_roots = _gen_mod_roots(config)

        # Remove each of the pkg folders from mod roots
        for root_name, root_folder in mod_roots.items():
            pkg_mod_root = os.path.join(root_folder, pkg_name)
            print pkg_mod_root
            if os.path.exists(pkg_mod_root):
                shutil.rmtree(pkg_mod_root, ignore_errors=True)

        logger.debug('Removing directory {0}'.format(pkg_dir))
        shutil.rmtree(pkg_dir, ignore_errors=True)

        # Remove from list of installed pkgs
        installed.pop(pkg_name)

        with open(INSTALLED, 'w') as f:
            f.write(yaml.dump(installed))

    else:
        logger.info('Package {0} is not installed'.format(pkg_name))


def install(url, opts):
    print opts
    _initialize_spm()

    pkg_name = _determine_package_name(url)

    installed = _get_installed()

    if pkg_name in installed:
        if installed[pkg_name]['url'] == url:
            logger.info('{0} is already installed'.format(pkg_name))
        else:
            logger.info('{0} is installed with different source.'.format(pkg_name))

        logger.info('Cancelling installation.')
        return False

    if opts.develop:
        # Install from local package
        pkg_root = url
    else:
        # Fetch the package
        pkg_root = fetch_pkg(pkg_name, url)

    # Fetch salt configuration settings
    config = _fetch_salt_config()
    mod_roots = _gen_mod_roots(config)

    # Retrieve manifest dictionary
    manifest = _read_manifest(
        os.path.join(pkg_root, 'MANIFEST')
    )

    module_types = [
        'modules',
        'states',
        'runners',
        'grains',
        'formulas',
        'pillar',
    ]

    # Link all the files!
    created_files = []
    for mod_type in module_types:
        module_home = mod_roots[mod_type]
        named_folder = _initialize_module_folder(module_home, pkg_name)
        links = _link_files(named_folder, pkg_root, manifest[mod_type])
        created_files.extend(links)

    _mark_installed(pkg_name, url, created_files)

    return True


def list_pkgs():
    installed = _get_installed()
    for pkg in installed.keys():
        print pkg



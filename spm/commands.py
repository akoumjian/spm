import os
import yaml
import tempfile
import salt.config
import salt.client

import logging

logger = logging.getLogger('spm')


def _get_pkgs_dir():
    # TODO: Programmatic way to determine where to store these?
    src_dir = '/etc/salt/spm/pkgs'
    if not os.path.exists(src_dir):
        os.makedirs(src_dir)
    return src_dir


def _get_localclient_config():
    localclient_path = '/etc/salt/spm/client'
    if not os.path.exists(localclient_path):
        os.makedirs(os.path.split(localclient_path)[0])
        with open(localclient_path, 'w') as f:
            f.write('master: localhost\nfile_client: local')
    return localclient_path


def fetch_pkg(pkg_name, url):
    """
    Grab a package from a remote url
    """
    caller = salt.client.Caller(_get_localclient_config())
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


def _expand_path(pkg_root, rel_path):
    return os.path.join(pkg_root, rel_path)


def _link_files(module_home, pkg_root, path_list):
    """
    Link the modules in path_list inside of module_home
    """
    for mod_path in path_list:
        rel_src = os.path.normpath(mod_path)

        # Get the full path to the origin file
        abs_src = _expand_path(pkg_root, rel_src)
        # Create the path to the symlink target
        abs_dir, target = os.path.split(abs_src)
        abs_dest = os.path.join(module_home, target)
        # Create symlink
        _link_file(abs_src, abs_dest)


def _fetch_salt_config():
    master_path = '/etc/salt/master'
    minion_path = '/etc/salt/minion'
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


def _mark_installed(pkg_name, url):
    installed_file = '/etc/salt/spm/installed'
    with open(installed_file, 'r') as f:
        installed = f.read()
    installed = yaml.load(installed) or {}
    installed.update(pkg_name, url)
    with open(installed_file, 'w') as f:
        f.write(yaml.dumps(installed))


def _determine_package_name(url):
    url_pieces = url.split('/')
    pkg = url_pieces[-1]
    pkg_pieces = pkg.split('.')
    pkg_name = pkg_pieces[0]
    return pkg_name


def install(url):
    pkg_name = _determine_package_name(url)

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
    for mod_type in module_types:
        _link_files(mod_roots[mod_type], pkg_root, manifest[mod_type])

    _mark_installed(pkg_name, url)

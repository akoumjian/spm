SPM: A Salt Package Manager
===========================

Summary
-------

Allow salt users to pull down packages of formulas, modules, returners, or remove the associated files.

Benefits
--------

#. Encourages developers to write robust and isolated reuseable packages
#. Easy to keep track of what came from where, what is currently being used


Installation
------------

#. The package gets copied to a local packagesdirectory in /etc/salt/spm/pkgs.
#. SPM reads the package's MANIFEST file, which points to the location of different salt components. Where the list 
values such as ``pkg_modules/`` represent relative paths to the package's root folder::

    modules:
      - pkg_modules/
    states:
      - pkg_states/
    formulas:
      - pkgname/
    ...


#. SPM symlinks the paths from the MANIFEST into the appropriate places in the file_root and pillar_root.

    /etc/salt/spm/pkgs/pkgname/pkg_modules/ -> /srv/salt/_modules/pkgname/pkg_modules/
    /etc/salt/spm/pkgs/pkgname/pkgname/ -> /srv/salt/pkgname/
    
Background
----------

SPM has to do some discovery ground work to figure out where to place modules, formulas, and pillars. It does this 
by using the salt Loader to analyze the master config, or if not available the minion config.


Best Practices
--------------

Package maintainers should put all cofiguration into pillar values. The package should include an example pillar file 
with comment documentation explaining each of the parameters.

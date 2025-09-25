# Declarative method to manage archlinux packages

When trying to configure the perfect system installing and removing packages and will lose track of what were added and what were removed.

This python script is used to track installed packages. To run the script python and uv needs to be installed.
 
The package list are managed using yaml files. When running for the first time script will create 'system.yaml' file which is used to track installed packages.

More yaml files can be created with packages that needs to be installed and include the file names at the start of run.py this will automaticaly install those packages.
If a pakcage name is removed from the package list they will be uninstalled.

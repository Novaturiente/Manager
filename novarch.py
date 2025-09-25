import subprocess
import os
import sys
import time
import typer
import yaml


def is_root():
    return os.geteuid() == 0


if not is_root():
    print("Script is not running as root, run with sudo")
    sys.exit(1)

# ANSI color codes
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
GREEN = "\033[92m"
RESET = "\033[0m"
red_cross = f"{RED}✗{RESET}"
yellow_warning = f"{YELLOW}⚠{RESET}"
blue_gear = f"{BLUE}⚙{RESET}"
green_check = f"{GREEN}✓{RESET}"

app = typer.Typer(add_completion=False, no_args_is_help=True)
original_user = os.getenv("SUDO_USER")
script_dir = os.path.abspath(os.path.dirname(__file__))
systemfile = "/var/lib/novarch/system.yaml"
package_list = []


def run_command(command, check=True):

    result = subprocess.run(command, shell=True)
    if result.returncode != 0:
        print(f"{red_cross} Error running '{command}'")
        if check:
            print(f"{red_cross} '{command}' failed to complete exiting script")
            sys.exit(1)


@app.command(short_help="Change configured folder with yaml files")
def change():
    new_path = input("New path to the yaml files folder : ")
    if new_path.startswith("~"):
        new_path = new_path.replace("~", f"/home/{original_user}")
    if os.path.isdir(new_path):
        files = [file for file in os.listdir(new_path) if file.endswith(".yaml")]
        with open(systemfile, "r") as f:
            data = yaml.safe_load(f)

        data["folder"] = new_path
        data["files"] = files

        with open(systemfile, "w") as f:
            yaml.dump(data, f, sort_keys=False)
    else:
        print(f"{new_path} folder does not exist")
        sys.exit(1)


def setup_check():
    if not os.path.isdir("/var/lib/novarch"):
        run_command("mkdir /var/lib/novarch")
    if not os.path.exists(systemfile):
        print(f"{blue_gear} Starting fresh system")
        package_folder = input(f"Enter path for folder with package list yaml files : ")
        if package_folder.startswith("~"):
            package_folder = package_folder.replace("~", f"/home/{original_user}")
        if os.path.isdir(package_folder):
            files = [
                file for file in os.listdir(package_folder) if file.endswith(".yaml")
            ]
            packages = []

            data = {"folder": package_folder, "files": files, "packages": packages}

            with open(systemfile, "w") as f:
                yaml.dump(data, f, sort_keys=False)
        else:
            print(f"{package_folder} does not exist")
            sys.exit(1)
    else:
        with open(systemfile, "r") as f:
            data = yaml.safe_load(f)
        folder = data["folder"]
        if not os.path.isdir(folder):
            print("Packages folder does not exist")
            change()
        else:
            files = [file for file in os.listdir(folder) if file.endswith(".yaml")]
            data["files"] = files
            with open(systemfile, "w") as f:
                yaml.dump(data, f, sort_keys=False)


def chaotic_aur_setup():
    multilib_enabled = False
    chaotic_installed = False
    with open("/etc/pacman.conf", "r") as f:
        lines = f.readlines()

    for line in lines:
        if line.startswith("["):
            if "multilib" in line:
                multilib_enabled = True
                break
    if not multilib_enabled:
        with open("/etc/pacman.conf", "a") as f:
            f.write("[multilib]\n")
            f.write("Include = /etc/pacman.d/mirrorlist\n")
    run_command("pacman -Sy")

    for line in lines:
        if line.startswith("["):
            if "chaotic-aur" in line:
                chaotic_installed = True
                break
    if not chaotic_installed:
        print(f"{blue_gear} Configuring Chaotic-aur")
        run_command("pacman-key --init")
        run_command("pacman -Sy --noconfirm archlinux-keyring")
        run_command(
            "pacman-key --recv-key 3056513887B78AEB --keyserver keyserver.ubuntu.com"
        )
        run_command("pacman-key --lsign-key 3056513887B78AEB")
        run_command(
            "pacman -U --noconfirm 'https://cdn-mirror.chaotic.cx/chaotic-aur/chaotic-keyring.pkg.tar.zst'"
        )
        run_command(
            "pacman -U --noconfirm 'https://cdn-mirror.chaotic.cx/chaotic-aur/chaotic-mirrorlist.pkg.tar.zst'"
        )
        with open("/etc/pacman.conf", "a") as f:
            f.write("[chaotic-aur]\n")
            f.write("Include = /etc/pacman.d/chaotic-mirrorlist\n")

        run_command("pacman -Syu --noconfirm")


def update_system():
    print(f"{blue_gear} Updating system")
    paru_check = os.popen("pacman -Q reflector").readlines()
    if len(paru_check) == 0:
        print(f"{yellow_warning} reflector not installed installing now")
        run_command("pacman -S --noconfirm reflector")
    run_command(
        "reflector --latest 10 --protocol https --sort rate --save /etc/pacman.d/mirrorlist"
    )
    run_command("pacman -Syu --noconfirm")


def get_selected(package_folder, package_file):

    selected_packages = []
    for package in package_file:
        path = os.path.join(package_folder, package)
        if os.path.exists(path):
            with open(path, "r") as f:
                items = yaml.safe_load(f)

            selected_packages.extend(items)

        else:
            print(f"{red_cross} {package} not available")
            sys.exit(1)

    selected_packages = [item for item in selected_packages if item is not None]


def get_installed():
    installed_packages = []
    result = subprocess.run(["pacman", "-Q"], stdout=subprocess.PIPE, text=True)
    pkgs = result.stdout.split("\n")
    for pkg in pkgs:
        package = pkg.split(" ")[0]
        if package != "":
            installed_packages.append(package)

    return installed_packages


def get_system():

    with open(systemfile, "r") as f:
        data = yaml.safe_load(f)

    package_folder = data["folder"]
    package_file = data["files"]
    package_list = data["packages"]

    selected_packages = []
    for package in package_file:
        path = os.path.join(package_folder, package)
        if os.path.exists(path):
            with open(path, "r") as f:
                items = yaml.safe_load(f)

            selected_packages.extend(items)

        else:
            print(f"{red_cross} {package} not available")
            sys.exit(1)

    selected_packages = [item for item in selected_packages if item is not None]

    installed_packages = get_installed()

    return (
        package_list,
        selected_packages,
        installed_packages,
    )


def update_existing(package_list: list, action: int):

    with open(systemfile, "r") as f:
        data = yaml.safe_load(f)

    existing_packages = data["packages"]
    installed_packages = get_installed()

    if action == 1:
        print(f"Adding {package_list} to systemfile")
        for package in package_list:
            if package in installed_packages and package not in existing_packages:
                existing_packages.append(package)
    elif action == 0:
        print(f"Removing {package_list} from systemfile")
        for package in package_list:
            if package not in installed_packages and package in existing_packages:
                existing_packages.remove(package)
    else:
        print(f"{red_cross}{yellow_warning}option {action} not found ")

    existing_packages.sort()
    with open(systemfile, "w") as f:
        yaml.dump(data, f)


def install_packages():

    package_list, selected_packages, installed_packages = get_system()

    tobe_installed = []
    for selected in selected_packages:
        if selected not in package_list:
            tobe_installed.append(selected)

    install_command = ["sudo", "-u", original_user, "paru", "-S", "--noconfirm"]
    install_confirmation = "N"
    if len(tobe_installed) > 0:
        install_command.extend(tobe_installed)
        install_confirmation = input(
            f"\n{tobe_installed}\n Do you want to proceed with installing above packages? [Y/n] ⬇ :"
        )
    else:
        print(f"{green_check} No packages needs to be installed")

    if install_confirmation.lower == "y" or install_confirmation == "":

        for i in range(3):
            result = subprocess.run(install_command, text=True)
            if result.returncode == 0:
                update_existing(tobe_installed, 1)
                break  # Success, exit loop
            else:
                print(f"{red_cross} Error installing packages, retrying {i + 1}")
                time.sleep(3)
        else:
            print(f"{red_cross} Failed after 3 tries, exiting.")
            update_existing(tobe_installed, 1)
            sys.exit(1)


def remove_packages():

    package_list, selected_packages, installed_packages = get_system()

    tobe_removed = []

    for existing in package_list:
        if existing not in selected_packages and existing in installed_packages:
            result = subprocess.run(
                ["pactree", "-rl", existing], stdout=subprocess.PIPE, text=True
            )
            dependancy_list = result.stdout.split("\n")
            if len(dependancy_list) == 2:
                tobe_removed.append(existing)

    remove_command = ["pacman", "-Rns", "--noconfirm"]
    remove_confirmation = "N"
    if len(tobe_removed) > 0:
        remove_command.extend(tobe_removed)
        remove_confirmation = input(
            f"\n{tobe_removed}\n Do you want to proceed with removing above packages? [Y/n] ⬆ :"
        )
    else:
        print(f"{green_check} No packages needs to be removed")

    if remove_confirmation.lower == "y" or remove_confirmation == "":
        for i in range(2):
            result = subprocess.run(remove_command, text=True)
            if result.returncode != 0:
                ask = input(
                    f"{red_cross} Error removing packages do you want to retry ? : "
                )
                if ask.lower == "y":
                    time.sleep(3)
                else:
                    update_existing(tobe_removed, 0)
                    sys.exit(1)
            else:
                update_existing(tobe_removed, 0)
                break


def manage_packages():

    print("📦 Checking for paru")
    paru_check = os.popen("pacman -Q paru").readlines()
    if len(paru_check) == 0:
        print(f"{yellow_warning} paru not installed installing now")
        run_command("pacman -S --noconfirm paru")

    install_packages()
    remove_packages()


def copy_configurations():

    # Copy system configurations
    file = os.path.join(script_dir, "system/etc/greetd/config.toml")
    run_command(f"cp {file} /etc/greetd/config.toml", False)

    file = os.path.join(
        script_dir, "system/etc/modprobe.d/nvidia-power-management.conf"
    )
    run_command(f"cp {file} /etc/modprobe.d/nvidia-power-management.conf", False)

    file = os.path.join(script_dir, "system/etc/modules-load/ntsync.conf")
    run_command(f"cp {file} /etc/modules-load.d/ntsync.conf", False)

    file = os.path.join(script_dir, "system/etc/tlp.conf")
    run_command(f"cp {file} /etc/tlp.conf", False)

    # Link user configurations
    subprocess.run(
        f"sudo -u {original_user} mkdir /home/{original_user}/.config", shell=True
    )

    # Install Doom emacs
    run_command(
        f"sudo -u {original_user} git clone --depth 1 https://github.com/doomemacs/doomemacs /home/{original_user}/.config/emacs"
    )
    run_command(
        f"sudo -u {original_user} /home/{original_user}/.config/emacs/bin/doom install"
    )

    run_command(f"rm -rf /home/{original_user}/.config/doom")

    run_command(
        f"sudo -u {original_user} git clone --depth 1 https://github.com/Novaturiente/.dotfiles /home/{original_user}/.dotfiles"
    )

    subprocess.run(
        f"sudo -u {original_user} stow -t /home/{original_user}/ nova",
        cwd=os.path.dirname(f"/home/{original_user}/.dofiles"),
        shell=True,
    )

    # Install tmux tpm
    run_command(
        "git clone https://github.com/tmux-plugins/tpm ~/.tmux/plugins/tpm", False
    )

    run_command("systemctl enable greetd")

    run_command("cp novarch /usr/bin/novarch")

    run_command(f"chsh {original_user} -s $(which zsh)")


@app.command(short_help="Show info about current system configuration")
def info():
    with open(systemfile, "r") as f:
        data = yaml.safe_load(f)

    print(f'Packages folder : {data["folder"]}\n')
    print(f"Package files   : {data['files']}\n")
    print(f"No of packages  : {len(data['packages'])}\n")


@app.command(short_help="Configure system from scratch")
def init():
    setup_check()
    chaotic_aur_setup()
    update_system()
    manage_packages()
    copy_configurations()


@app.command(short_help="Install/Remove packages based on updated package list")
def install():
    setup_check()
    chaotic_aur_setup()
    manage_packages()


@app.command(short_help="Update entire system")
def update():
    setup_check()
    chaotic_aur_setup()
    update_system()
    manage_packages()
    result = subprocess.run(["pacman", "-Qdtq"], stdout=subprocess.PIPE, text=True)
    pkgs = result.stdout.split("\n")
    if len(pkgs) < 2:
        print(f"{green_check} No orphaned packages to remove")
    else:
        print(f"Removing orphaned packages : {pkgs}")
        subprocess.run("sudo pacman -Rns $(pacman -Qdtq)", shell=True)
    print(f"{green_check} SYSTEM UPDATE COMPLETED")


if __name__ == "__main__":
    app()

#!/usr/bin/python

import subprocess
import os
import time
import typer
import yaml

package_list = [
    "base_system.yaml",
    "hyprland.yaml",
    "internet.yaml",
    "terminal_tools.yaml",
    "virtual_management.yaml",
    "development.yaml",
    "media.yaml",
    "gaming.yaml",
]

app = typer.Typer(add_completion=False, no_args_is_help=True)

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

script_dir = os.path.abspath(os.path.dirname(__file__))
systemfile = os.path.join(script_dir, "system.yaml")


def run_command(command, check=True):

    i = 1
    while True:
        result = subprocess.run(command, shell=True)

        if result.returncode != 0:
            print(f"{red_cross} Error running '{command}'")
            if check:
                if i == 3:
                    print(f"{red_cross} '{command}' failed to complete exiting script")
                    exit(1)
                i += 1
                time.sleep(5)
            else:
                break
        else:
            break


def chaotic_aur_setup():

    chaotic_installed = False
    with open("/etc/pacman.conf", "r") as f:
        lines = f.readlines()
    for line in lines:
        if line.startswith("["):
            if "chaotic-aur" in line:
                chaotic_installed = True
                break
    if not chaotic_installed:
        print(f"{blue_gear} Configuring Chaotic-aur")
        run_command("sudo pacman-key --init")
        run_command("sudo pacman -Sy --noconfirm archlinux-keyring")
        run_command(
            "sudo pacman-key --recv-key 3056513887B78AEB --keyserver keyserver.ubuntu.com"
        )
        run_command("sudo pacman-key --lsign-key 3056513887B78AEB")
        run_command(
            "sudo pacman -U --noconfirm 'https://cdn-mirror.chaotic.cx/chaotic-aur/chaotic-keyring.pkg.tar.zst'"
        )
        run_command(
            "sudo pacman -U --noconfirm 'https://cdn-mirror.chaotic.cx/chaotic-aur/chaotic-mirrorlist.pkg.tar.zst'"
        )
        pacmanconf = os.path.join(script_dir, "pacman.conf")
        run_command(f"sudo cp {pacmanconf} /etc/pacman.conf")
        run_command("sudo pacman -Syu --noconfirm")
        run_command("sudo pacman -Sy --noconfirm reflector")
        run_command("sudo pacman -Sy --noconfirm archlinux-keyring")
    else:
        print(f"{green_check} Chaotic-aur already configured")


def update_system():

    print(f"{blue_gear} Updating system")
    run_command(
        "sudo reflector --latest 10 --protocol https --sort rate --save /etc/pacman.d/mirrorlist"
    )
    run_command("sudo pacman -Syu --noconfirm")


def get_selected():

    selected_packages = []
    for package in package_list:
        path = os.path.join(script_dir, package)
        if os.path.exists(path):
            with open(path, "r") as f:
                items = yaml.safe_load(f)

            selected_packages.extend(items)

        else:
            print(f"{red_cross} {package} not available")
            exit(1)

    selected_packages = [item for item in selected_packages if item is not None]
    return selected_packages


def get_existing():

    installed_packages = []
    result = subprocess.run(["pacman", "-Q"], stdout=subprocess.PIPE, text=True)
    pkgs = result.stdout.split("\n")
    for pkg in pkgs:
        package = pkg.split(" ")[0]
        if package != "":
            installed_packages.append(package)

    existing_packages = []
    if os.path.exists(systemfile):
        with open(systemfile, "r") as f:
            existing_packages = yaml.safe_load(f)
    else:
        print(f"{yellow_warning} Cuttent system does not exist starting fresh")
        update_list = []
        selected_packages = get_selected()

        for package in selected_packages:
            if package in installed_packages:
                update_list.append(package)

        with open(systemfile, "w") as f:
            yaml.dump(update_list, f)

    return existing_packages, installed_packages


def update_existing(package_list: list, action: int):

    existing_packages, installed_packages = get_existing()

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
        yaml.dump(existing_packages, f)


def install_packages():

    selected_packages = get_selected()
    existing_packages, installed_packages = get_existing()
    tobe_installed = []
    for selected in selected_packages:
        if selected not in installed_packages and selected not in existing_packages:
            tobe_installed.append(selected)

    install_command = ["paru", "-S", "--noconfirm"]
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
            exit(1)


def remove_packages():

    selected_packages = get_selected()
    existing_packages, installed_packages = get_existing()
    tobe_removed = []

    for existing in existing_packages:
        if existing not in selected_packages and existing in installed_packages:
            result = subprocess.run(
                ["pactree", "-rl", existing], stdout=subprocess.PIPE, text=True
            )
            dependancy_list = result.stdout.split("\n")
            if len(dependancy_list) == 2:
                tobe_removed.append(existing)

    remove_command = ["paru", "-Rns", "--noconfirm"]
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
                    exit(1)
            else:
                update_existing(tobe_removed, 0)
                break


def manage_packages():

    print("📦 Checking for paru")
    paru_check = os.popen("pacman -Q paru").readlines()
    if len(paru_check) == 0:
        print(f"{yellow_warning} paru not installed installing now")
        run_command("sudo pacman -S --noconfirm paru")

    install_packages()
    remove_packages()


def copy_configurations():

    # Copy system configurations
    file = os.path.join(script_dir, "system/etc/greetd/config.toml")
    run_command(f"sudo cp {file} /etc/greetd/config.toml", False)

    file = os.path.join(
        script_dir, "system/etc/modprobe.d/nvidia-power-management.conf"
    )
    run_command(f"sudo cp {file} /etc/modprobe.d/nvidia-power-management.conf", False)

    file = os.path.join(script_dir, "system/etc/modules-load/ntsync.conf")
    run_command(f"sudo cp {file} /etc/modules-load.d/ntsync.conf", False)

    file = os.path.join(script_dir, "system/etc/tlp.conf")
    run_command(f"sudo cp {file} /etc/tlp.conf", False)

    # Link user configurations
    subprocess.run("mkdir ~/.config", shell=True)

    # Install Doom emacs
    run_command(
        "git clone --depth 1 https://github.com/doomemacs/doomemacs ~/.config/emacs"
    )
    run_command("~/.config/emacs/bin/doom install")

    run_command("rm -rf ~/.config/doom")

    subprocess.run("stow -t ~ nova", cwd=os.path.dirname(script_dir), shell=True)

    # Install tmux tpm
    run_command(
        "git clone https://github.com/tmux-plugins/tpm ~/.tmux/plugins/tpm", False
    )

    run_command("sudo systemctl enable greetd")

    run_command("chsh -s $(which zsh)")


@app.command(short_help="Configure system from scratch")
def init():
    chaotic_aur_setup()
    update_system()
    manage_packages()
    copy_configurations()


@app.command(short_help="Install/Remove packages based on updated package list")
def install():
    manage_packages()


@app.command(short_help="Update entire system")
def update():
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

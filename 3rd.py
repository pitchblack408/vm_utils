import os
import subprocess
import sys
import argparse
import shutil

REQUIRED_PACKAGES = [
    "bison", "elfutils-libelf-devel", "flex", "gcc", "glibc-devel", "glibc-headers", 
    "kernel-devel", "kernel-headers", "libxcrypt-devel", "libzstd-devel", 
    "m4", "make", "openssl-devel", "zlib-devel"
]

class VirtualBoxAddonsInstallException(Exception):
    def __init__(self, message):
        self.message = message

    def __str__(self):
        return self.message


class VirtualBoxAddonsFileNotFoundException(VirtualBoxAddonsInstallException):
    def __init__(self, message):
        self.message = message

    def __str__(self):
        return self.message

def ensure_root():
    """Ensure the script is run as root."""
    if os.geteuid() != 0:
        print("This script must be run as root!")
        sys.exit(1)

def run_command(command, check=True):
    """Run a command and check for errors."""
    result = subprocess.run(command, shell=True)
    if result.returncode != 0 and check:
        print(f"Command failed: {command}. Exiting.", file=sys.stderr)
        sys.exit(1)
    return result

def install_required_packages():
    """Install required packages."""
    print(f"Attempting to install required packages: {', '.join(REQUIRED_PACKAGES)}")
    run_command(f"dnf install -y {' '.join(REQUIRED_PACKAGES)}")

def install_kernel_headers(kernel_version):
    """Install kernal headers."""
    print("Kernel headers or development files not found. Installing...")
    run_command(f"dnf install -y kernel-devel-{kernel_version} kernel-headers-{kernel_version}")
    command = f"dnf install -y kernel-devel-{kernel_version} kernel-headers-{kernel_version}"
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

def clean_old_kernel_headers():
    """Remove old kernel headers and development files."""
    print("Cleaning up old kernel headers and development files...")
    
    # Remove all but the latest kernel headers and development packages
    run_command("dnf remove -y $(dnf repoquery --installonly --latest-limit=-1 -q)")
    print("Old kernel headers cleaned up.")

def download_iso(iso_url, iso_file):
    """Download the ISO file."""
    print("Downloading VirtualBox Guest Additions ISO...")
    run_command(f"wget -q {iso_url} -O {iso_file}")

def create_directories(mount_dir, target_dir):
    """Create necessary directories."""
    print("Creating directories...")
    os.makedirs(mount_dir, exist_ok=True)
    os.makedirs(target_dir, exist_ok=True)

def mount_iso(iso_file, mount_dir):
    """Mount the ISO file."""
    print("Mounting the ISO...")
    run_command(f"mount -o loop {iso_file} {mount_dir}")

def copy_contents(mount_dir, target_dir):
    """Copy the contents of the mounted ISO."""
    print(f"Copying contents to {target_dir}...")
    run_command(f"cp -r {mount_dir}/* {target_dir}")

def unmount_iso(mount_dir):
    """Unmount the ISO file."""
    print("Unmounting the ISO...")
    run_command(f"umount {mount_dir}")

def clean_up(mount_dir, target_dir, iso_file):
    """Clean up temporary files and directories."""
    print("Cleaning up...")
    os.rmdir(mount_dir)
    os.remove(iso_file)
    shutil.rmtree(target_dir)

def run_guest_additions(target_dir):
    """Run the VBoxLinuxAdditions.run installer."""
    vbox_additions_script = os.path.join(target_dir, "VBoxLinuxAdditions.run")
    
    if os.path.isfile(vbox_additions_script):
        print(f"Running {vbox_additions_script}...")
        run_command(f"{vbox_additions_script}")
    else:
        print("VBoxLinuxAdditions.run not found. Exiting.", file=sys.stderr)
        sys.exit(1)

def prompt_reboot():
    """Prompt the user to reboot the system."""
    reboot = input("The installation is complete. Changes will not take effect until reboot is completed. Would you like to reboot the system now? (y/n): ").strip().lower()
    if reboot == 'y':
        print("Rebooting the system...")
        run_command("reboot")
    else:
        print("Reboot skipped.")

    

def main():
    parser = argparse.ArgumentParser(description="Install VirtualBox Guest Additions ISO.")
    parser.add_argument('--virtual-box-version', type=str, required=True, help="The version of VirtualBox manager.")

    args = parser.parse_args()
    iso_url = f"https://download.virtualbox.org/virtualbox/{args.virtual_box_version}/VBoxGuestAdditions_{args.virtual_box_version}.iso"
    iso_file = f"/tmp/VBoxGuestAdditions_{args.virtual_box_version}.iso"
    mount_dir = f"/mnt/iso"
    target_dir = f"/tmp/VBox_GA"
    
    ensure_root()
    install_required_packages()
    download_iso(iso_url, iso_file)
    create_directories(mount_dir, target_dir)
    mount_iso(iso_file, mount_dir)
    copy_contents(mount_dir, target_dir)
    unmount_iso(mount_dir)
    
    try:
        print("Attempting to install addons with existing kernal headers.")
        run_guest_additions(target_dir)
    except VirtualBoxAddonsFileNotFoundException as e:
        print(e, file=sys.stderr)
    except VirtualBoxAddonsInstallException:
        # Get the current kernel version
        kernel_version = subprocess.check_output("uname -r", shell=True).decode().strip()
        print(f"Failed to install with existing kernal headers. Installing headers for kernal {kernel_version}")
        install_kernel_headers(kernel_version)  # Kernel headers installation
        clean_old_kernel_headers()  # Clean up old kernel headers and development files
        print(f"Attempting to install addons with kernal {kernel_version} headers.")
        try:
            run_guest_additions(target_dir)
        except VirtualBoxAddonsInstallException:
            print(f"Failed to install addons with kernal {kernel_version} headers. Exiting...")
            sys.exit(1)

    clean_up(mount_dir, target_dir, iso_file)
    prompt_reboot()
    print("Done!")





if __name__ == "__main__":
    main()
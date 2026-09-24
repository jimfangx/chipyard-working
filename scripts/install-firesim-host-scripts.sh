#!/usr/bin/env bash

# Install the FireSim host helpers from this checkout. This repository is the
# source of truth; rerun this script after updating the FireSim submodule.

set -euo pipefail

repo_root="$(git -C "$(dirname "${BASH_SOURCE[0]}")" rev-parse --show-toplevel)"
install_root="${DESTDIR:-}"
install_dir="${install_root}/usr/local/bin"
sudo_scripts="${repo_root}/sims/firesim/deploy/sudo-scripts"
u250_scripts="${repo_root}/sims/firesim/platforms/xilinx_alveo_u250/scripts"

if [[ -z "${DESTDIR:-}" && "${EUID}" -ne 0 ]]; then
    echo "Run this installer as root (for example, with sudo)." >&2
    exit 1
fi

owner_args=()
if [[ -z "${DESTDIR:-}" ]]; then
    if ! getent group firesim >/dev/null; then
        echo "The required 'firesim' group does not exist." >&2
        exit 1
    fi
    owner_args=(-o root -g firesim)
fi

install "${owner_args[@]}" -d -m 0755 "${install_dir}"

install_script() {
    local source="$1"
    local mode=0644

    if [[ -x "${source}" ]]; then
        mode=0755
    fi

    install "${owner_args[@]}" -m "${mode}" "${source}" "${install_dir}/$(basename "${source}")"
}

for source in "${sudo_scripts}"/* "${u250_scripts}"/*; do
    [[ -f "${source}" ]] || continue
    install_script "${source}"
done

echo "Installed FireSim host scripts from ${repo_root} into ${install_dir}."

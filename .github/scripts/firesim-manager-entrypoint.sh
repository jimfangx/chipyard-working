#!/usr/bin/env bash
set -euo pipefail

export USER=root
export LOGNAME=root
export HOME=/root

CY_DIR="${CY_DIR:-/root/chipyard}"
FS_DIR="${CY_DIR}/sims/firesim"
PUBLIC_KEY_PATH="${FIRESIM_PUBLIC_KEY_PATH:-/root/firesim-public}"
EC2_SETUP_SCRIPT="${FIRESIM_EC2_SETUP_SCRIPT:-${CY_DIR}/scripts/firesim-ec2-setup.sh}"
BUILD_RECIPES="${FIRESIM_BUILD_RECIPES:-${CY_DIR}/sims/firesim-staging/sample_config_build_recipes.yaml}"
BUILD_CONFIG="${FIRESIM_BUILD_CONFIG:-${CY_DIR}/.github/firesim-bitstream-templates/f2/config_build.yaml}"
VIVADO_VERSION="${VIVADO_VERSION:-}"

if [ -n "${VIVADO_VERSION}" ]; then
  VIVADO_PATH="/opt/Xilinx/${VIVADO_VERSION}/Vivado/settings64.sh"
else
  VIVADO_PATH="$(find /opt/Xilinx -path '*/Vivado/settings64.sh' -type f 2>/dev/null | sort -V | tail -n 1)"
fi

if [ ! -f "${VIVADO_PATH}" ]; then
  echo "Missing Vivado settings script. Set VIVADO_VERSION or mount /opt/Xilinx into the container." >&2
  exit 1
fi

echo "Sourcing Vivado settings: ${VIVADO_PATH}"
had_nounset=0
case "$-" in
  *u*)
    had_nounset=1
    set +u
    ;;
esac

# shellcheck disable=SC1090
source "${VIVADO_PATH}"

if [ "${had_nounset}" -eq 1 ]; then
  set -u
fi

if [ ! -s "${PUBLIC_KEY_PATH}" ]; then
  echo "Missing public key mounted at ${PUBLIC_KEY_PATH}." >&2
  exit 1
fi

mkdir -p "${HOME}/.ssh"
chmod 700 "${HOME}/.ssh"
touch "${HOME}/.ssh/authorized_keys"
chmod 600 "${HOME}/.ssh/authorized_keys"
grep -qxFf "${PUBLIC_KEY_PATH}" "${HOME}/.ssh/authorized_keys" || cat "${PUBLIC_KEY_PATH}" >> "${HOME}/.ssh/authorized_keys"

cat >> /etc/ssh/sshd_config <<'EOF'
PermitRootLogin yes
PubkeyAuthentication yes
PasswordAuthentication no
EOF

mkdir -p /run/sshd
chmod 755 /run/sshd
/usr/sbin/sshd

if [ ! -x "${EC2_SETUP_SCRIPT}" ]; then
  echo "Missing executable EC2 setup script: ${EC2_SETUP_SCRIPT}" >&2
  exit 1
fi
export FORCE_NON_EC2=0
"${EC2_SETUP_SCRIPT}"

cd "${FS_DIR}"
had_nounset=0
case "$-" in
  *u*)
    had_nounset=1
    set +u
    ;;
esac

# shellcheck disable=SC1091
source sourceme-manager.sh

if [ "${had_nounset}" -eq 1 ]; then
  set -u
fi

printf '\n' | firesim managerinit --platform f2

python -m pip uninstall -y pyOpenSSL cryptography awscli botocore s3transfer urllib3
python -m pip install --no-cache-dir --upgrade \
  'urllib3<2' \
  'cryptography==42.0.8' \
  'pyOpenSSL==24.1.0' \
  awscli
hash -r

export USER=root
export LOGNAME=root
export HOME=/root

firesim buildbitstream \
  -r "${BUILD_RECIPES}" \
  -b "${BUILD_CONFIG}"

firesim shareagfi

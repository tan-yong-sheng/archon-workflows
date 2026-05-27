#!/usr/bin/env bash
# manage.sh - Automates installation, symlinking, and removal of Archon workflows.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKFLOWS_DIR="${SCRIPT_DIR}/workflows"

usage() {
    cat <<EOF
Archon Workflow Manager

Usage:
  $0 install <workflow-name> <target-project-path> [--symlink]
  $0 uninstall <workflow-name> <target-project-path>
  $0 list

Options:
  --symlink    Create symbolic links instead of copying files (best for local development).

Examples:
  # Copy the security review workflow to a target project
  $0 install security-reviewer /path/to/my-web-app

  # Symlink for development (changes in target reflex back to workflows/)
  $0 install security-reviewer /path/to/my-web-app --symlink

  # Remove security review files from a target project
  $0 uninstall security-reviewer /path/to/my-web-app
EOF
    exit 1
}

log_info() { echo -e "\033[0;34m[INFO]\033[0m $*"; }
log_success() { echo -e "\033[0;32m[SUCCESS]\033[0m $*"; }
log_error() { echo -e "\033[0;31m[ERROR]\033[0m $*" >&2; }

list_workflows() {
    echo "Available workflows:"
    if [ -d "$WORKFLOWS_DIR" ]; then
        for dir in "$WORKFLOWS_DIR"/*/; do
            if [ -d "$dir" ]; then
                echo "  - $(basename "$dir")"
            fi
        done
    else
        echo "No workflows found in ${WORKFLOWS_DIR}"
    fi
}

install_workflow() {
    local name="$1"
    local target="$2"
    local use_symlink="${3:-false}"

    local src_pkg="${WORKFLOWS_DIR}/${name}"
    local dest_archon="${target}/.archon"

    if [ ! -d "$src_pkg" ]; then
        log_error "Workflow '${name}' not found under ${WORKFLOWS_DIR}."
        list_workflows
        exit 1
    fi

    if [ ! -d "$target" ]; then
        log_error "Target project path '${target}' does not exist."
        exit 1
    fi

    log_info "Installing workflow '${name}' into '${target}'..."

    # Ensure required target directories exist
    mkdir -p "${dest_archon}/workflows"
    mkdir -p "${dest_archon}/commands"
    mkdir -p "${dest_archon}/scripts"
    mkdir -p "${dest_archon}/schemas"

    # Install workflow YAML
    local src_yaml="${src_pkg}/workflow.yaml"
    local dest_yaml="${dest_archon}/workflows/${name}.yaml"
    if [ -f "$src_yaml" ]; then
        if [ "$use_symlink" = true ]; then
            ln -sf "$src_yaml" "$dest_yaml"
        else
            cp -f "$src_yaml" "$dest_yaml"
        fi
    fi

    # Install Commands
    if [ -d "${src_pkg}/commands" ]; then
        for cmd_file in "${src_pkg}/commands"/*; do
            if [ -f "$cmd_file" ]; then
                local filename
                filename=$(basename "$cmd_file")
                if [ "$use_symlink" = true ]; then
                    ln -sf "$cmd_file" "${dest_archon}/commands/${filename}"
                else
                    cp -f "$cmd_file" "${dest_archon}/commands/${filename}"
                fi
            fi
        done
    fi

    # Install Scripts
    if [ -d "${src_pkg}/scripts" ]; then
        for script_file in "${src_pkg}/scripts"/*; do
            if [ -f "$script_file" ]; then
                local filename
                filename=$(basename "$script_file")
                if [ "$use_symlink" = true ]; then
                    ln -sf "$script_file" "${dest_archon}/scripts/${filename}"
                else
                    cp -f "$script_file" "${dest_archon}/scripts/${filename}"
                    chmod +x "${dest_archon}/scripts/${filename}"
                fi
            fi
        done
    fi

    # Install Schemas
    if [ -d "${src_pkg}/schemas" ]; then
        for schema_file in "${src_pkg}/schemas"/*; do
            if [ -f "$schema_file" ]; then
                local filename
                filename=$(basename "$schema_file")
                if [ "$use_symlink" = true ]; then
                    ln -sf "$schema_file" "${dest_archon}/schemas/${filename}"
                else
                    cp -f "$schema_file" "${dest_archon}/schemas/${filename}"
                fi
            fi
        done
    fi

    log_success "Workflow '${name}' successfully installed to '${dest_archon}'!"
}

uninstall_workflow() {
    local name="$1"
    local target="$2"
    local dest_archon="${target}/.archon"

    if [ ! -d "$dest_archon" ]; then
        log_info "No .archon directory found at '${target}'. Nothing to uninstall."
        return
    fi

    log_info "Uninstalling workflow '${name}' from '${target}'..."

    # Remove the workflow YAML
    rm -f "${dest_archon}/workflows/${name}.yaml"

    # Remove commands if they exist in source
    local src_pkg="${WORKFLOWS_DIR}/${name}"
    if [ -d "${src_pkg}/commands" ]; then
        for cmd_file in "${src_pkg}/commands"/*; do
            rm -f "${dest_archon}/commands/$(basename "$cmd_file")"
        done
    fi

    # Remove scripts if they exist in source
    if [ -d "${src_pkg}/scripts" ]; then
        for script_file in "${src_pkg}/scripts"/*; do
            rm -f "${dest_archon}/scripts/$(basename "$script_file")"
        done
    fi

    # Remove schemas if they exist in source
    if [ -d "${src_pkg}/schemas" ]; then
        for schema_file in "${src_pkg}/schemas"/*; do
            rm -f "${dest_archon}/schemas/$(basename "$schema_file")"
        done
    fi

    # Clean up empty directories
    find "$dest_archon" -type d -empty -delete 2>/dev/null || true

    log_success "Workflow '${name}' successfully uninstalled."
}

# Main Command Router
if [ $# -lt 1 ]; then
    usage
fi

CMD="$1"
shift

case "$CMD" in
    list)
        list_workflows
        ;;
    install)
        if [ $# -lt 2 ]; then usage; fi
        NAME="$1"
        TARGET="$2"
        SYMLINK=false
        if [ "${3:-}" = "--symlink" ]; then
            SYMLINK=true
        fi
        install_workflow "$NAME" "$TARGET" "$SYMLINK"
        ;;
    uninstall)
        if [ $# -lt 2 ]; then usage; fi
        NAME="$1"
        TARGET="$2"
        uninstall_workflow "$NAME" "$TARGET"
        ;;
    *)
        usage
        ;;
esac

#!/bin/bash
#
# Restricted shell for web-ide containers.
#
# Security model:
#   This shell is set as the user's login shell inside the container.
#   Its purpose is to block interactive terminal access while allowing
#   VS Code's non-interactive shell integration (which invokes
#   `bash -c '<command>'` or `bash -lc '<command>'`).
#
#   The `-[a-zA-Z]*c` pattern handles bash compound flags: `-c`, `-lc`,
#   `-ilc`, etc.  Bash processes combined short flags left-to-right and
#   treats the next positional argument as the command string for `-c`.
#
#   This is defense-in-depth.  The container's dropped capabilities and
#   seccomp profile are the primary enforcement layer.
#

# Audit log blocked attempts to stderr (visible in container logs).
log_blocked() {
    echo "restricted-shell: blocked (args: $*)" >&2
}

for arg in "$@"; do
    case "$arg" in
        --command)
            exec /bin/bash "$@"
            ;;
        -c)
            exec /bin/bash "$@"
            ;;
        -[a-zA-Z]*c)
            # Compound flag containing -c (e.g. -lc, -ilc).
            # Find the -c flag's position and verify a command string follows.
            idx=0
            found=0
            for a in "$@"; do
                if [ "$a" = "$arg" ]; then
                    found=1
                    break
                fi
                idx=$((idx + 1))
            done
            if [ "$found" -eq 1 ] && [ $((idx + 1)) -lt "$#" ]; then
                exec /bin/bash "$@"
            fi
            log_blocked "$@"
            echo "restricted-shell: -c flag requires a command argument." >&2
            exit 1
            ;;
    esac
done

log_blocked "$@"
echo "Terminal access is disabled in the web IDE."
echo "Use the atopile sidebar to build and manage your project."
exit 0

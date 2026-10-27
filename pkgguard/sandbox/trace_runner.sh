#!/bin/sh
set -eu

ecosystem=${1:?ecosystem is required}
archive=${2:?archive path is required}
package_name=${3:?package name is required}
import_name=${4:-$package_name}
phase=${SANDBOX_PHASE:-install}
mkdir -p /logs /app/site-packages
export PYTHONPATH="/opt/sandbox-hooks:/app/site-packages${PYTHONPATH:+:$PYTHONPATH}"
runtime_log="/logs/runtime.${phase}.jsonl"
: > "$runtime_log"
export SANDBOX_RUNTIME_LOG="$runtime_log"

trace_file="/logs/strace.${phase}.log"
trace_args="-f -qq -s 4096 -o $trace_file"
trace_filter="-e trace=openat,openat2,creat,unlinkat,socket,connect,sendto,execve"

if [ "$phase" = "install" ]; then
    if [ "$ecosystem" = "pypi" ]; then
        cd /app
        set +e
        strace $trace_args $trace_filter python3 -m pip install --no-index --no-deps --no-build-isolation --upgrade --target /app/site-packages "$archive" > /logs/install.stdout 2>&1
        status=$?
        set -e
        if [ "$status" -eq 0 ] && [ ! -e "/app/site-packages/${import_name}" ]; then
            echo "pip completed but ${import_name} was not installed in /app/site-packages" >> /logs/install.stdout
            status=1
        fi
        # The directory is a host-mounted handoff between root containers and
        # must remain removable by the unprivileged host orchestrator.
        if [ -d /app/site-packages ]; then
            chmod -R a+rwX /app/site-packages 2>/dev/null || true
        fi
    elif [ "$ecosystem" = "npm" ]; then
        mkdir -p /app/npm-project
        cd /app/npm-project
        set +e
        rm -rf /app/npm-project/node_modules /app/npm-project/package
        mkdir -p /app/npm-project/node_modules
        tar -xzf "$archive" -C /app/npm-project
        mv /app/npm-project/package "/app/npm-project/node_modules/${package_name}"
        package_dir="/app/npm-project/node_modules/${package_name}"
        run_lifecycle() {
            script_name=$1
            script=$(node -e "const p=require('${package_dir}/package.json'); process.stdout.write((p.scripts && p.scripts['${script_name}']) || '')")
            if [ -n "$script" ]; then
                (cd "$package_dir" && /bin/sh -c "$script")
            fi
        }
        run_lifecycle preinstall
        run_lifecycle install
        run_lifecycle postinstall
        status=$?
        set -e
    else
        echo "unsupported ecosystem: $ecosystem" >&2
        exit 64
    fi
else
    if [ "$ecosystem" = "pypi" ]; then
        set +e
        strace $trace_args $trace_filter python3 -c "import ${import_name}" > /logs/import.stdout 2>&1
        status=$?
        set -e
    elif [ "$ecosystem" = "npm" ]; then
        cd /app/npm-project
        set +e
        strace $trace_args $trace_filter node -e "require(process.argv[1])" "$import_name" > /logs/import.stdout 2>&1
        status=$?
        set -e
    else
        echo "unsupported ecosystem: $ecosystem" >&2
        exit 64
    fi
fi

if [ "${status:-64}" -ne 0 ]; then
    cat "/logs/${phase}.stdout" >&2
fi
exit "${status:-64}"
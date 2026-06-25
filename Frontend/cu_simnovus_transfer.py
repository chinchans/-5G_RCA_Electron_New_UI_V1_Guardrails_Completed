#!/usr/bin/env python3
"""Transfer cu_simnovus.conf to remote host using password auth (paramiko)."""
import json
import os
import sys

import paramiko


def transfer(config):
    local_source = config["local_source"]
    remote_host = config["remote_host"]
    remote_user = config["remote_user"]
    remote_password = config["remote_password"]
    remote_dir = config["remote_dir"]
    remote_file = config.get("remote_file", "cu_simnovus.conf")
    remote_backup = config.get("remote_backup", "cu_simnovus_backup.conf")

    if not os.path.isfile(local_source):
        return {"success": False, "error": f"Local file not found: {local_source}"}

    remote_path = os.path.join(remote_dir, remote_file).replace("\\", "/")
    remote_backup_path = os.path.join(remote_dir, remote_backup).replace("\\", "/")
    steps = []

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(
            remote_host,
            username=remote_user,
            password=remote_password,
            timeout=15,
            allow_agent=False,
            look_for_keys=False,
        )
        steps.append(f"SSH OK: {remote_user}@{remote_host}")

        stdin, stdout, stderr = ssh.exec_command(f'mkdir -p "{remote_dir}"')
        stdout.channel.recv_exit_status()
        steps.append(f"Remote directory ready: {remote_dir}")

        backup_cmd = (
            f'cd "{remote_dir}" && '
            f'if [ -f "{remote_file}" ]; then '
            f'rm -f "{remote_backup}"; mv -f "{remote_file}" "{remote_backup}"; echo renamed; '
            f'else echo skip; fi'
        )
        stdin, stdout, stderr = ssh.exec_command(backup_cmd)
        backup_out = (stdout.read() or b"").decode().strip()
        backup_err = (stderr.read() or b"").decode().strip()
        exit_code = stdout.channel.recv_exit_status()
        if exit_code != 0:
            raise RuntimeError(backup_err or backup_out or f"Backup failed (exit {exit_code})")
        steps.append(f"Backup: {backup_out or 'done'}")

        # Verify backup presence (helps debugging when users don't see it)
        stdin, stdout, stderr = ssh.exec_command(
            f'if [ -f "{remote_backup_path}" ]; then ls -la "{remote_backup_path}"; else echo "Backup missing: {remote_backup_path}"; fi'
        )
        backup_verify_out = (stdout.read() or b"").decode().strip()
        backup_verify_err = (stderr.read() or b"").decode().strip()
        _ = stdout.channel.recv_exit_status()
        if backup_verify_err:
            steps.append(backup_verify_err)
        if backup_verify_out:
            steps.append(backup_verify_out)

        sftp = ssh.open_sftp()
        try:
            sftp.put(local_source, remote_path)
        finally:
            sftp.close()
        steps.append(f"Transferred to {remote_user}@{remote_host}:{remote_path}")

        stdin, stdout, stderr = ssh.exec_command(f'ls -la "{remote_path}"')
        verify_out = (stdout.read() or b"").decode().strip()
        verify_err = (stderr.read() or b"").decode().strip()
        exit_code = stdout.channel.recv_exit_status()
        if exit_code != 0:
            raise RuntimeError(verify_err or verify_out or "Remote verify failed")
        if verify_out:
            steps.append(verify_out)

        # Also show directory listing for extra confidence/debugging
        stdin, stdout, stderr = ssh.exec_command(f'ls -la "{remote_dir}" | tail -n 25')
        dir_out = (stdout.read() or b"").decode().strip()
        dir_err = (stderr.read() or b"").decode().strip()
        _ = stdout.channel.recv_exit_status()
        if dir_err:
            steps.append(dir_err)
        if dir_out:
            steps.append(f"Directory snapshot (last 25):\n{dir_out}")

        return {
            "success": True,
            "local_source": local_source,
            "remote_host": remote_host,
            "remote_path": f"{remote_user}@{remote_host}:{remote_path}",
            "remote_backup_path": f"{remote_user}@{remote_host}:{remote_backup_path}",
            "steps": steps,
        }
    except Exception as exc:
        return {
            "success": False,
            "error": str(exc),
            "local_source": local_source,
            "remote_host": remote_host,
            "steps": steps,
        }
    finally:
        ssh.close()


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"success": False, "error": "Missing config JSON argument"}))
        sys.exit(1)
    config = json.loads(sys.argv[1])
    result = transfer(config)
    print(json.dumps(result))
    sys.exit(0 if result.get("success") else 1)


if __name__ == "__main__":
    main()

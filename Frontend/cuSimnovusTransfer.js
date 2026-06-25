/**
 * Transfer ~/Config/cu_simnovus.conf to remote 95 machine via paramiko (password auth).
 */
const { spawn } = require('child_process');
const fs = require('fs');
const os = require('os');
const path = require('path');

const DEFAULT_LOCAL_SOURCE = path.join(os.homedir(), 'Config', 'cu_simnovus.conf');
const DEFAULT_REMOTE_USER = process.env.CU_DEPLOY_REMOTE_USER || 'tcs';
const DEFAULT_REMOTE_HOST = process.env.CU_DEPLOY_REMOTE_HOST || '10.138.77.95';
const DEFAULT_REMOTE_PASSWORD = process.env.CU_DEPLOY_REMOTE_PASSWORD || 'tcs@12345';
const DEFAULT_REMOTE_DIR = process.env.CU_DEPLOY_REMOTE_DIR || path.join(
    os.homedir(),
    'chandu/5g_standalone_split8_v4_simnovus_cu_du_ue_2022_For_GenAI/5g_sa_split8_v4_simnovus_cu_usrp_oct_25_2022/targets/PROJECTS/GENERIC-NR-5GC/CONF'
);
const DEFAULT_REMOTE_FILE = 'cu_simnovus.conf';
const DEFAULT_REMOTE_BACKUP = 'cu_simnovus_backup.conf';
const TRANSFER_SCRIPT = path.join(__dirname, 'cu_simnovus_transfer.py');

function runPythonTransfer(config) {
    return new Promise((resolve, reject) => {
        const configJson = JSON.stringify(config);
        const child = spawn('python3', [TRANSFER_SCRIPT, configJson], {
            stdio: ['ignore', 'pipe', 'pipe']
        });
        let stdout = '';
        let stderr = '';
        child.stdout.on('data', (d) => { stdout += d.toString(); });
        child.stderr.on('data', (d) => { stderr += d.toString(); });
        child.on('error', (err) => {
            if (err.code === 'ENOENT') {
                reject(new Error('python3 not found. Install Python 3 and paramiko: pip install paramiko'));
            } else {
                reject(err);
            }
        });
        child.on('close', (code) => {
            const trimmed = stdout.trim();
            if (trimmed) {
                try {
                    const result = JSON.parse(trimmed);
                    resolve(result);
                    return;
                } catch (_) {
                    /* fall through */
                }
            }
            if (code === 0 && trimmed) {
                resolve({ success: true, output: trimmed });
                return;
            }
            reject(new Error((stderr || trimmed || `Transfer script exited with code ${code}`).trim()));
        });
    });
}

/**
 * @param {object} [options]
 * @param {string} [options.localSource]
 * @param {string} [options.remoteUser]
 * @param {string} [options.remoteHost]
 * @param {string} [options.remotePassword]
 * @param {string} [options.remoteDir]
 * @param {string} [options.remoteFile]
 * @param {string} [options.remoteBackup]
 */
async function transferCuSimnovusConf(options = {}) {
    const localSource = options.localSource || DEFAULT_LOCAL_SOURCE;
    const remoteUser = options.remoteUser || DEFAULT_REMOTE_USER;
    const remoteHost = options.remoteHost || DEFAULT_REMOTE_HOST;
    const remotePassword = options.remotePassword || DEFAULT_REMOTE_PASSWORD;
    const remoteDir = options.remoteDir || DEFAULT_REMOTE_DIR;
    const remoteFile = options.remoteFile || DEFAULT_REMOTE_FILE;
    const remoteBackup = options.remoteBackup || DEFAULT_REMOTE_BACKUP;

    if (!fs.existsSync(TRANSFER_SCRIPT)) {
        return {
            success: false,
            error: `Transfer script not found: ${TRANSFER_SCRIPT}`,
            localSource
        };
    }

    if (!fs.existsSync(localSource)) {
        return {
            success: false,
            error: `Local config not found: ${localSource}. Apply configuration first (Deploy).`,
            localSource
        };
    }

    try {
        const result = await runPythonTransfer({
            local_source: localSource,
            remote_user: remoteUser,
            remote_host: remoteHost,
            remote_password: remotePassword,
            remote_dir: remoteDir,
            remote_file: remoteFile,
            remote_backup: remoteBackup
        });
        return result;
    } catch (err) {
        return {
            success: false,
            error: err.message || String(err),
            localSource,
            remoteHost
        };
    }
}

module.exports = {
    DEFAULT_LOCAL_SOURCE,
    DEFAULT_REMOTE_HOST,
    DEFAULT_REMOTE_DIR,
    transferCuSimnovusConf
};

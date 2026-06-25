/**
 * Test Deployment: copy ~/Config/cu_simnovus.conf → cu_simnovus_test.conf,
 * then apply UI field values to the test file only (source is never modified).
 * Line numbers are 1-based per deployment spec.
 */
const fs = require('fs');
const os = require('os');
const path = require('path');

const CONFIG_DIR = path.join(os.homedir(), 'Config');
const SOURCE_CONF_PATH = path.join(CONFIG_DIR, 'cu_simnovus_default.conf');
const DEFAULT_TARGET_CONF_PATH = path.join(CONFIG_DIR, 'cu_simnovus.conf');

/** @deprecated Use SOURCE_CONF_PATH / DEFAULT_TARGET_CONF_PATH */
const DEFAULT_CONF_PATH = DEFAULT_TARGET_CONF_PATH;

const LINE_ABSOLUTE_FREQUENCY_SSB = [85];
const LINE_FREQUENCY_BAND = [86, 108];
const LINE_SUBCARRIER_SPACING = [93, 113];
const LINE_LOG_LEVELS = {
    mac: 258,
    rlc: 260,
    pdcp: 261,
    rrc: 262
};

const LOG_LEVEL_KEYS = {
    mac: 'mac_log_level',
    rlc: 'rlc_log_level',
    pdcp: 'pdcp_log_level',
    rrc: 'rrc_log_level'
};

function assignNumericOnLine(line, newValue) {
    if (line == null) return line;
    const value = String(newValue).trim();
    const assignMatch = line.match(/^(\s*)([A-Za-z0-9_.\[\]-]+)\s*=\s*([^;]*)(;?)(.*)$/);
    if (assignMatch) {
        const indent = assignMatch[1] || '';
        const key = assignMatch[2];
        const semi = assignMatch[4] || '';
        const tail = assignMatch[5] || '';
        return `${indent}${key} = ${value}${semi}${tail}`;
    }
    if (/^\s*-?\d+(\.\d+)?\s*;?\s*$/.test(line.trim())) {
        return line.replace(/-?\d+(\.\d+)?/, value);
    }
    return line.replace(/-?\d+(\.\d+)?/, value);
}

function assignQuotedOnLine(line, newValue) {
    if (line == null) return line;
    const value = String(newValue).toLowerCase().trim();
    const quoted = `"${value}"`;
    const keyMatch = line.match(/^(\s*)([A-Za-z0-9_]+)\s*=\s*([^;]*)(;?)(.*)$/);
    if (keyMatch) {
        const indent = keyMatch[1] || '';
        const key = keyMatch[2];
        const semi = keyMatch[4] || '';
        const tail = keyMatch[5] || '';
        return `${indent}${key} = ${quoted}${semi}${tail}`;
    }
    return line.replace(/"[^"]*"/, quoted);
}

function setLinesNumeric(lines, lineNumbers, value) {
    const updated = [];
    lineNumbers.forEach((lineNum) => {
        const idx = lineNum - 1;
        if (idx < 0 || idx >= lines.length) return;
        lines[idx] = assignNumericOnLine(lines[idx], value);
        updated.push(lineNum);
    });
    return updated;
}

function setLinesQuoted(lines, lineNumbers, value) {
    const updated = [];
    lineNumbers.forEach((lineNum) => {
        const idx = lineNum - 1;
        if (idx < 0 || idx >= lines.length) return;
        lines[idx] = assignQuotedOnLine(lines[idx], value);
        updated.push(lineNum);
    });
    return updated;
}

function patchLogLevelsByKey(lines, logLevels) {
    const updated = [];
    Object.entries(LOG_LEVEL_KEYS).forEach(([layer, keyName]) => {
        const level = logLevels[layer];
        if (!level) return;
        for (let i = 0; i < lines.length; i++) {
            const re = new RegExp(`\\b${keyName}\\b`);
            if (re.test(lines[i])) {
                lines[i] = assignQuotedOnLine(lines[i], level);
                updated.push({ line: i + 1, key: keyName, value: level });
            }
        }
    });
    return updated;
}

function applyPatchesToLines(lines, params, changes) {
    const ssb = String(params.absoluteFrequencySSB ?? '').trim();
    if (ssb) {
        setLinesNumeric(lines, LINE_ABSOLUTE_FREQUENCY_SSB, ssb).forEach((ln) => {
            changes.push({ field: 'absoluteFrequencySSB', line: ln, value: ssb });
        });
    }

    const band = String(params.frequencyBand ?? '').trim();
    if (band) {
        setLinesNumeric(lines, LINE_FREQUENCY_BAND, band).forEach((ln) => {
            changes.push({ field: 'frequencyBand', line: ln, value: band });
        });
    }

    const scs = String(params.subcarrierSpacing ?? '').trim();
    if (scs !== '') {
        setLinesNumeric(lines, LINE_SUBCARRIER_SPACING, scs).forEach((ln) => {
            changes.push({ field: 'subcarrierSpacing', line: ln, value: scs });
        });
    }

    const logLevels = params.logLevels || {};
    Object.entries(LINE_LOG_LEVELS).forEach(([layer, lineNum]) => {
        const level = logLevels[layer];
        if (!level) return;
        setLinesQuoted(lines, [lineNum], level).forEach((ln) => {
            changes.push({ field: `${layer}_log_level`, line: ln, value: level });
        });
    });
    patchLogLevelsByKey(lines, logLevels).forEach((entry) => {
        changes.push({ field: entry.key, line: entry.line, value: entry.value, via: 'key' });
    });
}

/**
 * @param {object} params
 * @param {string} params.absoluteFrequencySSB
 * @param {string} params.frequencyBand
 * @param {string|number} params.subcarrierSpacing
 * @param {{ mac?: string, rlc?: string, pdcp?: string, rrc?: string }} params.logLevels
 * @param {string} [sourcePath]
 * @param {string} [targetPath]
 */
function applyCuSimnovusConfPatch(
    params,
    sourcePath = SOURCE_CONF_PATH,
    targetPath = DEFAULT_TARGET_CONF_PATH
) {
    if (!params || typeof params !== 'object') {
        return { success: false, error: 'Invalid patch parameters' };
    }

    if (!fs.existsSync(sourcePath)) {
        return {
            success: false,
            error: `Source config not found: ${sourcePath}`,
            sourcePath,
            confPath: targetPath
        };
    }

    let content;
    try {
        content = fs.readFileSync(sourcePath, 'utf8');
    } catch (err) {
        return {
            success: false,
            error: err.message || String(err),
            sourcePath,
            confPath: targetPath
        };
    }

    const lines = content.split(/\r?\n/);
    const changes = [];
    applyPatchesToLines(lines, params, changes);

    try {
        fs.mkdirSync(path.dirname(targetPath), { recursive: true });
        fs.writeFileSync(targetPath, lines.join('\n'), 'utf8');
    } catch (err) {
        return {
            success: false,
            error: err.message || String(err),
            sourcePath,
            confPath: targetPath
        };
    }

    return {
        success: true,
        sourcePath,
        confPath: targetPath,
        targetPath,
        changes
    };
}

module.exports = {
    CONFIG_DIR,
    SOURCE_CONF_PATH,
    DEFAULT_TARGET_CONF_PATH,
    DEFAULT_CONF_PATH,
    applyCuSimnovusConfPatch
};

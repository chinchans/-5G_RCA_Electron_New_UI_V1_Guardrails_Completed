const { contextBridge, ipcRenderer } = require('electron');

// Expose Electron IPC helpers under electronAPI (not "API") so the renderer
 // can freely own window.API for HTTP helpers without fighting a frozen bridge object.
contextBridge.exposeInMainWorld('electronAPI', {
    showOpenDirectoryDialog: async (title = 'Select folder') => {
        return await ipcRenderer.invoke('show-open-directory-dialog', { title });
    },
    listFilesInDirectory: async (folderPath) => {
        return await ipcRenderer.invoke('list-files-in-directory', { folderPath });
    },
    readFileForUpload: async (filePath, workingDirectory) => {
        return await ipcRenderer.invoke('read-file-for-upload', { filePath, workingDirectory });
    },
    getBackendExtractRoot: async () => {
        return await ipcRenderer.invoke('get-backend-extract-root');
    },
    launchWifiApp: async () => {
        return await ipcRenderer.invoke('launch-wifi-app');
    },
    applyCuSimnovusConf: async (params, options = {}) => {
        return await ipcRenderer.invoke('apply-cu-simnovus-conf', {
            params,
            confPath: options.confPath,
            openAfterWrite: !!options.openAfterWrite
        });
    },
    transferCuSimnovusConf: async (options = {}) => {
        return await ipcRenderer.invoke('transfer-cu-simnovus-conf', options);
    }
});

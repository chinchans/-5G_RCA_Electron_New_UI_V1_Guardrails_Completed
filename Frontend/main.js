const { app, BrowserWindow, dialog, ipcMain, shell } = require('electron');
const fs = require('fs');
const path = require('path');
const { spawn } = require('child_process');
const {
    applyCuSimnovusConfPatch,
    SOURCE_CONF_PATH,
    DEFAULT_TARGET_CONF_PATH
} = require('./cuSimnovusConfPatch');
const { transferCuSimnovusConf } = require('./cuSimnovusTransfer');

let mainWindow;

function createWindow() {
    // Create the browser window
    mainWindow = new BrowserWindow({
        width: 1400,
        height: 900,
        webPreferences: {
            nodeIntegration: false,
            contextIsolation: true,
            preload: path.join(__dirname, 'preload.js')
        },
        icon: path.join(__dirname, 'assets/icon.png'), // Optional: add an icon
        show: false, // Don't show until ready
        titleBarStyle: 'default',
        autoHideMenuBar: true, // Hide the menu bar
        menuBarVisible: false   // Ensure menu bar is hidden
    });

    // Load the main HTML file
    mainWindow.loadFile('index.html');

    // Show window when ready to prevent visual flash
    mainWindow.once('ready-to-show', () => {
        mainWindow.show();
        
        // Optional: Open DevTools in development
        if (process.env.NODE_ENV === 'development') {
            mainWindow.webContents.openDevTools();
        }
    });

    // Handle window closed
    mainWindow.on('closed', () => {
        mainWindow = null;
    });
}

// App event listeners
app.whenReady().then(() => {
    createWindow();

    // On macOS, re-create window when dock icon is clicked
    app.on('activate', () => {
        if (BrowserWindow.getAllWindows().length === 0) {
            createWindow();
        }
    });
});

// IPC handlers for folder dialog and file listing
ipcMain.handle('show-open-directory-dialog', async (event, { title }) => {
    const result = await dialog.showOpenDialog({
        properties: ['openDirectory'],
        title: title || 'Select folder',
    });
    return result.filePaths;
});

ipcMain.handle('list-files-in-directory', async (event, { folderPath }) => {
    try {
        const files = fs.readdirSync(folderPath)
            .filter((file) => {
                try {
                    return fs.statSync(path.join(folderPath, file)).isFile();
                } catch {
                    return false;
                }
            })
            .map((file) => ({
                name: file,
                path: path.join(folderPath, file),
                size: fs.statSync(path.join(folderPath, file)).size
            }));
        return files;
    } catch (e) {
        return [];
    }
});

function getBackendExtractRoot() {
    const backendRoot = path.join(path.resolve(__dirname, '..'), 'Backend');
    const primary = path.join(backendRoot, 'extract');
    const legacy = path.join(backendRoot, 'resources', 'extract');
    try {
        if (fs.existsSync(primary)) return primary;
    } catch (_) { /* fall through */ }
    return legacy;
}

/** Resolve dataset file paths that may be relative to Backend, not Electron cwd (Frontend). */
function resolveDatasetFilePath(filePath, workingDirectory) {
    if (!filePath || typeof filePath !== 'string') return null;

    const backendExtract = getBackendExtractRoot();
    const backendRoot = path.join(path.resolve(__dirname, '..'), 'Backend');
    const normalizedInput = filePath.replace(/\\/g, '/');
    const candidates = [];

    const addCandidate = (p) => {
        if (!p) return;
        try {
            candidates.push(path.normalize(p));
        } catch (_) {
            /* ignore invalid paths */
        }
    };

    addCandidate(filePath);

    if (path.isAbsolute(filePath)) {
        addCandidate(filePath);
    } else {
        // Wrong default: path.resolve(filePath) uses process.cwd() (often Frontend/)
        addCandidate(path.resolve(process.cwd(), filePath));
        addCandidate(path.resolve(__dirname, filePath));

        const rel = normalizedInput.replace(/^\.?\//, '');
        const relNoExtractPrefix = rel.replace(/^extract\//, '').replace(/^resources\/extract\//, '');

        addCandidate(path.join(backendExtract, relNoExtractPrefix));
        addCandidate(path.join(backendExtract, rel));
        addCandidate(path.join(backendRoot, rel));
        addCandidate(path.join(backendRoot, 'extract', relNoExtractPrefix));
        addCandidate(path.join(backendRoot, 'resources', 'extract', relNoExtractPrefix));

        if (rel.includes('datasets/')) {
            const fromDatasets = rel.substring(rel.indexOf('datasets/'));
            addCandidate(path.join(backendExtract, fromDatasets));
        }

        if (workingDirectory && typeof workingDirectory === 'string') {
            addCandidate(path.resolve(workingDirectory, filePath));
            addCandidate(path.join(workingDirectory, relNoExtractPrefix));
            addCandidate(path.join(workingDirectory, rel));
            if (relNoExtractPrefix && !relNoExtractPrefix.startsWith('datasets/')) {
                addCandidate(path.join(workingDirectory, 'datasets', relNoExtractPrefix));
            }
        }
    }

    const seen = new Set();
    for (const candidate of candidates) {
        if (!candidate || seen.has(candidate)) continue;
        seen.add(candidate);
        try {
            if (fs.existsSync(candidate) && fs.statSync(candidate).isFile()) {
                return candidate;
            }
        } catch (_) {
            /* try next candidate */
        }
    }

    return null;
}

// Read a file from disk for staging in the renderer (e.g. total_content.txt → Test Script Generator upload)
ipcMain.handle('read-file-for-upload', async (event, { filePath, workingDirectory }) => {
    try {
        if (!filePath || typeof filePath !== 'string') {
            return { success: false, error: 'No file path provided' };
        }
        const resolved = resolveDatasetFilePath(filePath, workingDirectory);
        if (!resolved) {
            return {
                success: false,
                error: `File not found: ${filePath} (searched under Backend/extract and Backend/resources/extract)`
            };
        }
        const stat = fs.statSync(resolved);
        if (!stat.isFile()) {
            return { success: false, error: 'Path is not a file' };
        }
        const content = fs.readFileSync(resolved, 'utf-8');
        return {
            success: true,
            name: path.basename(resolved),
            path: resolved,
            size: stat.size,
            content
        };
    } catch (e) {
        return { success: false, error: e.message || String(e) };
    }
});

ipcMain.handle('get-backend-extract-root', async () => {
    return { success: true, extractRoot: getBackendExtractRoot() };
});

ipcMain.handle('apply-cu-simnovus-conf', async (event, payload = {}) => {
    try {
        const sourcePath = payload.sourcePath || SOURCE_CONF_PATH;
        const targetPath = payload.confPath || payload.targetPath || DEFAULT_TARGET_CONF_PATH;
        const result = applyCuSimnovusConfPatch(
            payload.params || payload,
            sourcePath,
            targetPath
        );
        if (result.success && payload.openAfterWrite) {
            await shell.openPath(targetPath);
        }
        return result;
    } catch (e) {
        return { success: false, error: e.message || String(e) };
    }
});

ipcMain.handle('transfer-cu-simnovus-conf', async (event, options = {}) => {
    try {
        return await transferCuSimnovusConf(options);
    } catch (e) {
        return { success: false, error: e.message || String(e) };
    }
});

// IPC handler to launch WiFi JavaFX application and FastAPI backend
ipcMain.handle('launch-wifi-app', async (event) => {
    try {
        // Get paths - Windows structure: WiFi_Test_Automation_Framework_Latest_Version-main/fastapi_javafx_app
        const basePath = path.resolve(__dirname, '..', '..', 'WiFi_Test_Automation_Framework_Latest_Version-main');
        const appPath = path.join(basePath, 'fastapi_javafx_app');
        const backendPath = path.join(appPath, 'backend');
        const frontendPath = path.join(appPath, 'frontend');
        const venvPython = path.join(basePath, 'venv', 'Scripts', 'python.exe'); // venv is at root level
        const backendMain = path.join(backendPath, 'app', 'main.py');
        const javafxMain = path.join(frontendPath, 'src', 'main', 'java', 'com', 'yourorg', 'javafxapp', 'Main.java');
        const targetClasses = path.join(frontendPath, 'target', 'classes');
        const libPath = path.join(frontendPath, 'lib');
        
        // Try multiple possible JavaFX SDK locations - prioritize JavaFX 21 (matches Java 21)
        const possibleJavaFxPaths = [
            path.join(process.env.USERPROFILE, 'Downloads', 'openjfx-21.0.9_windows-x64_bin-sdk', 'javafx-sdk-21.0.9', 'lib'), // Your actual JavaFX 21 location
            'C:\\Program Files\\Java\\javafx-sdk-21\\lib',       // Program Files (JavaFX 21) - matches your command structure
            path.join(process.env.USERPROFILE, 'javafx-sdk-21', 'lib'),      // User folder (JavaFX 21)
            path.join(process.env.USERPROFILE, 'Downloads', 'javafx-sdk-21', 'lib'),     // Downloads folder (JavaFX 21)
            'C:\\Program Files\\Java\\javafx-sdk-24.0.1\\lib',  // Fallback to 24 if 21 not found
        ];
        
        let javafxLib = null;
        for (const possiblePath of possibleJavaFxPaths) {
            if (fs.existsSync(possiblePath)) {
                javafxLib = possiblePath;
                console.log('Found JavaFX SDK at:', javafxLib);
                break;
            }
        }
        
        if (!javafxLib) {
            return { 
                success: false, 
                error: `JavaFX SDK not found. Please ensure JavaFX SDK 21 (to match Java 21) is installed at one of these locations:\n` +
                       `- ${path.join(process.env.USERPROFILE, 'Downloads', 'openjfx-21.0.9_windows-x64_bin-sdk', 'javafx-sdk-21.0.9', 'lib')}\n` +
                       `- ${path.join(process.env.USERPROFILE, 'javafx-sdk-21', 'lib')}\n` +
                       `- ${path.join(process.env.USERPROFILE, 'Downloads', 'javafx-sdk-21', 'lib')}\n` +
                       `Or install to C:\\Program Files\\Java\\javafx-sdk-21\\lib (requires admin)`
            };
        }
        
        console.log('=== Launching WiFi App ===');
        console.log('Backend path:', backendPath);
        console.log('Frontend path:', frontendPath);
        
        // Check if paths exist
        if (!fs.existsSync(backendPath)) {
            return { success: false, error: `Backend folder not found at: ${backendPath}` };
        }
        if (!fs.existsSync(frontendPath)) {
            return { success: false, error: `Frontend folder not found at: ${frontendPath}` };
        }
        if (!fs.existsSync(venvPython)) {
            return { success: false, error: `Virtual environment not found at: ${venvPython}. Please ensure venv is created in WiFi_Test_Automation_Framework_Latest_Version-main folder.` };
        }
        
        // Start FastAPI backend (runs on port 8001) - in a visible terminal window
        // Backend path: fastapi_javafx_app\backend
        console.log('Starting FastAPI backend on port 8001...');
        console.log('Backend path:', backendPath);
        console.log('Venv Python:', venvPython);
        
        // Build command - backend path is: fastapi_javafx_app\backend
        // Need to cd to backend folder and run uvicorn
        const backendCmd = `cd /d "${backendPath}" && "${venvPython}" -m uvicorn app.main:app --host 0.0.0.0 --port 8001`;
        console.log('Backend command:', backendCmd);
        
        // Launch in new terminal window - run command directly
        const backendFullCmd = `cd /d "${backendPath}" && "${venvPython}" -m uvicorn app.main:app --host 0.0.0.0 --port 8001`;
        console.log('Executing backend command:', backendFullCmd);
        // Use shell: true to properly parse the command string
        spawn(`start "WiFi Backend" cmd /k "${backendFullCmd}"`, [], {
            detached: true,
            stdio: 'ignore',
            shell: true
        });
        
        // Wait a bit for backend to start
        await new Promise(resolve => setTimeout(resolve, 3000));
        
        // Compile JavaFX if needed - using exact command structure from user
        const mainClass = path.join(targetClasses, 'com', 'yourorg', 'javafxapp', 'Main.class');
        
        // Force recompilation to ensure Java 21 compatibility (delete old compiled classes)
        if (fs.existsSync(mainClass)) {
            console.log('Removing old compiled classes to force Java 21 recompilation...');
            try {
                fs.rmSync(targetClasses, { recursive: true, force: true });
            } catch (e) {
                console.log('Could not remove old classes:', e.message);
            }
        }
        
        if (!fs.existsSync(mainClass)) {
            console.log('Compiling JavaFX application with Java 21...');
            
            // Create target/classes directory if it doesn't exist
            if (!fs.existsSync(targetClasses)) {
                fs.mkdirSync(targetClasses, { recursive: true });
            }
            
            // Use EXACT command structure from user with Java 21 flags: javac -source 21 -target 21 -d target\classes -sourcepath src\main\java -cp ".;lib\*;javafx-lib\*" --module-path javafx-lib --add-modules javafx.controls,javafx.fxml src\main\java\com\yourorg\javafxapp\Main.java
            // Build classpath properly - single quoted string with semicolon-separated paths
            const libPathPart = libPath ? `${libPath}\\*` : '';
            const javafxLibPart = `${javafxLib}\\*`;
            const classpath = libPath ? `.;${libPathPart};${javafxLibPart}` : `.;${javafxLibPart}`;
            
            // Build the exact command with Java 21 flags - classpath is one quoted string
            const compileCmd = `javac -source 21 -target 21 -d target\\classes -sourcepath src\\main\\java -cp "${classpath}" --module-path "${javafxLib}" --add-modules javafx.controls,javafx.fxml src\\main\\java\\com\\yourorg\\javafxapp\\Main.java`;
            
            console.log('Compilation command:', compileCmd);
            
            const compileProcess = spawn(compileCmd, [], {
                cwd: frontendPath,
                shell: true
            });
            
            let compileOutput = '';
            let compileError = '';
            
            compileProcess.stdout.on('data', (data) => {
                compileOutput += data.toString();
            });
            
            compileProcess.stderr.on('data', (data) => {
                compileError += data.toString();
            });
            
            await new Promise((resolve, reject) => {
                compileProcess.on('close', (code) => {
                    if (code !== 0) {
                        console.error('Compilation error:', compileError);
                        reject(new Error(`Compilation failed: ${compileError || 'Unknown error'}`));
                    } else {
                        console.log('Compilation successful');
                        resolve();
                    }
                });
                compileProcess.on('error', (err) => {
                    reject(new Error(`Failed to start compilation: ${err.message}`));
                });
            });
        } else {
            console.log('JavaFX already compiled, skipping compilation');
        }
        
        // Run JavaFX application - using EXACT command structure from user (with JavaFX 21): java -cp "target\classes;lib\*;C:\Program Files\Java\javafx-sdk-21\lib\*" --module-path "C:\Program Files\Java\javafx-sdk-21\lib" --add-modules javafx.controls,javafx.fxml com.yourorg.javafxapp.Main
        console.log('Starting JavaFX application...');
        
        // Build classpath properly - single quoted string with semicolon-separated paths
        const libPathPart = libPath ? `${libPath}\\*` : '';
        const javafxLibPart = `${javafxLib}\\*`;
        const javaClasspath = libPath ? `target\\classes;${libPathPart};${javafxLibPart}` : `target\\classes;${javafxLibPart}`;
        
        // Build the exact command - classpath is one quoted string (matching user's format with version 21)
        const javaCmd = `java -cp "${javaClasspath}" --module-path "${javafxLib}" --add-modules javafx.controls,javafx.fxml com.yourorg.javafxapp.Main`;
        
        console.log('Java execution command:', javaCmd);
        
        // Launch in a visible terminal window - run command directly
        const javaFullCmd = `cd /d "${frontendPath}" && ${javaCmd}`;
        console.log('Executing Java command:', javaFullCmd);
        // Use shell: true to properly parse the command string
        spawn(`start "WiFi JavaFX" cmd /k "${javaFullCmd}"`, [], {
            detached: true,
            stdio: 'ignore',
            shell: true
        });
        
        return { success: true, message: 'WiFi application launched successfully' };
    } catch (error) {
        console.error('Error launching WiFi app:', error);
        return { success: false, error: error.message };
    }
});

// Quit when all windows are closed
app.on('window-all-closed', () => {
    // On macOS, keep app running even when all windows are closed
    if (process.platform !== 'darwin') {
        app.quit();
    }
});

// Security: Prevent new window creation
app.on('web-contents-created', (event, contents) => {
    contents.on('new-window', (event, navigationUrl) => {
        event.preventDefault();
    });
});

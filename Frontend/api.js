// API Configuration and Helper Functions
// Centralized API management for the RCA Frontend

// Backend API Configuration
const API_BASE_URL = 'http://127.0.0.1:8000';

/**
 * Parse FastAPI 422 guardrail rejection bodies (upload / dataset load).
 * Returns structured fields for UI modals regardless of which upload code path ran.
 */
function parseGuardrailHttpErrorBody(errorText) {
    const result = {
        message: errorText,
        guardrailDetail: null,
        guardrailFindings: [],
        guardrailReasons: [],
        isGuardrailBlock: false,
    };
    try {
        const parsed = JSON.parse(errorText);
        const detail = parsed.detail;
        if (typeof detail === 'object' && detail !== null) {
            result.guardrailDetail = detail;
            result.guardrailFindings = detail.findings
                || detail.guardrails?.scan?.findings
                || [];
            result.guardrailReasons = Array.isArray(detail.reasons) ? detail.reasons : [];
            result.message = detail.message || result.message;
            if (detail.error) {
                result.isGuardrailBlock = detail.error === 'document_blocked_by_guardrails';
                result.message = `${detail.error}: ${result.message}`;
            }
            if (result.guardrailReasons.length) {
                result.message += ` (${result.guardrailReasons.join('; ')})`;
            }
        } else if (typeof detail === 'string') {
            result.message = detail;
        }
    } catch (_e) {
        /* use raw errorText */
    }
    return result;
}

function attachGuardrailFieldsToError(err, errorText) {
    const info = parseGuardrailHttpErrorBody(errorText);
    err.guardrailDetail = info.guardrailDetail;
    err.guardrailFindings = info.guardrailFindings;
    err.guardrailReasons = info.guardrailReasons;
    err.isGuardrailBlock = info.isGuardrailBlock;
    return err;
}

if (typeof window !== 'undefined') {
    if (!window.API) window.API = {};
    window.API.parseGuardrailHttpErrorBody = parseGuardrailHttpErrorBody;
    window.API.attachGuardrailFieldsToError = attachGuardrailFieldsToError;
}

// Generic API call helper
async function makeAPICall(endpoint, method = 'GET', data = null) {
    try {
        const options = {
            method: method,
            headers: {
                'Content-Type': 'application/json',
            },
        };

        if (data) {
            options.body = JSON.stringify(data);
        }

        const response = await fetch(`${API_BASE_URL}${endpoint}`, options);
        
        if (!response.ok) {
            // Try to extract error message from response body
            // Note: We can only read response body once, so clone it first
            let errorMessage = `HTTP error! status: ${response.status}`;
            
            // Clone response to read it safely
            const responseClone = response.clone();
            try {
                const errorData = await responseClone.json();
                if (errorData.detail) {
                    errorMessage = errorData.detail;
                } else if (errorData.message) {
                    errorMessage = errorData.message;
                } else if (errorData.error) {
                    errorMessage = errorData.error;
                }
            } catch (e) {
                // If response is not JSON, try to get text from original response
                try {
                    const errorText = await response.text();
                    if (errorText && errorText.trim()) {
                        errorMessage = errorText.trim();
                    }
                } catch (e2) {
                    // If that also fails, use default message with status
                    console.warn('Could not extract error message from response:', e2);
                }
            }
            
            const error = new Error(errorMessage);
            error.status = response.status;
            error.response = response;
            throw error;
        }
        
        return await response.json();
    } catch (error) {
        console.error('API call failed:', error);
        console.error('  - Endpoint:', endpoint);
        console.error('  - Method:', method);
        console.error('  - Error message:', error.message);
        throw error;
    }
}

// Health check API
async function checkBackendHealth() {
    try {
        console.log('Testing backend connection to:', API_BASE_URL);
        const response = await fetch(`${API_BASE_URL}/health`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
            }
            // Removed mode: 'cors' to match working endpoints (Bug Discovery, Code Assistant)
        });
        
        console.log('Response status:', response.status);
        
        if (response.ok) {
            const result = await response.json();
            console.log('✅ Backend is running:', result);
            return result;
        } else {
            console.error('❌ Backend health check failed:', response.status);
            const errorText = await response.text();
            console.error('Error response:', errorText);
            throw new Error(`Health check failed: ${response.status}`);
        }
    } catch (error) {
        console.error('❌ Backend connection failed:', error);
        console.error('🔧 Troubleshooting steps:');
        console.error('1. Make sure the backend is running: cd Backend && python main.py');
        console.error('2. Check if the backend is accessible at:', API_BASE_URL);
        console.error('3. Try opening', API_BASE_URL + '/health', 'in your browser');
        console.error('4. Check for firewall or antivirus blocking the connection');
        console.error('5. Verify the backend is running on port 8000');
        throw error;
    }
}

// Dataset Generator API Functions
async function uploadDocument(file) {
    console.log('Starting document upload for file:', file.name);
    const formData = new FormData();
    formData.append('file', file);
    
    try {
        console.log('Making API call to:', `${API_BASE_URL}/api/dataset/upload-document`);
        const response = await fetch(`${API_BASE_URL}/api/dataset/upload-document`, {
            method: 'POST',
            body: formData
        });
        
        console.log('API response status:', response.status);
        console.log('API response headers:', response.headers);
        
        if (!response.ok) {
            const errorText = await response.text();
            console.error('API error response:', errorText);
            const info = parseGuardrailHttpErrorBody(errorText);
            const err = new Error(`HTTP error! status: ${response.status} - ${info.message}`);
            attachGuardrailFieldsToError(err, errorText);
            throw err;
        }
        
        const result = await response.json();
        console.log('Upload successful, result:', result);
        return result;
    } catch (error) {
        console.error('Document upload failed:', error);
        throw error;
    }
}

// CRITICAL: Immediately assign uploadDocument to window.API as soon as function is defined
// This ensures it's available even if later initialization code fails
if (typeof window !== 'undefined') {
    if (!window.API) {
        window.API = {};
    }
    window.API.uploadDocument = uploadDocument;
    console.log('[api.js] ✅ IMMEDIATE: uploadDocument assigned to window.API right after definition');
}

async function getDocumentSections(fileId) {
    return await makeAPICall(`/api/dataset/document-sections/${fileId}`);
}

async function getDocumentSubsections(fileId, section) {
    return await makeAPICall(`/api/dataset/document-subsections/${fileId}/${encodeURIComponent(section)}`);
}

async function setWorkingDirectory(directoryPath) {
    const formData = new FormData();
    formData.append('directory_path', directoryPath);
    
    const response = await fetch(`${API_BASE_URL}/api/dataset/set-working-directory`, {
        method: 'POST',
        body: formData
    });
    
    if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    return await response.json();
}

async function setOutputDirectory(directoryPath) {
    const formData = new FormData();
    formData.append('directory_path', directoryPath);
    
    const response = await fetch(`${API_BASE_URL}/api/dataset/set-output-directory`, {
        method: 'POST',
        body: formData
    });
    
    if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    return await response.json();
}

async function generateDataset(fileId, section, subsection, workingDir, outputDir) {
    const formData = new FormData();
    formData.append('file_id', fileId);
    formData.append('section', section);
    formData.append('subsection', subsection);
    formData.append('working_directory', workingDir);
    formData.append('output_directory', outputDir);
    
    const response = await fetch(`${API_BASE_URL}/api/dataset/generate`, {
        method: 'POST',
        body: formData
    });
    
    
    if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    return await response.json();
}

// NEW: PyQt-style synchronous dataset extraction
async function generateDatasetPyQtStyle(fileId, section, subsection, workingDir, outputDir) {
    const formData = new FormData();
    formData.append('file_id', fileId);
    formData.append('section', section);
    formData.append('subsection', subsection);
    formData.append('working_directory', workingDir);
    formData.append('output_directory', outputDir);
    
    console.log('Calling PyQt-style extraction endpoint...');
    
    const response = await fetch(`${API_BASE_URL}/api/dataset/extract-pyqt-style`, {
        method: 'POST',
        body: formData
    });
    
    if (!response.ok) {
        const errorText = await response.text();
        let detailMessage = errorText;
        let outputGuardrails = null;
        try {
            const parsed = JSON.parse(errorText);
            const detail = parsed.detail;
            if (typeof detail === 'string') {
                detailMessage = detail;
            } else if (typeof detail === 'object' && detail?.message) {
                detailMessage = detail.message;
                if (detail.error === 'dataset_output_guardrails_failed' && Array.isArray(detail.reasons) && detail.reasons.length) {
                    const preview = detail.reasons.slice(0, 4).join('; ');
                    detailMessage = `${detail.message} ${preview}`;
                }
                outputGuardrails = detail.output_guardrails || null;
            }
        } catch (_e) { /* use raw */ }
        const err = new Error(`HTTP error! status: ${response.status}, message: ${detailMessage}`);
        if (outputGuardrails) {
            err.outputGuardrails = outputGuardrails;
        }
        throw err;
    }
    
    return await response.json();
}

// Get extract folder path
async function getExtractFolderPath() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/dataset/extract-folder-path`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
            }
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
        }

        return await response.json();
    } catch (error) {
        console.error('Failed to get extract folder path:', error);
        throw error;
    }
}

// Open folder in Explorer
async function openFolderInExplorer(folderPath) {
    try {
        const response = await fetch(`${API_BASE_URL}/api/dataset/open-folder`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ folder_path: folderPath })
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
        }

        return await response.json();
    } catch (error) {
        console.error('Failed to open folder:', error);
        throw error;
    }
}

async function getDatasetStatus(jobId) {
    return await makeAPICall(`/api/dataset/status/${jobId}`);
}

async function downloadDataset(jobId) {
    const response = await fetch(`${API_BASE_URL}/api/dataset/download/${jobId}`);
    
    if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    return response;
}

async function getDatasetFiles(jobId) {
    return await makeAPICall(`/api/dataset/files/${jobId}`);
}

// Test Script Generator API Functions

// File upload helper for multipart/form-data
async function uploadFile(endpoint, file, additionalData = {}) {
    try {
        const formData = new FormData();
        formData.append('file', file);
        
        // Add additional form data
        for (const [key, value] of Object.entries(additionalData)) {
            formData.append(key, value);
        }

        const response = await fetch(`${API_BASE_URL}${endpoint}`, {
            method: 'POST',
            body: formData,
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        return await response.json();
    } catch (error) {
        console.error('File upload failed:', error);
        throw error;
    }
}

// Multiple files upload helper
async function uploadMultipleFiles(endpoint, files, additionalData = {}) {
    try {
        const formData = new FormData();
        
        // Append multiple files
        files.forEach(file => {
            formData.append('files', file);
        });
        
        // Add additional form data
        for (const [key, value] of Object.entries(additionalData)) {
            formData.append(key, value);
        }

        const response = await fetch(`${API_BASE_URL}${endpoint}`, {
            method: 'POST',
            body: formData,
        });

        if (!response.ok) {
            const errorText = await response.text();
            let detailMessage = errorText;
            let outputGuardrails = null;
            try {
                const parsed = JSON.parse(errorText);
                const detail = parsed.detail;
                if (typeof detail === 'string') {
                    detailMessage = detail;
                } else if (typeof detail === 'object' && detail?.message) {
                    detailMessage = detail.message;
                    if (detail.error === 'document_blocked_by_guardrails' && Array.isArray(detail.reasons) && detail.reasons.length) {
                        detailMessage = `${detail.message} ${detail.reasons.slice(0, 3).join('; ')}`;
                    }
                    if (detail.error === 'dataset_output_guardrails_failed' && Array.isArray(detail.reasons) && detail.reasons.length) {
                        detailMessage = `${detail.message} ${detail.reasons.slice(0, 3).join('; ')}`;
                    }
                    outputGuardrails = detail.output_guardrails || null;
                }
            } catch (_e) { /* use raw */ }
            const err = new Error(`HTTP error! status: ${response.status}, message: ${detailMessage}`);
            if (outputGuardrails) {
                err.outputGuardrails = outputGuardrails;
            }
            throw err;
        }

        return await response.json();
    } catch (error) {
        console.error('Multiple files upload failed:', error);
        throw error;
    }
}

// Get available prompt templates
async function getPromptTemplates() {
    return await makeAPICall('/api/test-script/prompts');
}

// Generate test script
async function generateTestScript(promptKey, textContent, variables = null, customPrompt = null) {
    const requestData = {
        prompt_key: promptKey,
        text_content: textContent,
        variables: variables,
        custom_prompt: customPrompt
    };
    
    return await makeAPICall('/api/test-script/generate', 'POST', requestData);
}

// Refine existing test script
async function refineTestScript(textContent, newPrompt, previousResponse = null) {
    const requestData = {
        text_content: textContent,
        new_prompt: newPrompt,
        previous_response: previousResponse
    };
    
    return await makeAPICall('/api/test-script/refine', 'POST', requestData);
}

// IMMEDIATE: Assign refineTestScript to window.API right after definition
if (typeof window !== 'undefined') {
    if (!window.API) {
        window.API = {};
    }
    window.API.refineTestScript = refineTestScript;
    console.log('[api.js] ✅ IMMEDIATE: refineTestScript assigned to window.API right after definition');
}

// Upload reference code file
async function uploadReferenceCode(file) {
    return await uploadFile('/api/test-script/upload-reference', file);
}

// Load dataset from multiple files
async function loadTestDataset(files) {
    return await uploadMultipleFiles('/api/test-script/load-dataset', files);
}

// Get available test types
async function getTestTypes() {
    return await makeAPICall('/api/test-script/test-types');
}

// Generate test by specific type
async function generateTestByType(testType, inputText, outputDirectory = null) {
    const formData = new FormData();
    formData.append('test_type', testType);
    formData.append('input_text', inputText);
    if (outputDirectory) {
        formData.append('output_directory', outputDirectory);
    }

    const response = await fetch(`${API_BASE_URL}/api/test-script/generate-by-type`, {
        method: 'POST',
        body: formData,
    });

    if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
    }

    return await response.json();
}

async function saveTestScriptResponse(content, templateType, language = "Python") {
    try {
        const response = await fetch(`${API_BASE_URL}/api/save-test-script`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                content: content,
                template_type: templateType,
                language: language
            })
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        return await response.json();
    } catch (error) {
        console.error('Error saving test script:', error);
        throw error;
    }
}

// Save or update template prompt
async function saveTemplatePrompt(templateName, templateContent) {
    try {
        const response = await fetch(`${API_BASE_URL}/api/test-script/save-template`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                template_name: templateName,
                template_content: templateContent
            })
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        return await response.json();
    } catch (error) {
        console.error('Error saving template:', error);
        throw error;
    }
}

// IMMEDIATE: Assign saveTemplatePrompt to window.API right after definition (like uploadDocument)
if (typeof window !== 'undefined') {
    if (!window.API) {
        window.API = {};
    }
    window.API.saveTemplatePrompt = saveTemplatePrompt;
    console.log('[api.js] ✅ IMMEDIATE: saveTemplatePrompt assigned to window.API right after definition');
}

// Delete custom template
async function deleteTemplatePrompt(templateName) {
    try {
        const response = await fetch(`${API_BASE_URL}/api/test-script/delete-template`, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                template_name: templateName
            })
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        return await response.json();
    } catch (error) {
        console.error('Error deleting template:', error);
        throw error;
    }
}

// Get custom template names
async function getCustomTemplates() {
    return await makeAPICall('/api/test-script/custom-templates', 'GET');
}

// Test Deployment API Functions

// Deploy test scripts to target environment
async function deployTestScripts(configName = "default", customConfig = null) {
    const requestData = {
        config_name: configName,
        custom_config: customConfig
    };
    
    return await makeAPICall('/api/deployment/deploy', 'POST', requestData);
}

// IMMEDIATE: Assign deployTestScripts to window.API right after definition (like uploadDocument)
if (typeof window !== 'undefined') {
    if (!window.API) {
        window.API = {};
    }
    window.API.deployTestScripts = deployTestScripts;
    console.log('[api.js] ✅ IMMEDIATE: deployTestScripts assigned to window.API right after definition');
}

// Get deployment status
async function getDeploymentStatus(jobId) {
    return await makeAPICall(`/api/deployment/status/${jobId}`);
}

// Get available deployment configurations
async function getDeploymentConfigs() {
    return await makeAPICall('/api/deployment/configs');
}

// Test Execution API Functions

// Execute test scripts via Jenkins
async function executeTestScripts(configName = "default", customConfig = null) {
    const requestData = {
        config_name: configName,
        custom_config: customConfig
    };
    
    return await makeAPICall('/api/test-execution/execute', 'POST', requestData);
}

// Get test execution status
async function getTestExecutionStatus(jobId) {
    return await makeAPICall(`/api/test-execution/status/${jobId}`);
}

// Get available test execution configurations
async function getTestExecutionConfigs() {
    return await makeAPICall('/api/test-execution/configs');
}

// Test connection to deployment server
async function testDeploymentConnection() {
    return await makeAPICall('/api/deployment/test-connection');
}

// Upload deployment configuration file
async function uploadDeploymentConfig(file) {
    return await uploadFile('/api/deployment/upload-config', file);
}

// Get list of deployment configuration files
async function getDeploymentConfigFiles() {
    return await makeAPICall('/api/deployment/config-files');
}

// Delete deployment configuration file
async function deleteDeploymentConfigFile(fileId) {
    return await makeAPICall(`/api/deployment/config-files/${fileId}`, 'DELETE');
}

// IMMEDIATE: Assign all deployment functions to window.API right after definition
if (typeof window !== 'undefined') {
    if (!window.API) {
        window.API = {};
    }
    // Test Execution functions - CRITICAL: Assign immediately after definition
    console.log('[api.js] Assigning test execution functions (early block)...');
    console.log('[api.js] typeof executeTestScripts:', typeof executeTestScripts);
    window.API.executeTestScripts = executeTestScripts;
    window.API.getTestExecutionStatus = getTestExecutionStatus;
    window.API.getTestExecutionConfigs = getTestExecutionConfigs;
    console.log('[api.js] ✅ Test execution functions assigned (early block)');
    console.log('[api.js] window.API.executeTestScripts type:', typeof window.API.executeTestScripts);
    
    // Deployment functions
    window.API.getDeploymentStatus = getDeploymentStatus;
    window.API.getDeploymentConfigs = getDeploymentConfigs;
    window.API.testDeploymentConnection = testDeploymentConnection;
    window.API.uploadDeploymentConfig = uploadDeploymentConfig;
    window.API.getDeploymentConfigFiles = getDeploymentConfigFiles;
    window.API.deleteDeploymentConfigFile = deleteDeploymentConfigFile;
    console.log('[api.js] ✅ IMMEDIATE: All deployment and test execution functions assigned to window.API');
}

// RCA / Bug Discovery API Functions
async function uploadRCALogs(files) {
    try {
        const formData = new FormData();
        files.forEach(file => {
            formData.append('files', file);
        });
        
        const response = await fetch(`${API_BASE_URL}/api/rca/upload-logs`, {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        return await response.json();
    } catch (error) {
        console.error('RCA logs upload failed:', error);
        throw error;
    }
}

async function startRCAAnalysis(logFileName, analysisType) {
    try {
        console.log('📡 Sending RCA analysis request:');
        console.log('   - Log file name:', logFileName);
        console.log('   - Analysis type:', analysisType);
        
        const requestBody = {
            log_file_name: logFileName,
            analysis_type: analysisType
        };
        
        console.log('   - Request body:', JSON.stringify(requestBody));
        
        const response = await fetch(`${API_BASE_URL}/api/rca/analyze`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(requestBody)
        });
        
        console.log('📥 Response status:', response.status);
        
        if (!response.ok) {
            const errorText = await response.text();
            console.error('❌ API error response:', errorText);
            throw new Error(`HTTP error! status: ${response.status} - ${errorText}`);
        }
        
        const result = await response.json();
        console.log('✅ RCA analysis completed successfully');
        return result;
    } catch (error) {
        console.error('❌ RCA analysis failed:', error);
        throw error;
    }
}

async function logBugDiscoveryHistory(record) {
    return await makeAPICall('/api/history/bug-discovery', 'POST', record);
}

// User History API
async function getUserHistory(filters = {}) {
    return await makeAPICall('/api/history/user', 'POST', filters);
}

// Export all API functions for use in other files
// Initialize window.API immediately and synchronously to prevent race conditions
// This MUST execute before any code tries to use window.API

// Immediately initialize window.API (don't wait for anything)
if (typeof window !== 'undefined') {
    try {
        // CRITICAL: Initialize window.API as empty object first to ensure it exists
        window.API = window.API || {};
        
        // CRITICAL: Verify critical functions exist before assignment
        console.log('[api.js] Verifying function availability before assignment...');
        console.log('[api.js] typeof uploadDocument:', typeof uploadDocument);
        console.log('[api.js] typeof checkBackendHealth:', typeof checkBackendHealth);
        console.log('[api.js] typeof makeAPICall:', typeof makeAPICall);
        console.log('[api.js] typeof getUserHistory:', typeof getUserHistory);
        
        // Assign configuration first
        window.API.API_BASE_URL = API_BASE_URL || 'http://localhost:8000';
        
        // CRITICAL: Assign functions individually to ensure they're all set
        // This prevents one undefined function from breaking the entire assignment
        
        // Health check - CRITICAL: must be available immediately
        if (typeof checkBackendHealth === 'function') {
            window.API.checkBackendHealth = checkBackendHealth;
        } else {
            console.error('[api.js] ❌ checkBackendHealth is not a function!');
        }
        
        // Generic helpers
        if (typeof makeAPICall === 'function') {
            window.API.makeAPICall = makeAPICall;
        }
        if (typeof uploadFile === 'function') {
            window.API.uploadFile = uploadFile;
        }
        if (typeof uploadMultipleFiles === 'function') {
            window.API.uploadMultipleFiles = uploadMultipleFiles;
        }
        
        // Dataset Generator APIs - CRITICAL: uploadDocument must be assigned
        // Direct assignment - async functions are hoisted, so uploadDocument should always exist
        window.API.uploadDocument = uploadDocument;
        console.log('[api.js] ✅ uploadDocument directly assigned to window.API');
        if (typeof window.API.uploadDocument !== 'function') {
            console.error('[api.js] ❌ uploadDocument assignment failed! Type:', typeof uploadDocument);
            console.error('[api.js] uploadDocument value:', uploadDocument);
        }
        if (typeof getDocumentSections === 'function') {
            window.API.getDocumentSections = getDocumentSections;
        }
        if (typeof getDocumentSubsections === 'function') {
            window.API.getDocumentSubsections = getDocumentSubsections;
        }
        if (typeof setWorkingDirectory === 'function') {
            window.API.setWorkingDirectory = setWorkingDirectory;
        }
        if (typeof setOutputDirectory === 'function') {
            window.API.setOutputDirectory = setOutputDirectory;
        }
        if (typeof generateDataset === 'function') {
            window.API.generateDataset = generateDataset;
        }
        if (typeof generateDatasetPyQtStyle === 'function') {
            window.API.generateDatasetPyQtStyle = generateDatasetPyQtStyle;
        }
        if (typeof getExtractFolderPath === 'function') {
            window.API.getExtractFolderPath = getExtractFolderPath;
        }
        if (typeof openFolderInExplorer === 'function') {
            window.API.openFolderInExplorer = openFolderInExplorer;
        }
        if (typeof getDatasetStatus === 'function') {
            window.API.getDatasetStatus = getDatasetStatus;
        }
        if (typeof downloadDataset === 'function') {
            window.API.downloadDataset = downloadDataset;
        }
        if (typeof getDatasetFiles === 'function') {
            window.API.getDatasetFiles = getDatasetFiles;
        }
        
        // Test Script Generator APIs
        if (typeof getPromptTemplates === 'function') {
            window.API.getPromptTemplates = getPromptTemplates;
        }
        if (typeof generateTestScript === 'function') {
            window.API.generateTestScript = generateTestScript;
        }
        // CRITICAL: refineTestScript must be assigned
        window.API.refineTestScript = refineTestScript;
        console.log('[api.js] ✅ refineTestScript directly assigned to window.API');
        if (typeof window.API.refineTestScript !== 'function') {
            console.error('[api.js] ❌ refineTestScript assignment failed! Type:', typeof refineTestScript);
            console.error('[api.js] refineTestScript value:', refineTestScript);
        }
        if (typeof uploadReferenceCode === 'function') {
            window.API.uploadReferenceCode = uploadReferenceCode;
        }
        if (typeof loadTestDataset === 'function') {
            window.API.loadTestDataset = loadTestDataset;
        }
        if (typeof getTestTypes === 'function') {
            window.API.getTestTypes = getTestTypes;
        }
        if (typeof generateTestByType === 'function') {
            window.API.generateTestByType = generateTestByType;
        }
        if (typeof saveTestScriptResponse === 'function') {
            window.API.saveTestScriptResponse = saveTestScriptResponse;
        }
        if (typeof saveTemplatePrompt === 'function') {
            window.API.saveTemplatePrompt = saveTemplatePrompt;
        }
        if (typeof deleteTemplatePrompt === 'function') {
            window.API.deleteTemplatePrompt = deleteTemplatePrompt;
        }
        if (typeof getCustomTemplates === 'function') {
            window.API.getCustomTemplates = getCustomTemplates;
        }
        
        // Test Deployment APIs
        if (typeof deployTestScripts === 'function') {
            window.API.deployTestScripts = deployTestScripts;
        }
        if (typeof getDeploymentStatus === 'function') {
            window.API.getDeploymentStatus = getDeploymentStatus;
        }
        if (typeof getDeploymentConfigs === 'function') {
            window.API.getDeploymentConfigs = getDeploymentConfigs;
        }
        if (typeof testDeploymentConnection === 'function') {
            window.API.testDeploymentConnection = testDeploymentConnection;
        }
        if (typeof uploadDeploymentConfig === 'function') {
            window.API.uploadDeploymentConfig = uploadDeploymentConfig;
        }
        if (typeof getDeploymentConfigFiles === 'function') {
            window.API.getDeploymentConfigFiles = getDeploymentConfigFiles;
        }
        if (typeof deleteDeploymentConfigFile === 'function') {
            window.API.deleteDeploymentConfigFile = deleteDeploymentConfigFile;
        }
        
        // Test Execution APIs - CRITICAL: Must be assigned here in main initialization
        // Direct assignment (like uploadDocument) to ensure they're always available
        window.API.executeTestScripts = executeTestScripts;
        console.log('[api.js] ✅ executeTestScripts directly assigned to window.API');
        if (typeof window.API.executeTestScripts !== 'function') {
            console.error('[api.js] ❌ executeTestScripts assignment failed! Type:', typeof executeTestScripts);
        }
        
        window.API.getTestExecutionStatus = getTestExecutionStatus;
        console.log('[api.js] ✅ getTestExecutionStatus directly assigned to window.API');
        
        window.API.getTestExecutionConfigs = getTestExecutionConfigs;
        console.log('[api.js] ✅ getTestExecutionConfigs directly assigned to window.API');
        
        // RCA / Bug Discovery APIs
        if (typeof uploadRCALogs === 'function') {
            window.API.uploadRCALogs = uploadRCALogs;
        }
        if (typeof startRCAAnalysis === 'function') {
            window.API.startRCAAnalysis = startRCAAnalysis;
        }
        if (typeof logBugDiscoveryHistory === 'function') {
            window.API.logBugDiscoveryHistory = logBugDiscoveryHistory;
        }
        // CRITICAL: getUserHistory must be assigned directly (like uploadDocument)
        console.log('[api.js] Before assignment - typeof getUserHistory:', typeof getUserHistory);
        console.log('[api.js] getUserHistory function:', getUserHistory);
        if (typeof getUserHistory === 'function') {
            window.API.getUserHistory = getUserHistory;
            console.log('[api.js] ✅ getUserHistory assigned to window.API');
        } else {
            console.error('[api.js] ❌ getUserHistory is not a function! Type:', typeof getUserHistory);
        }
        if (typeof window.API.getUserHistory !== 'function') {
            console.error('[api.js] ❌ getUserHistory assignment failed! Type:', typeof getUserHistory);
            console.error('[api.js] window.API.getUserHistory value:', window.API.getUserHistory);
        } else {
            console.log('[api.js] ✅ Verified: window.API.getUserHistory is a function');
        }
        
        // Final verification - log all API functions
        console.log('[api.js] Final window.API functions:', Object.keys(window.API));
        console.log('[api.js] getUserHistory in final check:', typeof window.API.getUserHistory);
        
        // CRITICAL: Verify critical functions were assigned correctly
        if (typeof window.API.checkBackendHealth !== 'function') {
            console.error('[api.js] ❌ checkBackendHealth was not assigned correctly!');
            console.error('[api.js] checkBackendHealth type:', typeof window.API.checkBackendHealth);
            console.error('[api.js] checkBackendHealth value:', window.API.checkBackendHealth);
            // Force assign it
            window.API.checkBackendHealth = checkBackendHealth;
            console.warn('[api.js] ⚠️ Force-assigned checkBackendHealth');
        }
        
        // CRITICAL: Verify uploadDocument was assigned correctly
        // Direct assignment again to ensure it's set (in case first assignment didn't work)
        window.API.uploadDocument = uploadDocument;
        if (typeof window.API.uploadDocument !== 'function') {
            console.error('[api.js] ❌ uploadDocument verification failed after direct assignment!');
            console.error('[api.js] uploadDocument type:', typeof window.API.uploadDocument);
            console.error('[api.js] uploadDocument value:', window.API.uploadDocument);
            console.error('[api.js] typeof uploadDocument:', typeof uploadDocument);
            console.error('[api.js] uploadDocument function itself:', uploadDocument);
        } else {
            console.log('[api.js] ✅ uploadDocument verified and ready');
        }
        
        // CRITICAL: Verify refineTestScript was assigned correctly
        // Direct assignment again to ensure it's set (in case first assignment didn't work)
        window.API.refineTestScript = refineTestScript;
        if (typeof window.API.refineTestScript !== 'function') {
            console.error('[api.js] ❌ refineTestScript verification failed after direct assignment!');
            console.error('[api.js] refineTestScript type:', typeof window.API.refineTestScript);
            console.error('[api.js] refineTestScript value:', window.API.refineTestScript);
            console.error('[api.js] typeof refineTestScript:', typeof refineTestScript);
            console.error('[api.js] refineTestScript function itself:', refineTestScript);
        } else {
            console.log('[api.js] ✅ refineTestScript verified and ready');
        }
        
        // CRITICAL: Force re-assign getUserHistory to ensure it's set
        if (typeof getUserHistory === 'function') {
            window.API.getUserHistory = getUserHistory;
            console.log('[api.js] ✅ Force-assigned getUserHistory');
        } else {
            console.error('[api.js] ❌ getUserHistory not available for force assignment!');
        }
        
        // CRITICAL: Final verification before proceeding
        console.log('[api.js] ✅ window.API initialized with', Object.keys(window.API).length, 'functions');
        console.log('[api.js] ✅ checkBackendHealth available:', typeof window.API.checkBackendHealth === 'function');
        console.log('[api.js] ✅ uploadDocument available:', typeof window.API.uploadDocument === 'function');
        console.log('[api.js] ✅ refineTestScript available:', typeof window.API.refineTestScript === 'function');
        console.log('[api.js] ✅ getUserHistory available:', typeof window.API.getUserHistory === 'function');
        console.log('[api.js] ✅ uploadDocument function reference:', window.API.uploadDocument);
        console.log('[api.js] ✅ refineTestScript function reference:', window.API.refineTestScript);
        console.log('[api.js] ✅ getUserHistory function reference:', window.API.getUserHistory);
        console.log('[api.js] ✅ API_BASE_URL:', window.API.API_BASE_URL);
        
        // CRITICAL: Test that uploadDocument can be called (don't actually call it, just verify it's callable)
        if (typeof window.API.uploadDocument === 'function') {
            console.log('[api.js] ✅ uploadDocument is callable and ready');
            // Store a reference for debugging
            window._uploadDocumentRef = window.API.uploadDocument;
        } else {
            console.error('[api.js] ❌ uploadDocument verification failed!');
            console.error('[api.js] typeof window.API.uploadDocument:', typeof window.API.uploadDocument);
            console.error('[api.js] window.API.uploadDocument value:', window.API.uploadDocument);
        }
        
        // Dispatch custom event to notify that API is ready
        if (typeof document !== 'undefined') {
            try {
                const apiReadyEvent = new CustomEvent('apiReady', { 
                    detail: { 
                        api: window.API,
                        functionCount: Object.keys(window.API).length,
                        checkBackendHealthAvailable: typeof window.API.checkBackendHealth === 'function',
                        uploadDocumentAvailable: typeof window.API.uploadDocument === 'function'
                    } 
                });
                document.dispatchEvent(apiReadyEvent);
                console.log('[api.js] ✅ Dispatched apiReady event with uploadDocument status');
            } catch (eventError) {
                console.warn('[api.js] ⚠️ Could not dispatch apiReady event:', eventError);
            }
        }
    } catch (initError) {
        console.error('[api.js] ❌ Error initializing window.API:', initError);
        console.error('[api.js] Stack trace:', initError.stack);
        // Try to create minimal API object even if there's an error
        if (typeof window !== 'undefined') {
            window.API = window.API || {};
            // CRITICAL: Assign all critical functions even if Object.assign failed
            window.API.checkBackendHealth = checkBackendHealth;
            window.API.uploadDocument = uploadDocument;
            window.API.getDocumentSections = getDocumentSections;
            window.API.getDocumentSubsections = getDocumentSubsections;
            window.API.generateDataset = generateDataset;
            window.API.getPromptTemplates = getPromptTemplates;
            window.API.generateTestScript = generateTestScript;
            window.API.loadTestDataset = loadTestDataset;
            window.API.makeAPICall = makeAPICall;
            if (typeof getUserHistory === 'function') {
                window.API.getUserHistory = getUserHistory;
                console.log('[api.js] ⚠️ getUserHistory assigned in fallback');
            } else {
                console.error('[api.js] ⚠️ getUserHistory not available in fallback!');
            }
            window.API.API_BASE_URL = API_BASE_URL || 'http://localhost:8000';
            console.warn('[api.js] ⚠️ Created minimal window.API object after error with critical functions');
            console.log('[api.js] ⚠️ Minimal window.API has', Object.keys(window.API).length, 'functions');
            console.log('[api.js] ⚠️ uploadDocument available:', typeof window.API.uploadDocument === 'function');
            console.log('[api.js] ⚠️ getUserHistory available:', typeof window.API.getUserHistory === 'function');
        }
    }
} else {
    console.error('[api.js] ❌ window object is not available - this should not happen in a browser');
}

// Error Fixing API Functions

// Analyze error using the complete error fixing pipeline
async function analyzeError(requestData) {
    try {
        console.log('🔍 Calling error analysis API with data:', requestData);
        const result = await makeAPICall('/api/error-fixing/analyze', 'POST', requestData);
        console.log('✅ Error analysis API response:', result);
        return result;
    } catch (error) {
        console.error('❌ Error analysis API failed:', error);
        throw error;
    }
}

// Update embeddings after applying patches
async function updateEmbeddings(requestData) {
    try {
        console.log('🔄 Calling embedding update API with data:', requestData);
        const result = await makeAPICall('/api/error-fixing/update-embeddings', 'POST', requestData);
        console.log('✅ Embedding update API response:', result);
        return result;
    } catch (error) {
        console.error('❌ Embedding update API failed:', error);
        throw error;
    }
}

// Get error fixing pipeline status
async function getErrorFixingStatus() {
    try {
        console.log('📊 Getting error fixing pipeline status...');
        const result = await makeAPICall('/api/error-fixing/status', 'GET');
        console.log('✅ Error fixing status:', result);
        return result;
    } catch (error) {
        console.error('❌ Error fixing status API failed:', error);
        throw error;
    }
}

// Get available log files
async function getAvailableLogFiles(logDirectory = null) {
    try {
        console.log('📁 Getting available log files...');
        const endpoint = logDirectory ? 
            `/api/error-fixing/log-files?log_directory=${encodeURIComponent(logDirectory)}` : 
            '/api/error-fixing/log-files';
        const result = await makeAPICall(endpoint, 'GET');
        console.log('✅ Available log files:', result);
        return result;
    } catch (error) {
        console.error('❌ Get log files API failed:', error);
        throw error;
    }
}

// Upload log file for error analysis
async function uploadLogFile(file) {
    try {
        console.log('📤 Uploading log file:', file.name);
        
        const formData = new FormData();
        formData.append('file', file);
        
        const response = await fetch(`${API_BASE_URL}/api/error-fixing/upload-log`, {
            method: 'POST',
            body: formData,
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const result = await response.json();
        console.log('✅ Log file uploaded:', result);
        return result;
    } catch (error) {
        console.error('❌ Log file upload failed:', error);
        throw error;
    }
}

// Update the window.API object to include error fixing functions
// CRITICAL: Always MERGE, never overwrite existing window.API
if (typeof window !== 'undefined') {
    // CRITICAL: Ensure window.API exists before adding error fixing functions
    // DO NOT overwrite if it already exists - it should have been initialized earlier
    if (!window.API) {
        console.error('❌ window.API not found! This should never happen.');
        console.error('❌ Creating minimal object with critical functions only...');
        // Only create minimal object as last resort
        window.API = window.API || {};
    } else {
        console.log('[api.js] ✅ window.API exists with', Object.keys(window.API).length, 'functions before error fixing merge');
    }
    
    try {
        // CRITICAL: Use Object.assign to MERGE error fixing functions
        // This will NOT overwrite existing functions
        if (typeof analyzeError === 'function') {
            window.API.analyzeError = analyzeError;
        }
        if (typeof updateEmbeddings === 'function') {
            window.API.updateEmbeddings = updateEmbeddings;
        }
        if (typeof getErrorFixingStatus === 'function') {
            window.API.getErrorFixingStatus = getErrorFixingStatus;
        }
        if (typeof getAvailableLogFiles === 'function') {
            window.API.getAvailableLogFiles = getAvailableLogFiles;
        }
        if (typeof uploadLogFile === 'function') {
            window.API.uploadLogFile = uploadLogFile;
        }
        
        console.log('✅ Error fixing APIs added to window.API');
        console.log('✅ Final window.API has', Object.keys(window.API).length, 'functions');
        console.log('✅ checkBackendHealth still available:', typeof window.API.checkBackendHealth === 'function');
        console.log('✅ uploadDocument still available:', typeof window.API.uploadDocument === 'function');
        
        // CRITICAL: Verify critical functions are still present after adding error fixing functions
        if (typeof window.API.uploadDocument !== 'function') {
            console.error('❌ uploadDocument was lost! Force reassigning...');
            if (typeof uploadDocument === 'function') {
                window.API.uploadDocument = uploadDocument;
                console.warn('⚠️ Force-reassigned uploadDocument');
            } else {
                console.error('❌ uploadDocument function itself is undefined!');
            }
        }
        if (typeof window.API.checkBackendHealth !== 'function') {
            console.error('❌ checkBackendHealth was lost! Force reassigning...');
            if (typeof checkBackendHealth === 'function') {
                window.API.checkBackendHealth = checkBackendHealth;
                console.warn('⚠️ Force-reassigned checkBackendHealth');
            } else {
                console.error('❌ checkBackendHealth function itself is undefined!');
            }
        }
        
        // CRITICAL: Final verification - ensure uploadDocument is definitely there
        if (typeof window.API.uploadDocument === 'function') {
            console.log('[api.js] ✅ FINAL VERIFICATION: uploadDocument is available and ready');
        } else {
            console.error('[api.js] ❌ FINAL VERIFICATION FAILED: uploadDocument is NOT available!');
            console.error('[api.js] window.API keys:', Object.keys(window.API));
        }
    } catch (error) {
        console.error('❌ Failed to add error fixing APIs:', error);
        console.error('❌ Error stack:', error.stack);
        // CRITICAL: Even if merge fails, ensure critical functions are still available
        if (typeof window.API.uploadDocument !== 'function') {
            if (typeof uploadDocument === 'function') {
                window.API.uploadDocument = uploadDocument;
                console.warn('⚠️ Force-reassigned uploadDocument after error');
            } else {
                console.error('❌ Cannot reassign uploadDocument - function is undefined!');
            }
        }
    }
} else {
    console.error('❌ window object not available when trying to add error fixing functions');
}

// CRITICAL: Final guarantee - ensure uploadDocument is ALWAYS assigned
// This runs after ALL initialization code to guarantee it's set
if (typeof window !== 'undefined') {
    // Ensure window.API exists
    if (!window.API) {
        console.error('[api.js] ❌ CRITICAL: window.API does not exist at final check! Creating it...');
        window.API = {};
    }
    
    // CRITICAL: Directly assign uploadDocument - force it multiple times to ensure it sticks
    // Assign it directly without any conditions - the function must exist at this point
    window.API.uploadDocument = uploadDocument;
    window.API.uploadDocument = uploadDocument; // Assign twice to be absolutely sure
    
    console.log('[api.js] ✅ FINAL GUARANTEE: uploadDocument assigned directly (multiple times)');
    
    // Final verification
    if (typeof window.API.uploadDocument === 'function') {
        console.log('[api.js] ✅ FINAL VERIFICATION PASSED: uploadDocument is available');
        // Test that it's actually callable
        try {
            const testCallable = typeof window.API.uploadDocument === 'function';
            console.log('[api.js] ✅ uploadDocument is callable:', testCallable);
        } catch (e) {
            console.error('[api.js] ❌ Error testing uploadDocument callability:', e);
        }
    } else {
        console.error('[api.js] ❌ FINAL VERIFICATION FAILED: uploadDocument is still not available!');
        console.error('[api.js] typeof window.API.uploadDocument:', typeof window.API.uploadDocument);
        console.error('[api.js] typeof uploadDocument:', typeof uploadDocument);
        console.error('[api.js] window.API keys:', Object.keys(window.API));
        // Create a working fallback that actually calls the real function
        if (typeof uploadDocument === 'function') {
            window.API.uploadDocument = function(file) {
                console.log('[api.js] ⚠️ Using fallback wrapper for uploadDocument');
                return uploadDocument(file);
            };
            console.log('[api.js] ✅ Created fallback wrapper for uploadDocument');
        } else {
            // Last resort: create error function
            window.API.uploadDocument = function() {
                throw new Error('uploadDocument function was not properly initialized. The function definition may not have loaded.');
            };
        }
    }
    
    // ONE MORE TIME - assign it at the very end
    window.API.uploadDocument = uploadDocument;
    console.log('[api.js] ✅ LAST ASSIGNMENT: uploadDocument assigned one more time at the very end');
    
    // CRITICAL: Also ensure refineTestScript is ALWAYS assigned
    // Assign it directly without any conditions - the function must exist at this point
    window.API.refineTestScript = refineTestScript;
    window.API.refineTestScript = refineTestScript; // Assign twice to be absolutely sure
    
    console.log('[api.js] ✅ FINAL GUARANTEE: refineTestScript assigned directly (multiple times)');
    
    // Final verification for refineTestScript
    if (typeof window.API.refineTestScript === 'function') {
        console.log('[api.js] ✅ FINAL VERIFICATION PASSED: refineTestScript is available');
    } else {
        console.error('[api.js] ❌ FINAL VERIFICATION FAILED: refineTestScript is still not available!');
        console.error('[api.js] typeof window.API.refineTestScript:', typeof window.API.refineTestScript);
        console.error('[api.js] typeof refineTestScript:', typeof refineTestScript);
        // Create a working fallback that actually calls the real function
        if (typeof refineTestScript === 'function') {
            window.API.refineTestScript = function(textContent, newPrompt, previousResponse) {
                console.log('[api.js] ⚠️ Using fallback wrapper for refineTestScript');
                return refineTestScript(textContent, newPrompt, previousResponse);
            };
            console.log('[api.js] ✅ Created fallback wrapper for refineTestScript');
        } else {
            // Last resort: create error function
            window.API.refineTestScript = function() {
                throw new Error('refineTestScript function was not properly initialized. The function definition may not have loaded.');
            };
        }
    }
    
    // ONE MORE TIME - assign refineTestScript at the very end
    window.API.refineTestScript = refineTestScript;
    console.log('[api.js] ✅ LAST ASSIGNMENT: refineTestScript assigned one more time at the very end');
    
    // CRITICAL: Also ensure deployTestScripts is ALWAYS assigned
    // Assign it directly without any conditions - the function must exist at this point
    window.API.deployTestScripts = deployTestScripts;
    window.API.deployTestScripts = deployTestScripts; // Assign twice to be absolutely sure
    
    console.log('[api.js] ✅ FINAL GUARANTEE: deployTestScripts assigned directly (multiple times)');
    
    // Final verification for deployTestScripts
    if (typeof window.API.deployTestScripts === 'function') {
        console.log('[api.js] ✅ FINAL VERIFICATION PASSED: deployTestScripts is available');
    } else {
        console.error('[api.js] ❌ FINAL VERIFICATION FAILED: deployTestScripts is still not available!');
        console.error('[api.js] typeof window.API.deployTestScripts:', typeof window.API.deployTestScripts);
        console.error('[api.js] typeof deployTestScripts:', typeof deployTestScripts);
        // Create a working fallback that actually calls the real function
        if (typeof deployTestScripts === 'function') {
            window.API.deployTestScripts = function(configName, customConfig) {
                console.log('[api.js] ⚠️ Using fallback wrapper for deployTestScripts');
                return deployTestScripts(configName, customConfig);
            };
            console.log('[api.js] ✅ Created fallback wrapper for deployTestScripts');
        } else {
            // Last resort: create error function
            window.API.deployTestScripts = function() {
                throw new Error('deployTestScripts function was not properly initialized. The function definition may not have loaded.');
            };
        }
    }
    
    // ONE MORE TIME - assign deployTestScripts at the very end
    window.API.deployTestScripts = deployTestScripts;
    console.log('[api.js] ✅ LAST ASSIGNMENT: deployTestScripts assigned one more time at the very end');
    
    // CRITICAL: Also ensure saveTemplatePrompt is ALWAYS assigned
    // Assign it directly without any conditions - the function must exist at this point
    window.API.saveTemplatePrompt = saveTemplatePrompt;
    window.API.saveTemplatePrompt = saveTemplatePrompt; // Assign twice to be absolutely sure
    
    console.log('[api.js] ✅ FINAL GUARANTEE: saveTemplatePrompt assigned directly (multiple times)');
    
    // Final verification for saveTemplatePrompt
    if (typeof window.API.saveTemplatePrompt === 'function') {
        console.log('[api.js] ✅ FINAL VERIFICATION PASSED: saveTemplatePrompt is available');
    } else {
        console.error('[api.js] ❌ FINAL VERIFICATION FAILED: saveTemplatePrompt is still not available!');
        console.error('[api.js] typeof window.API.saveTemplatePrompt:', typeof window.API.saveTemplatePrompt);
        console.error('[api.js] typeof saveTemplatePrompt:', typeof saveTemplatePrompt);
        // Create a working fallback that actually calls the real function
        if (typeof saveTemplatePrompt === 'function') {
            window.API.saveTemplatePrompt = function(templateName, templateContent) {
                console.log('[api.js] ⚠️ Using fallback wrapper for saveTemplatePrompt');
                return saveTemplatePrompt(templateName, templateContent);
            };
            console.log('[api.js] ✅ Created fallback wrapper for saveTemplatePrompt');
        } else {
            // Last resort: create error function
            window.API.saveTemplatePrompt = function() {
                throw new Error('saveTemplatePrompt function was not properly initialized. The function definition may not have loaded.');
            };
        }
    }
    
    // ONE MORE TIME - assign saveTemplatePrompt at the very end
    window.API.saveTemplatePrompt = saveTemplatePrompt;
    console.log('[api.js] ✅ LAST ASSIGNMENT: saveTemplatePrompt assigned one more time at the very end');
    
    // FINAL GUARANTEE: Test Execution functions - assign at the very end to ensure they're always available
    console.log('[api.js] FINAL: Assigning test execution functions at the very end...');
    window.API.executeTestScripts = executeTestScripts;
    window.API.getTestExecutionStatus = getTestExecutionStatus;
    window.API.getTestExecutionConfigs = getTestExecutionConfigs;
    console.log('[api.js] ✅ FINAL: Test execution functions assigned at the very end');
    console.log('[api.js] FINAL: window.API.executeTestScripts type:', typeof window.API.executeTestScripts);
    console.log('[api.js] FINAL: All window.API keys:', Object.keys(window.API).filter(k => k.includes('Test') || k.includes('test')));
}

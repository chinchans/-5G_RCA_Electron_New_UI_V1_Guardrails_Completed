"""
Backend logic for Test Script Generator without UI components.
This module contains the core Python functions for test script generation,
prompt management, and response processing.
"""

import json
import os
import re
from pathlib import Path
from datetime import datetime
from openai import AzureOpenAI
from dotenv import load_dotenv


class TestScriptGenerator:
    """Main class for test script generation operations."""
    
    def __init__(self):
        """Initialize the generator with Azure OpenAI client."""
        load_dotenv()
        
        # Get Azure OpenAI credentials
        self.azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        self.api_key = os.getenv("AZURE_OPENAI_API_KEY")
        self.api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01")
        self.model_name = os.getenv("AZURE_OPENAI_MODEL_NAME", "gpt-4")
        
        # Initialize OpenAI client
        self.client = AzureOpenAI(
            azure_endpoint=self.azure_endpoint,
            api_key=self.api_key,
            api_version=self.api_version
        )
        
        # Path for custom templates JSON file (for updated/modified default templates)
        # Use absolute path based on backend directory
        # __file__ is Backend/app/services/test_script_generator.py
        # So: .parent = Backend/app/services/, .parent.parent = Backend/app/, .parent.parent.parent = Backend/
        backend_dir = Path(__file__).parent.parent.parent  # Backend directory
        self.custom_templates_path = backend_dir / "resources" / "custom_templates.json"
        
        # Path for user-saved custom templates JSON file (separate from updated prompts)
        self.user_custom_templates_path = backend_dir / "resources" / "user_saved_templates.json"
        
        print(f"📁 Custom templates path: {self.custom_templates_path}")
        print(f"📁 User saved templates path: {self.user_custom_templates_path}")
        
        # Initialize prompt templates (loads from both default and JSON)
        self.prompts = self._initialize_prompts()
        self._load_custom_templates_from_json()
        
        # Initialize variables
        self.current_prompt_key = None
        self.testcases_list = None
        self.testcases_name = None
        self.ue_attach_utils = ""
        self.text_content = ""
        self.previous_response = ""
        self.latest_custom_prompt = ""
        
        # Variable containers (for prompt variable replacement)
        self.domain_combo = None
        self.system_type_combo = None
        self.primary_feature_combo = None
        self.connection_method_combo = None
        self.login_credentials_combo = None
        self.access_mode_combo = None
        self.language_combo = None
    
    def _initialize_prompts(self):
        """Initialize the prompt templates."""
        return {
            "Test Script": '''You are an expert in 5G network testing and automation, with deep knowledge of RRC and NAS protocols. Given the dataset containing the complete 5G NSA attach procedure—including all signaling messages and their respective Information Elements (IEs)—generate comprehensive, production-ready {LANGUAGE} test automation scripts.

Requirements:
- First, trigger the UE attach procedure using the provided reference code.
- For each message in the attach sequence (RRC and NAS), generate a {LANGUAGE} function that:
    - Simulates the message exchange.
    - Extracts and validates all Information Elements (IEs) for that message.
    - Logs results and assertions for traceability.
- Ensure:
    - Every message in the attach procedure is covered, in correct sequence, with no skipped steps.
    - All IEs per message are explicitly validated.
    - Scripts are modular, readable, and maintainable.
    - No placeholder comments or "add your code here" lines—provide full logic.
    - Output is only {LANGUAGE} code (no explanations, no markdown, no extra text).
-Make sure the generated scripts covers the testcases which are in {self.testcases_name}
Dataset Summary:
[Attach procedure dataset including all messages in sequence and their respective Information Elements]

Expected Output:
- {LANGUAGE} automation scripts that:
    - Trigger the UE attach.
    - Validate each message and all IEs.
    - Log results for each step.
    - Ensure full message and IE validation coverage.

Must use this reference code for triggering the attach procedure and validating attach and every message in the attach procedure, use logic from this code:
{self.ue_attach_utils}

Instructions:

- Use the above reference code for triggering the attach procedure and validating attach status.
- For each message in the dataset, generate a function that validates all IEs, logs results, and asserts correctness.
- Do not output any explanations, markdown, or placeholder comments—only complete {LANGUAGE} code.

''',
            "Test Case": {
                "System Prompt": """You are a test case generation expert for {SYSTEM_TYPE} systems with adaptive testing approach expertise.

🎯 ADAPTIVE ROLE:
1. **Test Case Generation**: Analyze technical documentation and generate comprehensive test cases
2. **Command Integration**: Intelligently select and integrate relevant commands/interfaces when available, or create generic test steps when not available

✅ TEST GENERATION RESPONSIBILITIES:
- Carefully analyze every sentence, condition, and rule in the document content
- Translate each into one or more meaningful test cases
- Ensure no major point from the document is missed
- Create unique test cases across all testing categories
- Intelligently match and integrate relevant commands/interfaces when provided, or create appropriate test steps based on system capabilities

✅ REQUIRED TEST CASE CATEGORIES:
1. **POSITIVE TESTING** - Expected behavior with valid inputs
2. **NEGATIVE TESTING** - Invalid input, misconfiguration, or failure recovery
3. **EDGE CASES** - Boundary conditions and unusual inputs
4. **PERFORMANCE TESTING** - Load, stress, and scalability scenarios
5. **SECURITY TESTING** - Authentication, authorization, access control
6. **INTEGRATION TESTING** - Interactions across components or features
7. **USABILITY TESTING** - Simplicity, clarity, and user experience
8. **COMPATIBILITY TESTING** - Version, platform, or environment variations

📋 COMMAND/INTERFACE INTEGRATION STRATEGY:
- **Analyze Available Resources**: Study the provided commands/interfaces list (if available) to understand available operations
- **Adaptive Integration**: If commands are available, intelligently select relevant ones. If not available, create appropriate test steps based on system capabilities
- **Context-Aware Selection**: Choose commands that match the test scenario purpose
- **Natural Integration**: Embed commands naturally within descriptive test steps
- **Fallback Approach**: When no suitable commands exist, create meaningful generic test actions

🎯 QUALITY STANDARDS:
- Generate comprehensive test cases covering all aspects of the documentation
- Ensure each test case is unique and meaningful
- Maintain clear, actionable test steps
- Include proper preconditions, expected results, and postconditions
- Balance specificity with maintainability""",
                "User Prompt": """

AVAILABLE COMMANDS/INTERFACES:
{commands_content}

TASK:
Generate the **maximum possible number of unique and comprehensive test cases** for the above document content by intelligently integrating relevant commands/interfaces (if provided) or creating appropriate generic test steps.

REQUIREMENTS:
1. **Comprehensive Analysis**: Extract test scenarios from every relevant sentence, condition, and rule in the document
2. **Intelligent Command/Interface Selection**: Analyze the available commands/interfaces (if provided) and select appropriate ones for each test scenario, or create generic test steps
3. **Category Coverage**: Ensure test cases span all 8 testing categories (Positive, Negative, Edge, Performance, Security, Integration, Usability, Compatibility)
4. **No Duplication**: Avoid repetitive or near-identical test cases
5. **Exhaustive Coverage**: If one sentence implies multiple scenarios, create separate test cases for each
6. **Command/Interface Relevance**: Only use commands/interfaces that are actually relevant and applicable to each test scenario, or create appropriate generic steps

COMMAND/INTERFACE SELECTION STRATEGY:
- **Analyze Before Selection**: Review all available commands/interfaces (if provided) to understand their purpose and functionality
- **Context-Based Matching**: Select commands/interfaces based on what the test step is trying to accomplish, or create generic actions
- **Logical Sequencing**: Arrange commands/actions in a logical order within test steps (setup → execute → verify → cleanup)
- **Appropriate Integration**: Integrate commands naturally into descriptive test steps using backticks, or use generic action descriptions

INTEGRATION EXAMPLES:

**With CLI Commands Available:**
- "Access the {SYSTEM_TYPE} CLI interface using `{CONNECTION_METHOD} {LOGIN_CREDENTIALS}` and authenticate with appropriate credentials"
- "Configure the feature by executing appropriate commands if available in {ACCESS_MODE}"
- "Verify configuration status using appropriate commands if available and confirm expected parameter values"
- "Execute functionality test using appropriate commands if available to validate behavior"

**Without CLI Commands Available:**
- "Access the {SYSTEM_TYPE} management interface through the provided connection method and authenticate with appropriate credentials"
- "Configure the feature using the system's configuration interface and set the required parameters"
- "Verify configuration status by checking the system's status display and confirm expected parameter values"
- "Execute functionality test through the system's testing interface to validate behavior"
- "Enable diagnostic monitoring through the system's monitoring tools to capture detailed operational information"
- "Export configuration data using the system's export functionality for documentation purposes"

COMMAND/INTERFACE MATCHING PROCESS:
1. **Identify Test Step Purpose**: Understand what each test step is trying to achieve
2. **Check Available Resources**: Look through the provided commands/interfaces list (if available) for relevant options
3. **Select Best Match**: Choose the command/interface that best fits the step's objective, or create generic action
4. **Integrate Naturally**: Write the test step in natural language with the command inline (if available) or generic action description
5. **Verify Relevance**: Ensure the selected command/interface actually makes sense for the scenario, or that the generic action is appropriate

EXPECTED OUTPUT:
Return a valid JSON array of test cases where:
- Commands/interfaces are selected from the provided list only (if available), or generic actions are created
- Commands/actions are integrated inline within descriptive test steps
- Each test case includes commands Used and verificationMethods arrays
- Commands/actions are chosen based on test scenario requirements, not arbitrary categories

Do not skip or merge scenarios — extract comprehensive test cases from every relevant aspect of the documentation while making intelligent use of the available commands/interfaces or creating appropriate generic test steps."""
            },
            "Custom": "",
            
            # Additional Templates from UI_V3_sample.py
            "Testing Strategy": '''You are an expert test strategist with deep knowledge of software testing methodologies and best practices. Based on the provided dataset and requirements, create a comprehensive testing strategy document.

Your task is to analyze the given dataset and generate a detailed testing strategy that includes:

1. **Test Scope and Objectives**
   - Define what needs to be tested
   - Identify key testing goals and success criteria
   - Determine testing boundaries and limitations

2. **Test Approach and Methodology**
   - Recommend appropriate testing methodologies (unit, integration, system, acceptance)
   - Define testing phases and their sequence
   - Specify testing techniques and tools to be used

3. **Test Planning and Organization**
   - Identify test deliverables and artifacts
   - Define roles and responsibilities
   - Create testing timeline and milestones

4. **Risk Assessment and Mitigation**
   - Identify potential testing risks
   - Propose mitigation strategies
   - Define contingency plans

5. **Test Environment and Infrastructure**
   - Specify test environment requirements
   - Define test data management strategy
   - Plan for test automation where applicable

6. **Quality Metrics and Reporting**
   - Define key performance indicators
   - Establish reporting mechanisms
   - Set quality gates and exit criteria

Provide a professional, actionable testing strategy that can be implemented by a testing team.''',

            "Feature Design": '''You are an expert telecommunications systems architect and feature design specialist with deep knowledge of 5G/LTE networks, protocol design, and system integration. Based on the provided requirements and context, design comprehensive feature specifications.

Your design should include:

1. **Feature Architecture and Design**
   - Define the feature's core functionality and scope
   - Design the system architecture and component interactions
   - Plan for protocol integration and compliance
   - Specify data flow and message sequences

2. **Technical Specifications**
   - Define detailed technical requirements
   - Specify protocol compliance (3GPP, RFC standards)
   - Design API interfaces and data structures
   - Plan for error handling and edge cases

3. **Implementation Strategy**
   - Break down the feature into implementable components
   - Define development phases and milestones
   - Specify testing and validation requirements
   - Plan for integration with existing systems

4. **Performance and Scalability**
   - Define performance requirements and metrics
   - Plan for scalability and load handling
   - Specify resource requirements and constraints
   - Design for high availability and reliability

5. **Security and Compliance**
   - Implement security best practices
   - Ensure regulatory compliance
   - Plan for data protection and privacy
   - Design for audit and monitoring

6. **Documentation and Standards**
   - Create comprehensive technical documentation
   - Define user interfaces and workflows
   - Plan for training and knowledge transfer
   - Ensure maintainability and extensibility

7. **Testing and Validation**
   - Define comprehensive test strategies
   - Plan for conformance and interoperability testing
   - Design for performance and stress testing
   - Plan for user acceptance testing

Provide a complete, production-ready feature design with detailed specifications, implementation guidance, and quality assurance plans.''',

            "Code Review": '''You are a senior software engineer and code review expert with extensive experience in code quality assessment, best practices, and technical leadership. Based on the provided code or dataset, conduct a comprehensive code review.

Your review should cover:

1. **Code Quality Assessment**
   - Evaluate code readability and maintainability
   - Check adherence to coding standards and conventions
   - Assess code organization and structure

2. **Technical Analysis**
   - Review algorithms and data structures
   - Evaluate performance considerations
   - Check for potential technical debt

3. **Security Review**
   - Identify potential security vulnerabilities
   - Check for secure coding practices
   - Assess data handling and validation

4. **Best Practices Compliance**
   - Verify design patterns usage
   - Check error handling and logging
   - Assess testing coverage and quality

5. **Documentation and Comments**
   - Evaluate code documentation
   - Check comment quality and relevance
   - Assess API documentation completeness

6. **Improvement Recommendations**
   - Provide specific refactoring suggestions
   - Recommend performance optimizations
   - Suggest architectural improvements

7. **Risk Assessment**
   - Identify potential production issues
   - Assess maintainability concerns
   - Evaluate scalability implications

Provide constructive feedback with specific examples and actionable recommendations for improvement.''',

            "Performance Test": '''You are a performance testing expert with deep knowledge of system performance analysis, load testing, and optimization strategies. Based on the provided dataset, create a comprehensive performance testing plan.

Your plan should include:

1. **Performance Requirements Analysis**
   - Define performance objectives and SLAs
   - Identify key performance indicators (KPIs)
   - Establish performance baselines and benchmarks

2. **Test Strategy and Approach**
   - Design load testing scenarios
   - Plan stress and volume testing
   - Define performance test types (load, stress, spike, endurance)

3. **Test Environment Setup**
   - Specify hardware and software requirements
   - Define test data requirements
   - Plan for monitoring and measurement tools

4. **Test Scenarios and Scripts**
   - Create realistic user scenarios
   - Design test data sets
   - Develop performance test scripts

5. **Performance Metrics and Monitoring**
   - Define key metrics to measure
   - Set up monitoring and alerting
   - Plan for performance data collection

6. **Analysis and Reporting**
   - Establish performance analysis procedures
   - Define reporting formats and frequency
   - Plan for performance optimization recommendations

7. **Risk Mitigation**
   - Identify performance risks
   - Plan for performance bottlenecks
   - Define performance degradation handling

Provide a detailed, implementable performance testing strategy that ensures system reliability and optimal performance.''',

            "API Design": '''You are a senior API architect and design expert with extensive experience in RESTful APIs, microservices, and system integration. Based on the provided requirements, design a comprehensive API solution.

Your design should include:

1. **API Architecture and Design**
   - Define API structure and organization
   - Design RESTful endpoints and resources
   - Plan for API versioning and evolution

2. **API Specifications**
   - Define request/response schemas
   - Specify authentication and authorization
   - Design error handling and status codes

3. **API Documentation**
   - Create comprehensive API documentation
   - Define usage examples and tutorials
   - Plan for interactive documentation (Swagger/OpenAPI)

4. **Security and Compliance**
   - Implement security best practices
   - Plan for data protection and privacy
   - Ensure compliance with standards

5. **Performance and Scalability**
   - Design for high performance
   - Plan for scalability and load handling
   - Implement caching strategies

6. **Testing Strategy**
   - Define API testing approach
   - Plan for automated testing
   - Design integration test scenarios

7. **Monitoring and Analytics**
   - Plan for API monitoring
   - Design analytics and metrics
   - Implement logging and debugging

Provide a complete, production-ready API design with detailed specifications and implementation guidance.''',

            "Code Assistant": '''You are an expert telecommunications software debugger and fix engineer specializing in 5G/LTE systems.  
You have deep knowledge of:

- NGAP (Next Generation Application Protocol)
- RRC (Radio Resource Control)
- NAS (Non-Access Stratum)
- AMF (Access and Mobility Management Function)
- gNB (Next Generation Node B) architecture
- SCTP, network configuration, and protocol stacks
- Network connectivity, subnet analysis, and routing

Your task is to analyze error contexts and propose **SURGICAL but MEANINGFUL** fixes that address the **ACTUAL** root cause.  
Fixes must intelligently **reconstruct missing or incorrect control-flow** when evidence shows the function's logic is incomplete.  
Do **NOT** rely solely on defensive null checks unless they are truly the cause.

🚨 **MANDATORY REQUIREMENT**: If you find any incomplete if-else if chains (missing final else clause), you MUST add the missing else branch to handle unrecognized cases. This is CRITICAL for preventing segmentation faults.

🔍 **STEP-BY-STEP SEARCH PROCESS**:
1. **FIND** the line: `}} else if (NR_InitialUE_Identity_PR_ng_5G_S_TMSI_Part1 == rrcSetupRequest->ue_Identity.present) {{`
2. **SCAN DOWN** to find the ACTUAL LAST line in this else if block (look for assignments like `UE->ng_5G_S_TMSI_Part1 = s_tmsi_part1;`)
3. **FIND** the closing brace `}}` right after that last assignment
4. **USE** that closing section as your original_code

⚠️ **EXAMPLE OF MISSING ELSE**: If you see code like:
```
if (condition1) {{
    // some code
}} else if (condition2) {{
    // some code
    UE->some_field = value;  // <- FIND THE ACTUAL LAST ASSIGNMENT
}}
// <-- MISSING ELSE CLAUSE HERE!
NR_CellGroupConfig_t *cellGroupConfig = NULL;  // Code continues
```
You MUST find the LAST assignment (like `UE->ng_5G_S_TMSI_Part1 = s_tmsi_part1;`) + closing brace and add the else clause there.

### ROOT CAUSE ANALYSIS REQUIREMENTS
- Always check **network connectivity first** for 5G issues.  
- Distinguish between **network vs. code logic** failures.  
- Trace error flow from **log messages** to code path.  
- **CRITICAL**: Look for **incomplete conditional logic patterns**:
  * Hardcoded constant comparisons (e.g., `== 3`) instead of runtime field checks
  * Missing `else` branches in multi-case scenarios (enum handling, protocol states)
  * Unvalidated assumptions about input data structure/presence
- If branches or identity handling are clearly missing or malformed, **reconstruct the expected flow** using:
  * 3GPP specifications
  * Variable names and surrounding code context
  * Typical OpenAirInterface gNB patterns  
- Do **NOT** require the original code to be supplied—derive expected behavior from specs and context.

### CODE PATCH RULES
- **CRITICAL**: Preserve existing correct logic; **insert or adjust only the minimal lines** necessary to restore intended behavior.  
- Use **exact surrounding code lines or variable names** for placement (`after line containing "..."`).  
- **CRITICAL**: Look for **hardcoded constant comparisons** (like `== 3`, `== 1`) and replace with **proper dynamic checks** using available variables/fields.
- **CRITICAL**: If the function has incomplete conditional logic (missing `else` branches, unhandled enum cases), **reconstruct the missing branches** instead of adding trivial guards.  
- **CRITICAL**: For segmentation faults, trace the **actual cause** (uninitialized variables, missing validation, incomplete state handling) rather than adding generic null checks.
- Never invent functions or config parameters that don't exist.  
- Validate variable scope before referencing them.  
- **AVOID GENERIC NULL CHECKS**: If a segmentation fault is due to skipped handling of input cases, **add the missing handling**, not just a pointer check.

### COMMON SEGMENTATION FAULT PATTERNS TO LOOK FOR
- **Hardcoded enum comparisons**: `if (ENUM_CONSTANT == hardcoded_value)` → should be `if (data->field == ENUM_CONSTANT)`
- **CRITICAL: Missing else/default cases**: Incomplete switch/if-else chains for enum/state handling
- **MANDATORY: Always add else branch to any if-else if chain that lacks final else clause**
- **Uninitialized pointers**: Variables that remain NULL when certain conditions aren't met
- **Protocol state violations**: Functions proceeding without validating required protocol fields
- **Array/structure access**: Accessing fields without checking structure validity first

### 🚨 CRITICAL REQUIREMENT: MISSING ELSE BRANCHES 🚨
**EXAMINE THE PROVIDED CODE CAREFULLY**: Look for incomplete if-else if chains and add the missing else clause:
- In the provided code, if you see: `if (condition1) {{ ... }} else if (condition2) {{ ... }}` WITHOUT a final `else`
- AND the code continues AFTER the closing brace without handling other cases
- You MUST create a SEPARATE patch with these EXACT specifications:
  * `"original_code": "FIND THE ACTUAL LAST ASSIGNMENT in the else if block (like UE->ng_5G_S_TMSI_Part1 = s_tmsi_part1;) + closing brace }}"` 
  * `"patched_code": "SAME ENDING LINES + }} else {{\\n    LOG_E(NR_RRC, \\"Unhandled ue_Identity.present value: %d\\", rrcSetupRequest->ue_Identity.present);\\n    return;\\n}}"` 
  * `"line_numbers": "replace the section ending with the actual last assignment + closing brace"`
  * **CRITICAL**: Look for the ACTUAL FINAL STATEMENT in the else if block (not function calls in the middle)
- **NEVER** use function calls like rrc_gNB_create_ue_context - find the REAL LAST assignment like UE->field = value;

### CONFIGURATION VALIDATION
- Use actual config names and values from candidate configs.  
- Verify subnet and port compatibility using deployment context when relevant.  
- Suggest meaningful corrections only (never no-ops).

### RESPONSE FORMAT
Respond with **ONLY valid JSON** in this EXACT structure:

{{
    "suspected_functions": ["function1", "function2"],
    "suspected_configs": ["config1", "config2"], 
    "reason": "Detailed root cause explanation",
    "config_fix": "Specific configuration corrections with exact values",
    "code_patches": [
        {{
            "function_name": "function_name",
            "file_path": "path/to/file.c",
            "patch_type": "targeted_insertion_or_adjustment",
            "original_code": "// Line(s) around the issue",
            "patched_code": "// The exact corrected code snippet",
            "line_numbers": "EXACT line numbers (e.g., '120-125') or specific context (e.g., 'after line containing \\"amf_desc_p = ngap_gNB_get_AMF\\"')",
            "description": "Why this correction resolves the error"
        }}
    ],
    "config_patches": [
        {{
            "config_name": "parameter_name",
            "file_path": "path/to/config.conf",
            "patch_type": "set_value",
            "current_value": "current_value",
            "new_value": "corrected_value",
            "line_number": "approximate_line_or_section",
            "relevance_score": "confidence_score_from_analysis",
            "description": "Why this config change resolves the error"
        }}
    ],
    "root_cause_analysis": "Deep technical analysis of why this error occurs",
    "investigation_steps": ["step1", "step2", "step3"]
}}

### ADDITIONAL HINTS
- **Protocol Compliance**: Use 3GPP specifications and RFCs to understand expected behavior and mandatory validations.
- **Network Connectivity**: For 5G/LTE issues, verify IP reachability, routing, and port accessibility between components.
- **Context Analysis**: Look at surrounding code patterns, variable names, and function purposes to understand intended behavior.
- **Error Correlation**: Connect error messages to specific code paths and protocol state transitions.''',

            "Bug Analysis": '''You are an expert software debugging and bug analysis specialist with deep knowledge of telecommunications systems, 5G/LTE protocols, and root cause analysis methodologies. Based on the provided dataset, logs, or error information, conduct a comprehensive bug analysis.

Your task is to analyze the given information and provide a detailed bug analysis that includes:

1. **Problem Identification**
   - Clearly define the bug or issue
   - Identify the symptoms and error messages
   - Determine the scope and impact of the problem

2. **Root Cause Analysis**
   - Trace the issue to its fundamental cause
   - Identify contributing factors and dependencies
   - Analyze the sequence of events leading to the problem

3. **Technical Analysis**
   - Examine relevant code sections, configurations, or protocols
   - Identify specific failure points and error conditions
   - Analyze system behavior and state transitions

4. **Impact Assessment**
   - Evaluate the severity and priority of the issue
   - Assess potential risks and consequences
   - Determine affected components and users

5. **Resolution Recommendations**
   - Propose specific fixes and workarounds
   - Suggest preventive measures and monitoring
   - Provide implementation guidance and testing strategies

Provide a comprehensive, actionable bug analysis that helps resolve the issue and prevent similar problems in the future.'''
        }
    
    def handle_prompt_selection(self, prompt_key, prompt_text_edit=None):
        """Handle prompt selection and update the prompt content."""
        try:
            self.current_prompt_key = prompt_key
            
            if prompt_key == "Custom":
                if prompt_text_edit:
                    prompt_text_edit.clear()
                    prompt_text_edit.setReadOnly(False)
                    prompt_text_edit.setPlaceholderText("Enter your custom prompt here...")
                self.latest_custom_prompt = ""
                
            elif prompt_key in self.prompts:
                # Handle dictionary structure for Test Case template
                if prompt_key == "Test Case" and isinstance(self.prompts[prompt_key], dict):
                    # Merge system and user prompts
                    system_prompt = self.prompts[prompt_key].get("System Prompt", "")
                    user_prompt = self.prompts[prompt_key].get("User Prompt", "")
                    merged_prompt = f"{system_prompt}\n\n{user_prompt}"
                    if prompt_text_edit:
                        prompt_text_edit.setReadOnly(True)
                        prompt_text_edit.setText(merged_prompt)
                elif prompt_key == "Test Script":
                    # Handle Test Script template
                    if prompt_text_edit:
                        prompt_text_edit.setReadOnly(True)
                        prompt_text_edit.setText(self.prompts[prompt_key])
                else:
                    # Handle regular string prompts
                    if prompt_text_edit:
                        prompt_text_edit.setReadOnly(True)
                        prompt_text_edit.setText(self.prompts[prompt_key])
            else:
                if prompt_text_edit:
                    prompt_text_edit.clear()
                    prompt_text_edit.setReadOnly(True)
                    prompt_text_edit.setPlaceholderText("Select a template or choose 'Custom' to enter your own prompt...")
            
        except Exception as e:
            raise Exception(f"Error handling prompt selection: {str(e)}")
    
    def update_prompt_variables(self, prompt_text_edit=None):
        """Update the prompt with selected variable values."""
        try:
            # Determine which template is currently selected
            current_prompt_key = self.current_prompt_key
            
            # Get the original prompt template based on current selection
            if current_prompt_key == "Test Case" and 'Test Case' in self.prompts:
                test_case_prompt = self.prompts['Test Case']
                if isinstance(test_case_prompt, dict):
                    # Merge system and user prompts
                    system_prompt = test_case_prompt.get('System Prompt', '')
                    user_prompt = test_case_prompt.get('User Prompt', '')
                    original_prompt = f"{system_prompt}\n\n{user_prompt}"
                else:
                    original_prompt = test_case_prompt
            elif current_prompt_key == "Test Script" and 'Test Script' in self.prompts:
                original_prompt = self.prompts['Test Script']
            else:
                return
            
            # Create a copy to work with
            updated_prompt = original_prompt
            
            # Replace all variables with their current selections
            if self.domain_combo and not self.domain_combo.startswith("Select"):
                updated_prompt = updated_prompt.replace('{DOMAIN}', self.domain_combo)
            if self.system_type_combo and not self.system_type_combo.startswith("Select"):
                updated_prompt = updated_prompt.replace('{SYSTEM_TYPE}', self.system_type_combo)
            if self.primary_feature_combo and not self.primary_feature_combo.startswith("Select"):
                updated_prompt = updated_prompt.replace('{PRIMARY_FEATURE}', self.primary_feature_combo)
            if self.connection_method_combo and not self.connection_method_combo.startswith("Select"):
                updated_prompt = updated_prompt.replace('{CONNECTION_METHOD}', self.connection_method_combo)
            if self.login_credentials_combo and not self.login_credentials_combo.startswith("Select"):
                updated_prompt = updated_prompt.replace('{LOGIN_CREDENTIALS}', self.login_credentials_combo)
            if self.access_mode_combo and not self.access_mode_combo.startswith("Select"):
                updated_prompt = updated_prompt.replace('{ACCESS_MODE}', self.access_mode_combo)
            if self.language_combo and not self.language_combo.startswith("Select"):
                language_text = self.language_combo
                # Remove "(Coming Soon)" text if present
                if " (Coming Soon)" in language_text:
                    language_text = language_text.replace(" (Coming Soon)", "")
                updated_prompt = updated_prompt.replace('{LANGUAGE}', language_text)
            
            # For Test Script, also replace the reference code placeholder
            if current_prompt_key == "Test Script" and self.ue_attach_utils:
                updated_prompt = updated_prompt.replace('{self.ue_attach_utils}', self.ue_attach_utils)
            
            # Update the prompt text
            if prompt_text_edit:
                prompt_text_edit.setPlainText(updated_prompt)
                
        except Exception as e:
            raise Exception(f"Error updating prompt variables: {str(e)}")
    
    def handle_language_selection(self, selected_language):
        """Handle language selection with validation."""
        try:
            if "Coming Soon" in selected_language:
                raise Exception(f"{selected_language.split(' (')[0]} support is coming soon! Currently only Python is supported for test script generation.")
            
            # Update prompt variables if Python is selected
            if selected_language == "Python":
                self.update_prompt_variables()
                
        except Exception as e:
            raise Exception(f"Error handling language selection: {str(e)}")
    
    def upload_reference_code(self, file_path):
        """Handle file upload for reference code."""
        try:
            if not file_path or not os.path.exists(file_path):
                raise Exception("Invalid file path provided")
            
            # Read the file content
            with open(file_path, 'r', encoding='utf-8') as file:
                file_content = file.read()
            
            # Update the ue_attach_utils with the uploaded content
            self.ue_attach_utils = file_content
            
            # Return file name for display
            file_name = os.path.basename(file_path)
            return file_name
                
        except Exception as e:
            raise Exception(f"Error uploading reference code: {str(e)}")
    
    def get_current_prompt(self, prompt_text_edit=None):
        """Get the current prompt from either template or custom input."""
        try:
            if prompt_text_edit:
                prompt_text = prompt_text_edit.toPlainText().strip()
            else:
                # If no UI component, return the current prompt based on selection
                if self.current_prompt_key == "Custom":
                    prompt_text = self.latest_custom_prompt
                elif self.current_prompt_key in self.prompts:
                    prompt_text = self.prompts[self.current_prompt_key]
                else:
                    prompt_text = ""
            
            if not prompt_text:
                return None
                
            return prompt_text
        except Exception as e:
            raise Exception(f"Error getting current prompt: {str(e)}")
    
    def generate_response_from_text(self, text_content, selected_prompt, update_progress_callback=None):
        """Generate test scripts with improved structure and error handling."""
        try:
            print(f"🔍 DEBUG generate_response_from_text:")
            print(f"  - current_prompt_key: {self.current_prompt_key}")
            print(f"  - text_content length: {len(text_content) if text_content else 0}")
            print(f"  - selected_prompt length: {len(selected_prompt) if selected_prompt else 0}")
            print(f"  - selected_prompt preview: {selected_prompt[:100] if selected_prompt else 'EMPTY'}...")
            print(f"  - text_content preview: {text_content[:200] if text_content else 'EMPTY'}...")
            
            if update_progress_callback:
                update_progress_callback(30)
            
            # Create the prompt based on whether it's a template or custom prompt
            if self.current_prompt_key == "Custom":
                prompt = f'''
Based on the following dataset, please respond to the user's request:

DATASET:
{text_content}

USER REQUEST:
{selected_prompt}

Please base your response on the dataset content above and reference specific data, values, or steps from the dataset when applicable.
'''         
            elif self.current_prompt_key == "Test Case":
                # For Test Case, use the merged prompt directly with dataset
                prompt = f'''
DATASET:
{text_content}

{selected_prompt}
'''
                self.testcases_list = "Test Case"
            elif self.current_prompt_key == "Test Script":
                prompt = f'''
You are an expert in 5G network test automation.

Based ONLY on the following dataset, generate a complete Python test script.

DATASET:
{text_content}

INSTRUCTIONS:
{selected_prompt}
Note: Make Sure the generated scripts covers the testcases which are in {self.testcases_name}
'''
            else:
                # For other templates (Testing Strategy, Bug Analysis, etc.), use the template directly with dataset
                prompt = f'''
DATASET:
{text_content}

{selected_prompt}
'''
            
            if update_progress_callback:
                update_progress_callback(50)
            
            # Generate response using OpenAI
            response = self.generate_response(prompt)
            if not response or "Error:" in response:
                return f"Error generating response: {response}"
                
            if update_progress_callback:
                update_progress_callback(70)
            
            # Post-process the response
            processed_response = self.post_process_test_script(response)
            
            if update_progress_callback:
                update_progress_callback(90)
            
            return processed_response
            
        except Exception as e:
            return f"An error occurred while generating the test script: {str(e)}"
    
    def generate_response(self, prompt):
        """Generate response using OpenAI API with proper error handling."""
        try:
            print("=== PROMPT SENT TO OPENAI ===")
            print(prompt)
            print("=============================")
            
            # Make the API call with proper parameters
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": "You are an expert test automation engineer specializing in 5G network testing."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=2000,
                top_p=1.0,
                frequency_penalty=0.0,
                presence_penalty=0.0
            )

            # Extract and validate the response
            if response and hasattr(response, 'choices') and response.choices:
                if len(response.choices) > 0 and hasattr(response.choices[0], 'message'):
                    content = response.choices[0].message.content
                    if content and isinstance(content, str):
                        return content.strip()
            
            return "Error: Invalid response structure"

        except Exception as e:
            error_msg = f"Error in response generation: {str(e)}"
            print(error_msg)
            return error_msg
    
    def post_process_test_script(self, script_content):
        """Return the script as generated by the LLM, no extra prepending."""
        if not script_content:
            return "Error: No script content to process"
        return script_content
    
    def save_response_to_file(self, response, folder_path):
        """Save generated test scripts in a structured test suite format."""
        try:
            print(f"🔍 DEBUG: save_response_to_file called with folder_path={folder_path}")
            print(f"🔍 DEBUG: current_prompt_key={self.current_prompt_key}")
            print(f"🔍 DEBUG: response length={len(response) if response else 0}")
            # Create base test suite directory if it doesn't exist
            test_suite_dir = Path(folder_path) / "test_suite"
            test_suite_dir.mkdir(parents=True, exist_ok=True)

            # Create subdirectories based on test type
            if self.current_prompt_key:
                test_type = self.current_prompt_key.lower().replace(" ", "_")
                test_type_dir = test_suite_dir / test_type
                test_type_dir.mkdir(exist_ok=True)

                # Generate timestamp for unique file naming
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

                # Save as JSON if test type is 'test_case', else as .py
                if test_type == "test_case":
                    test_script_file = test_type_dir / f"{test_type}_{timestamp}.json"
                    # Try to parse response as JSON, else save as raw string
                    try:
                        parsed_response = json.loads(response)
                        with open(test_script_file, 'w', encoding='utf-8') as f:
                            json.dump(parsed_response, f, indent=4)
                    except json.JSONDecodeError:
                        # If not valid JSON, save as raw text
                        with open(test_script_file, 'w', encoding='utf-8') as f:
                            json.dump({"test_cases": response}, f, indent=4)
                else:
                    test_script_file = test_type_dir / f"{test_type}_{timestamp}.py"
                    with open(test_script_file, 'w', encoding='utf-8') as f:
                        f.write(response)

                return True, str(test_script_file)
            else:
                # Default save location if no specific test type
                default_file = Path(folder_path) / f"generated_script_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py"
                with open(default_file, 'w', encoding='utf-8') as f:
                    f.write(response)
                
                return True, str(default_file)

        except Exception as e:
            print(f"❌ ERROR in save_response_to_file: {str(e)}")
            import traceback
            print(f"❌ Traceback: {traceback.format_exc()}")
            return False, f"Error saving file: {str(e)}"
    
    def generate_with_new_prompt(self, text_content, new_prompt, previous_response=None):
        """Generate a new response using the new prompt, previous response, and dataset."""
        try:
            if not text_content:
                raise Exception("Please load a dataset first.")
            if not new_prompt:
                raise Exception("Please enter a new prompt.")
            
            previous_script = previous_response or self.previous_response or ""
            dataset_summary = text_content[:1000]  # Use first 1000 chars as summary
            
            # Build iterative refinement prompt
            iterative_prompt = f"""
Using the dataset provided and the current user prompt, generate or update a detailed, well-structured test script. If a previous script is provided, use it as a foundation to refine, expand, or optimize the script based on the new prompt.

Your goals:
1. Improve the test script with each new prompt.
2. Retain relevant parts of the previous script.
3. Integrate new instructions or validations as requested.
4. Ensure the final script is complete, readable, and executable.

Inputs:
- Current Prompt: {new_prompt}
- Previous Test Script (previous response): {previous_script}
- Dataset Summary: {dataset_summary}

Respond only with the refined script. Format it using appropriate comments and structure.

Note: Make Sure you update the script or testcase which is placed in {new_prompt} and don't modify any other thing which is not placed in {new_prompt}
"""
            
            # Generate response
            response = self.generate_response(iterative_prompt)
            
            # Update previous response
            self.previous_response = response
            
            return response
            
        except Exception as e:
            raise Exception(f"Error generating with new prompt: {str(e)}")
    
    def load_dataset(self, file_paths):
        """Load dataset from multiple file paths."""
        try:
            if not file_paths:
                raise Exception("No file paths provided")
            
            content_parts = []
            for file_path in file_paths:
                if not os.path.exists(file_path):
                    continue
                
                file_extension = os.path.splitext(file_path)[1].lower()
                
                if file_extension == '.txt':
                    with open(file_path, 'r', encoding='utf-8') as file:
                        content = file.read()
                elif file_extension == '.json':
                    with open(file_path, 'r', encoding='utf-8') as file:
                        data = json.load(file)
                        content = json.dumps(data, indent=2)
                elif file_extension == '.pdf':
                    content = self._extract_pdf_content(file_path)
                elif file_extension == '.docx':
                    content = self._extract_docx_content(file_path)
                elif file_extension == '.xlsx':
                    content = self._extract_xlsx_content(file_path)
                elif file_extension in ['.py', '.md', '.csv', '.log']:
                    # For other text-based file types, try to read as text
                    try:
                        with open(file_path, 'r', encoding='utf-8') as file:
                            content = file.read()
                    except:
                        continue
                else:
                    # For unknown file types, try to read as text
                    try:
                        with open(file_path, 'r', encoding='utf-8') as file:
                            content = file.read()
                    except:
                        continue
                
                content_parts.append(f"=== {os.path.basename(file_path)} ===\n{content}\n")
            
            if not content_parts:
                raise Exception("No valid files could be loaded")
            
            self.text_content = "\n".join(content_parts)
            return self.text_content
            
        except Exception as e:
            raise Exception(f"Error loading dataset: {str(e)}")
    
    def create_test_generation_prompt(self, test_type, input_text):
        """Create appropriate prompt for test generation based on type."""
        prompts = {
            "unit": f"Generate a Python unit test script for the following function/description:\n{input_text}\n\nInclude:\n- Test class setup\n- Multiple test cases\n- Edge cases\n- Error handling\n- Mocking if needed",
            "integration": f"Generate a Python integration test script for the following scenario:\n{input_text}\n\nInclude:\n- Test environment setup\n- Dependencies handling\n- Multiple integration scenarios\n- Cleanup procedures",
            "performance": f"Generate a Python performance test script with these requirements:\n{input_text}\n\nInclude:\n- Performance metrics collection\n- Load simulation\n- Results analysis\n- Threshold validation",
            "conformance": f"Generate a Python test script for 3GPP conformance testing based on:\n{input_text}\n\nInclude:\n- 3GPP specification compliance\n- Protocol conformance checks\n- Message flow validation\n- Success/failure criteria"
        }
        return prompts.get(test_type, "")
    
    def handle_test_generation(self, test_type, input_text, output_directory=None):
        """Handle the generation of test scripts based on type and input."""
        try:
            # Generate appropriate prompt based on test type
            prompt = self.create_test_generation_prompt(test_type, input_text)
            
            # Generate test script using OpenAI
            response = self.generate_response(prompt)
            
            # Post-process the response
            processed_script = self.post_process_test_script(response)
            
            # Save the generated test script if output directory is provided
            if output_directory:
                success, result = self.save_response_to_file(processed_script, output_directory)
                if not success:
                    raise Exception(f"Failed to save test script: {result}")
                return processed_script, result
            else:
                return processed_script, None
            
        except Exception as e:
            raise Exception(f"Failed to generate test script: {str(e)}")
    
    def set_variables(self, domain=None, system_type=None, primary_feature=None, 
                     connection_method=None, login_credentials=None, access_mode=None, language=None):
        """Set the variable values for prompt replacement."""
        self.domain_combo = domain
        self.system_type_combo = system_type
        self.primary_feature_combo = primary_feature
        self.connection_method_combo = connection_method
        self.login_credentials_combo = login_credentials
        self.access_mode_combo = access_mode
        self.language_combo = language
    
    def get_prompts(self):
        """Get available prompts."""
        return self.prompts
    
    def add_custom_prompt(self, name, content):
        """Add a new custom prompt."""
        if name in self.prompts:
            raise Exception(f"Prompt '{name}' already exists")
        self.prompts[name] = content
    
    def update_prompt(self, name, content):
        """Update an existing prompt."""
        if name not in self.prompts:
            raise Exception(f"Prompt '{name}' does not exist")
        self.prompts[name] = content
    
    def _load_custom_templates_from_json(self):
        """Load custom templates from JSON files and override defaults."""
        try:
            # Load updated/modified default templates from custom_templates.json
            if self.custom_templates_path.exists():
                with open(self.custom_templates_path, 'r', encoding='utf-8') as f:
                    custom_templates = json.load(f)
                
                # Override default prompts with custom ones
                for name, content in custom_templates.items():
                    # Special handling for "Test Case" - load as string from JSON, convert to dict for API use
                    if name == "Test Case":
                        if isinstance(content, str):
                            # Content is saved as string in JSON - convert to dict for in-memory use
                            if "AVAILABLE COMMANDS/INTERFACES:" in content or "TASK:" in content:
                                marker_pos = content.find("AVAILABLE COMMANDS/INTERFACES:")
                                if marker_pos == -1:
                                    marker_pos = content.find("TASK:")
                                if marker_pos > 0:
                                    system_prompt = content[:marker_pos].rstrip()
                                    user_prompt = content[marker_pos:]  # Keep marker and everything after
                                    self.prompts[name] = {
                                        "System Prompt": system_prompt,
                                        "User Prompt": user_prompt
                                    }
                                    print(f"✅ Loaded Test Case from JSON (string) and converted to dict structure")
                                else:
                                    # Can't split, use as User Prompt only
                                    if name in self.prompts and isinstance(self.prompts[name], dict):
                                        original = self.prompts[name]
                                        self.prompts[name] = {
                                            "System Prompt": original.get("System Prompt", ""),
                                            "User Prompt": content
                                        }
                                    else:
                                        self.prompts[name] = {
                                            "System Prompt": "",
                                            "User Prompt": content
                                        }
                            else:
                                # No marker found - use as System Prompt, preserve original User Prompt if available
                                if name in self.prompts and isinstance(self.prompts[name], dict):
                                    original = self.prompts[name]
                                    self.prompts[name] = {
                                        "System Prompt": content,
                                        "User Prompt": original.get("User Prompt", "")
                                    }
                                else:
                                    # No original, create new structure
                                    self.prompts[name] = {
                                        "System Prompt": content,
                                        "User Prompt": ""
                                    }
                        elif isinstance(content, dict):
                            # Legacy format - still support dict in JSON
                            self.prompts[name] = content
                        else:
                            # Unknown type, keep as is
                            self.prompts[name] = content
                    else:
                        self.prompts[name] = content
                
                print(f"✅ Loaded {len(custom_templates)} updated templates from custom_templates.json")
            
            # Load user-saved custom templates from user_saved_templates.json
            if self.user_custom_templates_path.exists():
                with open(self.user_custom_templates_path, 'r', encoding='utf-8') as f:
                    user_templates = json.load(f)
                
                # Add user-saved templates to prompts
                for name, content in user_templates.items():
                    self.prompts[name] = content
                
                print(f"✅ Loaded {len(user_templates)} user-saved templates from user_saved_templates.json")
            else:
                print(f"ℹ️ No user-saved templates file found. Creating new file.")
                # Create empty file if it doesn't exist
                self.user_custom_templates_path.parent.mkdir(parents=True, exist_ok=True)
                with open(self.user_custom_templates_path, 'w', encoding='utf-8') as f:
                    json.dump({}, f, indent=2)
        except Exception as e:
            print(f"⚠️ Error loading custom templates from JSON: {e}")
    
    def save_prompt_to_file(self, name, content):
        """Save or update a prompt permanently to JSON file.
        
        If it's a default template name (like "Test Script", "Test Case"), save to custom_templates.json (updated prompts).
        If it's a user-created custom template (like "5G"), save to user_saved_templates.json.
        
        Special handling for "Test Case" template: If content is a string (merged), try to split it back into dict structure.
        """
        try:
            # For "Test Case", convert dict to string for saving, but keep dict in memory for API use
            if name == "Test Case":
                # If content is a dict, merge it into a single string for saving
                if isinstance(content, dict):
                    system_prompt = content.get("System Prompt", "")
                    user_prompt = content.get("User Prompt", "")
                    # Merge into single string for JSON storage
                    merged_content = system_prompt + "\n\n" + user_prompt if user_prompt else system_prompt
                    # Keep dict in memory for API use
                    self.prompts[name] = content
                    # Use merged string for saving to JSON
                    content = merged_content
                elif isinstance(content, str):
                    # Content is already a string - save it directly
                    # But for in-memory use, convert to dict if we have original structure
                    if name in self.prompts and isinstance(self.prompts[name], dict):
                        # Keep the dict structure in memory for API compatibility
                        # The string will be saved to JSON
                        pass
                    else:
                        # No original dict, create one from the string for API use
                        if "AVAILABLE COMMANDS/INTERFACES:" in content or "TASK:" in content:
                            marker_pos = content.find("AVAILABLE COMMANDS/INTERFACES:")
                            if marker_pos == -1:
                                marker_pos = content.find("TASK:")
                            if marker_pos > 0:
                                system_prompt = content[:marker_pos].rstrip()
                                user_prompt = content[marker_pos:]
                                self.prompts[name] = {
                                    "System Prompt": system_prompt,
                                    "User Prompt": user_prompt
                                }
                            else:
                                self.prompts[name] = content
                        else:
                            self.prompts[name] = content
                else:
                    # Unknown type, convert to string
                    content = str(content)
                    self.prompts[name] = content
            else:
                # For other templates, update in-memory prompts dictionary
                self.prompts[name] = content
            
            # Check if it's a default template (updated/modified) or user-created custom template
            default_templates = ["Test Script", "Test Case", "Testing Strategy", "Bug Analysis", 
                               "Feature Design", "Code Review", "Performance Test", "API Design", "Code Assistant"]
            
            is_default_template = name in default_templates
            
            if is_default_template:
                # Save to custom_templates.json (for updated default templates)
                custom_templates = {}
                if self.custom_templates_path.exists():
                    try:
                        with open(self.custom_templates_path, 'r', encoding='utf-8') as f:
                            custom_templates = json.load(f)
                    except:
                        custom_templates = {}
                
                # For "Test Case", save as string (already converted above if it was a dict)
                # At this point, content should be a string for "Test Case"
                if name == "Test Case":
                    if not isinstance(content, str):
                        # Safety check: convert to string if somehow still not a string
                        content = str(content)
                    print(f"💾 Saving 'Test Case' as string (length: {len(content)} chars)")
                
                custom_templates[name] = content
                print(f"💾 Saving '{name}' to custom_templates.json (type: {type(content).__name__})")
                if isinstance(content, dict):
                    print(f"   Dict keys: {list(content.keys())}")
                    if "System Prompt" in content:
                        print(f"   System Prompt length: {len(content['System Prompt'])} chars")
                    if "User Prompt" in content:
                        print(f"   User Prompt length: {len(content['User Prompt'])} chars")
                
                self.custom_templates_path.parent.mkdir(parents=True, exist_ok=True)
                
                with open(self.custom_templates_path, 'w', encoding='utf-8') as f:
                    json.dump(custom_templates, f, indent=2, ensure_ascii=False)
                
                # Verify the file was written correctly
                try:
                    with open(self.custom_templates_path, 'r', encoding='utf-8') as f:
                        verify_data = json.load(f)
                        if name in verify_data:
                            saved_content = verify_data[name]
                            if isinstance(saved_content, dict):
                                print(f"✅ Verification: '{name}' saved as dict with keys: {list(saved_content.keys())}")
                            else:
                                print(f"✅ Verification: '{name}' saved as {type(saved_content).__name__}")
                        else:
                            print(f"⚠️ Warning: '{name}' not found in saved file!")
                except Exception as e:
                    print(f"⚠️ Could not verify saved file: {e}")
                
                print(f"✅ Updated default template '{name}' saved to: {self.custom_templates_path}")
                return True, f"Updated template '{name}' saved successfully to {self.custom_templates_path}"
            else:
                # Save to user_saved_templates.json (for user-created custom templates)
                print(f"💾 Saving user-created custom template '{name}' to user_saved_templates.json")
                print(f"   File path: {self.user_custom_templates_path}")
                print(f"   File path exists before save: {self.user_custom_templates_path.exists()}")
                
                user_templates = {}
                if self.user_custom_templates_path.exists():
                    try:
                        with open(self.user_custom_templates_path, 'r', encoding='utf-8') as f:
                            user_templates = json.load(f)
                            print(f"   Loaded existing templates: {list(user_templates.keys())}")
                    except Exception as e:
                        print(f"   Warning: Could not load existing file: {e}")
                        user_templates = {}
                else:
                    print(f"   File does not exist, will create new file")
                
                user_templates[name] = content
                print(f"   Adding template '{name}' to dictionary")
                print(f"   Dictionary now has {len(user_templates)} template(s): {list(user_templates.keys())}")
                
                # Ensure directory exists
                self.user_custom_templates_path.parent.mkdir(parents=True, exist_ok=True)
                print(f"   Directory created/verified: {self.user_custom_templates_path.parent}")
                
                # Save to JSON file
                with open(self.user_custom_templates_path, 'w', encoding='utf-8') as f:
                    json.dump(user_templates, f, indent=2, ensure_ascii=False)
                
                print(f"   File written successfully")
                print(f"   File exists after save: {self.user_custom_templates_path.exists()}")
                
                # Verify the file was written correctly
                try:
                    with open(self.user_custom_templates_path, 'r', encoding='utf-8') as f:
                        verify_templates = json.load(f)
                        print(f"   Verification: File contains {len(verify_templates)} template(s): {list(verify_templates.keys())}")
                        if name in verify_templates:
                            print(f"   ✅ Template '{name}' verified in file!")
                        else:
                            print(f"   ❌ Template '{name}' NOT found in file after save!")
                except Exception as e:
                    print(f"   ❌ Error verifying file: {e}")
                
                print(f"✅ User-saved custom template '{name}' saved to: {self.user_custom_templates_path}")
                return True, f"Custom template '{name}' saved successfully to {self.user_custom_templates_path}"
                
        except Exception as e:
            print(f"❌ Error saving prompt to JSON: {e}")
            return False, str(e)
    
    def delete_custom_template(self, name):
        """Delete a custom template from JSON file."""
        try:
            # Check if it's a default template (cannot delete)
            default_templates = ["Test Script", "Test Case", "Testing Strategy", "Bug Analysis", 
                               "Feature Design", "Code Review", "Performance Test", "API Design", "Code Assistant"]
            
            if name in default_templates:
                return False, f"Cannot delete default template '{name}'"
            
            # Remove from memory
            if name in self.prompts:
                del self.prompts[name]
            
            # Try to delete from user_saved_templates.json first (user-created templates)
            if self.user_custom_templates_path.exists():
                with open(self.user_custom_templates_path, 'r', encoding='utf-8') as f:
                    user_templates = json.load(f)
                
                if name in user_templates:
                    del user_templates[name]
                    
                    # Save updated JSON
                    with open(self.user_custom_templates_path, 'w', encoding='utf-8') as f:
                        json.dump(user_templates, f, indent=2, ensure_ascii=False)
                    
                    print(f"✅ Template '{name}' deleted from user_saved_templates.json")
                    return True, f"Template '{name}' deleted successfully"
            
            # Fallback: Try to delete from custom_templates.json (updated defaults)
            if self.custom_templates_path.exists():
                with open(self.custom_templates_path, 'r', encoding='utf-8') as f:
                    custom_templates = json.load(f)
                
                if name in custom_templates:
                    del custom_templates[name]
                    
                    # Save updated JSON
                    with open(self.custom_templates_path, 'w', encoding='utf-8') as f:
                        json.dump(custom_templates, f, indent=2, ensure_ascii=False)
                    
                    print(f"✅ Template '{name}' deleted from custom_templates.json")
                    return True, f"Template '{name}' deleted successfully"
            
            return False, f"Template '{name}' not found in custom templates"
                
        except Exception as e:
            print(f"❌ Error deleting template: {e}")
            return False, str(e)
    
    def get_custom_template_names(self):
        """Get list of user-saved custom template names (from user_saved_templates.json).
        This returns only user-created custom templates, not updated default templates.
        """
        try:
            print(f"🔍 Getting custom template names from: {self.user_custom_templates_path}")
            print(f"   File exists: {self.user_custom_templates_path.exists()}")
            
            user_custom_names = []
            
            # Load from user_saved_templates.json (user-created custom templates)
            if self.user_custom_templates_path.exists():
                with open(self.user_custom_templates_path, 'r', encoding='utf-8') as f:
                    user_templates = json.load(f)
                    print(f"   File content: {user_templates}")
                    user_custom_names = list(user_templates.keys())
                    print(f"✅ Found {len(user_custom_names)} user-saved custom templates in user_saved_templates.json")
                    print(f"   Template names: {user_custom_names}")
            else:
                print(f"ℹ️ user_saved_templates.json not found at: {self.user_custom_templates_path}")
                print(f"   Will create empty file on next save")
            
            return user_custom_names
        except Exception as e:
            print(f"❌ Error getting custom template names: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def _extract_pdf_content(self, file_path):
        """Extract text content from PDF file."""
        try:
            import PyPDF2
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                content = ""
                for page in pdf_reader.pages:
                    content += page.extract_text() + "\n"
                return content
        except ImportError:
            return f"[PDF file: {os.path.basename(file_path)} - PyPDF2 not installed]"
        except Exception as e:
            return f"[Error reading PDF: {str(e)}]"
    
    def _extract_docx_content(self, file_path):
        """Extract text content from DOCX file."""
        try:
            from docx import Document
            doc = Document(file_path)
            content = ""
            for paragraph in doc.paragraphs:
                content += paragraph.text + "\n"
            return content
        except ImportError:
            return f"[DOCX file: {os.path.basename(file_path)} - python-docx not installed]"
        except Exception as e:
            return f"[Error reading DOCX: {str(e)}]"
    
    def _extract_xlsx_content(self, file_path):
        """Extract text content from XLSX file."""
        try:
            import pandas as pd
            # Read all sheets
            excel_file = pd.ExcelFile(file_path)
            content = ""
            for sheet_name in excel_file.sheet_names:
                df = pd.read_excel(file_path, sheet_name=sheet_name)
                content += f"\n=== Sheet: {sheet_name} ===\n"
                content += df.to_string(index=False) + "\n"
            return content
        except ImportError:
            return f"[XLSX file: {os.path.basename(file_path)} - pandas not installed]"
        except Exception as e:
            return f"[Error reading XLSX: {str(e)}]"


# Example usage and testing
if __name__ == "__main__":
    # Initialize the test script generator
    generator = TestScriptGenerator()
    
    # Example: Set variables
    generator.set_variables(
        domain="Network Infrastructure",
        system_type="5G",
        primary_feature="Attach",
        connection_method="SSH",
        login_credentials="admin@<IP>",
        access_mode="CLI mode",
        language="Python"
    )
    
    # Example: Generate test script
    sample_text = "Sample dataset content for 5G attach procedure..."
    sample_prompt = "Generate test cases for UE attach procedure"
    
    try:
        result = generator.generate_response_from_text(sample_text, sample_prompt)
        print("Generated test script:")
        print(result) 
    except Exception as e:
        print(f"Error: {e}")

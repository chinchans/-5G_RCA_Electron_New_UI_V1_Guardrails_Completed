[
  {
    "testCaseID": "TC_POS_001_LTE_5G_NSA_Single_UE_Attach_Detach",
    "title": "Positive Test: Successful LTE and 5G NSA Attach and Detach of Single UE under Excellent Radio Conditions",
    "category": "POSITIVE TESTING",
    "preconditions": [
      "Test setup configured as single cell scenario with only one active UE",
      "UE placed under excellent radio conditions (LTE RSRP or 5G SS-RSRP as per Clause 4.6)",
      "All other cells powered off",
      "End-to-end system operational for LTE or 5G NSA"
    ],
    "testSteps": [
      "Configure test setup according to test configuration and record parameters",
      "Start logs to capture call flow and signaling",
      "Power ON the UE to trigger attach to LTE or 5G NSA cell",
      "Wait for successful attach indication (attach complete message received)",
      "Verify UE is attached to correct cell by checking PCI, Global eNB ID/Global gNB ID, ARFCN/NR-ARFCN",
      "Power OFF the UE to trigger detach from network",
      "Wait for successful detach confirmation (detach accept received)",
      "Stop and save logs for analysis",
      "Repeat the attach-detach cycle 10 times and record attach success rate, detach success rate, and attach latency"
    ],
    "expectedResults": [
      "Attach success rate is 100% for all 10 iterations",
      "Detach success rate is 100% for all 10 iterations",
      "Attach latency measured and recorded with minimum, average, and maximum values",
      "UE remains attached to correct cell throughout the test",
      "No connectivity issues during the test"
    ],
    "postconditions": [
      "Test logs saved for reference",
      "KPI values recorded in Table 5-2 and Table 5-3"
    ],
    "commandsUsed": [],
    "verificationMethods": [
      "Monitor and analyze attach request and attach complete messages in logs",
      "Validate detach request and detach accept messages in logs",
      "Check UE log/application for correct cell attachment",
      "Measure and record attach latency from attach request to attach complete"
    ]
  },
  {
    "testCaseID": "TC_NEG_001_LTE_5G_NSA_Attach_Detach_Failure_Recovery",
    "title": "Negative Test: UE Attach/Detach Failure and Recovery Handling under Non-Excellent Radio Conditions",
    "category": "NEGATIVE TESTING",
    "preconditions": [
      "Test setup as single cell with one UE",
      "Radio conditions degraded deliberately (RSRP below excellent threshold)",
      "End-to-end system operational"
    ],
    "testSteps": [
      "Configure test setup and record parameters",
      "Start logs to capture signaling",
      "Power ON the UE to initiate attach procedure",
      "Observe attach failure scenarios such as attach reject or timeout",
      "Verify UE retries attach procedure according to specification",
      "Power OFF UE to initiate detach procedure during failure state",
      "Verify detach procedure behavior and recovery",
      "Stop and save logs"
    ],
    "expectedResults": [
      "Attach failure is properly handled with retries or failure indication",
      "Detach procedure completes gracefully even if attach failed",
      "UE recovers and can eventually complete attach when radio conditions improve",
      "No unexpected crashes or deadlocks in UE or network"
    ],
    "postconditions": [
      "Logs saved for failure analysis",
      "Failure KPIs documented"
    ],
    "commandsUsed": [],
    "verificationMethods": [
      "Check signaling logs for attach reject, timeout, and retry messages",
      "Validate detach procedures even under failure",
      "Monitor UE state transitions and error handling"
    ]
  },
  {
    "testCaseID": "TC_EDGE_001_LTE_5G_NSA_Radio_Condition_Boundary",
    "title": "Edge Case Test: Attach and Detach at Boundary of Excellent Radio Conditions",
    "category": "EDGE CASES",
    "preconditions": [
      "Test setup with single cell and one UE",
      "Set radio conditions exactly at minimum coupling loss limit and borderline RSRP threshold for excellent conditions"
    ],
    "testSteps": [
      "Configure test environment with radio conditions at boundary values",
      "Start capture logs",
      "Power ON UE to initiate attach",
      "Verify attach success or failure at boundary",
      "Power OFF UE to initiate detach",
      "Verify detach success",
      "Repeat 10 times to observe stability"
    ],
    "expectedResults": [
      "Attach and detach succeed with stable performance at boundary conditions",
      "If failure occurs, it is logged and appropriate error handling is verified"
    ],
    "postconditions": [
      "Logs saved for boundary condition analysis"
    ],
    "commandsUsed": [],
    "verificationMethods": [
      "Analyze RSRP and coupling loss measurements",
      "Validate signaling flows for attach and detach",
      "Evaluate KPIs at boundary conditions"
    ]
  },
  {
    "testCaseID": "TC_PERF_001_LTE_5G_NSA_Attach_Detach_Stress_Test",
    "title": "Performance Test: Load and Stress Test of 10 Consecutive Attach/Detach Cycles under Excellent Radio Conditions",
    "category": "PERFORMANCE TESTING",
    "preconditions": [
      "Single cell test setup with one UE",
      "Excellent radio conditions maintained throughout the test"
    ],
    "testSteps": [
      "Configure test setup and record parameters",
      "Start logging signaling and call flow",
      "Repeat 10 times: Power ON UE -> Wait for successful attach -> Power OFF UE -> Wait for successful detach",
      "Measure attach latency, attach success rate, detach success rate",
      "Monitor system resource usage and any degradation during repeated attach/detach"
    ],
    "expectedResults": [
      "All 10 attach and detach cycles complete successfully with 100% success rate",
      "Attach latency remains within acceptable limits without significant increase over iterations",
      "No resource leakage or system degradation observed"
    ],
    "postconditions": [
      "Performance KPIs recorded and saved with logs"
    ],
    "commandsUsed": [],
    "verificationMethods": [
      "Measure attach latency and success rates",
      "Monitor system logs for errors or warnings",
      "Check resource utilization statistics if available"
    ]
  },
  {
    "testCaseID": "TC_SEC_001_LTE_5G_NSA_Attach_Detach_Authentication_Authorization",
    "title": "Security Test: Authentication and Authorization Validation during Attach and Detach Procedures",
    "category": "SECURITY TESTING",
    "preconditions": [
      "Test setup with single UE",
      "Security credentials provisioned correctly for UE"
    ],
    "testSteps": [
      "Start logging signaling",
      "Power ON UE and initiate attach",
      "Verify authentication and authorization procedures complete successfully (e.g., security context establishment)",
      "Power OFF UE and initiate detach",
      "Verify security context is properly released and no unauthorized access occurs",
      "Attempt attach with invalid credentials and verify rejection"
    ],
    "expectedResults": [
      "Authentication and authorization succeed with valid credentials",
      "Detach procedure securely releases context",
      "Attach rejected with invalid credentials"
    ],
    "postconditions": [
      "Security logs saved for audit"
    ],
    "commandsUsed": [],
    "verificationMethods": [
      "Analyze signaling logs for authentication messages",
      "Check UE and network security context states",
      "Verify attach rejection on invalid credentials"
    ]
  },
  {
    "testCaseID": "TC_INT_001_LTE_5G_NSA_Secondary_Node_Release_Procedure",
    "title": "Integration Test: 5G NSA Secondary Node Release (SN Release) Procedure Validation",
    "category": "INTEGRATION TESTING",
    "preconditions": [
      "5G NSA setup with Master Node (MN) and Secondary Node (SN)",
      "UE attached to both MN and SN"
    ],
    "testSteps": [
      "Start logging signaling",
      "Initiate SN Release procedure from MN by sending SgNB Release Request",
      "Verify SN sends SgNB Release Request Acknowledge or rejects if SN change triggered",
      "Verify MN sends RRCConnectionReconfiguration to UE to release SCG configuration",
      "Verify SN sends SN Status Transfer message and Secondary RAT Data Usage Report",
      "Confirm data forwarding starts and path update procedure if applicable",
      "Verify UE Context Release message reception by SN and resource release",
      "Repeat SN Release procedure initiated by SN with SgNB Release Required message",
      "Verify MN response and resource cleanup"
    ],
    "expectedResults": [
      "SN Release procedure completes successfully for both MN and SN initiated cases",
      "Signaling flows match 3GPP TS 37.340 Clause 10.4.1",
      "UE releases SCG configuration properly",
      "Data forwarding and reporting messages sent correctly",
      "Resources properly released in SN"
    ],
    "postconditions": [
      "Logs saved for integration validation"
    ],
    "commandsUsed": [],
    "verificationMethods": [
      "Analyze signaling message sequence for SN Release",
      "Verify UE RRC reconfiguration messages",
      "Check data forwarding start and reports",
      "Confirm resource release in SN"
    ]
  },
  {
    "testCaseID": "TC_USAB_001_LTE_5G_NSA_Test_Procedure_Clarity_and_Usability",
    "title": "Usability Test: Clarity and Simplicity of LTE and 5G NSA Attach-Detach Test Procedure Documentation",
    "category": "USABILITY TESTING",
    "preconditions": [
      "Test documentation available to test engineers"
    ],
    "testSteps": [
      "Review the test procedure steps for LTE and 5G NSA attach-detach",
      "Evaluate clarity and completeness of instructions",
      "Attempt to execute test based solely on documentation",
      "Collect feedback from test engineers on usability",
      "Identify any ambiguities or missing details"
    ],
    "expectedResults": [
      "Test procedure is clear, complete, and can be followed without external guidance",
      "No ambiguities or conflicting instructions found",
      "Test engineers can successfully execute tests as per documentation"
    ],
    "postconditions": [
      "Usability report with recommendations"
    ],
    "commandsUsed": [],
    "verificationMethods": [
      "Gather subjective feedback",
      "Observe test execution based on documentation"
    ]
  },
  {
    "testCaseID": "TC_COMP_001_LTE_5G_NSA_Environment_Variation_Compatibility",
    "title": "Compatibility Test: Attach-Detach Functionality in Lab vs Field Environments for LTE and 5G NSA",
    "category": "COMPATIBILITY TESTING",
    "preconditions": [
      "Test system available for both lab and field setups",
      "UE and network configured identically for both environments"
    ],
    "testSteps": [
      "Execute attach-detach test sequence in lab environment with RF shielded box or cable connection",
      "Record KPIs and success rates",
      "Execute same attach-detach test sequence in field environment with UE near radiated antenna",
      "Record KPIs and success rates",
      "Compare results for any discrepancies or compatibility issues"
    ],
    "expectedResults": [
      "Attach and detach success rates are consistent across environments",
      "KPIs within acceptable variance range",
      "No environment-specific failures or issues observed"
    ],
    "postconditions": [
      "Compatibility report generated"
    ],
    "commandsUsed": [],
    "verificationMethods": [
      "Analyze KPIs and logs from both environments",
      "Compare attach latency and success rates"
    ]
  },
  {
    "testCaseID": "TC_5G_REG_001_5G_NSA_Registration_Procedure",
    "title": "5G NSA Registration Test: Registration Request → Registration Accept → Registration Complete",
    "category": "POSITIVE TESTING",
    "preconditions": [
      "5G NSA setup with UE and network properly configured",
      "UE powered OFF initially"
    ],
    "testSteps": [
      "Power ON UE to initiate Registration Request to the network",
      "Monitor network signaling to capture Registration Accept message",
      "Verify UE sends Registration Complete message",
      "Confirm registration state in network and UE",
      "Repeat for 10 iterations to confirm stability"
    ],
    "expectedResults": [
      "Registration procedure completes successfully for all iterations",
      "No registration failures or rejects",
      "UE registered on correct 5G NSA cell"
    ],
    "postconditions": [
      "Registration logs saved for audit"
    ],
    "commandsUsed": [],
    "verificationMethods": [
      "Analyze signaling for Registration Request, Accept, and Complete",
      "Verify UE registration state"
    ]
  },
  {
    "testCaseID": "TC_5G_PDU_001_5G_NSA_PDU_Session_Establishment",
    "title": "5G NSA PDU Session Test: PDU Session Establishment Request → Authentication → Accept → User Plane Setup → N3 Tunnel Creation",
    "category": "POSITIVE TESTING",
    "preconditions": [
      "5G NSA setup with UE registered",
      "SMF and UPF functional and accessible"
    ],
    "testSteps": [
      "Initiate PDU Session Establishment Request from UE",
      "Perform PDU Session Authentication if applicable",
      "Receive PDU Session Accept message from network",
      "Verify User Plane setup including N3 tunnel creation",
      "Monitor related signaling with SMF, UPF, and N11/N4 interfaces",
      "Confirm QoS Flow establishment and Session Release procedures"
    ],
    "expectedResults": [
      "PDU Session successfully established with all signaling completed",
      "User plane data path established via N3 tunnel",
      "QoS flows set up as per configuration",
      "Session release handled correctly on termination"
    ],
    "postconditions": [
      "Session logs and KPIs saved"
    ],
    "commandsUsed": [],
    "verificationMethods": [
      "Check signaling messages for PDU session establishment",
      "Verify N3 tunnel creation",
      "Monitor SMF, UPF, and session management interfaces"
    ]
  },
  {
    "testCaseID": "TC_5G_HAND_001_5G_NSA_Xn_Handover_Procedure",
    "title": "5G NSA Xn Handover Test: Measurement Report → Handover Required → Handover Request → Handover Request Ack → RRC Reconfiguration → Path Switch → Handover Complete",
    "category": "POSITIVE TESTING",
    "preconditions": [
      "5G NSA setup with UE attached and connected to source gNB",
      "Neighbor gNB available for handover"
    ],
    "testSteps": [
      "Trigger Measurement Report from UE indicating need for handover",
      "Receive and process Handover Required message at source gNB",
      "Send Handover Request to target gNB",
      "Receive Handover Request Ack from target gNB",
      "Send RRC Reconfiguration message to UE to switch to target gNB",
      "Perform path switch procedure in core network",
      "Confirm Handover Complete message from UE",
      "Verify data continuity and signaling integrity"
    ],
    "expectedResults": [
      "Handover completes successfully with no data loss",
      "Signaling flows occur in correct sequence as per 3GPP specs",
      "UE connected to target gNB after handover"
    ],
    "postconditions": [
      "Handover logs saved for analysis"
    ],
    "commandsUsed": [],
    "verificationMethods": [
      "Analyze signaling message sequence for Xn handover",
      "Verify data path continuity post handover"
    ]
  }
]
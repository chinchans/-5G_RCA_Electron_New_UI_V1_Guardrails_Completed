[
  {
    "testCaseID": "TC_POS_001_LTE_AttachDetach_Single_UE",
    "title": "Positive Test: LTE Attach and Detach with Single UE under Excellent Radio Conditions",
    "description": "Validate successful LTE attach and detach procedures for a single UE under excellent radio conditions as per 3GPP TS 23.401 Clause 5.3.2.1 and 5.3.8.2.1.",
    "preconditions": [
      "Single cell scenario with no inter-cell interference",
      "UE placed at cell center with LTE RSRP as defined in Clause 4.6",
      "All other cells powered off",
      "O-RAN C-plane operational"
    ],
    "testSteps": [
      "Configure test setup according to test configuration and record parameters",
      "Ensure UE is under excellent LTE radio conditions",
      "Start logging call flow and signaling messages",
      "Power ON the UE to trigger LTE attach procedure",
      "Wait for attach complete confirmation",
      "Verify UE is attached to correct cell by checking PCI, Global eNB ID, ARFCN as per test configuration",
      "Power OFF the UE to trigger LTE detach procedure",
      "Wait for detach complete confirmation validating UE context release and RRC connection release messages",
      "Stop and save logs",
      "Repeat attach-detach cycle 10 times and record attach success rate, detach success rate, and attach latency"
    ],
    "expectedResults": [
      "Attach success rate = 100%",
      "Detach success rate = 100%",
      "Attach latency recorded with minimum, average and maximum values",
      "Logs confirm correct attach and detach signaling per 3GPP specifications"
    ],
    "postconditions": [
      "UE detached and network state clean",
      "Test logs saved"
    ],
    "testCategory": [
      "POSITIVE TESTING",
      "INTEGRATION TESTING"
    ],
    "commandsUsed": [],
    "verificationMethods": [
      "Confirm attach request and attach complete messages in logs",
      "Confirm detach request and detach accept messages in logs",
      "Verify no connectivity issues during test",
      "Check radio parameters RSRP, RSRQ within expected excellent range"
    ]
  },
  {
    "testCaseID": "TC_POS_002_5GNSA_AttachDetach_Single_UE",
    "title": "Positive Test: 5G NSA Attach and Detach with Single UE under Excellent Radio Conditions",
    "description": "Validate successful 5G NSA attach, secondary node addition, and detach procedures for a single UE under excellent radio conditions as per 3GPP TS 23.401 and 3GPP TS 37.340.",
    "preconditions": [
      "Single cell scenario with no inter-cell interference",
      "UE placed at cell center with 5G SS-RSRP as per Clause 4.6",
      "All other cells powered off",
      "O-RAN C-plane operational"
    ],
    "testSteps": [
      "Configure test setup according to test configuration and record parameters",
      "Ensure UE is under excellent 5G NSA radio conditions",
      "Start logging call flow and signaling messages",
      "Power ON the UE to trigger 5G NSA attach procedure",
      "Wait for attach complete and secondary node addition (SgNB addition request & reconfiguration complete) confirmation",
      "Verify UE is attached to correct LTE and 5G cells by checking PCI, Global eNB ID/Global gNB, ARFCN/NR-ARFCN as per test configuration",
      "Power OFF the UE to trigger LTE detach and 5G secondary node release procedures",
      "Wait for detach complete confirmation validating UE context release, RRC connection release messages, and secondary node release signaling",
      "Stop and save logs",
      "Repeat attach-detach cycle 10 times and record attach success rate, secondary node addition success rate, and detach success rate"
    ],
    "expectedResults": [
      "Attach success rate = 100%",
      "Secondary node addition success rate = 100%",
      "Detach success rate = 100%",
      "Logs confirm correct attach, secondary node addition, and detach signaling per 3GPP specifications"
    ],
    "postconditions": [
      "UE detached and network state clean",
      "Test logs saved"
    ],
    "testCategory": [
      "POSITIVE TESTING",
      "INTEGRATION TESTING"
    ],
    "commandsUsed": [],
    "verificationMethods": [
      "Confirm attach request and attach complete messages in logs",
      "Confirm SgNB addition request and reconfiguration complete messages in logs",
      "Confirm detach request and detach accept messages in logs",
      "Confirm secondary node release signaling flows (SgNB Release Request, Release Acknowledge, RRCConnectionReconfiguration)",
      "Check radio parameters 5G SS-RSRP within expected excellent range"
    ]
  },
  {
    "testCaseID": "TC_NEG_001_LTE_Attach_Invalid_RadioConditions",
    "title": "Negative Test: LTE Attach with Poor Radio Conditions",
    "description": "Validate LTE attach failure when UE experiences poor radio conditions below minimum coupling loss or RSRP threshold.",
    "preconditions": [
      "Single cell scenario",
      "UE placed at cell edge or inside shielded box with poor LTE RSRP (below Clause 4.6 minimum)",
      "O-RAN C-plane operational"
    ],
    "testSteps": [
      "Configure test setup with poor radio conditions",
      "Start logging call flow and signaling messages",
      "Power ON UE to trigger LTE attach",
      "Wait for attach failure or timeout",
      "Stop and save logs"
    ],
    "expectedResults": [
      "Attach procedure fails or times out",
      "No successful attach complete message",
      "UE logs or applications show attach failure",
      "Attach success rate recorded as less than 100%"
    ],
    "postconditions": [
      "UE not attached to cell",
      "Test logs saved"
    ],
    "testCategory": [
      "NEGATIVE TESTING"
    ],
    "commandsUsed": [],
    "verificationMethods": [
      "Verify absence of attach complete messages in logs",
      "Check UE logs for attach failure indications",
      "Confirm radio parameters below threshold"
    ]
  },
  {
    "testCaseID": "TC_NEG_002_5GNSA_Detach_Failure_Missing_SgNB_ReleaseAck",
    "title": "Negative Test: 5G NSA Detach Failure Due to Missing SgNB Release Acknowledge",
    "description": "Validate network and UE behavior when Secondary Node Release procedure does not receive SgNB Release Request Acknowledge message (MN initiated).",
    "preconditions": [
      "5G NSA attach successful",
      "O-RAN C-plane operational"
    ],
    "testSteps": [
      "Trigger MN initiated Secondary Node Release by sending SgNB Release Request message",
      "Simulate SN not responding with SgNB Release Request Acknowledge message",
      "Monitor signaling and UE behavior",
      "Attempt UE detach procedure",
      "Log call flow and signaling messages"
    ],
    "expectedResults": [
      "MN detects missing SgNB Release Request Acknowledge",
      "Detachment procedure may stall or fallback to recovery",
      "UE context and SCG configuration release incomplete or delayed",
      "Logs show lack of secondary node release confirmation"
    ],
    "postconditions": [
      "Potential residual UE context at SN",
      "Test logs saved"
    ],
    "testCategory": [
      "NEGATIVE TESTING",
      "INTEGRATION TESTING"
    ],
    "commandsUsed": [],
    "verificationMethods": [
      "Check signaling logs for missing SgNB Release Request Acknowledge",
      "Verify UE and MN reaction to missing release acknowledgment",
      "Inspect for fallback or error recovery procedures"
    ]
  },
  {
    "testCaseID": "TC_EDGE_001_LTE_AttachDetach_At_Minimum_CouplingLoss",
    "title": "Edge Case Test: LTE Attach and Detach at Minimum Coupling Loss Threshold",
    "description": "Validate LTE attach and detach behavior when UE radio conditions are exactly at minimum coupling loss limit defined in Clause 4.6.",
    "preconditions": [
      "Single cell scenario",
      "UE placed to experience LTE RSRP exactly at minimum coupling loss threshold",
      "O-RAN C-plane operational"
    ],
    "testSteps": [
      "Setup radio conditions to minimum coupling loss",
      "Start logging call flow and signaling messages",
      "Power ON UE to attach",
      "Wait for attach complete confirmation",
      "Power OFF UE to detach",
      "Wait for detach complete confirmation",
      "Repeat 10 times recording KPIs"
    ],
    "expectedResults": [
      "Attach and detach success rate = 100%",
      "Attach latency within acceptable range",
      "No unexpected failures due to borderline radio conditions"
    ],
    "postconditions": [
      "UE detached cleanly",
      "Logs saved"
    ],
    "testCategory": [
      "EDGE CASES",
      "POSITIVE TESTING"
    ],
    "commandsUsed": [],
    "verificationMethods": [
      "Verify attach and detach messages in logs",
      "Confirm radio parameters exactly at threshold",
      "Review KPIs for anomalies"
    ]
  },
  {
    "testCaseID": "TC_PERF_001_LTE_AttachDetach_Iteration_Stress",
    "title": "Performance Test: LTE Attach and Detach Stress Test with 10 Iterations",
    "description": "Measure attach success rate, detach success rate, and attach latency over 10 consecutive attach-detach cycles under excellent radio conditions.",
    "preconditions": [
      "Single cell scenario",
      "UE under excellent LTE radio conditions",
      "O-RAN C-plane operational"
    ],
    "testSteps": [
      "Configure test setup and start logging",
      "Perform 10 consecutive attach-detach cycles by powering ON and OFF the UE",
      "Record attach success rate, detach success rate, and attach latency for each iteration",
      "Analyze latency values (min, average, max)"
    ],
    "expectedResults": [
      "Attach and detach success rate = 100%",
      "Attach latency stable and within defined performance bounds",
      "No degradation observed over iterations"
    ],
    "postconditions": [
      "UE detached and network stable",
      "Logs saved"
    ],
    "testCategory": [
      "PERFORMANCE TESTING"
    ],
    "commandsUsed": [],
    "verificationMethods": [
      "Analyze success/failure counters",
      "Latency statistics calculation",
      "Log review for any anomalies"
    ]
  },
  {
    "testCaseID": "TC_SEC_001_Attach_Authentication_Validation",
    "title": "Security Test: Validate Authentication during LTE and 5G NSA Attach Procedures",
    "description": "Verify that authentication procedures occur correctly during LTE and 5G NSA attach as per 3GPP standards and unauthorized attach attempts are rejected.",
    "preconditions": [
      "Single cell scenario",
      "UE configured with valid credentials",
      "O-RAN C-plane operational"
    ],
    "testSteps": [
      "Start logging signaling messages",
      "Power ON UE to perform attach with valid credentials",
      "Verify authentication challenge and response messages in attach procedure",
      "Attempt attach with invalid credentials (e.g., wrong SIM or IMSI)",
      "Verify attach rejection due to authentication failure",
      "Repeat for 5G NSA attach"
    ],
    "expectedResults": [
      "Authentication procedure triggers as per standard",
      "Valid UE attaches successfully",
      "Invalid UE attach requests rejected with appropriate cause",
      "No unauthorized network access"
    ],
    "postconditions": [
      "Unauthorized UEs not attached",
      "Logs saved for audit"
    ],
    "testCategory": [
      "SECURITY TESTING"
    ],
    "commandsUsed": [],
    "verificationMethods": [
      "Inspect authentication messages in logs",
      "Confirm attach accept or reject responses",
      "Check UE logs for authentication status"
    ]
  },
  {
    "testCaseID": "TC_INT_001_SecondaryNodeRelease_MN_Initiated",
    "title": "Integration Test: MN Initiated Secondary Node Release Procedure Verification",
    "description": "Validate the MN initiated Secondary Node Release procedure including SgNB Release Request and Acknowledge messages, RRCConnectionReconfiguration, SN Status Transfer, and UE Context Release as per Clause 10.4.1 EN-DC.",
    "preconditions": [
      "5G NSA attach successful with active secondary node",
      "O-RAN C-plane operational"
    ],
    "testSteps": [
      "Trigger MN initiated Secondary Node Release by sending SgNB Release Request",
      "Validate receipt of SgNB Release Request Acknowledge from SN",
      "Verify RRCConnectionReconfiguration message indicates release of SCG configuration to UE",
      "Confirm SN sends SN Status Transfer message",
      "Monitor data forwarding start between SN and MN",
      "Verify Secondary RAT Data Usage Report message sent by SN",
      "Check path update procedure initiation if applicable",
      "Confirm UE Context Release message reception and SN resource release"
    ],
    "expectedResults": [
      "All messages exchanged as per specification",
      "UE releases SCG configuration cleanly",
      "SN resources released properly",
      "Data forwarding occurs without service gap",
      "No signaling errors"
    ],
    "postconditions": [
      "Secondary node context released",
      "Logs collected for analysis"
    ],
    "testCategory": [
      "INTEGRATION TESTING",
      "POSITIVE TESTING"
    ],
    "commandsUsed": [],
    "verificationMethods": [
      "Verify message flows in logs per Clause 10.4.1",
      "Check UE RRC state transitions",
      "Confirm resource release on SN"
    ]
  },
  {
    "testCaseID": "TC_INT_002_SecondaryNodeRelease_SN_Initiated",
    "title": "Integration Test: SN Initiated Secondary Node Release Procedure Verification",
    "description": "Validate the SN initiated Secondary Node Release procedure including SgNB Release Required, SgNB Release Confirm, RRCConnectionReconfiguration, SN Status Transfer, and UE Context Release as per Clause 10.4.1 EN-DC.",
    "preconditions": [
      "5G NSA attach successful with active secondary node",
      "O-RAN C-plane operational"
    ],
    "testSteps": [
      "Trigger SN initiated Secondary Node Release by SN sending SgNB Release Required",
      "Verify MN responds with SgNB Release Confirm including data forwarding addresses",
      "Validate RRCConnectionReconfiguration message to UE for SCG release",
      "Confirm SN sends SN Status Transfer message",
      "Monitor data forwarding start between SN and MN",
      "Confirm Secondary RAT Data Usage Report message sent",
      "Check path update procedure initiation if applicable",
      "Verify UE Context Release message reception and SN resource release"
    ],
    "expectedResults": [
      "Complete message flow as per 3GPP specifications",
      "UE releases SCG configuration cleanly",
      "SN resources released properly",
      "Data forwarding occurs without service gap",
      "No signaling errors"
    ],
    "postconditions": [
      "Secondary node context released",
      "Logs collected"
    ],
    "testCategory": [
      "INTEGRATION TESTING",
      "POSITIVE TESTING"
    ],
    "commandsUsed": [],
    "verificationMethods": [
      "Message flow confirmation in logs",
      "UE RRC state monitoring",
      "SN resource release verification"
    ]
  },
  {
    "testCaseID": "TC_USAB_001_TestProcedure_Clarity",
    "title": "Usability Test: Verify Clarity and Simplicity of Test Procedure Documentation",
    "description": "Evaluate if the test procedure steps for LTE and 5G NSA attach-detach are clear, unambiguous, and easy to follow for test engineers.",
    "preconditions": [
      "Access to test procedure documentation"
    ],
    "testSteps": [
      "Review test procedure documentation for clarity and completeness",
      "Attempt to execute test as per documented steps without additional guidance",
      "Collect feedback from testers on ease of understanding",
      "Identify ambiguous or confusing instructions",
      "Suggest improvements"
    ],
    "expectedResults": [
      "Test procedure is easy to follow",
      "No significant ambiguities or missing information",
      "Testers can successfully carry out tests using documentation alone"
    ],
    "postconditions": [],
    "testCategory": [
      "USABILITY TESTING"
    ],
    "commandsUsed": [],
    "verificationMethods": [
      "Tester feedback collection",
      "Execution success rate based on documentation",
      "Documentation review metrics"
    ]
  },
  {
    "testCaseID": "TC_COMP_001_TestSetup_Environment_Variations",
    "title": "Compatibility Test: Verify Test Procedure Execution in Lab and Field Environments",
    "description": "Validate attach-detach test procedure performance and results consistency when executed in laboratory (with RF shielded box and variable attenuator) and in field setup (UE at cell center).",
    "preconditions": [
      "Test setup configured for lab environment with RF shielded box or emulator",
      "Test setup configured for field environment with UE near radiated antenna"
    ],
    "testSteps": [
      "Execute LTE attach-detach test procedure in lab setup",
      "Record KPIs and logs",
      "Execute LTE attach-detach test procedure in field setup",
      "Record KPIs and logs",
      "Compare attach success rate, detach success rate, attach latency, and radio parameters across environments"
    ],
    "expectedResults": [
      "Attach and detach success rates are consistent and close to 100% across environments",
      "Attach latency differences are within acceptable range",
      "Radio parameters meet excellent condition criteria in both setups",
      "No unexpected failures due to environment"
    ],
    "postconditions": [
      "Test logs saved from both environments"
    ],
    "testCategory": [
      "COMPATIBILITY TESTING",
      "PERFORMANCE TESTING"
    ],
    "commandsUsed": [],
    "verificationMethods": [
      "Compare KPIs and logs from both setups",
      "Check radio parameter measurements",
      "Analyze environment impact on attach-detach procedures"
    ]
  },
  {
    "testCaseID": "TC_REG_001_5GNSA_Registration_Procedure",
    "title": "5G NSA Registration Test: Registration Request → Registration Accept → Registration Complete",
    "description": "Validate the 5G NSA UE registration procedure including Registration Request, Registration Accept, and Registration Complete messages.",
    "preconditions": [
      "5G NSA network available",
      "UE powered off"
    ],
    "testSteps": [
      "Power ON the UE",
      "UE sends Registration Request message to AMF",
      "Network processes and responds with Registration Accept message",
      "UE sends Registration Complete message confirming registration",
      "Capture and log all registration signaling messages"
    ],
    "expectedResults": [
      "Registration Request message sent by UE",
      "Registration Accept message received from network",
      "Registration Complete message sent by UE",
      "UE registered successfully with network",
      "No errors or retransmissions in registration messages"
    ],
    "postconditions": [
      "UE registered and ready for session establishment"
    ],
    "testCategory": [
      "POSITIVE TESTING",
      "REGISTRATION TEST"
    ],
    "commandsUsed": [],
    "verificationMethods": [
      "Analyze signaling logs for registration messages",
      "Verify UE registration state",
      "Confirm no error messages"
    ]
  },
  {
    "testCaseID": "TC_PDU_001_5GNSA_PDU_Session_Establishment",
    "title": "5G NSA PDU Session Test: PDU Session Establishment Request → Authentication → Accept → User Plane Setup → N3 Tunnel Creation",
    "description": "Validate PDU Session Establishment procedure including request, authentication, acceptance, user plane setup, and N3 tunnel creation in 5G NSA.",
    "preconditions": [
      "UE registered on 5G NSA network",
      "Network supports PDU session establishment"
    ],
    "testSteps": [
      "UE sends PDU Session Establishment Request message",
      "Network performs PDU Session Authentication if applicable",
      "Network sends PDU Session Accept message",
      "User plane resources are setup including N3 tunnel creation between UPF and gNB",
      "Capture all signaling related to SMF, UPF, N11, N4 interfaces, QoS Flow setup",
      "Verify session release signaling after completion"
    ],
    "expectedResults": [
      "PDU Session Establishment Request accepted by network",
      "Authentication successful if required",
      "User plane established and N3 tunnel created",
      "QoS flows configured as per policy",
      "Session released correctly when requested"
    ],
    "postconditions": [
      "PDU session active and functional",
      "Logs saved for all signaling"
    ],
    "testCategory": [
      "POSITIVE TESTING",
      "PDU SESSION TEST"
    ],
    "commandsUsed": [],
    "verificationMethods": [
      "Examine signaling logs for PDU session messages",
      "Confirm user plane setup in network elements",
      "Verify QoS flow establishment",
      "Check session release messages"
    ]
  },
  {
    "testCaseID": "TC_HO_001_5GNSA_Xn_Handover",
    "title": "5G NSA Xn Handover Test: Measurement Report → Handover Required → Handover Request → Handover Request Ack → RRC Reconfiguration → Path Switch → Handover Complete",
    "description": "Validate the 5G NSA Xn handover procedure with all mandatory signaling messages and UE state transitions.",
    "preconditions": [
      "UE attached on 5G NSA network",
      "Neighboring cells available to handover"
    ],
    "testSteps": [
      "UE sends Measurement Report indicating need for handover",
      "Network sends Handover Required message to source gNB",
      "Source gNB sends Handover Request to target gNB",
      "Target gNB responds with Handover Request Acknowledge",
      "Source gNB sends RRC Reconfiguration message to UE to handover",
      "UE performs handover and sends Handover Complete message to target gNB",
      "Target gNB initiates Path Switch procedure to AMF/UPF",
      "Capture all signaling messages and UE state changes"
    ],
    "expectedResults": [
      "All handover signaling messages exchanged successfully",
      "UE seamlessly handed over to target gNB",
      "User plane switched correctly without interruption",
      "No dropped calls or failures"
    ],
    "postconditions": [
      "UE attached to target cell",
      "Logs saved for handover procedure"
    ],
    "testCategory": [
      "POSITIVE TESTING",
      "HANDOVER / MOBILITY TEST"
    ],
    "commandsUsed": [],
    "verificationMethods": [
      "Check signaling messages for handover flow",
      "Monitor UE RRC state transitions",
      "Verify path switch completion",
      "Confirm no user plane interruption"
    ]
  }
]
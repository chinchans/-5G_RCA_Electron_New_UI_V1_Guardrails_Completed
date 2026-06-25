```json
[
    {
        "testCaseId": "TC-001",
        "description": "Validate successful LTE attach procedure for a single UE.",
        "preconditions": "The UE is powered ON and in excellent radio conditions.",
        "steps": [
            "Power ON the UE to attach to the LTE cell.",
            "Wait for the attach process to complete.",
            "Observe signaling messages exchanged during the attach process."
        ],
        "expectedResult": "The UE successfully attaches to the LTE cell and receives an IP address allocation.",
        "commandsUsed": [],
        "verificationMethods": [
            "Check UE logs for successful attach request and attach complete.",
            "Validate attached cell information (PCI, Global eNB ID, ARFCN).",
            "Ensure that the IP address allocation was successful.",
            "Monitor the signaling messages to ensure they comply with 3GPP standards."
        ]
    },
    {
        "testCaseId": "TC-002",
        "description": "Measure attach latency for LTE attach procedure.",
        "preconditions": "The UE is powered ON and in excellent radio conditions.",
        "steps": [
            "Power ON the UE to attach to the LTE cell.",
            "Record the time from the attach request to the attach complete."
        ],
        "expectedResult": "Attach latency is captured and reported.",
        "commandsUsed": [],
        "verificationMethods": [
            "Calculate minimum, average, and maximum latency from recorded times."
        ]
    },
    {
        "testCaseId": "TC-003",
        "description": "Validate successful detach procedure for LTE.",
        "preconditions": "The UE is attached to the LTE cell.",
        "steps": [
            "Power OFF the connected UE to detach from the network.",
            "Wait for the detach process to complete."
        ],
        "expectedResult": "The UE successfully detaches from the LTE cell.",
        "commandsUsed": [],
        "verificationMethods": [
            "Check UE logs for successful detach request and detach accept.",
            "Validate signaling connection release messages."
        ]
    },
    {
        "testCaseId": "TC-004",
        "description": "Validate successful 5G NSA attach procedure for a single UE.",
        "preconditions": "The UE is powered ON and in excellent radio conditions.",
        "steps": [
            "Power ON the UE to attach to the 5G NSA cell.",
            "Wait for the attach process to complete."
        ],
        "expectedResult": "The UE successfully attaches to the 5G NSA cell.",
        "commandsUsed": [],
        "verificationMethods": [
            "Check UE logs for successful attach request and attach complete.",
            "Validate attached cell information (PCI, Global gNB ID, NR-ARFCN)."
        ]
    },
    {
        "testCaseId": "TC-005",
        "description": "Validate secondary node addition for 5G NSA.",
        "preconditions": "The UE is attached to the 5G NSA cell.",
        "steps": [
            "Send SgNB Addition Request to add secondary node.",
            "Wait for SgNB Addition Request Acknowledge."
        ],
        "expectedResult": "The secondary node is successfully added.",
        "commandsUsed": [
            "SgNB Addition Request"
        ],
        "verificationMethods": [
            "Validate SgNB Addition Request and SgNB Addition Request Acknowledge messages."
        ]
    },
    {
        "testCaseId": "TC-006",
        "description": "Validate 5G NSA detach procedure including secondary node release.",
        "preconditions": "The UE is attached to the 5G NSA cell with an active secondary node.",
        "steps": [
            "Power OFF the connected UE to detach from the network.",
            "Wait for the detach process to complete."
        ],
        "expectedResult": "The UE and secondary node successfully detach from the network.",
        "commandsUsed": [],
        "verificationMethods": [
            "Check UE logs for successful detach request and detach accept.",
            "Validate secondary node release signaling."
        ]
    },
    {
        "testCaseId": "TC-007",
        "description": "Validate attach success rate over 10 iterations for LTE.",
        "preconditions": "Setup is configured for 10 iterations of attach process.",
        "steps": [
            "Perform LTE attach procedure 10 times.",
            "Record success for each iteration."
        ],
        "expectedResult": "Attach success rate should be 100%.",
        "commandsUsed": [],
        "verificationMethods": [
            "Count successful attach instances and calculate the percentage."
        ]
    },
    {
        "testCaseId": "TC-008",
        "description": "Validate detach success rate over 10 iterations for LTE.",
        "preconditions": "Setup is configured for 10 iterations of detach process.",
        "steps": [
            "Perform LTE detach procedure 10 times.",
            "Record success for each iteration."
        ],
        "expectedResult": "Detach success rate should be 100%.",
        "commandsUsed": [],
        "verificationMethods": [
            "Count successful detach instances and calculate the percentage."
        ]
    },
    {
        "testCaseId": "TC-009",
        "description": "Validate edge cases for attach procedure under poor radio conditions.",
        "preconditions": "Setup is configured to simulate poor radio conditions.",
        "steps": [
            "Power ON the UE to attempt attach to the LTE cell.",
            "Observe the attach process."
        ],
        "expectedResult": "Attach should fail or timeout.",
        "commandsUsed": [],
        "verificationMethods": [
            "Check UE logs for failed attach request and appropriate error responses."
        ]
    },
    {
        "testCaseId": "TC-010",
        "description": "Validate edge cases for detach procedure while in a call.",
        "preconditions": "The UE is engaged in an active call.",
        "steps": [
            "Attempt to power OFF the connected UE to detach.",
            "Wait for the detach process to complete."
        ],
        "expectedResult": "Detach should be prevented or handled gracefully.",
        "commandsUsed": [],
        "verificationMethods": [
            "Check UE logs for error messages or detach prevention notifications."
        ]
    },
    {
        "testCaseId": "TC-011",
        "description": "Performance testing for attach latency under varying load.",
        "preconditions": "Setup is configured to simulate varying network load.",
        "steps": [
            "Power ON the UE to attach under different load conditions.",
            "Record attach latency for each load condition."
        ],
        "expectedResult": "Attach latency is measured and compared against thresholds.",
        "commandsUsed": [],
        "verificationMethods": [
            "Analyze latency data to determine impact of load on attach performance."
        ]
    },
    {
        "testCaseId": "TC-012",
        "description": "Security testing for attach procedure with invalid credentials.",
        "preconditions": "Setup is configured to simulate invalid credentials.",
        "steps": [
            "Power ON the UE to attach to the LTE or 5G NSA cell with invalid credentials.",
            "Wait for the attach process to complete."
        ],
        "expectedResult": "Attach should fail with authentication error.",
        "commandsUsed": [],
        "verificationMethods": [
            "Check UE logs for authentication failure messages."
        ]
    },
    {
        "testCaseId": "TC-013",
        "description": "Integration testing for successful communication between eNodeB and MME during attach.",
        "preconditions": "The UE is powered ON and in excellent radio conditions.",
        "steps": [
            "Power ON the UE to attach to the LTE cell.",
            "Monitor signaling messages between eNodeB and MME."
        ],
        "expectedResult": "All signaling messages are exchanged successfully.",
        "commandsUsed": [],
        "verificationMethods": [
            "Validate the message flow logs between eNodeB and MME."
        ]
    },
    {
        "testCaseId": "TC-014",
        "description": "Usability testing for user experience during attach process.",
        "preconditions": "The UE is powered ON and in excellent radio conditions.",
        "steps": [
            "Power ON the UE to attach to the LTE or 5G NSA cell.",
            "Observe user notifications and messages during the attach process."
        ],
        "expectedResult": "User receives clear notifications about attach status.",
        "commandsUsed": [],
        "verificationMethods": [
            "Collect feedback from the user regarding the clarity of notifications."
        ]
    },
    {
        "testCaseId": "TC-015",
        "description": "Compatibility testing for attach procedure across different UE models.",
        "preconditions": "Different UE models are available for testing.",
        "steps": [
            "Power ON each UE model to attach to the LTE or 5G NSA cell.",
            "Record attach results for each model."
        ],
        "expectedResult": "All UE models should successfully attach to the network.",
        "commandsUsed": [],
        "verificationMethods": [
            "Compare attach success rates across different UE models."
        ]
    }
]
```
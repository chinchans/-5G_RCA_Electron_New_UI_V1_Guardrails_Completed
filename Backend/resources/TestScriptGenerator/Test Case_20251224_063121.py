```json
[
    {
        "testCaseId": "TC-1",
        "description": "Validate successful LTE Attach procedure for a single UE under excellent radio conditions.",
        "category": "POSITIVE TESTING",
        "preconditions": "The UE is powered off and placed in the center of the LTE cell.",
        "steps": [
            "Start the logs to capture the call flow and signaling messages.",
            "Power ON the UE to initiate the attach procedure to the LTE cell.",
            "Wait for the attach complete message from the UE.",
            "Verify that the UE is in the ECM-CONNECTED state."
        ],
        "expectedResults": [
            "The attach request is sent successfully.",
            "The UE receives an attach accept message.",
            "The attach success rate is recorded.",
            "The UE transitions to the ECM-CONNECTED state without errors."
        ],
        "commandsUsed": [
            "AT+CFUN=1",  // Command to power ON the UE
            "AT+COPS=0"   // Command to select the LTE network
        ],
        "verificationMethods": [
            "Check logs for attach request and response messages.",
            "Use network monitoring tools to confirm UE state."
        ]
    }
]
```
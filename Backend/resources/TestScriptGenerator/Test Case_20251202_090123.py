```json
[
    {
        "testCaseID": "TC001",
        "description": "Validate successful E-UTRAN Initial Attach procedure for LTE.",
        "category": "POSITIVE TESTING",
        "steps": [
            "Power ON the UE.",
            "Send an Attach Request to the eNodeB including IMSI or old GUTI.",
            "Wait for Attach Accept from the network.",
            "Verify the Attach Complete message is received.",
            "Request IP address allocation and verify successful allocation.",
            "Check if the default EPS bearer is established."
        ],
        "commandsUsed": [
            "UE Power ON command",
            "Attach Request command with IMSI/GUTI",
            "Attach Accept confirmation",
            "Attach Complete command",
            "IP address allocation request",
            "EPS bearer establishment request"
        ],
        "verificationMethods": [
            "Check logs to confirm Attach Request and Attach Accept were exchanged successfully.",
            "Validate the UE is attached to the correct cell based on PCI and ARFCN.",
            "Confirm that the Attach Complete message is received.",
            "Verify that an IP address is allocated to the UE.",
            "Ensure that the default EPS bearer is established correctly."
        ]
    }
]
```
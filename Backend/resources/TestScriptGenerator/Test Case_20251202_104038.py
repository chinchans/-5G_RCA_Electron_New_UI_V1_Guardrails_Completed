```json
[
    {
        "testCaseID": "TC1",
        "description": "Validate successful LTE Attach procedure for a single UE.",
        "preconditions": "UE is powered ON and in excellent radio conditions.",
        "steps": [
            "Power ON the UE to attach to the LTE cell.",
            "Initiate the E-UTRAN Initial Attach procedure.",
            "Wait for the Attach Complete message from the network.",
            "Request IP address allocation from the network during the attach.",
            "Verify that the UE's Mobile Equipment Identity (IMEISV) is sent to the network."
        ],
        "expectedResult": "Attach is successful with proper UE context established, and IP address allocated.",
        "commandsUsed": [
            "AT+CGATT=1",  // Command to attach to the LTE network
            "AT+CGDCONT=1,\"IP\",\"<APN>\""  // Command to set APN for IP address allocation
        ],
        "verificationMethods": [
            "Check that the UE is attached to the correct cell.",
            "Validate attach request and attach complete messages.",
            "Verify that the IP address is allocated successfully.",
            "Ensure that the IMEISV is correctly communicated to the MME."
        ]
    }
]
```
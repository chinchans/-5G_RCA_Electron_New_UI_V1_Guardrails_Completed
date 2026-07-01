```json
[
  {
    "testCaseID": "POS_TC_001",
    "title": "Validate successful LTE Attach and Detach with a single UE under excellent radio conditions",
    "category": "POSITIVE TESTING",
    "preconditions": [
      "Test setup is a single isolated cell with only one active UE.",
      "UE is placed in the cell center with excellent LTE RSRP as per Clause 4.6.",
      "Test configuration parameters are recorded."
    ],
    "testSteps": [
      "Access the 5G CLI interface using `SSH admin@<IP>` and authenticate.",
      "Configure the test environment to LTE attach-detach scenario with recorded parameters.",
      "Ensure the UE is powered off initially.",
      "Start logging to capture call flow and signaling messages.",
      "Power ON the UE and wait for successful LTE attach (validate attach request and attach complete).",
      "Power OFF the UE and wait for successful LTE detach (validate detach request and detach accept).",
      "Stop and save the test logs.",
      "Verify UE is attached to the correct cell by checking PCI, Global eNB ID, and ARFCN in UE logs."
    ],
    "expectedResults": [
      "Attach is successful with attach complete message received.",
      "Detach is successful with detach accept message received.",
      "Attach success rate is 100% for this iteration.",
      "Detach success rate is 100% for this iteration.",
      "Attach latency is recorded and median value can be calculated.",
      "Test logs contain complete signaling message flow."
    ],
    "postconditions": [
      "UE is detached from the network and powered off."
    ],
    "commandsUsed": [
      "SSH admin@<IP>"
    ],
    "verificationMethods": [
      "Log analysis of attach and detach signaling messages.",
      "UE log verification for correct cell parameters."
    ]
  },
  {
    "testCaseID": "POS_TC_002",
    "title": "Validate successful 5G NSA Attach and Detach with Secondary Node Addition and Release under excellent radio conditions",
    "category": "POSITIVE TESTING",
    "preconditions": [
      "Test setup is a single isolated cell with only one active UE.",
      "UE is placed in the cell center with excellent 5G SS-RSRP as per Clause 4.6.",
      "Test configuration parameters for LTE and 5G cells are recorded."
    ],
    "testSteps": [
      "Access the 5G CLI interface using `SSH admin@<IP>` and authenticate.",
      "Configure the test environment for 5G NSA attach-detach scenario with recorded parameters.",
      "Ensure the UE is powered off initially.",
      "Start logging to capture call flow and signaling messages.",
      "Power ON the UE and wait for successful 5G NSA attach and Secondary Node Addition (validate attach request, attach complete, SgNB addition request, and SgNB reconfiguration complete).",
      "Power OFF the UE and wait for successful detach including Secondary Node Release (validate detach request, detach accept, and Secondary Node release messages).",
      "Stop and save the test logs.",
      "Verify UE is attached to correct LTE and 5G cells by checking PCI, Global eNB ID/Global gNB ID, ARFCN/NR-ARFCN in UE logs."
    ],
    "expectedResults": [
      "Attach and Secondary Node Addition are successful with all expected messages received.",
      "Detach and Secondary Node Release are successful with all expected messages received.",
      "Attach success rate and Secondary Node Addition success rate are 100% for this iteration.",
      "Detach success rate is 100% for this iteration.",
      "Test logs contain complete signaling message flow."
    ],
    "postconditions": [
      "UE is detached from the network and powered off."
    ],
    "commandsUsed": [
      "SSH admin@<IP>"
    ],
    "verificationMethods": [
      "Log analysis of attach, Secondary Node Addition, detach, and Secondary Node Release signaling messages.",
      "UE log verification for correct LTE and 5G cell parameters."
    ]
  },
  {
    "testCaseID": "NEG_TC_001",
    "title": "Test Attach procedure failure due to poor radio conditions (RSRP below minimum coupling loss)",
    "category": "NEGATIVE TESTING",
    "preconditions": [
      "Test setup is a single isolated cell with one active UE.",
      "Radio conditions are degraded to below minimum coupling loss threshold as per Clause 4.6."
    ],
    "testSteps": [
      "Access the 5G CLI interface using `SSH admin@<IP>` and authenticate.",
      "Configure the test environment for LTE attach scenario.",
      "Ensure the UE is powered off initially.",
      "Start logging to capture call flow and signaling messages.",
      "Power ON the UE and wait for attach attempt.",
      "Observe attach failure due to poor radio link quality.",
      "Stop and save the test logs."
    ],
    "expectedResults": [
      "Attach procedure fails due to radio conditions below acceptable threshold.",
      "Attach failure messages are logged.",
      "Attach success rate is 0% for this iteration.",
      "No successful attach complete message is received."
    ],
    "postconditions": [
      "UE remains detached from the network."
    ],
    "commandsUsed": [
      "SSH admin@<IP>"
    ],
    "verificationMethods": [
      "Log analysis showing attach failure messages.",
      "UE logs indicating attach failure due to radio conditions."
    ]
  },
  {
    "testCaseID": "NEG_TC_002",
    "title": "Test Detach failure due to signaling message loss",
    "category": "NEGATIVE TESTING",
    "preconditions": [
      "Successful attach completed.",
      "Simulate signaling message loss or corruption during detach procedure."
    ],
    "testSteps": [
      "Access the 5G CLI interface using `SSH admin@<IP>` and authenticate.",
      "Start logging to capture call flow and signaling messages.",
      "Power OFF the UE to initiate detach procedure.",
      "Simulate loss or corruption of detach accept message.",
      "Observe if detach procedure is incomplete or fails to complete.",
      "Stop and save the test logs."
    ],
    "expectedResults": [
      "Detach procedure fails to complete or timeouts occur.",
      "Detach success rate is reduced due to signaling failure.",
      "Network resources remain allocated to UE context."
    ],
    "postconditions": [
      "UE context release not confirmed.",
      "Resources may need manual cleanup."
    ],
    "commandsUsed": [
      "SSH admin@<IP>"
    ],
    "verificationMethods": [
      "Log analysis showing missing or corrupted detach accept messages.",
      "Network resource monitoring for UE context release status."
    ]
  },
  {
    "testCaseID": "EDGE_TC_001",
    "title": "Validate attach and detach procedure at cell edge with poor but acceptable radio conditions",
    "category": "EDGE CASES",
    "preconditions": [
      "UE positioned at cell edge with RSRP near minimum acceptable level but not below minimum coupling loss."
    ],
    "testSteps": [
      "Access the 5G CLI interface using `SSH admin@<IP>` and authenticate.",
      "Configure the test environment accordingly.",
      "Start logging to capture call flow and signaling messages.",
      "Power ON the UE and wait for successful attach.",
      "Power OFF the UE and wait for successful detach.",
      "Stop and save the test logs."
    ],
    "expectedResults": [
      "Attach and detach procedures complete successfully despite challenging radio conditions.",
      "Attach success rate >= 75%.",
      "Detach success rate >= 75%.",
      "Attach latency measurements recorded."
    ],
    "postconditions": [
      "UE is detached and powered off."
    ],
    "commandsUsed": [
      "SSH admin@<IP>"
    ],
    "verificationMethods": [
      "Log analysis confirming successful attach and detach.",
      "Measurement of attach latency and success rates."
    ]
  },
  {
    "testCaseID": "EDGE_TC_002",
    "title": "Validate attach latency median calculation and omission of min/max latency",
    "category": "EDGE CASES",
    "preconditions": [
      "Multiple attach iterations performed with latency recorded for each."
    ],
    "testSteps": [
      "Access the 5G CLI interface using `SSH admin@<IP>` and authenticate.",
      "Execute at least 5 attach cycles while recording attach latency each time.",
      "Sort latency values in ascending order.",
      "Calculate and record only the median latency value in KPI table.",
      "Verify omission of minimum and maximum latency values from the report."
    ],
    "expectedResults": [
      "Median latency is correctly calculated and reported.",
      "Minimum and maximum latency values are not included in the KPI table as per specification."
    ],
    "postconditions": [
      "Latency KPI report generated with median value only."
    ],
    "commandsUsed": [
      "SSH admin@<IP>"
    ],
    "verificationMethods": [
      "Analysis of latency values collected and KPI report content verification."
    ]
  },
  {
    "testCaseID": "PERF_TC_001",
    "title": "Measure attach and detach success rates and latency over 45 iterations under excellent radio conditions",
    "category": "PERFORMANCE TESTING",
    "preconditions": [
      "Test setup with single cell and single UE under excellent radio conditions."
    ],
    "testSteps": [
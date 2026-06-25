**5G SA Registration Overview**

5G Standalone (SA) registration is a critical process that allows a User Equipment (UE) to connect to and utilize the 5G network. The registration procedure enables the UE to establish its identity, connect to the network, and initiate services. Below, I outline the key steps involved in the 5G SA registration process based on the dataset provided.

### Purpose and Applicability
The registration process aims to:
- Verify the full registration of a single UE.
- Establish a Packet Data Unit (PDU) session.
- Ensure compliance with the 3GPP standards outlined in TS 23.502, specifically Clause 4.2.2.2.2 for initial registration.

### Test Setup and Configuration
The registration process is performed in a controlled test setup where:
- A single cell scenario is utilized, ensuring no inter-cell interference.
- The UE is stationary and placed under excellent radio conditions (as defined by SS-RSRP).
- The network slicing capability must be supported by the UE, RAN, and 5G Core for at least one Single Network Slice Selection Assistance Information (S-NSSAI).

### Test Procedure Steps
1. **Configuration**: The test setup is configured, and the serving cell is activated and unloaded. All other cells are powered off.

2. **Power On the UE**: The UE is powered on, and it sends a **Registration Request** message to the network.

3. **Successful Registration**: The UE successfully registers to the 5G SA network.

4. **PDU Session Establishment**: 
   - A full-buffer UDP bi-directional data transmission is initiated between the application server and the UE. 
   - The registration procedure messages are captured, and the latency of the registration procedure is measured.

5. **Duration of Test**: The duration of the test should last at least 3 minutes, with throughput stability confirmed during this time.

6. **Capture and Record Metrics**: The PDU session establishment procedure messages are also captured and verified.

7. **Deregistration**: 
   - The UE is powered off, and it sends a **Deregistration Request** message.
   - The UE successfully de-registers from the 5G SA network.

8. **Capture De-registration Metrics**: 
   - The de-registration procedure messages are captured, and the latency of the de-registration procedure is measured and recorded.

9. **Repeat Registration/Deregistration**: Steps 2 through 8 are repeated for a total of 10 iterations to gather performance data.

### Expected Results and Key Performance Indicators (KPIs)
- Radio parameters such as **Reference Signal Received Power (RSRP)**, **Reference Signal Received Quality (RSRQ)**, and **Channel Quality Indicator (CQI)** must be recorded.
- Latency KPIs should be captured, including:
  - **Registration Time Latency**: Time from Registration Request to Registration Complete.
  - **De-registration Time Latency**: Time from Deregistration Request to Signaling Connection Release.
  
10. The observed latency values for each iteration are sorted, and the Minimum, Average, and Maximum latency values are recorded in a KPI record table (Table 5-6).

### Conclusion
5G SA registration is a complex process that consists of multiple steps aimed at ensuring the successful connection of a UE to the 5G network. By following the outlined procedures and capturing the necessary metrics, the testing ensures that the network meets the required standards and performance levels as defined by 3GPP specifications.
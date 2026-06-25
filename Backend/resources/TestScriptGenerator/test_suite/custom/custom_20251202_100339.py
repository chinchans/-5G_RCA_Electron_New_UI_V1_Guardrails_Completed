The Non-Standalone (NSA) Attach process is used to establish a connection for a User Equipment (UE) in a network that utilizes both LTE and NR (New Radio) technologies. The process leverages existing LTE infrastructure while enabling the use of 5G capabilities. The following details outline the key steps and components involved in the NSA Attach process, based on the dataset provided.

### Overview of NSA Attach Process
The NSA Attach process involves a combination of LTE and NR components, specifically focusing on the E-UTRAN Initial Attach and EN-DC (E-UTRA NR Dual Connectivity) procedures. 

### Steps in the NSA Attach Process

1. **Initial Attach Request**:
   - The UE initiates the attach process by sending an **Attach Request** to the eNodeB (Evolved Node B). This request includes identifiers such as **IMSI** (International Mobile Subscriber Identity) or **GUTI** (Globally Unique Temporary Identifier), as well as information about the UE’s capabilities and desired bearer configurations.
   - The Attach Request is elaborated in **3GPP TS 23.401**, specifically in Section 5.3.2.1, where it specifies that the request may indicate the type of attach (e.g., EPS attach, combined EPS/IMSI attach, Emergency Attach, or RLOS Attach).

2. **eNodeB to MME Communication**:
   - After receiving the Attach Request, the eNodeB forwards this request to the **MME** (Mobility Management Entity) via an S1-MME control message. The eNodeB also includes the **Selected Network**, **TAI (Tracking Area Identity)**, and other relevant parameters.
   - The MME derives the appropriate context and checks if the UE is allowed to attach to the network. It may also verify the UE's identity by cross-referencing with subscriber information stored in the **HSS** (Home Subscriber Server).

3. **Context Setup**:
   - If the attach request is valid, the MME sends an **Update Location Request** to the HSS to update the UE's location and retrieve subscription data, including PDN (Packet Data Network) context.
   - The MME then constructs a context for the UE, including the necessary bearer information, and prepares for the connection to the PDN.

4. **Bearer Resource Command**:
   - The MME sends a **Create Session Request** to the Serving Gateway (SGW), including details about the EPS bearer, PDN type, and QoS (Quality of Service) parameters.
   - The SGW responds with a **Create Session Response**, which includes the allocated bearer identities and addresses for user and control plane data.

5. **Secondary Node Addition**:
   - Once the LTE connection is established, if the UE is to utilize NR capabilities, the **Secondary Node Addition** procedure is triggered (as referenced in 3GPP TS 37.340, Clause 10.2.1).
   - The **MN (Master Node)** requests the **SN (Secondary Node)** to allocate resources for specific E-RABs (Evolved Radio Access Bearers). This involves providing the SN with the UE capabilities and measurement results to optimize the SCG (Secondary Cell Group) configuration.

6. **RRC Connection Reconfiguration**:
   - After the SN confirms resource allocation, the MN sends an **RRC Connection Reconfiguration** message to the UE, which includes the NR RRC configuration.
   - The UE applies the configuration and responds with an **RRC Connection Reconfiguration Complete** message.

7. **Data Forwarding**:
   - Once the configuration is successful, data can begin to flow from the SN to the UE, with the SN reporting data usage to the MN.

### Key Metrics and Success Criteria:
- The success of the attach process can be measured by the attach success rate, latency, and the ability to establish dedicated bearers for data transfer. The expected success rate for both the attach and detach processes in a test scenario is 100%, indicating that the process should complete successfully across multiple iterations (as referenced in the test procedure).

### Conclusion
The NSA Attach process integrates LTE and NR technologies to provide enhanced connectivity for the UE. By leveraging existing LTE infrastructure while incorporating new NR capabilities, the process ensures efficient resource utilization and improved service delivery. Specific references to the 3GPP standards help delineate the detailed steps and requirements necessary for a successful attach operation.
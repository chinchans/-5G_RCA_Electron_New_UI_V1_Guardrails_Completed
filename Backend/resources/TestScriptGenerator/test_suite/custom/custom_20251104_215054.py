The Non-Standalone (NSA) Attach process involves establishing a connection for a User Equipment (UE) to a 5G network while still relying on the existing LTE infrastructure. This process is crucial for enabling 5G services while maintaining compatibility with LTE. Below is an explanation of the NSA Attach process based on the dataset content:

### Overview of NSA Attach Process
The NSA Attach process comprises two main stages: the initial attach to the LTE network and the addition of the 5G secondary node (gNB) to enable 5G services. The relevant specifications for this process are detailed in 3GPP TS 23.401 and TS 37.340.

### Steps of the NSA Attach Process

1. **Initial Attach to LTE (E-UTRAN)**
   - **Initiation**: The UE initiates the attach process by sending an Attach Request to the LTE eNodeB. This is governed by the specifications in Clause 5.3.2.1 of 3GPP TS 23.401.
   - **Attach Request**: The Attach Request includes the UE's identity and capabilities. The eNodeB forwards this request to the MME (Mobility Management Entity).
   - **Authentication and Security**: The MME performs authentication and security procedures, including potential NAS (Non-Access Stratum) message exchanges.
   - **Attach Accept**: Upon successful authentication, the MME sends an Attach Accept message back to the UE, confirming the attach to the LTE network.

2. **Secondary Node Addition (5G NR)**
   - **SgNB Addition Request**: Once the initial attach to LTE is completed, the next step is to establish 5G connectivity. The MME triggers the Secondary Node Addition procedure by sending a SgNB Addition Request to the gNB (5G Node B) as per Clause 10.2.1 of 3GPP TS 37.340.
   - **Resource Allocation**: The gNB checks if it can allocate resources for the specified E-RAB (Evolved Radio Access Bearer) and responds with an SgNB Addition Request Acknowledge message, which includes the NR RRC configuration.
   - **RRC Connection Reconfiguration**: The MN (Master Node, typically the LTE eNodeB) sends an RRCConnectionReconfiguration message to the UE, which includes the new 5G NR configuration. The UE applies this configuration and responds with an RRCConnectionReconfigurationComplete message.
   - **Data Forwarding**: If applicable, data forwarding is initiated from the gNB to the MN to ensure a seamless data experience for the user.

3. **Completion of the Attach Process**
   - After the successful completion of the above steps, the UE is now attached to both the LTE network and the 5G NR, allowing it to benefit from enhanced speeds and services provided by the 5G infrastructure.

### Key Points
- The NSA Attach process relies on the LTE infrastructure to initiate the connection before adding 5G capabilities, allowing for a smooth transition and improved service delivery.
- Throughout the process, various messages are exchanged between the UE, eNodeB, MME, and gNB, ensuring security and resource allocation are managed effectively.
- The success of this process is critical for operators looking to upgrade their networks to 5G while still supporting existing LTE users.

### Reference to the Dataset
- The attach process is outlined in **Clause 5.3.2.1** for LTE and **Clause 10.2.1** for the EN-DC (E-UTRA NR Dual Connectivity) in 3GPP TS 37.340, indicating the structured steps required for a successful attach.
- The dataset highlights that the test procedure for validating this process requires capturing logs and measuring performance metrics like the attach success rate, which should be 100% over multiple iterations. 

This detailed explanation of the NSA Attach process integrates relevant steps and specifications as outlined in the provided dataset.
The 5G Non-Standalone (NSA) Attach Process involves the establishment of a connection for a User Equipment (UE) to access a 5G network while still relying on LTE for certain operations. This process is defined in several clauses of the dataset, particularly referring to both the LTE and 5G functionalities. Below is a detailed explanation based on the provided dataset:

### Steps Involved in the 5G NSA Attach Process

1. **Initiating the Attach Procedure**: 
   - The attach process is initiated when the UE powers on and tries to attach to the LTE cell. The request sent by the UE is a **NAS Attach Request** which carries parameters such as the UE's identity and capability information.

2. **LTE Initial Attach**: 
   - According to **3GPP TS 23.401 [29], Clause 5.3.2.1**, the LTE attach process involves establishing the initial connection over the E-UTRAN (Evolved Universal Terrestrial Radio Access Network). The MME (Mobility Management Entity) processes the Attach Request and sends back an Attach Accept message confirming the attachment.
   - The UE will then respond with an **Attach Complete** message.

3. **5G NSA Secondary Node Addition**:
   - Following the successful LTE attach, the next step is to add the Secondary Node (SN) for 5G connectivity. This is described in **3GPP TS 37.340 [30], Clause 10.2.1**:
     - The **MN (Master Node)** (which can be an eNB) sends a request to the SN (gNB) to allocate resources for a specific E-RAB (Evolved Radio Access Bearer).
     - This request includes E-RAB characteristics, TNL (Transport Network Layer) address information, and the capabilities of the UE.
     - If the SN can accommodate the request, it allocates the necessary radio resources and may trigger a Random Access procedure to synchronize the SN radio resource configuration.

4. **Resource Configuration**:
   - The SN responds with an **SgNB Addition Request Acknowledge** message that includes the new SCG (Supplementary Cell Group) configuration and TNL address information for the E-RABs.
   - The MN then sends an **RRC Connection Reconfiguration** message to the UE to apply the new configuration, which may include information about the PSCell (Primary Serving Cell) and SCG.

5. **Confirmation of Configuration**:
   - The UE applies the configuration and responds with an **RRC Connection Reconfiguration Complete** message, which is sent back to the MN. The MN then informs the SN that the reconfiguration was successful through **SgNB Reconfiguration Complete**.

6. **Final Steps**:
   - Once the SN is successfully added, the MN can start forwarding data to and from the UE using both the LTE and 5G resources. The E-RAB can now utilize both the Master Node and Secondary Node to provide enhanced bandwidth and service.

### Key Performance Indicators
During the attach process, various KPIs (Key Performance Indicators) are measured, including:
- Attach success rate
- Latency of the attach process (time taken from the attach request to the attach complete).

For instance, the dataset states that the attach procedure should pass 10 consecutive times to mark the test case as passing, and the expected success rate for Attach/Detach is 100% (as mentioned in the **LTE/5G NSA attach and detach test case validation** section).

### Conclusion
The 5G NSA Attach Process is a complex interaction between the UE, the MN, and the SN, which together allow a seamless transition to enhanced 5G services while still utilizing LTE infrastructure. This process ensures that the UE can leverage the benefits of both networks effectively. The steps outlined in the dataset provide a comprehensive overview of how this is achieved.
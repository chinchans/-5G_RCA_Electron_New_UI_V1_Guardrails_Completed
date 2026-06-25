The 5G NSA (Non-Standalone) attach process involves the establishment of a user equipment (UE) context in both the LTE network (E-UTRAN) and the 5G network (NR) to provide end-to-end connectivity. This process is defined in the 3GPP specifications, particularly in clauses related to E-UTRAN Initial Attach and secondary node addition for 5G.

### Key Steps in the 5G NSA Attach Process

1. **Initiation of Attach Request**:
   - The UE, when powered on, starts the attach process by sending an **Attach Request** message to the LTE eNodeB. This message may include the old Global Unique Temporary Identifier (GUTI) or the International Mobile Subscriber Identity (IMSI), among other parameters (e.g., UE capabilities, PDN type).
   - The details of this attach request and the associated parameters are outlined in **Clause 5.3.2.1** of the dataset. The request may specify if it is a combined EPS/IMSI attach or an emergency attach.

2. **Forwarding to MME**:
   - The eNodeB forwards the **Attach Request** to the MME (Mobility Management Entity). This step includes the **Selected Network** and **CSG access mode** information (if applicable). The eNodeB utilizes the RRC parameters to derive the MME address (as noted in **Clause 5.3.2.1**, Step 2).

3. **MME Processing**:
   - Upon receiving the attach request, the MME checks if it supports the requested attach type (EPS attach, combined EPS/IMSI attach, etc.). If the network supports it, the MME may proceed with further steps including identity checks and security setup.
   - The MME may also send an **Update Location Request** to the HSS (Home Subscriber Server) to retrieve subscription data (as mentioned in **Clause 5.3.2.1**, Step 8).

4. **Create Session Request**:
   - Following successful validation, the MME sends a **Create Session Request** to the Serving Gateway (SGW). This request includes various parameters like the PDN address, bearer QoS, and the necessary security algorithms (as detailed in **Clause 5.3.2.1**, Step 12).
   - The SGW then allocates the necessary resources and sends a **Create Session Response** back to the MME, which includes the allocated bearer identity and the PDN address (as stated in **Clause 5.3.2.1**, Step 15).

5. **Secondary Node Addition**:
   - If the UE is accessing a 5G NR cell, the MME initiates the **Secondary Node Addition** procedure as defined in **Clause 10.2.1** of the dataset. Here, the MME sends a **SgNB Addition Request** to the selected secondary node (SN), indicating the E-RAB characteristics and other configuration information.
   - The SN allocates resources and sends an **SgNB Addition Request Acknowledge** back to the MN (Master Node), which then communicates the configuration to the UE via an RRC Connection Reconfiguration message.

6. **Completion of Attach Procedure**:
   - After the UE applies the new configuration, it sends an **RRC Connection Reconfiguration Complete** message back to the MN. The MN then confirms the successful attachment by sending an **Attach Accept** message to the UE.
   - The MME can now send a **Modify Bearer Request** to the SGW to finalize the bearer contexts.

7. **Uplink Data Forwarding**:
   - Once the attach process is complete, the UE can start sending and receiving data. The eNodeB forwards the uplink data to the SGW, which then routes it to the appropriate PDN Gateway (as noted in **Clause 5.3.4**).

### Additional Considerations
- Throughout the process, the UE capabilities are communicated, and specific parameters related to enhanced coverage, voice over PS sessions, and paging restrictions can also be included in the messages exchanged.
- The attach process is designed to ensure seamless connectivity while allowing for the scalability and flexibility needed in 5G networks, especially when integrating with the existing LTE infrastructure.

### Summary
The 5G NSA attach process involves multiple steps where the UE initiates the attach request, the eNodeB forwards it to the MME, and the MME manages the session establishment process with the SGW and SN. Each step is crucial for ensuring that the UE can successfully connect and utilize resources from both the LTE and 5G networks.
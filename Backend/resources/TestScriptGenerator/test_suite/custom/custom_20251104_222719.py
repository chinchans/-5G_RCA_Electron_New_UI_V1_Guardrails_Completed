The 5G Non-Standalone (NSA) Attach process involves several key steps that enable a User Equipment (UE) to connect to a 5G network while relying on existing LTE infrastructure. Below is a detailed explanation of the 5G NSA attach process based on the dataset content provided.

### Overview of 5G NSA Attach Process

The 5G NSA attach process is described in two primary references from the dataset:
1. **LTE Attach** as per 3GPP TS 23.401, Clause 5.3.2.1 E-UTRAN Initial Attach.
2. **5G NSA Attach** as per 3GPP TS 23.401, Clause 5.3.2.1 for the E-UTRAN Initial Attach and 3GPP TS 37.340 Clause 10.2.1 for the EN-DC (Secondary Node Addition).

### Key Steps in the 5G NSA Attach Process

1. **Power ON the UE:**
   - The process begins with the UE powering on and initiating the attach request to the LTE cell. This is referred to as the **E-UTRAN Initial Attach**.

2. **Attach Request:**
   - The UE sends an Attach Request message to the eNodeB, which includes the necessary information for establishing the connection. This may include UE identity, requested service type, etc.

3. **Network Response:**
   - Upon receiving the Attach Request, the eNodeB forwards this request to the Mobility Management Entity (MME). The MME processes the request and checks if the UE's credentials are valid.

4. **Authentication and Security:**
   - The MME performs authentication and security procedures. This step is critical in ensuring that the UE is authorized to access network services.

5. **Bearer Setup:**
   - Once authenticated, the MME sets up the default bearer for the UE. This involves establishing a path for data transfer between the UE and the network.

6. **SgNB Addition (Secondary Node Addition):**
   - After the initial LTE attach, the process extends to 5G by adding a Secondary Node (gNB). This is done using the **SgNB Addition** request as per **3GPP TS 37.340, Clause 10.2.1**.
   - The MME sends a request to the gNB to allocate resources for the specific E-RAB (Evolved Radio Access Bearer), indicating the UE capabilities and configuration needed.

7. **Resource Allocation:**
   - The gNB allocates the necessary resources and confirms the setup with the MME. If configured, the gNB can also set up a Secondary Cell Group (SCG) for better performance.

8. **RRC Connection Reconfiguration:**
   - The MN (Master Node) sends a **RRCConnectionReconfiguration** message to the UE, including details about the newly established resources and any secondary cells that have been added.

9. **UE Response:**
   - The UE applies the new configuration and responds back to the MN with an **RRCConnectionReconfigurationComplete** message. This indicates that the UE has successfully updated its context to include the new resources.

10. **Data Forwarding:**
    - With the connection established, user data can now be forwarded from the gNB to the UE through the LTE infrastructure, taking advantage of the 5G enhancements while still relying on LTE for initial connectivity.

### Summary

The 5G NSA attach process effectively combines LTE and 5G technologies to enable seamless connectivity for the UE. The critical steps include the initial attach request to the LTE network, subsequent resources allocation from the 5G gNB, and the successful configuration of the UE to utilize both LTE and 5G resources together.

The 5G NSA attach process is designed to ensure that users can benefit from enhanced speeds and lower latencies provided by 5G technology while still leveraging the existing LTE infrastructure. As per the testing procedures outlined in the dataset, the expected outcome is a success rate of 100% for attach and detach procedures, validating the reliability of the connection process.
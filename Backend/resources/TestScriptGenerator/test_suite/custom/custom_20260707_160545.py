Since no specific dataset is provided, I will generate a detailed test script for an LTE/5G NSA (Non-Standalone) attach and detach procedure for a single UE under excellent radio conditions, following standard 3GPP specifications (e.g., 3GPP TS 24.301 and TS 23.501). The test will run for 10 consecutive iterations.

---

### Test Script: LTE/5G NSA Attach and Detach Procedure for Single UE (10 Iterations)

**Objective:**  
Verify the correct attach and detach procedure of a single UE under excellent radio conditions in an LTE/5G NSA environment over 10 consecutive iterations.

---

#### Preconditions:
- UE is powered on and reset to factory default (no previous registration context).
- Network supports LTE/5G NSA mode with eNodeB and gNodeB configured.
- Radio conditions are excellent (e.g., RSRP > -80 dBm, SINR > 20 dB).
- UE has valid SIM credentials.
- Test equipment is configured to log all signaling messages and radio measurements.

---

#### Test Parameters:
| Parameter                      | Value                           |
|-------------------------------|--------------------------------|
| Number of iterations           | 10                             |
| Radio conditions              | Excellent (RSRP > -80 dBm)      |
| UE state at start             | Power off / Not registered      |
| Attach type                  | EPS attach (LTE anchor with 5G secondary) |
| Network type                  | LTE/5G NSA                     |

---

#### Test Steps Per Iteration:

1. **Power On UE**
   - UE transitions from powered off to powered on.
   - UE performs initial radio scan and selects LTE cell.

2. **LTE RRC Connection Establishment**
   - UE sends RRC Connection Request to eNodeB.
   - eNodeB responds with RRC Connection Setup.
   - UE sends RRC Connection Setup Complete.

3. **Attach Request**
   - UE sends NAS Attach Request message via LTE S1 interface, indicating EPS attach with 5G NSA capability.
     - Attach type: EPS attach
     - UE Network Capability includes 5G NSA support.
   - MME processes the attach request.

4. **Authentication and Security**
   - MME sends Authentication Request to UE.
   - UE responds with Authentication Response.
   - MME sends Security Mode Command.
   - UE responds with Security Mode Complete.

5. **ESM Procedure**
   - UE sends Activate Default EPS Bearer Context Request.
   - MME responds with Activate Default EPS Bearer Context Accept.

6. **Secondary 5G Cell Addition**
   - UE receives RRC Reconfiguration message to add 5G NR secondary cell.
   - UE performs measurement and confirms addition of 5G NR cell.
   - UE sends RRC Reconfiguration Complete.

7. **Attach Complete**
   - UE sends Attach Complete NAS message to MME.

8. **Verify UE is Registered**
   - Confirm UE is registered in the network.
   - Confirm default bearer is active.
   - Confirm secondary 5G NR cell is active.

9. **Detach Procedure**
   - UE initiates detach by sending NAS Detach Request with type "Switch-off" or "Normal detach".
   - MME responds with Detach Accept.
   - UE releases RRC connection.

10. **Verify UE is Deregistered**
    - Confirm UE is deregistered in the network.
    - Confirm bearers are released.
    - Confirm UE returns to idle state.

---

#### Validation Criteria:

- All signaling messages are exchanged as per 3GPP TS 24.301 and TS 23.501.
- Attach and detach procedures complete successfully without errors.
- 5G NR secondary cell is successfully added during attach.
- Bearers are properly established and released.
- No radio link failures or protocol errors occur.
- Test completes all 10 iterations with consistent success.

---

#### Logging:

- Log all RRC and NAS messages.
- Log radio measurements (RSRP, SINR).
- Log timestamps for each step.
- Log any errors or anomalies.

---

#### Example Pseudocode for Automation:

```python
for iteration in range(1, 11):
    power_on_ue()
    wait_for_rsrp_above(-80)
    establish_rrc_connection()
    send_attach_request(eps_attach=True, nsa_support=True)
    perform_authentication()
    activate_default_bearer()
    add_secondary_5g_cell()
    send_attach_complete()
    verify_registration()
    send_detach_request()
    verify_deregistration()
    power_off_ue()
    log_iteration_result(iteration)
```

---

If you require a script in a specific test automation language or tool (e.g., Python with s1ap library, or a proprietary test tool), please specify.
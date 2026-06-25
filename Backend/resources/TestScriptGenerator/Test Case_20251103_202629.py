```plaintext
### **1. Positive Testing**
# Test Case 1: Successful Initial Registration
# This test verifies that a User Equipment (UE) can successfully register to the 5G Standalone (SA) network under ideal conditions.

- **Preconditions**: 
  - UE is powered on.
  - Connected to an isolated cell.
  - Excellent radio conditions are ensured.

- **Test Steps**:
  1. Power on the UE.
  2. Send a REGISTRATION REQUEST message to the network.
  3. Verify that a successful registration response is received.

- **Expected Result**: 
  - UE successfully registers to the 5G SA network, transitioning to the RM-REGISTERED state.

- **Postconditions**: 
  - UE is confirmed to be in the RM-REGISTERED state.
```
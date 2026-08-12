```python
import pytest
import time

# Placeholder UE and Network Interface APIs (Mocks/Stubs)
# In real test environment, these would interface with actual test equipment / simulators.

class UE:
    def __init__(self, ue_id):
        self.ue_id = ue_id
        self.attached = False
        self.rrc_connected = False
        self.nas_state = "IDLE"  # Possible states: IDLE, ATTACHING, ATTACHED, DETACHING

    def rrc_connect(self):
        # Trigger RRC connection setup (RRC_CONNECTED state)
        # In NSA, RRC connects to LTE eNB (Master Node)
        self.rrc_connected = True
        # Simulate time delay for RRC setup under excellent radio conditions
        time.sleep(0.05)

    def nas_attach_request(self):
        assert self.rrc_connected, "RRC must be connected before NAS attach"
        self.nas_state = "ATTACHING"
        # Simulate sending NAS Attach Request and receiving Attach Accept
        time.sleep(0.1)
        self.nas_state = "ATTACHED"
        self.attached = True

    def check_kpi_post_attach(self):
        # Check KPIs relevant to attach procedure
        # Example KPIs: RRC state, NAS attach state, attach success rate = 1
        assert self.rrc_connected, "RRC should be connected after attach"
        assert self.nas_state == "ATTACHED", "NAS state should be ATTACHED"
        assert self.attached, "UE should be attached"

    def nas_detach_request(self):
        assert self.attached, "UE must be attached before detach"
        self.nas_state = "DETACHING"
        # Simulate sending NAS Detach Request and receiving Detach Accept
        time.sleep(0.05)
        self.nas_state = "IDLE"
        self.attached = False

    def rrc_release(self):
        assert not self.attached, "UE must be detached before RRC release"
        self.rrc_connected = False
        time.sleep(0.02)

    def check_kpi_post_detach(self):
        # Check KPIs relevant to detach procedure
        assert not self.attached, "UE should be detached"
        assert self.nas_state == "IDLE", "NAS state should be IDLE after detach"
        assert not self.rrc_connected, "RRC should be released after detach"


@pytest.fixture(scope="function")
def ue():
    # Instantiate a single UE
    return UE(ue_id="UE_001")

@pytest.mark.parametrize("iteration", range(10))
def test_lte_5g_nsa_attach_detach(ue, iteration):
    """
    Test LTE/5G NSA attach and detach procedure for a single UE
    under excellent radio conditions over 10 consecutive iterations.
    """

    # Step 1: RRC Connection Setup (LTE eNB Master Node)
    ue.rrc_connect()
    assert ue.rrc_connected, f"Iteration {iteration}: RRC connection failed"

    # Step 2: NAS Attach Procedure
    ue.nas_attach_request()
    ue.check_kpi_post_attach()

    # (Optional) Additional checks for NSA dual connectivity:
    # - Secondary Node (5G gNB) setup could be done here
    # - For simplicity, assume NSA secondary node setup implicit in attach success

    # Step 3: NAS Detach Procedure
    ue.nas_detach_request()

    # Step 4: RRC Release
    ue.rrc_release()

    ue.check_kpi_post_detach()

    # Small delay between iterations to simulate realistic UE behavior
    time.sleep(0.1)
```
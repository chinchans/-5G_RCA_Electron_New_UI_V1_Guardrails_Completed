```python
import pytest
import time

# Placeholder imports for UE and network interface libraries
# from lte_5g_simulator import UE, Network, RRC, NAS, KPI

class UE:
    """
    Simplified UE model for LTE/5G NSA attach/detach simulation.
    """

    def __init__(self, imsi: str):
        self.imsi = imsi
        self.attached = False
        self.rrc_connected = False
        self.nas_registered = False
        self.kpi = {
            'rrc_setup_time_ms': None,
            'nas_attach_time_ms': None,
            'detach_time_ms': None,
        }

    def rrc_setup(self):
        """
        Simulate RRC connection establishment.
        According to 3GPP TS 36.331 / 38.331.
        """
        start = time.time()
        # Simulate RRC connection request/response (ideal condition, minimal delay)
        # In reality, UE sends RRCSetupRequest, receives RRCSetup, sends RRCSetupComplete
        time.sleep(0.01)  # 10ms typical RRC setup duration under excellent conditions
        self.rrc_connected = True
        self.kpi['rrc_setup_time_ms'] = (time.time() - start) * 1000

    def nas_attach(self):
        """
        Simulate NAS attach procedure (EPS attach for LTE or 5G NSA).
        According to 3GPP TS 24.301.
        """
        assert self.rrc_connected, "RRC connection must be established before NAS attach"

        start = time.time()
        # Simulate NAS attach request, authentication, security setup, attach accept
        # Under excellent conditions, assume minimal delay
        time.sleep(0.02)  # 20ms typical NAS attach duration
        self.nas_registered = True
        self.attached = True
        self.kpi['nas_attach_time_ms'] = (time.time() - start) * 1000

    def check_kpi(self):
        """
        Check that KPI timings are within expected thresholds under excellent conditions.
        Thresholds are placeholders and should be adapted to realistic values.
        """
        assert self.kpi['rrc_setup_time_ms'] is not None and self.kpi['rrc_setup_time_ms'] < 50, \
            f"RRC setup too long: {self.kpi['rrc_setup_time_ms']:.2f} ms"
        assert self.kpi['nas_attach_time_ms'] is not None and self.kpi['nas_attach_time_ms'] < 100, \
            f"NAS attach too long: {self.kpi['nas_attach_time_ms']:.2f} ms"

    def detach(self):
        """
        Simulate UE-initiated detach procedure.
        According to 3GPP TS 24.301.
        """
        assert self.attached, "UE must be attached to detach"

        start = time.time()
        # Simulate NAS Detach Request, network detach accept, RRC release
        time.sleep(0.015)  # 15ms typical detach duration
        self.attached = False
        self.nas_registered = False
        self.rrc_connected = False
        self.kpi['detach_time_ms'] = (time.time() - start) * 1000

    def check_detach_kpi(self):
        """
        Check detach KPI timing.
        """
        assert self.kpi['detach_time_ms'] is not None and self.kpi['detach_time_ms'] < 50, \
            f"Detach too long: {self.kpi['detach_time_ms']:.2f} ms"


@pytest.mark.parametrize("iteration", range(10))
def test_lte_5g_nsa_attach_detach(iteration):
    """
    Test LTE/5G NSA attach and detach procedure for a single UE under excellent radio conditions,
    repeated for 10 consecutive iterations.

    Steps:
    1. UE performs RRC connection setup.
    2. UE performs NAS attach procedure.
    3. KPI checks on attach timing.
    4. UE performs detach procedure.
    5. KPI checks on detach timing.
    """
    ue = UE(imsi=f"00101000000000{iteration:02d}")  # IMSI placeholder

    # Step 1: RRC Setup
    ue.rrc_setup()
    assert ue.rrc_connected, "RRC connection failed"

    # Step 2: NAS Attach
    ue.nas_attach()
    assert ue.attached and ue.nas_registered, "NAS attach failed"

    # Step 3: KPI Checks on attach
    ue.check_kpi()

    # Step 4: Detach
    ue.detach()
    assert not ue.attached and not ue.nas_registered and not ue.rrc_connected, "Detach failed"

    # Step 5: KPI Checks on detach
    ue.check_detach_kpi()
```
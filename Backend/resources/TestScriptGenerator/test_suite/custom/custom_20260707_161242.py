```python
import time
import pytest

class UE:
    """
    Emulated UE class to simulate power on/off and attach/detach procedures.
    """

    def __init__(self, technology="LTE"):
        self.technology = technology  # "LTE" or "5G_NSA"
        self.attached = False
        self.secondary_node_added = False  # For 5G NSA only
        self.radio_conditions = None
        self.attach_start_time = None
        self.attach_complete_time = None

    def set_radio_conditions(self, rsrp, rsrq):
        """
        Set radio conditions for the UE to simulate excellent conditions.
        """
        self.radio_conditions = {"RSRP": rsrp, "RSRQ": rsrq}

    def power_on(self):
        """
        Simulate UE power on which triggers attach procedure.
        """
        # Start attach procedure timing
        self.attach_start_time = time.monotonic()

        # Simulate attach procedure steps based on technology
        # 3GPP TS 23.401 Clause 5.3.2.1 for LTE Attach
        # 3GPP TS 23.401 Clause 5.3.2.1 + TS 37.340 Clause 10.2.1 for 5G NSA

        # Simulate attach request/response (placeholder)
        time.sleep(0.2)  # Simulate signaling delay for attach request/response

        # For 5G NSA simulate secondary node addition signaling
        if self.technology == "5G_NSA":
            # Simulate SgNB addition request and reconfiguration complete
            time.sleep(0.1)
            self.secondary_node_added = True

        self.attached = True
        self.attach_complete_time = time.monotonic()

    def power_off(self):
        """
        Simulate UE power off which triggers detach procedure.
        """
        # Simulate detach procedure according to 3GPP TS 23.401 Clause 5.3.8.2.1
        # and for 5G NSA also TS 37.340 Clause 10.4.1 Secondary Node Release

        if not self.attached:
            # Detach cannot proceed if UE not attached
            return False

        # Simulate detach request/accept signaling
        time.sleep(0.15)

        if self.technology == "5G_NSA" and self.secondary_node_added:
            # Simulate secondary node release procedure signaling
            time.sleep(0.1)
            self.secondary_node_added = False

        self.attached = False
        return True

    def get_attach_latency(self):
        if self.attach_start_time and self.attach_complete_time:
            return self.attach_complete_time - self.attach_start_time
        return None

    def check_attach_success(self):
        """
        Validate attach success by checking UE state and placeholder for logs.
        """
        # Placeholder for checking UE logs or signaling messages to confirm attach success
        # For test, we assume success if self.attached is True and radio conditions are excellent
        if not self.attached:
            return False
        if self.radio_conditions is None:
            return False
        # Example threshold for excellent RSRP and RSRQ (placeholder values)
        if self.technology == "LTE":
            return self.radio_conditions["RSRP"] >= -85 and self.radio_conditions["RSRQ"] >= -10
        else:  # 5G NSA
            # SS-RSRP threshold placeholder
            return self.radio_conditions["RSRP"] >= -90 and self.radio_conditions["RSRQ"] >= -10

    def check_detach_success(self):
        """
        Validate detach success by checking UE state and placeholder for logs.
        """
        # Placeholder for checking UE logs or signaling messages to confirm detach success
        # For test, success if UE not attached and secondary node released for 5G NSA
        if self.attached:
            return False
        if self.technology == "5G_NSA" and self.secondary_node_added:
            return False
        return True

    def check_correct_cell_attachment(self, expected_cell_info):
        """
        Check if UE is attached to the expected cell (PCI, Global eNB/gNB ID, ARFCN/NR-ARFCN).
        expected_cell_info: dict with keys depending on technology
        """
        # Placeholder: In real test, parse UE logs or report from UE application
        # For simulation, assume always correct cell if attached
        return self.attached


@pytest.fixture(scope="module")
def ue_lte():
    ue = UE(technology="LTE")
    # Set excellent radio conditions for LTE (example RSRP and RSRQ)
    ue.set_radio_conditions(rsrp=-80, rsrq=-8)
    return ue

@pytest.fixture(scope="module")
def ue_5g_nsa():
    ue = UE(technology="5G_NSA")
    # Set excellent radio conditions for 5G NSA (SS-RSRP and RSRQ)
    ue.set_radio_conditions(rsrp=-85, rsrq=-8)
    return ue

def test_lte_attach_detach_10_iterations(ue_lte):
    iterations = 10
    attach_success_count = 0
    detach_success_count = 0
    attach_latencies = []

    expected_cell_info = {
        "PCI": 123,              # Placeholder PCI
        "Global_eNB_ID": "00-11-22",  # Placeholder Global eNB ID
        "ARFCN": 300              # Placeholder ARFCN
    }

    for i in range(iterations):
        # Power ON UE - attach
        ue_lte.power_on()

        # Check attach success
        assert ue_lte.check_attach_success(), f"Attach failed on iteration {i+1}"
        assert ue_lte.check_correct_cell_attachment(expected_cell_info), f"Incorrect cell attached on iteration {i+1}"
        attach_success_count += 1

        latency = ue_lte.get_attach_latency()
        assert latency is not None and latency > 0, f"Invalid attach latency on iteration {i+1}"
        attach_latencies.append(latency)

        # Power OFF UE - detach
        detach_ok = ue_lte.power_off()
        assert detach_ok, f"Detach procedure failed to initiate on iteration {i+1}"

        # Check detach success
        assert ue_lte.check_detach_success(), f"Detach failed on iteration {i+1}"
        detach_success_count += 1

    # KPI validations
    assert attach_success_count == iterations, f"Attach success rate below 100%, count {attach_success_count}/{iterations}"
    assert detach_success_count == iterations, f"Detach success rate below 100%, count {detach_success_count}/{iterations}"

    attach_latencies.sort()
    min_latency = attach_latencies[0]
    max_latency = attach_latencies[-1]
    avg_latency = sum(attach_latencies) / iterations

    # Placeholder assertions for latency thresholds - adjust as per real system expectations
    assert min_latency > 0, "Minimum attach latency invalid"
    assert max_latency < 5, "Maximum attach latency too high"
    assert avg_latency < 3, "Average attach latency too high"

    # Print KPI summary (would be logged in real test report)
    print(f"LTE Attach-Detach 10 Iterations KPI:")
    print(f"Attach Success Count: {attach_success_count}")
    print(f"Detach Success Count: {detach_success_count}")
    print(f"Attach Latency (s): min={min_latency:.3f}, avg={avg_latency:.3f}, max={max_latency:.3f}")

def test_5g_nsa_attach_detach_10_iterations(ue_5g_nsa):
    iterations = 10
    attach_success_count = 0
    secondary_node_add_success_count = 0
    detach_success_count = 0
    attach_latencies = []

    expected_cell_info = {
        "PCI": 456,               # Placeholder PCI
        "Global_eNB_ID": "AA-BB-CC",  # Placeholder Global eNB ID
        "Global_gNB_ID": "GG-HH-II",  # Placeholder Global gNB ID
        "ARFCN": 310,             # Placeholder LTE ARFCN
        "NR_ARFCN": 1000          # Placeholder NR ARFCN
    }

    for i in range(iterations):
        # Power ON UE - attach + Secondary Node Addition
        ue_5g_nsa.power_on()

        # Check attach success
        assert ue_5g_nsa.check_attach_success(), f"Attach failed on iteration {i+1}"

        # Check secondary node addition success
        assert ue_5g_nsa.secondary_node_added, f"Secondary node addition failed on iteration {i+1}"
        secondary_node_add_success_count +=1

        assert ue_5g_nsa.check_correct_cell_attachment(expected_cell_info), f"Incorrect cell attached on iteration {i+1}"
        attach_success_count += 1

        latency = ue_5g_nsa.get_attach_latency()
        assert latency is not None and latency > 0, f"Invalid attach latency on iteration {i+1}"
        attach_latencies.append(latency)

        # Power OFF UE - detach + Secondary Node Release
        detach_ok = ue_5g_nsa.power_off()
        assert detach_ok, f"Detach procedure failed to initiate on iteration {i+1}"

        # Check detach success
        assert ue_5g_nsa.check_detach_success(), f"Detach failed on iteration {i+1}"
        detach_success_count += 1

    # KPI validations
    assert attach_success_count == iterations, f"Attach success rate below 100%, count {attach_success_count}/{iterations}"
    assert secondary_node_add_success_count == iterations, f"Secondary Node Addition success rate below 100%, count {secondary_node_add_success_count}/{iterations}"
    assert detach_success_count == iterations, f"Detach success rate below 100%, count {detach_success_count}/{iterations}"

    attach_latencies.sort()
    min_latency = attach_latencies[0]
    max_latency = attach_latencies[-1]
    avg_latency = sum(attach_latencies) / iterations

    # Placeholder assertions for latency thresholds - adjust as per real system expectations
    assert min_latency > 0, "Minimum attach latency invalid"
    assert max_latency < 6, "Maximum attach latency too high"
    assert avg_latency < 4, "Average attach latency too high"

    # Print KPI summary (would be logged in real test report)
    print(f"5G NSA Attach-Detach 10 Iterations KPI:")
    print(f"Attach Success Count: {attach_success_count}")
    print(f"Secondary Node Addition Success Count: {secondary_node_add_success_count}")
    print(f"Detach Success Count: {detach_success_count}")
    print(f"Attach Latency (s): min={min_latency:.3f}, avg={avg_latency:.3f}, max={max_latency:.3f}")
```
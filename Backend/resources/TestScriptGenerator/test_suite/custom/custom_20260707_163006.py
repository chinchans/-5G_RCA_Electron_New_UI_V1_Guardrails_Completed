```python
import time
import pytest
from collections import namedtuple

# Placeholder classes/interfaces simulating UE, Network, and Logger behavior.

class UE:
    def __init__(self, technology):
        """
        technology: "LTE" or "5G_NSA"
        """
        self.tech = technology
        self.powered_on = False
        self.attached = False
        self.secondary_node_added = False  # For 5G NSA
        self.cell_info = None

    def power_on(self):
        # Simulate UE power on and attach procedure start
        self.powered_on = True
        # Attach procedure will be triggered by the network simulation in test
        return True

    def power_off(self):
        # Simulate UE power off and detach procedure start
        self.powered_on = False
        # Detach procedure will be triggered by the network simulation in test
        return True

    def is_attached(self):
        return self.attached

    def get_cell_info(self):
        # Return cell info such as PCI, Global eNB ID / gNB ID, ARFCN / NR-ARFCN
        return self.cell_info

    def set_cell_info(self, cell_info):
        self.cell_info = cell_info

class Network:
    def __init__(self, technology):
        """
        technology: "LTE" or "5G_NSA"
        """
        self.tech = technology
        self.cell_active = False
        self.ue_context = None

    def activate_serving_cell(self):
        self.cell_active = True
        # Cell info placeholders
        if self.tech == "LTE":
            self.cell_info = {
                "PCI": 123,
                "Global_eNB_ID": "eNB001",
                "ARFCN": 300
            }
        else:  # 5G NSA
            self.cell_info = {
                "PCI": 234,
                "Global_eNB_ID": "eNB001",
                "Global_gNB_ID": "gNB001",
                "ARFCN": 300,
                "NR_ARFCN": 1000
            }
        return True

    def deactivate_other_cells(self):
        # No other cells active in isolated test scenario
        return True

    def perform_attach(self, ue: UE):
        if not self.cell_active:
            raise RuntimeError("Serving cell not active")
        # Simulate attach attach request and response per 3GPP TS 23.401 and TS 37.340
        # For NSA, also simulate Secondary Node Addition procedure
        attach_request_time = time.time()
        # Simulated processing delay for attach
        time.sleep(0.05)  # 50 ms attach latency simulated

        # Mark UE as attached
        ue.attached = True
        ue.set_cell_info(self.cell_info)

        attach_complete_time = time.time()
        attach_latency = attach_complete_time - attach_request_time

        # For 5G NSA, simulate Secondary Node Addition success
        secondary_node_addition_success = True
        if self.tech == "5G_NSA":
            # Simulate Secondary Node Addition signalling messages per TS 37.340 Clause 10.2.1
            time.sleep(0.02)  # 20 ms delay for SN Addition
            ue.secondary_node_added = True
        else:
            ue.secondary_node_added = False

        return {
            "attach_success": True,
            "attach_latency": attach_latency,
            "secondary_node_addition_success": secondary_node_addition_success,
        }

    def perform_detach(self, ue: UE):
        if not ue.attached:
            # Already detached
            return {"detach_success": False}
        # Simulate detach request and detach accept messages per 3GPP TS 23.401 and TS 37.340
        detach_request_time = time.time()
        time.sleep(0.03)  # 30 ms detach processing time simulated

        # For 5G NSA, simulate Secondary Node Release procedure per TS 37.340 Clause 10.4.1
        if self.tech == "5G_NSA" and ue.secondary_node_added:
            # Simulate MN initiated SN Release (Figure 10.4.1-1)
            time.sleep(0.02)  # 20 ms delay for SN Release signalling
            ue.secondary_node_added = False

        ue.attached = False
        ue.set_cell_info(None)
        detach_accept_time = time.time()
        detach_latency = detach_accept_time - detach_request_time

        return {
            "detach_success": True,
            "detach_latency": detach_latency,
        }

    def get_radio_parameters(self, ue: UE):
        # Return RSRP, RSRQ under excellent radio conditions (placeholders)
        if self.tech == "LTE":
            return {
                "RSRP": -80,  # dBm, excellent LTE RSRP
                "RSRQ": -10,  # dB, excellent LTE RSRQ
            }
        else:
            return {
                "SS_RSRP": -75,  # dBm, excellent 5G SS-RSRP
                "SS_RSRQ": -9,   # dB, excellent 5G SS-RSRQ
            }

class Logger:
    def __init__(self):
        self.logs = []

    def start_capture(self):
        self.logs.append("Log capture started")

    def stop_capture(self):
        self.logs.append("Log capture stopped")

    def save_logs(self, filename):
        # Save logs to a file or mock saving
        self.logs.append(f"Logs saved to {filename}")

# KPI data structure for reporting and assertions
KPI = namedtuple('KPI', [
    'attach_success_rate',
    'detach_success_rate',
    'secondary_node_addition_success_rate',  # Only relevant for 5G NSA
    'attach_latency_min',
    'attach_latency_avg',
    'attach_latency_max',
])

ITERATIONS = 10

@pytest.mark.parametrize("technology", ["LTE", "5G_NSA"])
def test_lte_5g_nsa_attach_detach(technology):
    """
    Test LTE or 5G NSA attach and detach for a single UE under excellent radio conditions,
    repeated 10 consecutive times validating 100% success rates and measuring latency KPIs.
    """
    ue = UE(technology=technology)
    network = Network(technology=technology)
    logger = Logger()

    # Test Setup: configure and activate serving cell, deactivate other cells
    assert network.activate_serving_cell(), "Failed to activate serving cell"
    assert network.deactivate_other_cells(), "Failed to deactivate other cells"

    attach_success_count = 0
    detach_success_count = 0
    secondary_node_addition_success_count = 0
    attach_latencies = []

    radio_params = network.get_radio_parameters(ue)
    # Validate radio parameters are within excellent conditions (placeholder thresholds)
    if technology == "LTE":
        assert radio_params["RSRP"] >= -90, f"LTE RSRP too low: {radio_params['RSRP']} dBm"
        assert radio_params["RSRQ"] >= -15, f"LTE RSRQ too low: {radio_params['RSRQ']} dB"
    else:
        assert radio_params["SS_RSRP"] >= -85, f"5G SS-RSRP too low: {radio_params['SS_RSRP']} dBm"
        assert radio_params["SS_RSRQ"] >= -12, f"5G SS-RSRQ too low: {radio_params['SS_RSRQ']} dB"

    for iteration in range(1, ITERATIONS + 1):
        logger.start_capture()

        # Step 1: Power ON UE to start attach
        assert ue.power_on(), f"Iteration {iteration}: UE power on failed"

        # Step 2: Perform attach procedure and measure latency
        attach_result = network.perform_attach(ue)

        assert attach_result["attach_success"], f"Iteration {iteration}: Attach failed"
        attach_success_count += 1
        attach_latencies.append(attach_result["attach_latency"])

        # For 5G NSA: validate secondary node addition success
        if technology == "5G_NSA":
            assert attach_result["secondary_node_addition_success"], f"Iteration {iteration}: Secondary Node Addition failed"
            secondary_node_addition_success_count += 1

        # Validate UE attached to correct cell as per test config
        cell_info = ue.get_cell_info()
        assert cell_info is not None, f"Iteration {iteration}: UE cell info missing after attach"
        if technology == "LTE":
            # Check LTE cell parameters
            assert cell_info.get("PCI") == 123, f"Iteration {iteration}: Unexpected PCI for LTE cell"
            assert cell_info.get("Global_eNB_ID") == "eNB001", f"Iteration {iteration}: Unexpected Global eNB ID"
            assert cell_info.get("ARFCN") == 300, f"Iteration {iteration}: Unexpected ARFCN"
        else:
            # Check 5G NSA cell parameters (LTE + NR)
            assert cell_info.get("PCI") == 234, f"Iteration {iteration}: Unexpected PCI for 5G NSA cell"
            assert cell_info.get("Global_eNB_ID") == "eNB001", f"Iteration {iteration}: Unexpected Global eNB ID"
            assert cell_info.get("Global_gNB_ID") == "gNB001", f"Iteration {iteration}: Unexpected Global gNB ID"
            assert cell_info.get("ARFCN") == 300, f"Iteration {iteration}: Unexpected LTE ARFCN"
            assert cell_info.get("NR_ARFCN") == 1000, f"Iteration {iteration}: Unexpected NR ARFCN"

        # Step 3: Power OFF UE to start detach
        assert ue.power_off(), f"Iteration {iteration}: UE power off failed"

        # Step 4: Perform detach procedure
        detach_result = network.perform_detach(ue)

        assert detach_result["detach_success"], f"Iteration {iteration}: Detach failed"
        detach_success_count += 1

        logger.stop_capture()
        logger.save_logs(filename=f"test_log_iteration_{iteration}.log")

    # Calculate KPIs
    attach_success_rate = attach_success_count / ITERATIONS
    detach_success_rate = detach_success_count / ITERATIONS
    if technology == "5G_NSA":
        secondary_node_addition_success_rate = secondary_node_addition_success_count / ITERATIONS
    else:
        secondary_node_addition_success_rate = None

    attach_latency_min = min(attach_latencies)
    attach_latency_max = max(attach_latencies)
    attach_latency_avg = sum(attach_latencies) / ITERATIONS

    # Assertions on KPIs per spec: expected success rate 100%
    assert attach_success_rate == 1.0, "Attach success rate less than 100%"
    assert detach_success_rate == 1.0, "Detach success rate less than 100%"
    if secondary_node_addition_success_rate is not None:
        assert secondary_node_addition_success_rate == 1.0, "Secondary Node Addition success rate less than 100%"

    # Print KPI summary (in real test framework, this might go to report/log)
    print(f"\nTechnology: {technology}")
    print(f"Attach Success Rate: {attach_success_rate*100:.1f}%")
    print(f"Detach Success Rate: {detach_success_rate*100:.1f}%")
    if secondary_node_addition_success_rate is not None:
        print(f"Secondary Node Addition Success Rate: {secondary_node_addition_success_rate*100:.1f}%")
    print(f"Attach Latency (s): Min={attach_latency_min:.3f}, Avg={attach_latency_avg:.3f}, Max={attach_latency_max:.3f}")

    # Construct KPI namedtuple (could be used for further reporting)
    kpi = KPI(
        attach_success_rate=attach_success_rate,
        detach_success_rate=detach_success_rate,
        secondary_node_addition_success_rate=secondary_node_addition_success_rate,
        attach_latency_min=attach_latency_min,
        attach_latency_avg=attach_latency_avg,
        attach_latency_max=attach_latency_max,
    )

    # Optionally return KPI for external usage
    return kpi
```
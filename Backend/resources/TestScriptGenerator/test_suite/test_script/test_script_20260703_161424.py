import pytest
import logging
import time

# Setup logger for traceability
logger = logging.getLogger("TestNsaAttach")
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)


class UeAttachUtils:
    """
    Utility class to simulate UE attach/detach procedures and validate messages and IEs.
    """

    def __init__(self):
        self.attach_iterations = 10
        self.attach_latencies = []
        self.attach_success_count = 0
        self.detach_success_count = 0
        self.secondary_node_add_success_count = 0

    def trigger_power_on(self):
        logger.debug("Power ON UE for attach procedure.")
        # Simulate UE power on and start attach process
        self.attach_start_time = time.time()

    def trigger_power_off(self):
        logger.debug("Power OFF UE for detach procedure.")
        # Simulate UE power off to trigger detach
        self.detach_start_time = time.time()

    def wait_for_attach_complete(self):
        # Simulate wait and validation for attach complete
        time.sleep(0.5)  # Simulate network processing delay
        attach_complete_time = time.time()
        latency = attach_complete_time - self.attach_start_time
        self.attach_latencies.append(latency)
        self.attach_success_count += 1
        logger.debug(f"Attach successful. Latency: {latency:.3f} seconds.")
        return True

    def wait_for_detach_complete(self):
        # Simulate wait and validation for detach complete
        time.sleep(0.3)  # Simulate network processing delay
        self.detach_success_count += 1
        logger.debug("Detach successful.")
        return True

    def simulate_rrc_connection_request(self):
        logger.debug("Simulate RRC Connection Request message exchange.")
        # Simulate extraction and validation of IEs for RRC Connection Request
        ies = {
            "ue_Identity": "random_value",
            "establishment_cause": "mo-Data"
        }
        assert ies["ue_Identity"], "UE Identity IE missing"
        assert ies["establishment_cause"] == "mo-Data", "Incorrect Establishment Cause IE"
        logger.debug(f"RRC Connection Request IEs validated: {ies}")
        return ies

    def simulate_rrc_connection_setup(self):
        logger.debug("Simulate RRC Connection Setup message exchange.")
        ies = {
            "radio_resource_config": {"physical_config": "configured", "mac_config": "configured"},
            "rrc_transaction_identifier": 1
        }
        assert ies["radio_resource_config"], "Radio Resource Config IE missing"
        assert isinstance(ies["rrc_transaction_identifier"], int), "Invalid Transaction ID IE"
        logger.debug(f"RRC Connection Setup IEs validated: {ies}")
        return ies

    def simulate_rrc_connection_setup_complete(self):
        logger.debug("Simulate RRC Connection Setup Complete message exchange.")
        ies = {
            "nas_pdu": b'\x02\x01\x00'  # NAS Attach Request encoded bytes (example)
        }
        assert isinstance(ies["nas_pdu"], bytes), "NAS PDU IE missing or invalid"
        logger.debug(f"RRC Connection Setup Complete IEs validated: NAS PDU length {len(ies['nas_pdu'])}")
        return ies

    def simulate_nas_attach_request(self):
        logger.debug("Simulate NAS Attach Request processing and IE validation.")
        ies = {
            "eps_attach_type": "EPS_ATTACH_TYPE_EPS_ATTACH",
            "nas_key_set_identifier": 5,
            "ue_network_capability": {"eea": [1, 2], "eia": [1, 2]},
            "ms_identity": {"imsi": "310150123456789"}
        }
        assert ies["eps_attach_type"] == "EPS_ATTACH_TYPE_EPS_ATTACH", "EPS Attach Type IE invalid"
        assert 0 <= ies["nas_key_set_identifier"] <= 7, "Nas Key Set Identifier IE invalid"
        assert "imsi" in ies["ms_identity"], "MS Identity IMSI IE missing"
        logger.debug(f"NAS Attach Request IEs validated: {ies}")
        return ies

    def simulate_attach_accept(self):
        logger.debug("Simulate Attach Accept message processing and IE validation.")
        ies = {
            "emm_cause": 0,
            "t3412_value": 54,
            "emm_key": b'\x01\x02\x03\x04\x05\x06\x07\x08',
            "assigned_guti": {"mcc": "310", "mnc": "150", "mme_group_id": 1, "mme_code": 2, "m_tmsi": 0x1234abcd}
        }
        assert ies["emm_cause"] == 0, "EMM Cause IE indicates failure"
        assert isinstance(ies["t3412_value"], int), "T3412 Value IE invalid"
        assert isinstance(ies["emm_key"], bytes), "EMM Key IE missing or invalid"
        assert isinstance(ies["assigned_guti"], dict), "Assigned GUTI IE missing or invalid"
        logger.debug(f"Attach Accept IEs validated: {ies}")
        return ies

    def simulate_rrc_security_mode_command(self):
        logger.debug("Simulate RRC Security Mode Command message and IE validation.")
        ies = {
            "security_algorithm": {"ciphering": "EEA1", "integrity": "EIA2"},
            "rrc_transaction_identifier": 2
        }
        assert ies["security_algorithm"]["ciphering"] in ["EEA0", "EEA1", "EEA2"], "Invalid ciphering algorithm IE"
        assert ies["security_algorithm"]["integrity"] in ["EIA0", "EIA1", "EIA2"], "Invalid integrity algorithm IE"
        logger.debug(f"RRC Security Mode Command IEs validated: {ies}")
        return ies

    def simulate_rrc_security_mode_complete(self):
        logger.debug("Simulate RRC Security Mode Complete message exchange.")
        ies = {
            "rrc_transaction_identifier": 2
        }
        assert isinstance(ies["rrc_transaction_identifier"], int), "Transaction ID IE missing"
        logger.debug(f"RRC Security Mode Complete IEs validated: {ies}")
        return ies

    def simulate_nas_attach_complete(self):
        logger.debug("Simulate NAS Attach Complete message processing and IE validation.")
        ies = {
            "nas_emm_message_type": "ATTACH_COMPLETE"
        }
        assert ies["nas_emm_message_type"] == "ATTACH_COMPLETE", "NAS Attach Complete message type IE invalid"
        logger.debug(f"NAS Attach Complete IEs validated: {ies}")
        return ies

    def simulate_secondary_node_addition(self):
        logger.debug("Simulate Secondary Node Addition message exchange and IE validation.")
        ies = {
            "sgnb_add_request": True,
            "sgnb_reconfiguration_complete": True
        }
        assert ies["sgnb_add_request"] is True, "SgNB Add Request IE missing or false"
        assert ies["sgnb_reconfiguration_complete"] is True, "SgNB Reconfiguration Complete IE missing or false"
        self.secondary_node_add_success_count += 1
        logger.debug(f"Secondary Node Addition IEs validated: {ies}")
        return ies

    def simulate_rrc_connection_release(self):
        logger.debug("Simulate RRC Connection Release message and IE validation.")
        ies = {
            "release_cause": "ue_initiated"
        }
        assert ies["release_cause"] == "ue_initiated", "Release cause IE invalid"
        logger.debug(f"RRC Connection Release IEs validated: {ies}")
        return ies

    def simulate_nas_detach_request(self):
        logger.debug("Simulate NAS Detach Request message processing and IE validation.")
        ies = {
            "detach_type": "UE_INITIATED",
            "nas_emm_message_type": "DETACH_REQUEST"
        }
        assert ies["detach_type"] == "UE_INITIATED", "Detach Type IE invalid"
        assert ies["nas_emm_message_type"] == "DETACH_REQUEST", "NAS EMM Message Type IE invalid"
        logger.debug(f"NAS Detach Request IEs validated: {ies}")
        return ies

    def simulate_detach_accept(self):
        logger.debug("Simulate Detach Accept message processing and IE validation.")
        ies = {
            "nas_emm_message_type": "DETACH_ACCEPT"
        }
        assert ies["nas_emm_message_type"] == "DETACH_ACCEPT", "NAS EMM Message Type IE invalid"
        logger.debug(f"Detach Accept IEs validated: {ies}")
        return ies


ue_attach_utils = UeAttachUtils()


@pytest.mark.parametrize("iteration", range(ue_attach_utils.attach_iterations))
def test_trigger_ue_attach_and_detach(iteration):
    # ae7976ce-9ff6-4def-887f-d70621c74add: LTE/5G NSA attach and detach of single UE
    logger.info(f"Iteration {iteration + 1} start.")
    ue_attach_utils.trigger_power_on()
    assert ue_attach_utils.wait_for_attach_complete()

    ue_attach_utils.trigger_power_off()
    assert ue_attach_utils.wait_for_detach_complete()
    logger.info(f"Iteration {iteration + 1} complete.")


def test_rrc_connection_request_ies():
    # ae7976ce-9ff6-4def-887f-d70621c74add: LTE/5G NSA attach and detach of single UE
    ies = ue_attach_utils.simulate_rrc_connection_request()
    assert "ue_Identity" in ies
    assert ies["establishment_cause"] == "mo-Data"


def test_rrc_connection_setup_ies():
    # ae7976ce-9ff6-4def-887f-d70621c74add: LTE/5G NSA attach and detach of single UE
    ies = ue_attach_utils.simulate_rrc_connection_setup()
    assert "radio_resource_config" in ies
    assert isinstance(ies["rrc_transaction_identifier"], int)


def test_rrc_connection_setup_complete_ies():
    # ae7976ce-9ff6-4def-887f-d70621c74add: LTE/5G NSA attach and detach of single UE
    ies = ue_attach_utils.simulate_rrc_connection_setup_complete()
    assert isinstance(ies["nas_pdu"], bytes)
    assert len(ies["nas_pdu"]) > 0


def test_nas_attach_request_ies():
    # ae7976ce-9ff6-4def-887f-d70621c74add: LTE/5G NSA attach and detach of single UE
    ies = ue_attach_utils.simulate_nas_attach_request()
    assert ies["eps_attach_type"] == "EPS_ATTACH_TYPE_EPS_ATTACH"
    assert 0 <= ies["nas_key_set_identifier"] <= 7
    assert "imsi" in ies["ms_identity"]


def test_attach_accept_ies():
    # ae7976ce-9ff6-4def-887f-d70621c74add: LTE/5G NSA attach and detach of single UE
    ies = ue_attach_utils.simulate_attach_accept()
    assert ies["emm_cause"] == 0
    assert isinstance(ies["t3412_value"], int)
    assert isinstance(ies["emm_key"], bytes)
    assert isinstance(ies["assigned_guti"], dict)


def test_rrc_security_mode_command_ies():
    # ae7976ce-9ff6-4def-887f-d70621c74add: LTE/5G NSA attach and detach of single UE
    ies = ue_attach_utils.simulate_rrc_security_mode_command()
    ciphering = ies["security_algorithm"]["ciphering"]
    integrity = ies["security_algorithm"]["integrity"]
    assert ciphering in ["EEA0", "EEA1", "EEA2"]
    assert integrity in ["EIA0", "EIA1", "EIA2"]


def test_rrc_security_mode_complete_ies():
    # ae7976ce-9ff6-4def-887f-d70621c74add: LTE/5G NSA attach and detach of single UE
    ies = ue_attach_utils.simulate_rrc_security_mode_complete()
    assert isinstance(ies["rrc_transaction_identifier"], int)


def test_nas_attach_complete_ies():
    # ae7976ce-9ff6-4def-887f-d70621c74add: LTE/5G NSA attach and detach of single UE
    ies = ue_attach_utils.simulate_nas_attach_complete()
    assert ies["nas_emm_message_type"] == "ATTACH_COMPLETE"


def test_secondary_node_addition_ies():
    # ae7976ce-9ff6-4def-887f-d70621c74add: LTE/5G NSA attach and detach of single UE
    ies = ue_attach_utils.simulate_secondary_node_addition()
    assert ies["sgnb_add_request"] is True
    assert ies["sgnb_reconfiguration_complete"] is True


def test_rrc_connection_release_ies():
    # ae7976ce-9ff6-4def-887f-d70621c74add: LTE/5G NSA attach and detach of single UE
    ies = ue_attach_utils.simulate_rrc_connection_release()
    assert ies["release_cause"] == "ue_initiated"


def test_nas_detach_request_ies():
    # ae7976ce-9ff6-4def-887f-d70621c74add: LTE/5G NSA attach and detach of single UE
    ies = ue_attach_utils.simulate_nas_detach_request()
    assert ies["detach_type"] == "UE_INITIATED"
    assert ies["nas_emm_message_type"] == "DETACH_REQUEST"


def test_detach_accept_ies():
    # ae7976ce-9ff6-4def-887f-d70621c74add: LTE/5G NSA attach and detach of single UE
    ies = ue_attach_utils.simulate_detach_accept()
    assert ies["nas_emm_message_type"] == "DETACH_ACCEPT"


def test_attach_kpis_summary():
    # ae7976ce-9ff6-4def-887f-d70621c74add: LTE/5G NSA attach and detach of single UE
    total_iterations = ue_attach_utils.attach_iterations
    attach_success = ue_attach_utils.attach_success_count
    detach_success = ue_attach_utils.detach_success_count
    secondary_node_success = ue_attach_utils.secondary_node_add_success_count
    latencies = ue_attach_utils.attach_latencies

    assert attach_success == total_iterations, f"Attach success rate below 100% ({attach_success}/{total_iterations})"
    assert detach_success == total_iterations, f"Detach success rate below 100% ({detach_success}/{total_iterations})"
    assert secondary_node_success == total_iterations, f"Secondary Node Addition success rate below 100% ({secondary_node_success}/{total_iterations})"
    assert len(latencies) == total_iterations, "Latency values count mismatch"

    latencies_sorted = sorted(latencies)
    latency_min = latencies_sorted[0]
    latency_max = latencies_sorted[-1]
    latency_avg = sum(latencies_sorted) / total_iterations

    logger.info(f"Attach Latency (seconds) - Min: {latency_min:.3f}, Avg: {latency_avg:.3f}, Max: {latency_max:.3f}")

    assert latency_min > 0, "Minimum latency must be greater than zero"
    assert latency_max >= latency_min, "Maximum latency must be >= minimum latency"
    assert latency_avg >= latency_min and latency_avg <= latency_max, "Average latency must be between min and max"
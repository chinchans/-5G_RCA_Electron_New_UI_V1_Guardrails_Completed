import pytest
import logging
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class UEAttachUtils:
    """
    Utility class to simulate UE attach/detach procedures and validate messages/IEs.
    """

    def __init__(self):
        self.attach_iterations = 10
        self.attach_latencies = []
        self.attach_success_count = 0
        self.detach_success_count = 0

    def power_on_ue(self):
        logger.info("Powering ON UE to initiate attach.")
        start_time = time.time()
        # Simulate sending RRC Connection Request message
        rrc_conn_req = self.send_rrc_connection_request()
        if not self.validate_rrc_connection_request(rrc_conn_req):
            logger.error("RRC Connection Request validation failed.")
            return False, None
        # Simulate sending Attach Request message
        attach_req = self.send_attach_request()
        if not self.validate_attach_request(attach_req):
            logger.error("Attach Request validation failed.")
            return False, None
        # Simulate receiving Attach Accept message
        attach_accept = self.receive_attach_accept()
        if not self.validate_attach_accept(attach_accept):
            logger.error("Attach Accept validation failed.")
            return False, None
        latency = time.time() - start_time
        logger.info(f"Attach latency: {latency:.3f} seconds")
        self.attach_latencies.append(latency)
        self.attach_success_count += 1
        return True, attach_accept

    def power_off_ue(self):
        logger.info("Powering OFF UE to initiate detach.")
        # Simulate sending Detach Request message
        detach_req = self.send_detach_request()
        if not self.validate_detach_request(detach_req):
            logger.error("Detach Request validation failed.")
            return False
        # Simulate receiving Detach Accept message
        detach_accept = self.receive_detach_accept()
        if not self.validate_detach_accept(detach_accept):
            logger.error("Detach Accept validation failed.")
            return False
        self.detach_success_count += 1
        return True

    def send_rrc_connection_request(self):
        msg = {
            "message_type": "RRC Connection Request",
            "ue_identity": "random_ue_id",
            "establishment_cause": "mo-Data"
        }
        logger.debug(f"Sent RRC Connection Request: {msg}")
        return msg

    def validate_rrc_connection_request(self, msg):
        logger.info("Validating RRC Connection Request IEs")
        valid = True
        valid &= "message_type" in msg and msg["message_type"] == "RRC Connection Request"
        valid &= "ue_identity" in msg and isinstance(msg["ue_identity"], str) and len(msg["ue_identity"]) > 0
        valid &= "establishment_cause" in msg and msg["establishment_cause"] in ["mo-Data", "mo-Signalling", "emergency"]
        logger.info(f"RRC Connection Request validation result: {valid}")
        return valid

    def send_attach_request(self):
        msg = {
            "message_type": "Attach Request",
            "ue_identity": "random_ue_id",
            "nas_message": {
                "attach_type": "EPS attach",
                "ue_network_capability": {
                    "cs_supported": True,
                    "ps_supported": True,
                    "emergency_supported": True
                },
                "ue_security_capability": {
                    "encryption_algorithms": ["EEA0", "EEA1", "EEA2"],
                    "integrity_algorithms": ["EIA0", "EIA1", "EIA2"]
                },
                "old_guti": None,
                "last_visited_registered_tai": "001,01",
                "ms_identity": "IMSI123456789012345",
                "supported_eps_bearer_contexts": []
            }
        }
        logger.debug(f"Sent Attach Request: {msg}")
        return msg

    def validate_attach_request(self, msg):
        logger.info("Validating Attach Request IEs")
        valid = True
        if msg.get("message_type") != "Attach Request":
            logger.error("Invalid message type for Attach Request")
            return False
        nas_msg = msg.get("nas_message", {})
        valid &= nas_msg.get("attach_type") == "EPS attach"
        ue_net_cap = nas_msg.get("ue_network_capability", {})
        valid &= ue_net_cap.get("cs_supported") is True
        valid &= ue_net_cap.get("ps_supported") is True
        valid &= ue_net_cap.get("emergency_supported") is True
        ue_sec_cap = nas_msg.get("ue_security_capability", {})
        valid &= isinstance(ue_sec_cap.get("encryption_algorithms"), list) and len(ue_sec_cap["encryption_algorithms"]) > 0
        valid &= isinstance(ue_sec_cap.get("integrity_algorithms"), list) and len(ue_sec_cap["integrity_algorithms"]) > 0
        valid &= nas_msg.get("ms_identity", "").startswith("IMSI")
        logger.info(f"Attach Request validation result: {valid}")
        return valid

    def receive_attach_accept(self):
        msg = {
            "message_type": "Attach Accept",
            "nas_message": {
                "emm_cause": 0,
                "guti": "new_guti_value",
                "t3412_value": 54,
                "active_eps_bearers": 1
            },
            "rrc_message": {
                "security_mode_command": True,
                "mme_ue_s1ap_id": 12345,
                "attach_result": "success"
            }
        }
        logger.debug(f"Received Attach Accept: {msg}")
        return msg

    def validate_attach_accept(self, msg):
        logger.info("Validating Attach Accept IEs")
        valid = True
        if msg.get("message_type") != "Attach Accept":
            logger.error("Invalid message type for Attach Accept")
            return False
        nas_msg = msg.get("nas_message", {})
        valid &= nas_msg.get("emm_cause") == 0
        valid &= "guti" in nas_msg and isinstance(nas_msg["guti"], str) and len(nas_msg["guti"]) > 0
        valid &= nas_msg.get("active_eps_bearers") >= 1
        rrc_msg = msg.get("rrc_message", {})
        valid &= rrc_msg.get("security_mode_command") is True
        valid &= rrc_msg.get("attach_result") == "success"
        logger.info(f"Attach Accept validation result: {valid}")
        return valid

    def send_detach_request(self):
        msg = {
            "message_type": "Detach Request",
            "nas_message": {
                "detach_type": "UE initiated",
                "eps_mobile_identity": "IMSI123456789012345"
            }
        }
        logger.debug(f"Sent Detach Request: {msg}")
        return msg

    def validate_detach_request(self, msg):
        logger.info("Validating Detach Request IEs")
        valid = True
        if msg.get("message_type") != "Detach Request":
            logger.error("Invalid message type for Detach Request")
            return False
        nas_msg = msg.get("nas_message", {})
        valid &= nas_msg.get("detach_type") == "UE initiated"
        valid &= nas_msg.get("eps_mobile_identity", "").startswith("IMSI")
        logger.info(f"Detach Request validation result: {valid}")
        return valid

    def receive_detach_accept(self):
        msg = {
            "message_type": "Detach Accept",
            "nas_message": {
                "emm_cause": 0
            }
        }
        logger.debug(f"Received Detach Accept: {msg}")
        return msg

    def validate_detach_accept(self, msg):
        logger.info("Validating Detach Accept IEs")
        if msg.get("message_type") != "Detach Accept":
            logger.error("Invalid message type for Detach Accept")
            return False
        nas_msg = msg.get("nas_message", {})
        valid = nas_msg.get("emm_cause") == 0
        logger.info(f"Detach Accept validation result: {valid}")
        return valid

ue_utils = UEAttachUtils()

@pytest.mark.parametrize("iteration", range(1, 11))
# TC_POS_001: Validate successful LTE/5G NSA Attach and Detach of single UE for iteration
def test_ue_attach_detach_procedure(iteration):
    logger.info(f"Starting iteration {iteration} of UE attach-detach procedure")
    success_attach, attach_accept_msg = ue_utils.power_on_ue()
    assert success_attach, f"Attach failed at iteration {iteration}"
    assert attach_accept_msg is not None, f"No Attach Accept message at iteration {iteration}"

    success_detach = ue_utils.power_off_ue()
    assert success_detach, f"Detach failed at iteration {iteration}"
    logger.info(f"Iteration {iteration} completed successfully")

# TC_POS_001: Validate RRC Connection Request message IEs
def test_rrc_connection_request_ies():
    rrc_req = ue_utils.send_rrc_connection_request()
    assert ue_utils.validate_rrc_connection_request(rrc_req), "RRC Connection Request IEs validation failed"

# TC_POS_001: Validate Attach Request message IEs
def test_attach_request_ies():
    attach_req = ue_utils.send_attach_request()
    assert ue_utils.validate_attach_request(attach_req), "Attach Request IEs validation failed"

# TC_POS_001: Validate Attach Accept message IEs
def test_attach_accept_ies():
    attach_accept = ue_utils.receive_attach_accept()
    assert ue_utils.validate_attach_accept(attach_accept), "Attach Accept IEs validation failed"

# TC_POS_001: Validate Detach Request message IEs
def test_detach_request_ies():
    detach_req = ue_utils.send_detach_request()
    assert ue_utils.validate_detach_request(detach_req), "Detach Request IEs validation failed"

# TC_POS_001: Validate Detach Accept message IEs
def test_detach_accept_ies():
    detach_accept = ue_utils.receive_detach_accept()
    assert ue_utils.validate_detach_accept(detach_accept), "Detach Accept IEs validation failed"

# TC_POS_001: Validate attach latency statistics after all iterations
def test_attach_latency_statistics():
    assert len(ue_utils.attach_latencies) == ue_utils.attach_iterations, "Attach latency count mismatch"
    latencies_sorted = sorted(ue_utils.attach_latencies)
    minimum = latencies_sorted[0]
    maximum = latencies_sorted[-1]
    average = sum(latencies_sorted) / len(latencies_sorted)
    logger.info(f"Attach latency statistics (seconds): Min={minimum:.3f}, Avg={average:.3f}, Max={maximum:.3f}")
    assert minimum > 0, "Minimum attach latency should be greater than zero"
    assert average > 0, "Average attach latency should be greater than zero"
    assert maximum > 0, "Maximum attach latency should be greater than zero"

# TC_POS_001: Validate attach and detach success rates after all iterations
def test_attach_detach_success_rates():
    attach_rate = ue_utils.attach_success_count / ue_utils.attach_iterations
    detach_rate = ue_utils.detach_success_count / ue_utils.attach_iterations
    logger.info(f"Attach success rate: {attach_rate*100:.2f}%")
    logger.info(f"Detach success rate: {detach_rate*100:.2f}%")
    assert attach_rate == 1.0, "Attach success rate must be 100%"
    assert detach_rate == 1.0, "Detach success rate must be 100%"
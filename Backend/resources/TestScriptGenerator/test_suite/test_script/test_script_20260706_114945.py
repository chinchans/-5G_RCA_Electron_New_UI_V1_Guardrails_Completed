import pytest
import logging
import time

# Setup logger
logger = logging.getLogger("TestNsaAttachProcedure")
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)


class UeAttachUtils:
    """
    Utility class to simulate UE attach procedure and validate messages and IEs.
    This is the reference code to trigger attach and validate each message.
    """

    def __init__(self):
        self.attach_iterations = 10
        self.attach_latencies = []
        self.attach_success_count = 0
        self.detach_success_count = 0
        self.secondary_node_add_success_count = 0

    def configure_test_setup(self):
        logger.debug("Configuring test setup with single cell, excellent radio conditions, and UE placement.")
        # Simulate test setup configuration
        time.sleep(0.5)
        return True

    def start_logging(self):
        logger.debug("Starting test logs for call flow and signaling messages.")
        # Simulate starting logs
        time.sleep(0.2)
        return True

    def stop_logging(self):
        logger.debug("Stopping and saving test logs.")
        # Simulate stopping logs
        time.sleep(0.2)
        return True

    def power_on_ue(self):
        logger.debug("Powering ON UE to initiate attach procedure.")
        # Simulate UE power on and attach request sent
        time.sleep(0.5)
        self.attach_start_time = time.time()
        return True

    def power_off_ue(self):
        logger.debug("Powering OFF UE to initiate detach procedure.")
        # Simulate UE power off and detach request sent
        time.sleep(0.5)
        return True

    def wait_for_attach_complete(self):
        # Simulate waiting for attach complete within timeout
        time.sleep(1)
        self.attach_end_time = time.time()
        latency_ms = (self.attach_end_time - self.attach_start_time) * 1000
        self.attach_latencies.append(latency_ms)
        self.attach_success_count += 1
        logger.debug(f"Attach complete received, latency recorded: {latency_ms:.2f} ms")
        return True

    def wait_for_detach_complete(self):
        # Simulate waiting for detach complete within timeout
        time.sleep(1)
        self.detach_success_count += 1
        logger.debug("Detach complete received.")
        return True

    def trigger_secondary_node_addition(self):
        # Simulate Secondary Node Addition in 5G NSA attach
        time.sleep(0.5)
        self.secondary_node_add_success_count += 1
        logger.debug("Secondary Node Addition successful.")
        return True

    def validate_rrc_connection_request_ies(self, msg):
        logger.debug(f"Validating RRC Connection Request IEs: {msg}")
        # Validate mandatory IEs for RRC Connection Request
        required_ies = ["ue-Identity", "establishmentCause"]
        for ie in required_ies:
            if ie not in msg:
                logger.error(f"Missing IE: {ie} in RRC Connection Request")
                return False
        logger.debug("All RRC Connection Request IEs validated successfully.")
        return True

    def validate_rrc_connection_setup_ies(self, msg):
        logger.debug(f"Validating RRC Connection Setup IEs: {msg}")
        required_ies = ["radioResourceConfigDedicated", "securityConfig"]
        for ie in required_ies:
            if ie not in msg:
                logger.error(f"Missing IE: {ie} in RRC Connection Setup")
                return False
        logger.debug("All RRC Connection Setup IEs validated successfully.")
        return True

    def validate_rrc_connection_setup_complete_ies(self, msg):
        logger.debug(f"Validating RRC Connection Setup Complete IEs: {msg}")
        required_ies = ["nas-PDU"]
        for ie in required_ies:
            if ie not in msg:
                logger.error(f"Missing IE: {ie} in RRC Connection Setup Complete")
                return False
        logger.debug("All RRC Connection Setup Complete IEs validated successfully.")
        return True

    def validate_attach_request_ies(self, msg):
        logger.debug(f"Validating Attach Request IEs: {msg}")
        required_ies = ["EPS Mobile Identity", "UE Network Capability", "DRX Parameters"]
        for ie in required_ies:
            if ie not in msg:
                logger.error(f"Missing IE: {ie} in Attach Request")
                return False
        logger.debug("All Attach Request IEs validated successfully.")
        return True

    def validate_authentication_request_ies(self, msg):
        logger.debug(f"Validating Authentication Request IEs: {msg}")
        required_ies = ["RAND", "AUTN"]
        for ie in required_ies:
            if ie not in msg:
                logger.error(f"Missing IE: {ie} in Authentication Request")
                return False
        logger.debug("All Authentication Request IEs validated successfully.")
        return True

    def validate_authentication_response_ies(self, msg):
        logger.debug(f"Validating Authentication Response IEs: {msg}")
        required_ies = ["RES"]
        for ie in required_ies:
            if ie not in msg:
                logger.error(f"Missing IE: {ie} in Authentication Response")
                return False
        logger.debug("All Authentication Response IEs validated successfully.")
        return True

    def validate_security_mode_command_ies(self, msg):
        logger.debug(f"Validating Security Mode Command IEs: {msg}")
        required_ies = ["securityAlgorithms", "nas-Security-Algorithms"]
        for ie in required_ies:
            if ie not in msg:
                logger.error(f"Missing IE: {ie} in Security Mode Command")
                return False
        logger.debug("All Security Mode Command IEs validated successfully.")
        return True

    def validate_security_mode_complete_ies(self, msg):
        logger.debug(f"Validating Security Mode Complete IEs: {msg}")
        required_ies = ["nas-PDU"]
        for ie in required_ies:
            if ie not in msg:
                logger.error(f"Missing IE: {ie} in Security Mode Complete")
                return False
        logger.debug("All Security Mode Complete IEs validated successfully.")
        return True

    def validate_esm_information_request_ies(self, msg):
        logger.debug(f"Validating ESM Information Request IEs: {msg}")
        required_ies = ["requestedIP"]
        for ie in required_ies:
            if ie not in msg:
                logger.error(f"Missing IE: {ie} in ESM Information Request")
                return False
        logger.debug("All ESM Information Request IEs validated successfully.")
        return True

    def validate_esm_information_response_ies(self, msg):
        logger.debug(f"Validating ESM Information Response IEs: {msg}")
        required_ies = ["apn"]
        for ie in required_ies:
            if ie not in msg:
                logger.error(f"Missing IE: {ie} in ESM Information Response")
                return False
        logger.debug("All ESM Information Response IEs validated successfully.")
        return True

    def validate_attach_accept_ies(self, msg):
        logger.debug(f"Validating Attach Accept IEs: {msg}")
        required_ies = ["ESM message container", "TAI list", "GUTI"]
        for ie in required_ies:
            if ie not in msg:
                logger.error(f"Missing IE: {ie} in Attach Accept")
                return False
        logger.debug("All Attach Accept IEs validated successfully.")
        return True

    def validate_rrc_security_mode_command_ies(self, msg):
        logger.debug(f"Validating RRC Security Mode Command IEs: {msg}")
        required_ies = ["securityAlgorithm", "integrityProtection"]
        for ie in required_ies:
            if ie not in msg:
                logger.error(f"Missing IE: {ie} in RRC Security Mode Command")
                return False
        logger.debug("All RRC Security Mode Command IEs validated successfully.")
        return True

    def validate_rrc_security_mode_complete_ies(self, msg):
        logger.debug(f"Validating RRC Security Mode Complete IEs: {msg}")
        required_ies = []
        # No mandatory IE, just acknowledge
        logger.debug("RRC Security Mode Complete validation passed.")
        return True

    def validate_rrc_connection_reconfiguration_ies(self, msg):
        logger.debug(f"Validating RRC Connection Reconfiguration IEs: {msg}")
        required_ies = ["radioResourceConfigDedicated", "measConfig"]
        for ie in required_ies:
            if ie not in msg:
                logger.error(f"Missing IE: {ie} in RRC Connection Reconfiguration")
                return False
        logger.debug("All RRC Connection Reconfiguration IEs validated successfully.")
        return True

    def validate_rrc_connection_reconfiguration_complete_ies(self, msg):
        logger.debug(f"Validating RRC Connection Reconfiguration Complete IEs: {msg}")
        required_ies = []
        # No mandatory IE, just confirm
        logger.debug("RRC Connection Reconfiguration Complete validation passed.")
        return True

    def validate_secondary_node_addition(self, msg):
        logger.debug(f"Validating Secondary Node Addition IEs: {msg}")
        required_ies = ["SgNB Addition Request", "SgNB Reconfiguration Complete"]
        for ie in required_ies:
            if ie not in msg:
                logger.error(f"Missing IE: {ie} in Secondary Node Addition")
                return False
        logger.debug("All Secondary Node Addition IEs validated successfully.")
        return True

    def validate_detach_request_ies(self, msg):
        logger.debug(f"Validating Detach Request IEs: {msg}")
        required_ies = ["Detach Type", "NAS PDU"]
        for ie in required_ies:
            if ie not in msg:
                logger.error(f"Missing IE: {ie} in Detach Request")
                return False
        logger.debug("All Detach Request IEs validated successfully.")
        return True

    def validate_detach_accept_ies(self, msg):
        logger.debug(f"Validating Detach Accept IEs: {msg}")
        required_ies = ["NAS PDU"]
        for ie in required_ies:
            if ie not in msg:
                logger.error(f"Missing IE: {ie} in Detach Accept")
                return False
        logger.debug("All Detach Accept IEs validated successfully.")
        return True

    def validate_rrc_connection_release_ies(self, msg):
        logger.debug(f"Validating RRC Connection Release IEs: {msg}")
        required_ies = ["releaseCause"]
        for ie in required_ies:
            if ie not in msg:
                logger.error(f"Missing IE: {ie} in RRC Connection Release")
                return False
        logger.debug("All RRC Connection Release IEs validated successfully.")
        return True


ue_utils = UeAttachUtils()


@pytest.fixture(scope="module", autouse=True)
def setup_test_environment():
    # Configure test setup once for the test module
    assert ue_utils.configure_test_setup()
    yield
    # Teardown or cleanup if needed


# Test cases per message and procedure steps


# TC_POS_001: LTE/5G NSA attach and detach of single UE
def test_trigger_ue_attach_and_detach_procedure():
    for iteration in range(ue_utils.attach_iterations):
        logger.info(f"Starting attach-detach iteration {iteration + 1}")

        assert ue_utils.start_logging()

        assert ue_utils.power_on_ue()

        assert ue_utils.wait_for_attach_complete()

        # Trigger Secondary Node Addition for 5G NSA
        assert ue_utils.trigger_secondary_node_addition()

        assert ue_utils.power_off_ue()

        assert ue_utils.wait_for_detach_complete()

        assert ue_utils.stop_logging()

    # Validate success rates
    attach_success_rate = ue_utils.attach_success_count / ue_utils.attach_iterations
    detach_success_rate = ue_utils.detach_success_count / ue_utils.attach_iterations
    secondary_node_add_rate = ue_utils.secondary_node_add_success_count / ue_utils.attach_iterations
    logger.info(f"Attach Success Rate: {attach_success_rate * 100:.1f}%")
    logger.info(f"Detach Success Rate: {detach_success_rate * 100:.1f}%")
    logger.info(f"Secondary Node Addition Success Rate: {secondary_node_add_rate * 100:.1f}%")

    assert attach_success_rate == 1.0, "Attach success rate is not 100%"
    assert detach_success_rate == 1.0, "Detach success rate is not 100%"
    assert secondary_node_add_rate == 1.0, "Secondary Node Addition success rate is not 100%"


# TC_POS_001: LTE/5G NSA attach and detach of single UE
def test_attach_latency_measurements():
    latencies = sorted(ue_utils.attach_latencies)
    min_latency = latencies[0]
    max_latency = latencies[-1]
    avg_latency = sum(latencies) / len(latencies)
    logger.info(f"Attach Latency Min: {min_latency:.2f} ms, Avg: {avg_latency:.2f} ms, Max: {max_latency:.2f} ms")
    assert len(latencies) == ue_utils.attach_iterations
    assert min_latency > 0
    assert max_latency >= min_latency
    assert avg_latency >= min_latency and avg_latency <= max_latency


# TC_POS_001: LTE/5G NSA attach and detach of single UE
def test_rrc_connection_request_ies():
    message = {"ue-Identity": "temp-Id", "establishmentCause": "mo-Signalling"}
    assert ue_utils.validate_rrc_connection_request_ies(message)


# TC_POS_001: LTE/5G NSA attach and detach of single UE
def test_rrc_connection_setup_ies():
    message = {"radioResourceConfigDedicated": {}, "securityConfig": {}}
    assert ue_utils.validate_rrc_connection_setup_ies(message)


# TC_POS_001: LTE/5G NSA attach and detach of single UE
def test_rrc_connection_setup_complete_ies():
    message = {"nas-PDU": b"\x01\x02\x03"}
    assert ue_utils.validate_rrc_connection_setup_complete_ies(message)


# TC_POS_001: LTE/5G NSA attach and detach of single UE
def test_attach_request_ies():
    message = {
        "EPS Mobile Identity": "IMSI-123456789012345",
        "UE Network Capability": {"encryptionAlgorithms": ["EA0", "EA1"]},
        "DRX Parameters": {"value": 2}
    }
    assert ue_utils.validate_attach_request_ies(message)


# TC_POS_001: LTE/5G NSA attach and detach of single UE
def test_authentication_request_ies():
    message = {"RAND": b"random", "AUTN": b"authenticator"}
    assert ue_utils.validate_authentication_request_ies(message)


# TC_POS_001: LTE/5G NSA attach and detach of single UE
def test_authentication_response_ies():
    message = {"RES": b"response"}
    assert ue_utils.validate_authentication_response_ies(message)


# TC_POS_001: LTE/5G NSA attach and detach of single UE
def test_security_mode_command_ies():
    message = {"securityAlgorithms": {"ciphering": "EEA1", "integrity": "EIA1"}, "nas-Security-Algorithms": {"ciphering": "EEA1", "integrity": "EIA1"}}
    assert ue_utils.validate_security_mode_command_ies(message)


# TC_POS_001: LTE/5G NSA attach and detach of single UE
def test_security_mode_complete_ies():
    message = {"nas-PDU": b"\x05\x06\x07"}
    assert ue_utils.validate_security_mode_complete_ies(message)


# TC_POS_001: LTE/5G NSA attach and detach of single UE
def test_esm_information_request_ies():
    message = {"requestedIP": "192.168.1.2"}
    assert ue_utils.validate_esm_information_request_ies(message)


# TC_POS_001: LTE/5G NSA attach and detach of single UE
def test_esm_information_response_ies():
    message = {"apn": "internet"}
    assert ue_utils.validate_esm_information_response_ies(message)


# TC_POS_001: LTE/5G NSA attach and detach of single UE
def test_attach_accept_ies():
    message = {"ESM message container": b"\x10\x20", "TAI list": ["00101"], "GUTI": "12345"}
    assert ue_utils.validate_attach_accept_ies(message)


# TC_POS_001: LTE/5G NSA attach and detach of single UE
def test_rrc_security_mode_command_ies():
    message = {"securityAlgorithm": "AES", "integrityProtection": "HMAC"}
    assert ue_utils.validate_rrc_security_mode_command_ies(message)


# TC_POS_001: LTE/5G NSA attach and detach of single UE
def test_rrc_security_mode_complete_ies():
    message = {}
    assert ue_utils.validate_rrc_security_mode_complete_ies(message)


# TC_POS_001: LTE/5G NSA attach and detach of single UE
def test_rrc_connection_reconfiguration_ies():
    message = {"radioResourceConfigDedicated": {}, "measConfig": {}}
    assert ue_utils.validate_rrc_connection_reconfiguration_ies(message)


# TC_POS_001: LTE/5G NSA attach and detach of single UE
def test_rrc_connection_reconfiguration_complete_ies():
    message = {}
    assert ue_utils.validate_rrc_connection_reconfiguration_complete_ies(message)


# TC_POS_001: LTE/5G NSA attach and detach of single UE
def test_secondary_node_addition_ies():
    message = {"SgNB Addition Request": {}, "SgNB Reconfiguration Complete": {}}
    assert ue_utils.validate_secondary_node_addition(message)


# TC_POS_001: LTE/5G NSA attach and detach of single UE
def test_detach_request_ies():
    message = {"Detach Type": "UE initiated", "NAS PDU": b"\x08\x09"}
    assert ue_utils.validate_detach_request_ies(message)


# TC_POS_001: LTE/5G NSA attach and detach of single UE
def test_detach_accept_ies():
    message = {"NAS PDU": b"\x0a\x0b"}
    assert ue_utils.validate_detach_accept_ies(message)


# TC_POS_001: LTE/5G NSA attach and detach of single UE
def test_rrc_connection_release_ies():
    message = {"releaseCause": "UE requested release"}
    assert ue_utils.validate_rrc_connection_release_ies(message)
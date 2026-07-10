import pytest
import logging
import time

logger = logging.getLogger("TestNsaAttachSequence")
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

class UeAttachUtils:
    """
    Utility class to simulate UE attach/detach and message handling.
    This is the reference code for triggering attach and validating messages.
    """

    def __init__(self):
        self.attach_iterations = 10
        self.attach_latencies = []
        self.attach_success_count = 0
        self.detach_success_count = 0
        self.secondary_node_add_success_count = 0

    def configure_test_setup(self):
        logger.info("Configuring test setup for single UE 5G NSA attach/detach under excellent radio conditions.")
        # Setup test environment (cell activation, UE placement, radio conditions)
        # Emulated by sleep
        time.sleep(1)

    def start_logging(self, iteration):
        logger.info(f"Starting logs for iteration {iteration + 1}.")

    def stop_logging(self, iteration):
        logger.info(f"Stopping logs for iteration {iteration + 1}.")

    def power_on_ue(self):
        logger.info("Power ON UE to initiate attach.")

    def power_off_ue(self):
        logger.info("Power OFF UE to initiate detach.")

    def wait_for_attach_success(self):
        # Simulate attach procedure timing
        start_time = time.time()
        # Simulate attach request & complete message exchange and validation
        time.sleep(0.5)
        attach_latency = time.time() - start_time
        logger.info(f"Attach successful, latency={attach_latency:.3f}s")
        self.attach_latencies.append(attach_latency)
        self.attach_success_count += 1
        return True

    def wait_for_detach_success(self):
        # Simulate detach procedure timing
        time.sleep(0.3)
        logger.info("Detach successful.")
        self.detach_success_count += 1
        return True

    def validate_rrc_connection_request(self, message):
        # Validate all IEs of RRC Connection Request message
        logger.info("Validating RRC Connection Request IEs.")
        required_ies = ['ue-Identity', 'establishmentCause']
        for ie in required_ies:
            if ie not in message:
                logger.error(f"Missing IE in RRC Connection Request: {ie}")
                return False
            logger.info(f"IE {ie} validated with value: {message[ie]}")
        return True

    def validate_rrc_connection_setup(self, message):
        logger.info("Validating RRC Connection Setup IEs.")
        required_ies = ['radioResourceConfigDedicated']
        for ie in required_ies:
            if ie not in message:
                logger.error(f"Missing IE in RRC Connection Setup: {ie}")
                return False
            logger.info(f"IE {ie} validated with value: {message[ie]}")
        return True

    def validate_rrc_connection_setup_complete(self, message):
        logger.info("Validating RRC Connection Setup Complete IEs.")
        required_ies = ['nas-PDU']
        for ie in required_ies:
            if ie not in message:
                logger.error(f"Missing IE in RRC Connection Setup Complete: {ie}")
                return False
            logger.info(f"IE {ie} validated with value: {message[ie]}")
        return True

    def validate_attach_request(self, message):
        logger.info("Validating Attach Request IEs.")
        required_ies = ['ueNetworkCapability', 'epsAttachType', 'nasKeySetIdentifier']
        for ie in required_ies:
            if ie not in message:
                logger.error(f"Missing IE in Attach Request: {ie}")
                return False
            logger.info(f"IE {ie} validated with value: {message[ie]}")
        return True

    def validate_authentication_request(self, message):
        logger.info("Validating Authentication Request IEs.")
        required_ies = ['rand', 'autn']
        for ie in required_ies:
            if ie not in message:
                logger.error(f"Missing IE in Authentication Request: {ie}")
                return False
            logger.info(f"IE {ie} validated with value: {message[ie]}")
        return True

    def validate_authentication_response(self, message):
        logger.info("Validating Authentication Response IEs.")
        required_ies = ['res']
        for ie in required_ies:
            if ie not in message:
                logger.error(f"Missing IE in Authentication Response: {ie}")
                return False
            logger.info(f"IE {ie} validated with value: {message[ie]}")
        return True

    def validate_security_mode_command(self, message):
        logger.info("Validating Security Mode Command IEs.")
        required_ies = ['securityAlgorithmConfig', 'nasCount']
        for ie in required_ies:
            if ie not in message:
                logger.error(f"Missing IE in Security Mode Command: {ie}")
                return False
            logger.info(f"IE {ie} validated with value: {message[ie]}")
        return True

    def validate_security_mode_complete(self, message):
        logger.info("Validating Security Mode Complete IEs.")
        required_ies = ['nasSecurityModeComplete']
        for ie in required_ies:
            if ie not in message:
                logger.error(f"Missing IE in Security Mode Complete: {ie}")
                return False
            logger.info(f"IE {ie} validated with value: {message[ie]}")
        return True

    def validate_esm_information_request(self, message):
        logger.info("Validating ESM Information Request IEs.")
        required_ies = ['esmMessageContainer']
        for ie in required_ies:
            if ie not in message:
                logger.error(f"Missing IE in ESM Information Request: {ie}")
                return False
            logger.info(f"IE {ie} validated with value: {message[ie]}")
        return True

    def validate_esm_information_response(self, message):
        logger.info("Validating ESM Information Response IEs.")
        required_ies = ['esmMessageContainer']
        for ie in required_ies:
            if ie not in message:
                logger.error(f"Missing IE in ESM Information Response: {ie}")
                return False
            logger.info(f"IE {ie} validated with value: {message[ie]}")
        return True

    def validate_attach_accept(self, message):
        logger.info("Validating Attach Accept IEs.")
        required_ies = ['emmCause', 't3412Value', 'esmMessageContainer']
        for ie in required_ies:
            if ie not in message:
                logger.error(f"Missing IE in Attach Accept: {ie}")
                return False
            logger.info(f"IE {ie} validated with value: {message[ie]}")
        return True

    def validate_attach_complete(self, message):
        logger.info("Validating Attach Complete IEs.")
        required_ies = ['esmMessageContainer']
        for ie in required_ies:
            if ie not in message:
                logger.error(f"Missing IE in Attach Complete: {ie}")
                return False
            logger.info(f"IE {ie} validated with value: {message[ie]}")
        return True

    def validate_secondary_node_addition(self, message):
        logger.info("Validating Secondary Node Addition IEs.")
        required_ies = ['SgNBAdditionRequest', 'SgNBReconfigurationComplete']
        for ie in required_ies:
            if ie not in message:
                logger.error(f"Missing IE in Secondary Node Addition: {ie}")
                return False
            logger.info(f"IE {ie} validated with value: {message[ie]}")
        self.secondary_node_add_success_count += 1
        return True

    def validate_ue_context_release(self, message):
        logger.info("Validating UE Context Release IEs.")
        required_ies = ['ueContextReleaseRequest', 'rrcConnectionRelease']
        for ie in required_ies:
            if ie not in message:
                logger.error(f"Missing IE in UE Context Release: {ie}")
                return False
            logger.info(f"IE {ie} validated with value: {message[ie]}")
        return True

    def validate_detach_request(self, message):
        logger.info("Validating Detach Request IEs.")
        required_ies = ['detachType', 'epsDetachType']
        for ie in required_ies:
            if ie not in message:
                logger.error(f"Missing IE in Detach Request: {ie}")
                return False
            logger.info(f"IE {ie} validated with value: {message[ie]}")
        return True

    def validate_detach_accept(self, message):
        logger.info("Validating Detach Accept IEs.")
        required_ies = ['detachAccept']
        for ie in required_ies:
            if ie not in message:
                logger.error(f"Missing IE in Detach Accept: {ie}")
                return False
            logger.info(f"IE {ie} validated with value: {message[ie]}")
        return True


@pytest.fixture(scope="module")
def ue_utils():
    utils = UeAttachUtils()
    utils.configure_test_setup()
    return utils


@pytest.mark.parametrize("iteration", range(10))
def test_ue_attach_detach_procedure(ue_utils, iteration):
    ue_utils.start_logging(iteration)

    # Power ON UE - Trigger attach
    ue_utils.power_on_ue()

    # Simulate and validate messages in attach procedure in sequence

    # RRC Connection Request
    rrc_conn_req_msg = {
        'ue-Identity': 'random-ue-identity',
        'establishmentCause': 'mo-Signalling'
    }
    assert ue_utils.validate_rrc_connection_request(rrc_conn_req_msg)

    # RRC Connection Setup
    rrc_conn_setup_msg = {
        'radioResourceConfigDedicated': 'configured'
    }
    assert ue_utils.validate_rrc_connection_setup(rrc_conn_setup_msg)

    # RRC Connection Setup Complete with NAS PDU (Attach Request)
    rrc_conn_setup_comp_msg = {
        'nas-PDU': 'attach-request-pdu'
    }
    assert ue_utils.validate_rrc_connection_setup_complete(rrc_conn_setup_comp_msg)

    # Attach Request NAS message
    attach_req_msg = {
        'ueNetworkCapability': 'full',
        'epsAttachType': 'EPS_ATTACH_TYPE_EPS',
        'nasKeySetIdentifier': 'ksi-value'
    }
    assert ue_utils.validate_attach_request(attach_req_msg)

    # Authentication Request
    auth_req_msg = {
        'rand': 'random-challenge',
        'autn': 'auth-token'
    }
    assert ue_utils.validate_authentication_request(auth_req_msg)

    # Authentication Response
    auth_resp_msg = {
        'res': 'response'
    }
    assert ue_utils.validate_authentication_response(auth_resp_msg)

    # Security Mode Command
    sec_mode_cmd_msg = {
        'securityAlgorithmConfig': 'configured',
        'nasCount': 'count-value'
    }
    assert ue_utils.validate_security_mode_command(sec_mode_cmd_msg)

    # Security Mode Complete
    sec_mode_comp_msg = {
        'nasSecurityModeComplete': 'complete'
    }
    assert ue_utils.validate_security_mode_complete(sec_mode_comp_msg)

    # ESM Information Request
    esm_info_req_msg = {
        'esmMessageContainer': 'esm-info-request'
    }
    assert ue_utils.validate_esm_information_request(esm_info_req_msg)

    # ESM Information Response
    esm_info_resp_msg = {
        'esmMessageContainer': 'esm-info-response'
    }
    assert ue_utils.validate_esm_information_response(esm_info_resp_msg)

    # Attach Accept
    attach_accept_msg = {
        'emmCause': '0',
        't3412Value': 'value',
        'esmMessageContainer': 'esm-attach-accept'
    }
    assert ue_utils.validate_attach_accept(attach_accept_msg)

    # Attach Complete
    attach_complete_msg = {
        'esmMessageContainer': 'esm-attach-complete'
    }
    assert ue_utils.validate_attach_complete(attach_complete_msg)

    # Secondary Node Addition for 5G NSA
    secondary_node_add_msg = {
        'SgNBAdditionRequest': 'request',
        'SgNBReconfigurationComplete': 'complete'
    }
    assert ue_utils.validate_secondary_node_addition(secondary_node_add_msg)

    # Wait for attach success confirmation
    assert ue_utils.wait_for_attach_success()

    # Power OFF UE - Trigger detach
    ue_utils.power_off_ue()

    # UE Context Release messages for detach
    ue_context_release_msg = {
        'ueContextReleaseRequest': 'request',
        'rrcConnectionRelease': 'release'
    }
    assert ue_utils.validate_ue_context_release(ue_context_release_msg)

    # Detach Request
    detach_req_msg = {
        'detachType': 'UE_INITIATED',
        'epsDetachType': 'EPS_DETACH'
    }
    assert ue_utils.validate_detach_request(detach_req_msg)

    # Detach Accept
    detach_accept_msg = {
        'detachAccept': 'accept'
    }
    assert ue_utils.validate_detach_accept(detach_accept_msg)

    # Wait for detach success confirmation
    assert ue_utils.wait_for_detach_success()

    ue_utils.stop_logging(iteration)


def test_final_kpi_validation(ue_utils):
    # Validate KPI metrics after 10 iterations

    assert ue_utils.attach_success_count == 10, f"Attach success count {ue_utils.attach_success_count} != 10"
    assert ue_utils.detach_success_count == 10, f"Detach success count {ue_utils.detach_success_count} != 10"
    assert ue_utils.secondary_node_add_success_count == 10, f"Secondary Node Addition success count {ue_utils.secondary_node_add_success_count} != 10"

    latencies_sorted = sorted(ue_utils.attach_latencies)
    min_latency = latencies_sorted[0]
    max_latency = latencies_sorted[-1]
    avg_latency = sum(ue_utils.attach_latencies) / len(ue_utils.attach_latencies)

    logger.info(f"Attach latency min: {min_latency:.3f}s, avg: {avg_latency:.3f}s, max: {max_latency:.3f}s")

    # Example thresholds (to be adjusted per test requirements)
    assert min_latency >= 0, "Minimum latency should be non-negative"
    assert max_latency < 5, "Maximum latency should be less than 5 seconds"
    assert avg_latency < 3, "Average latency should be less than 3 seconds"
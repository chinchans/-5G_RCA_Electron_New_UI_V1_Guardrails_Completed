import time
import logging

logger = logging.getLogger("AttachDetachTest")
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

class UEAttachUtils:
    """
    Reference attach utilities for UE attach/detach control and validation.
    """

    def __init__(self, ue):
        self.ue = ue  # UE interface object for control and log retrieval

    def power_on_ue(self):
        logger.info("Powering ON the UE.")
        result = self.ue.power_on()
        if not result:
            logger.error("Failed to power ON the UE.")
            raise RuntimeError("UE power ON failed.")
        logger.info("UE powered ON successfully.")

    def power_off_ue(self):
        logger.info("Powering OFF the UE.")
        result = self.ue.power_off()
        if not result:
            logger.error("Failed to power OFF the UE.")
            raise RuntimeError("UE power OFF failed.")
        logger.info("UE powered OFF successfully.")

    def wait_for_attach(self, timeout=30):
        logger.info("Waiting for UE attach success indication.")
        start_time = time.time()
        while time.time() - start_time < timeout:
            attach_status = self.ue.get_attach_status()
            if attach_status == "attached":
                logger.info("UE attach successful.")
                return True
            time.sleep(1)
        logger.error("UE attach timed out after %d seconds.", timeout)
        raise TimeoutError("UE attach procedure timed out.")

    def wait_for_detach(self, timeout=30):
        logger.info("Waiting for UE detach success indication.")
        start_time = time.time()
        while time.time() - start_time < timeout:
            detach_status = self.ue.get_detach_status()
            if detach_status == "detached":
                logger.info("UE detach successful.")
                return True
            time.sleep(1)
        logger.error("UE detach timed out after %d seconds.", timeout)
        raise TimeoutError("UE detach procedure timed out.")

    def start_logs(self):
        logger.info("Starting call flow and signaling logs capture.")
        self.ue.start_logging()

    def stop_logs(self):
        logger.info("Stopping and saving logs.")
        self.ue.stop_logging()
        logs = self.ue.get_logs()
        logger.debug("Captured logs length: %d bytes", len(logs))
        return logs

    def get_ue_logs(self):
        return self.ue.get_logs()

    def validate_attach_request(self, msg):
        logger.info("Validating Attach Request NAS message.")
        required_ies = ["EPS attach type", "NAS key set identifier", "UE network capability",
                        "EPS mobile identity", "PDN connectivity request"]
        for ie in required_ies:
            if ie not in msg:
                logger.error("Missing IE in Attach Request: %s", ie)
                raise AssertionError(f"IE '{ie}' missing in Attach Request message.")
            else:
                logger.debug("IE '%s' present with value: %s", ie, msg[ie])
        logger.info("Attach Request message validation passed.")

    def validate_authentication_request(self, msg):
        logger.info("Validating Authentication Request NAS message.")
        required_ies = ["RAND", "AUTN"]
        for ie in required_ies:
            if ie not in msg:
                logger.error("Missing IE in Authentication Request: %s", ie)
                raise AssertionError(f"IE '{ie}' missing in Authentication Request message.")
            else:
                logger.debug("IE '%s' present with value: %s", ie, msg[ie])
        logger.info("Authentication Request message validation passed.")

    def validate_authentication_response(self, msg):
        logger.info("Validating Authentication Response NAS message.")
        required_ies = ["RES"]
        for ie in required_ies:
            if ie not in msg:
                logger.error("Missing IE in Authentication Response: %s", ie)
                raise AssertionError(f"IE '{ie}' missing in Authentication Response message.")
            else:
                logger.debug("IE '%s' present with value: %s", ie, msg[ie])
        logger.info("Authentication Response message validation passed.")

    def validate_security_mode_command(self, msg):
        logger.info("Validating Security Mode Command NAS message.")
        required_ies = ["security header type", "selected NAS security algorithms", "IMEISV request"]
        for ie in required_ies:
            if ie not in msg:
                logger.error("Missing IE in Security Mode Command: %s", ie)
                raise AssertionError(f"IE '{ie}' missing in Security Mode Command message.")
            else:
                logger.debug("IE '%s' present with value: %s", ie, msg[ie])
        logger.info("Security Mode Command message validation passed.")

    def validate_security_mode_complete(self, msg):
        logger.info("Validating Security Mode Complete NAS message.")
        # This message may contain no IEs or optional ones, confirm at least security header type
        if "security header type" not in msg:
            logger.error("Missing IE 'security header type' in Security Mode Complete message.")
            raise AssertionError("IE 'security header type' missing in Security Mode Complete message.")
        logger.info("Security Mode Complete message validation passed.")

    def validate_esm_information_request(self, msg):
        logger.info("Validating ESM Information Request NAS message.")
        if "ESM message container" not in msg:
            logger.error("Missing IE 'ESM message container' in ESM Information Request.")
            raise AssertionError("IE 'ESM message container' missing in ESM Information Request message.")
        logger.info("ESM Information Request message validation passed.")

    def validate_esm_information_response(self, msg):
        logger.info("Validating ESM Information Response NAS message.")
        if "APN" not in msg:
            logger.error("Missing IE 'APN' in ESM Information Response.")
            raise AssertionError("IE 'APN' missing in ESM Information Response message.")
        logger.info("ESM Information Response message validation passed.")

    def validate_attach_accept(self, msg):
        logger.info("Validating Attach Accept NAS message.")
        required_ies = ["EPS mobile identity", "TAI list", "ESM message container", "GUTI"]
        for ie in required_ies:
            if ie not in msg:
                logger.error("Missing IE in Attach Accept: %s", ie)
                raise AssertionError(f"IE '{ie}' missing in Attach Accept message.")
            else:
                logger.debug("IE '%s' present with value: %s", ie, msg[ie])
        logger.info("Attach Accept message validation passed.")

    def validate_attach_complete(self, msg):
        logger.info("Validating Attach Complete NAS message.")
        # Attach Complete usually has no IEs, just message presence is enough
        logger.info("Attach Complete message validation passed.")

    def validate_rrc_connection_request(self, msg):
        logger.info("Validating RRC Connection Request message.")
        if "ue-Identity" not in msg:
            logger.error("Missing IE 'ue-Identity' in RRC Connection Request.")
            raise AssertionError("IE 'ue-Identity' missing in RRC Connection Request message.")
        logger.info("RRC Connection Request message validation passed.")

    def validate_rrc_connection_setup(self, msg):
        logger.info("Validating RRC Connection Setup message.")
        required_ies = ["radioResourceConfigDedicated", "securityConfig", "measConfig"]
        for ie in required_ies:
            if ie not in msg:
                logger.error("Missing IE '%s' in RRC Connection Setup.", ie)
                raise AssertionError(f"IE '{ie}' missing in RRC Connection Setup message.")
            else:
                logger.debug("IE '%s' present.", ie)
        logger.info("RRC Connection Setup message validation passed.")

    def validate_rrc_connection_setup_complete(self, msg):
        logger.info("Validating RRC Connection Setup Complete message.")
        if "nas-PDU" not in msg:
            logger.error("Missing IE 'nas-PDU' in RRC Connection Setup Complete.")
            raise AssertionError("IE 'nas-PDU' missing in RRC Connection Setup Complete message.")
        logger.info("RRC Connection Setup Complete message validation passed.")

    def validate_rrc_connection_release(self, msg):
        logger.info("Validating RRC Connection Release message.")
        if "releaseCause" not in msg:
            logger.error("Missing IE 'releaseCause' in RRC Connection Release.")
            raise AssertionError("IE 'releaseCause' missing in RRC Connection Release message.")
        logger.info("RRC Connection Release message validation passed.")


class UESimulator:
    """
    Simulated UE interface for attach/detach control, signaling message exchange and log retrieval.
    This dummy class should be replaced with actual UE interface implementation.
    """
    def __init__(self):
        self._powered_on = False
        self._attach_status = "detached"
        self._detach_status = "detached"
        self._logs = []
        self._message_log = []

    def power_on(self):
        self._powered_on = True
        self._attach_status = "attached"
        self._detach_status = "detached"
        self._logs.append("UE powered on.")
        return True

    def power_off(self):
        self._powered_on = False
        self._attach_status = "detached"
        self._detach_status = "detached"
        self._
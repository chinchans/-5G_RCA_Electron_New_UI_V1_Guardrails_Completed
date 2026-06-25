import logging
import unittest

# Assuming ue_attach_utils provides the following methods based on reference code:
# - trigger_ue_attach()
# - validate_attach_accept()
# - validate_rrc_message(message_name, ies)
# - validate_nas_message(message_name, ies)
# - extract_ies_from_message(message)
# - log_and_assert_ie(ie_name, ie_value, expected_value)

from ue_attach_utils import (
    trigger_ue_attach,
    validate_attach_accept,
    validate_rrc_message,
    validate_nas_message,
    extract_ies_from_message,
    log_and_assert_ie,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AttachProcedureTest")

class Test5GNSAAttachProcedure(unittest.TestCase):

    def test_ue_attach_procedure(self):
        # Step 1: Trigger UE Attach Procedure
        logger.info("Triggering UE Attach Procedure")
        attach_response = trigger_ue_attach()
        self.assertIsNotNone(attach_response, "Attach response should not be None")

        # Step 2: Validate RRC Setup Request Message
        self.validate_rrc_setup_request(attach_response["rrc_setup_request"])

        # Step 3: Validate RRC Setup Message
        self.validate_rrc_setup(attach_response["rrc_setup"])

        # Step 4: Validate RRC Security Mode Command Message
        self.validate_rrc_security_mode_command(attach_response["rrc_security_mode_command"])

        # Step 5: Validate RRC Security Mode Complete Message
        self.validate_rrc_security_mode_complete(attach_response["rrc_security_mode_complete"])

        # Step 6: Validate NAS Attach Request Message
        self.validate_nas_attach_request(attach_response["nas_attach_request"])

        # Step 7: Validate NAS Authentication Request Message
        self.validate_nas_authentication_request(attach_response["nas_authentication_request"])

        # Step 8: Validate NAS Authentication Response Message
        self.validate_nas_authentication_response(attach_response["nas_authentication_response"])

        # Step 9: Validate NAS Security Mode Command Message
        self.validate_nas_security_mode_command(attach_response["nas_security_mode_command"])

        # Step 10: Validate NAS Security Mode Complete Message
        self.validate_nas_security_mode_complete(attach_response["nas_security_mode_complete"])

        # Step 11: Validate NAS Attach Accept Message
        self.validate_nas_attach_accept(attach_response["nas_attach_accept"])

        # Step 12: Validate NAS Attach Complete Message
        self.validate_nas_attach_complete(attach_response["nas_attach_complete"])

        # Final validation of attach success
        logger.info("Validating overall Attach Accept message")
        validate_attach_accept(attach_response["nas_attach_accept"])

    def validate_rrc_setup_request(self, message):
        message_name = "RRC Setup Request"
        logger.info(f"Validating {message_name}")
        ies = extract_ies_from_message(message)
        validate_rrc_message(message_name, ies)

        # Explicit IE validations
        log_and_assert_ie("ue-Identity", ies.get("ue-Identity"), expected_value="random_5g_s_tmsi")
        log_and_assert_ie("establishmentCause", ies.get("establishmentCause"), expected_value="mo-Signalling")

    def validate_rrc_setup(self, message):
        message_name = "RRC Setup"
        logger.info(f"Validating {message_name}")
        ies = extract_ies_from_message(message)
        validate_rrc_message(message_name, ies)

        log_and_assert_ie("radioResourceConfigDedicated", ies.get("radioResourceConfigDedicated"), expected_value="configured")
        log_and_assert_ie("criticalExtensions", ies.get("criticalExtensions"), expected_value="rrcSetup")

    def validate_rrc_security_mode_command(self, message):
        message_name = "RRC Security Mode Command"
        logger.info(f"Validating {message_name}")
        ies = extract_ies_from_message(message)
        validate_rrc_message(message_name, ies)

        log_and_assert_ie("securityAlgorithmConfig", ies.get("securityAlgorithmConfig"), expected_value="nea2_128")
        log_and_assert_ie("integrityProtAlgorithm", ies.get("integrityProtAlgorithm"), expected_value="nia2_128")

    def validate_rrc_security_mode_complete(self, message):
        message_name = "RRC Security Mode Complete"
        logger.info(f"Validating {message_name}")
        ies = extract_ies_from_message(message)
        validate_rrc_message(message_name, ies)

        log_and_assert_ie("rrcTransactionIdentifier", ies.get("rrcTransactionIdentifier"), expected_value=1)
        log_and_assert_ie("criticalExtensions", ies.get("criticalExtensions"), expected_value="rrcSecurityModeComplete")

    def validate_nas_attach_request(self, message):
        message_name = "NAS Attach Request"
        logger.info(f"Validating {message_name}")
        ies = extract_ies_from_message(message)
        validate_nas_message(message_name, ies)

        log_and_assert_ie("nasMessageType", ies.get("nasMessageType"), expected_value="Attach Request")
        log_and_assert_ie("ueNetworkCapability", ies.get("ueNetworkCapability"), expected_value="5G")
        log_and_assert_ie("ueSecurityCapability", ies.get("ueSecurityCapability"), expected_value="nea2_nia2")

    def validate_nas_authentication_request(self, message):
        message_name = "NAS Authentication Request"
        logger.info(f"Validating {message_name}")
        ies = extract_ies_from_message(message)
        validate_nas_message(message_name, ies)

        log_and_assert_ie("nasMessageType", ies.get("nasMessageType"), expected_value="Authentication Request")
        log_and_assert_ie("authenticationParameterRAND", ies.get("authenticationParameterRAND"), expected_value="valid_rand")
        log_and_assert_ie("authenticationParameterAUTN", ies.get("authenticationParameterAUTN"), expected_value="valid_autn")

    def validate_nas_authentication_response(self, message):
        message_name = "NAS Authentication Response"
        logger.info(f"Validating {message_name}")
        ies = extract_ies_from_message(message)
        validate_nas_message(message_name, ies)

        log_and_assert_ie("nasMessageType", ies.get("nasMessageType"), expected_value="Authentication Response")
        log_and_assert_ie("authenticationParameterRES", ies.get("authenticationParameterRES"), expected_value="valid_res")

    def validate_nas_security_mode_command(self, message):
        message_name = "NAS Security Mode Command"
        logger.info(f"Validating {message_name}")
        ies = extract_ies_from_message(message)
        validate_nas_message(message_name, ies)

        log_and_assert_ie("nasMessageType", ies.get("nasMessageType"), expected_value="Security Mode Command")
        log_and_assert_ie("selectedAlgorithm", ies.get("selectedAlgorithm"), expected_value="nea2_nia2")
        log_and_assert_ie("nasSecurityContext", ies.get("nasSecurityContext"), expected_value="valid_context")

    def validate_nas_security_mode_complete(self, message):
        message_name = "NAS Security Mode Complete"
        logger.info(f"Validating {message_name}")
        ies = extract_ies_from_message(message)
        validate_nas_message(message_name, ies)

        log_and_assert_ie("nasMessageType", ies.get("nasMessageType"), expected_value="Security Mode Complete")
        log_and_assert_ie("nasSecurityContext", ies.get("nasSecurityContext"), expected_value="valid_context")

    def validate_nas_attach_accept(self, message):
        message_name = "NAS Attach Accept"
        logger.info(f"Validating {message_name}")
        ies = extract_ies_from_message(message)
        validate_nas_message(message_name, ies)

        log_and_assert_ie("nasMessageType", ies.get("nasMessageType"), expected_value="Attach Accept")
        log_and_assert_ie("guti", ies.get("guti"), expected_value="valid_guti")
        log_and_assert_ie("t3402", ies.get("t3402"), expected_value="60s")
        log_and_assert_ie("taiList", ies.get("taiList"), expected_value=["TAI1", "TAI2"])
        log_and_assert_ie("allowedNssai", ies.get("allowedNssai"), expected_value=["SST1", "SST2"])

    def validate_nas_attach_complete(self, message):
        message_name = "NAS Attach Complete"
        logger.info(f"Validating {message_name}")
        ies = extract_ies_from_message(message)
        validate_nas_message(message_name, ies)

        log_and_assert_ie("nasMessageType", ies.get("nasMessageType"), expected_value="Attach Complete")
        log_and_assert_ie("epsBearerContextStatus", ies.get("epsBearerContextStatus"), expected_value="active")

if __name__ == "__main__":
    unittest.main()
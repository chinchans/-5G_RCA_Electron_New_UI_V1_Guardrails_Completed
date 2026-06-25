```python
import logging
import time

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger("UEAttachDetachTest")

class UEAttachDetachTest:
    def __init__(self, ue_interface):
        """
        ue_interface: An abstraction to interact with UE and network,
                      providing methods to send/receive messages and control UE power.
        """
        self.ue = ue_interface
        self.attach_iterations = 10
        self.attach_latencies = []
        self.attach_success_count = 0
        self.detach_success_count = 0

    # --- Utility methods for timing and assertions ---

    def measure_latency(self, start_time, end_time):
        return end_time - start_time

    def assert_ie(self, ie_name, actual_value, expected_value):
        if actual_value != expected_value:
            logger.error(f"IE validation failed for {ie_name}: expected {expected_value}, got {actual_value}")
            raise AssertionError(f"IE validation failed for {ie_name}")
        logger.info(f"IE validated: {ie_name} = {actual_value}")

    def assert_true(self, condition, message):
        if not condition:
            logger.error(message)
            raise AssertionError(message)
        logger.info(message)

    # --- Message validation functions ---

    def validate_rrc_connection_request(self, msg):
        """
        Validate RRC Connection Request message IEs.
        Expected IEs:
          - ue_identity
          - establishment_cause
        """
        logger.info("Validating RRC Connection Request message")
        expected_ues = ["random_ue_id", "emergency", "mo_signalling", "mo_data", "mo_voice_call"]

        ue_identity = msg.get('ue_identity')
        self.assert_true(ue_identity is not None, "ue_identity IE must be present in RRC Connection Request")
        establishment_cause = msg.get('establishment_cause')
        self.assert_true(establishment_cause in expected_ues, f"Invalid establishment_cause: {establishment_cause}")
        self.assert_ie('ue_identity', ue_identity, ue_identity)  # Just presence check
        self.assert_ie('establishment_cause', establishment_cause, establishment_cause)

    def validate_rrc_connection_setup(self, msg):
        """
        Validate RRC Connection Setup message IEs.
        Expected IEs:
          - radio_resource_config
          - initial_security_id
        """
        logger.info("Validating RRC Connection Setup message")
        radio_resource_config = msg.get('radio_resource_config')
        self.assert_true(radio_resource_config is not None, "radio_resource_config IE must be present in RRC Connection Setup")
        initial_security_id = msg.get('initial_security_id')
        self.assert_true(initial_security_id in [0,1], "initial_security_id IE must be 0 or 1")
        self.assert_ie('initial_security_id', initial_security_id, initial_security_id)

    def validate_rrc_connection_setup_complete(self, msg):
        """
        Validate RRC Connection Setup Complete message IEs.
        Expected IEs:
          - nas_message_container (contains Attach Request)
        """
        logger.info("Validating RRC Connection Setup Complete message")
        nas_msg_container = msg.get('nas_message_container')
        self.assert_true(nas_msg_container is not None, "nas_message_container IE must be present in RRC Connection Setup Complete")
        self.assert_ie('nas_message_container', nas_msg_container, nas_msg_container)

    def validate_nas_attach_request(self, msg):
        """
        Validate NAS Attach Request message IEs.
        Expected IEs:
          - eps_attach_type
          - nas_key_set_identifier
          - ue_network_capability
          - eps_mobile_identity (IMSI)
          - ue_radio_capability
        """
        logger.info("Validating NAS Attach Request message")
        eps_attach_type = msg.get('eps_attach_type')
        self.assert_true(eps_attach_type in [1,2,3], "Invalid eps_attach_type in NAS Attach Request")
        nas_key_set_identifier = msg.get('nas_key_set_identifier')
        self.assert_true(nas_key_set_identifier is not None, "nas_key_set_identifier must be present")
        ue_network_capability = msg.get('ue_network_capability')
        self.assert_true(ue_network_capability is not None, "ue_network_capability must be present")
        eps_mobile_identity = msg.get('eps_mobile_identity')
        self.assert_true(eps_mobile_identity is not None, "eps_mobile_identity (IMSI) must be present")
        ue_radio_capability = msg.get('ue_radio_capability')
        self.assert_true(ue_radio_capability is not None, "ue_radio_capability must be present")

    def validate_nas_authentication_request(self, msg):
        """
        Validate NAS Authentication Request message IEs.
        Expected IEs:
          - rand
          - autn
        """
        logger.info("Validating NAS Authentication Request message")
        rand = msg.get('rand')
        autn = msg.get('autn')
        self.assert_true(rand is not None, "rand must be present in NAS Authentication Request")
        self.assert_true(autn is not None, "autn must be present in NAS Authentication Request")

    def validate_nas_authentication_response(self, msg):
        """
        Validate NAS Authentication Response message IEs.
        Expected IEs:
          - res
        """
        logger.info("Validating NAS Authentication Response message")
        res = msg.get('res')
        self.assert_true(res is not None, "res must be present in NAS Authentication Response")

    def validate_nas_security_mode_command(self, msg):
        """
        Validate NAS Security Mode Command message IEs.
        Expected IEs:
          - selected_algorithms
          - nas_key_set_identifier
        """
        logger.info("Validating NAS Security Mode Command message")
        selected_algorithms = msg.get('selected_algorithms')
        nas_key_set_identifier = msg.get('nas_key_set_identifier')
        self.assert_true(selected_algorithms is not None, "selected_algorithms must be present")
        self.assert_true(nas_key_set_identifier is not None, "nas_key_set_identifier must be present")

    def validate_nas_security_mode_complete(self, msg):
        """
        Validate NAS Security Mode Complete message IEs.
        Expected IEs: none mandatory
        """
        logger.info("Validating NAS Security Mode Complete message")

    def validate_nas_attach_accept(self, msg):
        """
        Validate NAS Attach Accept message IEs.
        Expected IEs:
          - eps_attach_result
          - t3412_value
          - tai_list
          - apn_configuration_profile
        """
        logger.info("Validating NAS Attach Accept message")
        eps_attach_result = msg.get('eps_attach_result')
        self.assert_true(eps_attach_result == 1, "EPS Attach Result must be 1 (success)")
        t3412_value = msg.get('t3412_value')
        self.assert_true(t3412_value is not None, "t3412_value must be present")
        tai_list = msg.get('tai_list')
        self.assert_true(tai_list is not None and len(tai_list) > 0, "tai_list must be present and non-empty")
        apn_config_profile = msg.get('apn_configuration_profile')
        self.assert_true(apn_config_profile is not None, "apn_configuration_profile must be present")

    def validate_rrc_security_mode_command(self, msg):
        """
        Validate RRC Security Mode Command message IEs.
        Expected IEs:
          - selected_integrity_algorithm
          - selected_ciphering_algorithm
        """
        logger.info("Validating RRC Security Mode Command message")
        integrity_alg = msg.get('selected_integrity_algorithm')
        ciphering_alg = msg.get('selected_ciphering_algorithm')
        self.assert_true(integrity_alg is not None, "selected_integrity_algorithm must be present")
        self.assert_true(ciphering_alg is not None, "selected_ciphering_algorithm must be present")

    def validate_rrc_security_mode_complete(self, msg):
        """
        Validate RRC Security Mode Complete message IEs.
        Expected IEs: none mandatory
        """
        logger.info("Validating RRC Security Mode Complete message")

    def validate_rrc_ue_capability_information(self, msg):
        """
        Validate RRC UE Capability Information message IEs.
        Expected IEs:
          - ue_radio_capability
        """
        logger.info("Validating RRC UE Capability Information message")
        ue_radio_capability = msg.get('ue_radio_capability')
        self.assert_true(ue_radio_capability is not None, "ue_radio_capability must be present")

    def validate_rrc_ue_context_release_command(self, msg):
        """
        Validate RRC UE Context Release Command message IEs.
        Expected IEs:
          - release_cause
        """
        logger.info("Validating RRC UE Context Release Command message")
        release_cause = msg.get('release_cause')
        self.assert_true(release_cause in ['ue_initiated', 'network_initiated'], "Invalid release_cause")

    # --- Test procedure methods ---

    def perform_attach_iteration(self, iteration):
        logger.info(f"Starting attach iteration {iteration+1}")

        # 1. Start logs capture (abstracted)
        self.ue.start_logging(f"attach_iteration_{iteration+1}")

        # 2. Power ON UE
        self.ue.power_on()

        # 3. Measure attach latency start time
        attach_start_time = time.time()

        #
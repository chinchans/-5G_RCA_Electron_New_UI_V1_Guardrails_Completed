import time
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

class UEAttachTest:
    def __init__(self, ue_ids, network_config):
        """
        Initialize the test with UE identifiers and network configuration.
        :param ue_ids: list of UE identifiers
        :param network_config: dict containing test configuration parameters like cell IDs, ARFCN, etc.
        """
        self.ue_ids = ue_ids
        self.network_config = network_config
        self.attach_iterations = 10
        self.attach_results = {ue: {'success': 0, 'latencies': []} for ue in ue_ids}
        self.detach_results = {ue: {'success': 0} for ue in ue_ids}
        self.secondary_node_addition_results = {ue: {'success': 0} for ue in ue_ids}
        # Assume ue_attach_utils provides methods for triggering attach, detach and log extraction
        from ue_attach_utils import UEAttachUtils
        self.attach_utils = UEAttachUtils(self.network_config)

    def log_and_assert(self, condition, message):
        if condition:
            logging.info(message)
        else:
            logging.error(message)
            assert False, message

    def validate_rrc_connection_request(self, ue_id, msg):
        """
        Validate RRC Connection Request message IEs for given UE.
        :param ue_id: UE identifier
        :param msg: message dict containing IEs
        """
        logging.info(f"Validating RRC Connection Request for UE {ue_id}")

        # Validate Message Type
        self.log_and_assert(msg.get('message_type') == 'RRCConnectionRequest',
                            f"UE {ue_id}: RRC Connection Request message type mismatch")

        # Validate ue-Identity
        ue_identity = msg.get('ue_Identity')
        self.log_and_assert(ue_identity is not None,
                            f"UE {ue_id}: ue_Identity IE missing in RRC Connection Request")

        # Validate establishmentCause
        establishment_cause = msg.get('establishmentCause')
        expected_causes = ['mo-Signalling', 'mo-Data', 'emergency', 'mo-VoiceCall', 'mo-Register']
        self.log_and_assert(establishment_cause in expected_causes,
                            f"UE {ue_id}: establishmentCause IE invalid in RRC Connection Request")

    def validate_rrc_connection_setup(self, ue_id, msg):
        """
        Validate RRC Connection Setup message IEs.
        """
        logging.info(f"Validating RRC Connection Setup for UE {ue_id}")

        self.log_and_assert(msg.get('message_type') == 'RRCConnectionSetup',
                            f"UE {ue_id}: RRC Connection Setup message type mismatch")

        # Validate criticalExtensions including c1 and rrc-TransactionIdentifier
        crit_ext = msg.get('criticalExtensions')
        self.log_and_assert(crit_ext is not None,
                            f"UE {ue_id}: criticalExtensions IE missing in RRC Connection Setup")
        c1 = crit_ext.get('c1')
        self.log_and_assert(c1 is not None,
                            f"UE {ue_id}: c1 IE missing inside criticalExtensions")

        rrc_trans_id = c1.get('rrc-TransactionIdentifier')
        self.log_and_assert(rrc_trans_id is not None,
                            f"UE {ue_id}: rrc-TransactionIdentifier missing in c1")

        rrc_setup = c1.get('rrcConnectionSetup')
        self.log_and_assert(rrc_setup is not None,
                            f"UE {ue_id}: rrcConnectionSetup missing in c1")

        # Validate radioResourceConfigDedicated exists and is well-formed
        rrc_setup_cfg = rrc_setup.get('radioResourceConfigDedicated')
        self.log_and_assert(rrc_setup_cfg is not None,
                            f"UE {ue_id}: radioResourceConfigDedicated missing in rrcConnectionSetup")

    def validate_rrc_connection_setup_complete(self, ue_id, msg):
        """
        Validate RRC Connection Setup Complete message.
        """
        logging.info(f"Validating RRC Connection Setup Complete for UE {ue_id}")

        self.log_and_assert(msg.get('message_type') == 'RRCConnectionSetupComplete',
                            f"UE {ue_id}: RRC Connection Setup Complete message type mismatch")

        # Validate criticalExtensions and NAS PDU presence
        crit_ext = msg.get('criticalExtensions')
        self.log_and_assert(crit_ext is not None,
                            f"UE {ue_id}: criticalExtensions missing in RRC Connection Setup Complete")

        c1 = crit_ext.get('c1')
        self.log_and_assert(c1 is not None,
                            f"UE {ue_id}: c1 missing in criticalExtensions")

        rrc_setup_complete = c1.get('rrcConnectionSetupComplete')
        self.log_and_assert(rrc_setup_complete is not None,
                            f"UE {ue_id}: rrcConnectionSetupComplete missing in c1")

        # Validate NAS PDU presence
        nas_pdu = rrc_setup_complete.get('nas-PDU')
        self.log_and_assert(nas_pdu is not None and len(nas_pdu) > 0,
                            f"UE {ue_id}: NAS PDU missing or empty in RRC Connection Setup Complete")

    def validate_nas_attach_request(self, ue_id, nas_msg):
        """
        Validate NAS Attach Request message IEs.
        """
        logging.info(f"Validating NAS Attach Request for UE {ue_id}")

        # Check message type
        self.log_and_assert(nas_msg.get('message_type') == 'AttachRequest',
                            f"UE {ue_id}: NAS message is not AttachRequest")

        # Check EPS attach type IE
        eps_attach_type = nas_msg.get('eps_attach_type')
        valid_types = ['EPS_ATTACH_TYPE_EPS', 'EPS_ATTACH_TYPE_COMBINED_EPS_IMSI']
        self.log_and_assert(eps_attach_type in valid_types,
                            f"UE {ue_id}: Invalid EPS attach type {eps_attach_type}")

        # Check UE network capability IE present
        ue_net_cap = nas_msg.get('ue_network_capability')
        self.log_and_assert(ue_net_cap is not None,
                            f"UE {ue_id}: UE Network Capability IE missing")

        # Check Additional IEs can be added as per spec if available

    def validate_nas_attach_accept(self, ue_id, nas_msg):
        """
        Validate NAS Attach Accept message IEs.
        """
        logging.info(f"Validating NAS Attach Accept for UE {ue_id}")

        self.log_and_assert(nas_msg.get('message_type') == 'AttachAccept',
                            f"UE {ue_id}: NAS message is not AttachAccept")

        # Check T3412 timer IE presence and valid value
        t3412 = nas_msg.get('t3412_value')
        self.log_and_assert(t3412 is not None,
                            f"UE {ue_id}: T3412 timer IE missing in Attach Accept")

        # Check ESM message container presence if any
        esm_msg = nas_msg.get('esm_message_container')
        self.log_and_assert(esm_msg is not None,
                            f"UE {ue_id}: ESM message container missing in Attach Accept")

    def validate_rrc_security_mode_command(self, ue_id, msg):
        """
        Validate RRC Security Mode Command message.
        """
        logging.info(f"Validating RRC Security Mode Command for UE {ue_id}")

        self.log_and_assert(msg.get('message_type') == 'SecurityModeCommand',
                            f"UE {ue_id}: Message is not SecurityModeCommand")

        crit_ext = msg.get('criticalExtensions')
        self.log_and_assert(crit_ext is not None,
                            f"UE {ue_id}: criticalExtensions missing")

        c1 = crit_ext.get('c1')
        self.log_and_assert(c1 is not None,
                            f"UE {ue_id}: c1 missing in criticalExtensions")

        security_mode_cmd = c1.get('securityModeCommand')
        self.log_and_assert(security_mode_cmd is not None,
                            f"UE {ue_id}: securityModeCommand missing in c1")

        # Validate security algorithms and parameters
        selected_algorithms = security_mode_cmd.get('selectedAlgorithm')
        self.log_and_assert(selected_algorithms is not None,
                            f"UE {ue_id}: selectedAlgorithm missing in securityModeCommand")

    def validate_rrc_security_mode_complete(self, ue_id, msg):
        """
        Validate RRC Security Mode Complete message.
        """
        logging.info(f"Validating RRC Security Mode Complete for UE {ue_id}")

        self.log_and_assert(msg.get('message_type') == 'SecurityModeComplete',
                            f"UE {ue_id}: Message is not SecurityModeComplete")

        crit_ext = msg.get('criticalExtensions')
        self.log_and_assert(crit_ext is not None,
                            f"UE {ue_id}: criticalExtensions missing")

        c1 = crit_ext.get('c1')
        self.log_and_assert(c1 is not None,
                            f"UE {ue_id}: c1 missing in criticalExtensions")

        security_mode_complete = c1.get('securityModeComplete')
        self.log_and_assert(security_mode_complete is not None,
                            f"UE {ue_id}: securityModeComplete missing in c1")

    def validate_rrc_ue_capability_enquiry(self, ue_id, msg):
        """
        Validate RRC UE Capability Enquiry message.
        """
        logging.info(f"Validating RRC UE Capability Enquiry for UE {ue_id}")

        self.log_and_assert
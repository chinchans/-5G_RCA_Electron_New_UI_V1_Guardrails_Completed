import logging

class UEAttachTest:
    def __init__(self, ue_attach_utils):
        self.ue_attach_utils = ue_attach_utils
        self.logger = logging.getLogger("UEAttachTest")
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    def run_attach_procedure(self):
        self.logger.info("Starting UE attach procedure.")
        attach_status = self.ue_attach_utils.trigger_ue_attach()
        assert attach_status == True, "UE Attach failed to start correctly."
        self.logger.info("UE attach triggered successfully.")

        self.validate_rrc_setup_request(self.ue_attach_utils.get_rrc_setup_request())
        self.validate_rrc_setup_response(self.ue_attach_utils.get_rrc_setup_response())
        self.validate_rrc_setup_complete(self.ue_attach_utils.get_rrc_setup_complete())
        self.validate_nas_attach_request(self.ue_attach_utils.get_nas_attach_request())
        self.validate_nas_authentication_request(self.ue_attach_utils.get_nas_authentication_request())
        self.validate_nas_authentication_response(self.ue_attach_utils.get_nas_authentication_response())
        self.validate_nas_security_mode_command(self.ue_attach_utils.get_nas_security_mode_command())
        self.validate_nas_security_mode_complete(self.ue_attach_utils.get_nas_security_mode_complete())
        self.validate_nas_attach_accept(self.ue_attach_utils.get_nas_attach_accept())
        self.validate_rrc_reconfiguration(self.ue_attach_utils.get_rrc_reconfiguration())
        self.validate_rrc_reconfiguration_complete(self.ue_attach_utils.get_rrc_reconfiguration_complete())
        self.validate_nas_attach_complete(self.ue_attach_utils.get_nas_attach_complete())

        self.logger.info("UE attach procedure completed successfully.")

    def validate_rrc_setup_request(self, msg):
        self.logger.info("Validating RRC Setup Request message.")
        assert msg['message_type'] == 'RRCSetupRequest', "Incorrect message type."
        assert 'ue_identity' in msg, "Missing UE Identity IE."
        assert isinstance(msg['ue_identity'], str) and len(msg['ue_identity']) > 0, "Invalid UE Identity IE."
        self.logger.info("RRC Setup Request IEs validated successfully.")

    def validate_rrc_setup_response(self, msg):
        self.logger.info("Validating RRC Setup Response message.")
        assert msg['message_type'] == 'RRCSetup', "Incorrect message type."
        assert 'rrc_transaction_id' in msg, "Missing RRC Transaction ID IE."
        assert isinstance(msg['rrc_transaction_id'], int), "Invalid RRC Transaction ID IE."
        assert 'master_cell_group' in msg, "Missing Master Cell Group IE."
        mcg = msg['master_cell_group']
        assert 'sp_cell_id' in mcg, "Missing SpCell ID in Master Cell Group."
        assert 'phy_config' in mcg, "Missing Physical Config in Master Cell Group."
        self.logger.info("RRC Setup Response IEs validated successfully.")

    def validate_rrc_setup_complete(self, msg):
        self.logger.info("Validating RRC Setup Complete message.")
        assert msg['message_type'] == 'RRCSetupComplete', "Incorrect message type."
        assert 'nas_message_container' in msg, "Missing NAS Message Container IE."
        nas_msg = msg['nas_message_container']
        assert nas_msg['message_type'] == 'AttachRequest', "Unexpected NAS message inside RRC Setup Complete."
        self.logger.info("RRC Setup Complete IEs validated successfully.")

    def validate_nas_attach_request(self, msg):
        self.logger.info("Validating NAS Attach Request message.")
        assert msg['message_type'] == 'AttachRequest', "Incorrect message type."
        assert 'eps_attach_type' in msg, "Missing EPS Attach Type IE."
        assert msg['eps_attach_type'] in ['EPS Attach', 'Emergency Attach'], "Invalid EPS Attach Type IE."
        assert 'ue_network_capability' in msg, "Missing UE Network Capability IE."
        unc = msg['ue_network_capability']
        assert 'encryption_algorithms' in unc, "Missing Encryption Algorithms in UE Network Capability."
        assert 'integrity_algorithms' in unc, "Missing Integrity Algorithms in UE Network Capability."
        assert 'nas_message_container' not in msg, "NAS Message Container should not be present in Attach Request."
        self.logger.info("NAS Attach Request IEs validated successfully.")

    def validate_nas_authentication_request(self, msg):
        self.logger.info("Validating NAS Authentication Request message.")
        assert msg['message_type'] == 'AuthenticationRequest', "Incorrect message type."
        assert 'rand' in msg, "Missing RAND IE."
        assert isinstance(msg['rand'], bytes) and len(msg['rand']) == 16, "Invalid RAND IE."
        assert 'autn' in msg, "Missing AUTN IE."
        assert isinstance(msg['autn'], bytes) and len(msg['autn']) == 16, "Invalid AUTN IE."
        self.logger.info("NAS Authentication Request IEs validated successfully.")

    def validate_nas_authentication_response(self, msg):
        self.logger.info("Validating NAS Authentication Response message.")
        assert msg['message_type'] == 'AuthenticationResponse', "Incorrect message type."
        assert 'res' in msg, "Missing RES IE."
        res = msg['res']
        assert isinstance(res, bytes) and len(res) > 0, "Invalid RES IE."
        self.logger.info("NAS Authentication Response IEs validated successfully.")

    def validate_nas_security_mode_command(self, msg):
        self.logger.info("Validating NAS Security Mode Command message.")
        assert msg['message_type'] == 'SecurityModeCommand', "Incorrect message type."
        assert 'selected_integrity_algorithm' in msg, "Missing Selected Integrity Algorithm IE."
        assert 'selected_ciphering_algorithm' in msg, "Missing Selected Ciphering Algorithm IE."
        assert 'nas_security_capability' in msg, "Missing NAS Security Capability IE."
        self.logger.info("NAS Security Mode Command IEs validated successfully.")

    def validate_nas_security_mode_complete(self, msg):
        self.logger.info("Validating NAS Security Mode Complete message.")
        assert msg['message_type'] == 'SecurityModeComplete', "Incorrect message type."
        self.logger.info("NAS Security Mode Complete IEs validated successfully.")

    def validate_nas_attach_accept(self, msg):
        self.logger.info("Validating NAS Attach Accept message.")
        assert msg['message_type'] == 'AttachAccept', "Incorrect message type."
        assert 'emergency_number_list' in msg, "Missing Emergency Number List IE."
        assert 'guti' in msg, "Missing GUTI IE."
        guti = msg['guti']
        assert 'mcc' in guti and 'mnc' in guti, "Missing MCC or MNC in GUTI."
        assert 't3412_value' in msg, "Missing T3412 Value IE."
        self.logger.info("NAS Attach Accept IEs validated successfully.")

    def validate_rrc_reconfiguration(self, msg):
        self.logger.info("Validating RRC Reconfiguration message.")
        assert msg['message_type'] == 'RRCReconfiguration', "Incorrect message type."
        assert 'meas_config' in msg, "Missing Measurement Configuration IE."
        assert 'radio_bearer_config' in msg, "Missing Radio Bearer Configuration IE."
        self.logger.info("RRC Reconfiguration IEs validated successfully.")

    def validate_rrc_reconfiguration_complete(self, msg):
        self.logger.info("Validating RRC Reconfiguration Complete message.")
        assert msg['message_type'] == 'RRCReconfigurationComplete', "Incorrect message type."
        self.logger.info("RRC Reconfiguration Complete IEs validated successfully.")

    def validate_nas_attach_complete(self, msg):
        self.logger.info("Validating NAS Attach Complete message.")
        assert msg['message_type'] == 'AttachComplete', "Incorrect message type."
        self.logger.info("NAS Attach Complete IEs validated successfully.")


if __name__ == "__main__":
    from ue_attach_utils import UEAttachUtils

    ue_attach_utils = UEAttachUtils()
    test = UEAttachTest(ue_attach_utils)
    test.run_attach_procedure()
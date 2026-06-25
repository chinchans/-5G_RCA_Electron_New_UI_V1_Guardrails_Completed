import logging
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')


class UEAttachTestAutomation:
    def __init__(self, ue_attach_utils):
        self.utils = ue_attach_utils
        self.logger = logging.getLogger("UEAttachTestAutomation")

    def trigger_ue_attach(self):
        self.logger.info("Triggering UE Attach Procedure")
        attach_response = self.utils.trigger_attach()
        assert attach_response is not None, "Attach trigger failed - no response"
        self.logger.info("UE Attach triggered successfully")
        return attach_response

    def validate_rrc_connection_request(self, rrc_msg):
        self.logger.info("Validating RRC Connection Request message")
        # Extract and validate IEs
        ue_identity = rrc_msg.get('ue_Identity')
        establishment_cause = rrc_msg.get('establishmentCause')

        assert ue_identity is not None, "Missing UE Identity IE"
        assert establishment_cause in ['mo-Signalling', 'mo-Data', 'mo-VoiceCall', 'mo-VideoCall',
                                       'mt-Access', 'delay-tolerant', 'mo-Signalling'], \
            f"Invalid establishmentCause IE: {establishment_cause}"

        self.logger.info(f"RRC Connection Request IE - UE Identity: {ue_identity}")
        self.logger.info(f"RRC Connection Request IE - Establishment Cause: {establishment_cause}")
        self.logger.info("RRC Connection Request message validated successfully")

    def validate_rrc_connection_setup(self, rrc_msg):
        self.logger.info("Validating RRC Connection Setup message")
        rb_config = rrc_msg.get('radioBearerConfig')
        security_config = rrc_msg.get('securityConfig')

        assert rb_config is not None, "Missing Radio Bearer Configuration IE"
        assert security_config is not None, "Missing Security Configuration IE"

        self.logger.info(f"RRC Connection Setup IE - Radio Bearer Config: {rb_config}")
        self.logger.info(f"RRC Connection Setup IE - Security Config: {security_config}")
        self.logger.info("RRC Connection Setup message validated successfully")

    def validate_rrc_connection_setup_complete(self, rrc_msg):
        self.logger.info("Validating RRC Connection Setup Complete message")
        nas_pdu = rrc_msg.get('nasPdu')
        assert nas_pdu is not None, "Missing NAS PDU IE"
        self.logger.info("RRC Connection Setup Complete message validated successfully")

    def validate_nas_attach_request(self, nas_msg):
        self.logger.info("Validating NAS Attach Request message")
        eps_attach_type = nas_msg.get('epsAttachType')
        nas_key_set_id = nas_msg.get('nasKeySetIdentifier')
        ue_network_capability = nas_msg.get('ueNetworkCapability')
        auth_params = nas_msg.get('authenticationParameters')

        assert eps_attach_type in ['EPS Attach', 'Combined EPS/IMSI Attach'], \
            f"Invalid EPS Attach Type: {eps_attach_type}"
        assert nas_key_set_id is not None, "Missing NAS Key Set Identifier"
        assert ue_network_capability is not None, "Missing UE Network Capability"
        # authenticationParameters IE can be optional in some cases
        self.logger.info(f"NAS Attach Request IE - EPS Attach Type: {eps_attach_type}")
        self.logger.info(f"NAS Attach Request IE - NAS Key Set Identifier: {nas_key_set_id}")
        self.logger.info(f"NAS Attach Request IE - UE Network Capability: {ue_network_capability}")
        self.logger.info("NAS Attach Request message validated successfully")

    def validate_nas_authentication_request(self, nas_msg):
        self.logger.info("Validating NAS Authentication Request message")
        rand = nas_msg.get('rand')
        autn = nas_msg.get('autn')

        assert rand is not None and len(rand) == 16, "Invalid or missing RAND IE"
        assert autn is not None and len(autn) == 16, "Invalid or missing AUTN IE"

        self.logger.info(f"NAS Authentication Request IE - RAND: {rand.hex()}")
        self.logger.info(f"NAS Authentication Request IE - AUTN: {autn.hex()}")
        self.logger.info("NAS Authentication Request message validated successfully")

    def validate_nas_authentication_response(self, nas_msg):
        self.logger.info("Validating NAS Authentication Response message")
        res = nas_msg.get('res')

        assert res is not None, "Missing RES IE"
        self.logger.info(f"NAS Authentication Response IE - RES: {res.hex()}")
        self.logger.info("NAS Authentication Response message validated successfully")

    def validate_nas_security_mode_command(self, nas_msg):
        self.logger.info("Validating NAS Security Mode Command message")
        selected_algorithms = nas_msg.get('selectedAlgorithms')
        nas_count = nas_msg.get('nasCount')

        assert selected_algorithms is not None, "Missing selected algorithms IE"
        assert nas_count is not None, "Missing NAS count IE"

        self.logger.info(f"NAS Security Mode Command IE - Selected Algorithms: {selected_algorithms}")
        self.logger.info(f"NAS Security Mode Command IE - NAS Count: {nas_count}")
        self.logger.info("NAS Security Mode Command message validated successfully")

    def validate_nas_security_mode_complete(self, nas_msg):
        self.logger.info("Validating NAS Security Mode Complete message")
        # No mandatory IEs except message type and security header
        self.logger.info("NAS Security Mode Complete message validated successfully")

    def validate_nas_esm_information_request(self, nas_msg):
        self.logger.info("Validating NAS ESM Information Request message")
        # ESM Information Request message normally has no IEs except message type
        self.logger.info("NAS ESM Information Request message validated successfully")

    def validate_nas_esm_information_response(self, nas_msg):
        self.logger.info("Validating NAS ESM Information Response message")
        apn = nas_msg.get('apn')
        ip_address = nas_msg.get('ipAddress')

        assert apn is not None, "Missing APN IE"
        # IP address may be IPv4 or IPv6 or none
        self.logger.info(f"NAS ESM Information Response IE - APN: {apn}")
        self.logger.info(f"NAS ESM Information Response IE - IP Address: {ip_address}")
        self.logger.info("NAS ESM Information Response message validated successfully")

    def validate_nas_attach_accept(self, nas_msg):
        self.logger.info("Validating NAS Attach Accept message")
        eps_mobile_identity = nas_msg.get('epsMobileIdentity')
        esm_message_container = nas_msg.get('esmMessageContainer')
        tai_list = nas_msg.get('taiList')
        guti = nas_msg.get('guti')

        assert eps_mobile_identity is not None, "Missing EPS Mobile Identity IE"
        assert esm_message_container is not None, "Missing ESM Message Container IE"
        # TAI list can be optional in some cases
        self.logger.info(f"NAS Attach Accept IE - EPS Mobile Identity: {eps_mobile_identity}")
        self.logger.info(f"NAS Attach Accept IE - ESM Message Container: {esm_message_container}")
        if tai_list:
            self.logger.info(f"NAS Attach Accept IE - TAI List: {tai_list}")
        if guti:
            self.logger.info(f"NAS Attach Accept IE - GUTI: {guti}")
        self.logger.info("NAS Attach Accept message validated successfully")

    def validate_rrc_security_mode_command(self, rrc_msg):
        self.logger.info("Validating RRC Security Mode Command message")
        security_algo = rrc_msg.get('securityAlgorithm')
        integrity_algo = rrc_msg.get('integrityAlgorithm')

        assert security_algo is not None, "Missing Security Algorithm IE"
        assert integrity_algo is not None, "Missing Integrity Algorithm IE"
        self.logger.info(f"RRC Security Mode Command IE - Security Algorithm: {security_algo}")
        self.logger.info(f"RRC Security Mode Command IE - Integrity Algorithm: {integrity_algo}")
        self.logger.info("RRC Security Mode Command message validated successfully")

    def validate_rrc_security_mode_complete(self, rrc_msg):
        self.logger.info("Validating RRC Security Mode Complete message")
        # Normally no IE except confirmation message type
        self.logger.info("RRC Security Mode Complete message validated successfully")

    def validate_rrc_ue_capability_information(self, rrc_msg):
        self.logger.info("Validating RRC UE Capability Information message")
        ue_capabilities = rrc_msg.get('ueCapabilities')
        assert ue_capabilities is not None, "Missing UE Capabilities IE"
        self.logger.info(f"RRC UE Capability Information IE - Capabilities: {ue_capabilities}")
        self.logger.info("RRC UE Capability Information message validated successfully")

    def validate_nas_attach_complete(self, nas_msg):
        self.logger.info("Validating NAS Attach Complete message")
        # Attach Complete message normally has no mandatory IEs except message type and security header
        self.logger.info("NAS Attach Complete message validated successfully")

    def validate_rrc_ue_context_release_command(self, rrc_msg):
        self.logger.info("Validating RRC UE Context Release Command message")
        release_cause = rrc_msg.get('releaseCause')
        assert release_cause is not None, "Missing Release Cause IE"
        self.logger.info(f"RRC UE Context Release Command IE - Release Cause: {release_cause}")
        self.logger.info("RRC UE Context Release Command message validated successfully")

    def run_full_attach_test(self):
        # Trigger
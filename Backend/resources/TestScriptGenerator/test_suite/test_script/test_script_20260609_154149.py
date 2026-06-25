import logging

class UEAttachTest:
    def __init__(self, ue_attach_utils):
        self.ue_attach_utils = ue_attach_utils
        self.logger = logging.getLogger("UEAttachTest")
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    def trigger_attach_procedure(self):
        self.logger.info("Triggering UE Attach Procedure...")
        attach_response = self.ue_attach_utils.initiate_attach()
        assert attach_response is not None, "Attach initiation failed: no response"
        self.logger.info("Attach procedure triggered successfully.")
        return attach_response

    def validate_rrc_setup_request(self, rrc_message):
        self.logger.info("Validating RRC Setup Request message and IEs...")
        # Extract IEs
        ies = rrc_message.get_information_elements()
        # Validate IE: ue_identity
        ue_identity = ies.get("ue_identity")
        assert ue_identity is not None, "Missing UE Identity IE"
        assert isinstance(ue_identity, str) and len(ue_identity) > 0, "UE Identity IE invalid"
        self.logger.info(f"UE Identity IE validated: {ue_identity}")
        # Validate IE: establishment_cause
        est_cause = ies.get("establishment_cause")
        assert est_cause in ["mo-signalling", "mo-data", "mt-access", "mo-voice-call", "mo-ims-call"], "Invalid Establishment Cause IE"
        self.logger.info(f"Establishment Cause IE validated: {est_cause}")

    def validate_rrc_setup(self, rrc_message):
        self.logger.info("Validating RRC Setup message and IEs...")
        ies = rrc_message.get_information_elements()
        # IE: radio_bearer_config
        rb_config = ies.get("radio_bearer_config")
        assert rb_config is not None and isinstance(rb_config, dict), "Missing or invalid Radio Bearer Config IE"
        self.logger.info(f"Radio Bearer Config IE validated: {rb_config}")
        # IE: meas_config (optional)
        meas_config = ies.get("meas_config")
        if meas_config:
            assert isinstance(meas_config, dict), "Invalid Measurement Config IE"
            self.logger.info(f"Measurement Config IE validated: {meas_config}")

    def validate_rrc_setup_complete(self, rrc_message):
        self.logger.info("Validating RRC Setup Complete message and IEs...")
        ies = rrc_message.get_information_elements()
        # IE: selected_plmn_identity
        plmn_id = ies.get("selected_plmn_identity")
        assert plmn_id is not None and len(plmn_id) == 3, "Invalid Selected PLMN Identity IE"
        self.logger.info(f"Selected PLMN Identity IE validated: {plmn_id}")
        # IE: dedicated_nas_message
        nas_msg = ies.get("dedicated_nas_message")
        assert nas_msg is not None and isinstance(nas_msg, bytes) and len(nas_msg) > 0, "Invalid Dedicated NAS Message IE"
        self.logger.info(f"Dedicated NAS Message IE validated with length {len(nas_msg)}")

    def validate_nas_attach_request(self, nas_message):
        self.logger.info("Validating NAS Attach Request message and IEs...")
        ies = nas_message.get_information_elements()
        # IE: mobile_identity
        mobile_id = ies.get("mobile_identity")
        assert mobile_id is not None and isinstance(mobile_id, str) and len(mobile_id) > 0, "Invalid Mobile Identity IE"
        self.logger.info(f"Mobile Identity IE validated: {mobile_id}")
        # IE: ue_network_capability
        ue_net_cap = ies.get("ue_network_capability")
        assert ue_net_cap is not None and isinstance(ue_net_cap, dict), "UE Network Capability IE missing or invalid"
        self.logger.info(f"UE Network Capability IE validated: {ue_net_cap}")
        # IE: esm_message_container (optional)
        esm_msg = ies.get("esm_message_container")
        if esm_msg:
            assert isinstance(esm_msg, bytes) and len(esm_msg) > 0, "Invalid ESM Message Container IE"
            self.logger.info(f"ESM Message Container IE validated with length {len(esm_msg)}")

    def validate_nas_authentication_request(self, nas_message):
        self.logger.info("Validating NAS Authentication Request message and IEs...")
        ies = nas_message.get_information_elements()
        # IE: rand
        rand = ies.get("rand")
        assert rand is not None and isinstance(rand, bytes) and len(rand) == 16, "Invalid RAND IE"
        self.logger.info(f"RAND IE validated: {rand.hex()}")
        # IE: autn
        autn = ies.get("autn")
        assert autn is not None and isinstance(autn, bytes) and len(autn) == 16, "Invalid AUTN IE"
        self.logger.info(f"AUTN IE validated: {autn.hex()}")

    def validate_nas_authentication_response(self, nas_message):
        self.logger.info("Validating NAS Authentication Response message and IEs...")
        ies = nas_message.get_information_elements()
        # IE: res
        res = ies.get("res")
        assert res is not None and isinstance(res, bytes) and len(res) > 0, "Invalid RES IE"
        self.logger.info(f"RES IE validated with length {len(res)}")

    def validate_nas_security_mode_command(self, nas_message):
        self.logger.info("Validating NAS Security Mode Command message and IEs...")
        ies = nas_message.get_information_elements()
        # IE: selected_nas_security_algo
        sec_algo = ies.get("selected_nas_security_algo")
        assert sec_algo in ["NEA0", "NEA1", "NEA2"], "Invalid NAS Security Algorithm IE"
        self.logger.info(f"Selected NAS Security Algorithm IE validated: {sec_algo}")
        # IE: selected_nas_integrity_algo
        integ_algo = ies.get("selected_nas_integrity_algo")
        assert integ_algo in ["NIA0", "NIA1", "NIA2"], "Invalid NAS Integrity Algorithm IE"
        self.logger.info(f"Selected NAS Integrity Algorithm IE validated: {integ_algo}")

    def validate_nas_security_mode_complete(self, nas_message):
        self.logger.info("Validating NAS Security Mode Complete message and IEs...")
        ies = nas_message.get_information_elements()
        # IE: spare_half_octet (should be zero)
        spare = ies.get("spare_half_octet")
        assert spare == 0, "Spare half octet must be zero"
        self.logger.info("Spare half octet validated as zero")

    def validate_nas_attach_accept(self, nas_message):
        self.logger.info("Validating NAS Attach Accept message and IEs...")
        ies = nas_message.get_information_elements()
        # IE: emm_cause
        emm_cause = ies.get("emm_cause")
        assert emm_cause == 0, "EMM Cause IE must be 0 (success)"
        self.logger.info(f"EMM Cause IE validated: {emm_cause}")
        # IE: t3412_value
        t3412 = ies.get("t3412_value")
        assert isinstance(t3412, int) and t3412 >= 0, "Invalid T3412 Value IE"
        self.logger.info(f"T3412 Value IE validated: {t3412}")
        # IE: esm_message_container
        esm_msg = ies.get("esm_message_container")
        assert esm_msg is not None and isinstance(esm_msg, bytes), "ESM Message Container IE missing or invalid"
        self.logger.info(f"ESM Message Container IE validated with length {len(esm_msg)}")

    def validate_nas_esm_information_request(self, nas_message):
        self.logger.info("Validating NAS ESM Information Request message and IEs...")
        ies = nas_message.get_information_elements()
        # IE: esm_information_type
        esm_info_type = ies.get("esm_information_type")
        assert esm_info_type in ["requested_PDN_address", "requested_PDN_type"], "Invalid ESM Information Type IE"
        self.logger.info(f"ESM Information Type IE validated: {esm_info_type}")

    def validate_nas_esm_information_response(self, nas_message):
        self.logger.info("Validating NAS ESM Information Response message and IEs...")
        ies = nas_message.get_information_elements()
        # IE: apn
        apn = ies.get("apn")
        assert apn is not None and isinstance(apn, str) and len(apn) > 0, "Invalid APN IE"
        self.logger.info(f"APN IE validated: {apn}")

    def validate_nas_attach_complete(self, nas_message):
        self.logger.info("Validating NAS Attach Complete message and IEs...")
        ies = nas_message.get_information_elements()
        # IE: spare_half_octet
        spare = ies.get("spare_half_octet")
        assert spare == 0, "Spare half octet must be zero"
        self.logger.info("Spare half octet validated as zero")

    def run_attach_test(self):
        # Trigger attach procedure
        attach_resp = self.trigger_attach_procedure()

        # RRC Setup Request
        rrc_setup_req = self.ue_attach_utils.get_message("RRCSetupRequest")
        self.validate_rrc_setup_request(rrc_setup_req)

        # RRC Setup
        r
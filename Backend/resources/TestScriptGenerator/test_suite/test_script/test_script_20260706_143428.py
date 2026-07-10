import logging
import time

# Setup logger
logger = logging.getLogger("UEAttachTest")
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)


class UEAttachTest:
    """
    # TC_POS_001: LTE/5G NSA attach and detach of single UE
    """

    def __init__(self, ue_attach_utils, test_config):
        """
        Initialize with utilities for attach and test configuration parameters.
        :param ue_attach_utils: Utility instance providing attach trigger and message parsing/validation
        :param test_config: Dictionary containing test parameters (PCI, eNB ID, ARFCN etc.)
        """
        self.ue_attach_utils = ue_attach_utils
        self.test_config = test_config
        self.attach_iterations = 10
        self.attach_latencies = []
        self.attach_success_count = 0
        self.detach_success_count = 0
        self.secondary_node_add_success_count = 0

    def trigger_attach(self):
        """
        Trigger UE attach using utility function.
        """
        logger.info("Triggering UE Power ON and attach procedure.")
        self.ue_attach_utils.power_on_ue()
        logger.debug("UE Power ON triggered.")

    def trigger_detach(self):
        """
        Trigger UE detach using utility function.
        """
        logger.info("Triggering UE Power OFF and detach procedure.")
        self.ue_attach_utils.power_off_ue()
        logger.debug("UE Power OFF triggered.")

    def validate_rrc_connection_request(self, msg):
        """
        Validate RRC Connection Request message and its IEs.
        """
        logger.info("Validating RRC Connection Request message.")
        assert 'ue_Identity' in msg, "Missing UE Identity IE in RRC Connection Request"
        assert 'establishmentCause' in msg, "Missing Establishment Cause IE in RRC Connection Request"
        logger.debug(f"UE Identity IE: {msg['ue_Identity']}")
        logger.debug(f"Establishment Cause IE: {msg['establishmentCause']}")

    def validate_rrc_connection_setup(self, msg):
        """
        Validate RRC Connection Setup message and its IEs.
        """
        logger.info("Validating RRC Connection Setup message.")
        cfg = msg.get('radioResourceConfig')
        assert cfg is not None, "Missing Radio Resource Config IE in RRC Connection Setup"
        # Validate critical IEs inside radioResourceConfig
        assert 'physicalConfigDedicated' in cfg, "Missing Physical Config Dedicated IE"
        assert 'macConfig' in cfg, "Missing MAC Config IE"
        logger.debug(f"Physical Config Dedicated: {cfg['physicalConfigDedicated']}")
        logger.debug(f"MAC Config: {cfg['macConfig']}")

    def validate_rrc_connection_setup_complete(self, msg):
        """
        Validate RRC Connection Setup Complete message and its IEs.
        """
        logger.info("Validating RRC Connection Setup Complete message.")
        nas_msg = msg.get('nasPdu')
        assert nas_msg is not None, "Missing NAS PDU IE in RRC Connection Setup Complete"
        logger.debug(f"NAS PDU length: {len(nas_msg)} bytes")

    def validate_attach_request(self, nas_msg):
        """
        Validate Attach Request NAS message and its IEs.
        """
        logger.info("Validating Attach Request NAS message.")
        assert nas_msg.get('messageType') == 'Attach Request', "NAS message is not Attach Request"
        # Validate mandatory IEs in Attach Request
        ie_required = ['ueIdentity', 'attachType', 'epsAttachType', 'ueNetworkCapability']
        for ie in ie_required:
            assert ie in nas_msg, f"Missing IE {ie} in Attach Request"
            logger.debug(f"{ie}: {nas_msg[ie]}")

    def validate_authentication_request(self, nas_msg):
        """
        Validate Authentication Request NAS message and its IEs.
        """
        logger.info("Validating Authentication Request NAS message.")
        assert nas_msg.get('messageType') == 'Authentication Request', "NAS message is not Authentication Request"
        rand = nas_msg.get('rand')
        autn = nas_msg.get('autn')
        assert rand is not None and autn is not None, "Missing RAND or AUTN in Authentication Request"
        logger.debug(f"RAND: {rand.hex()}")
        logger.debug(f"AUTN: {autn.hex()}")

    def validate_authentication_response(self, nas_msg):
        """
        Validate Authentication Response NAS message and its IEs.
        """
        logger.info("Validating Authentication Response NAS message.")
        assert nas_msg.get('messageType') == 'Authentication Response', "NAS message is not Authentication Response"
        res = nas_msg.get('res')
        assert res is not None, "Missing RES in Authentication Response"
        logger.debug(f"RES: {res.hex()}")

    def validate_security_mode_command(self, nas_msg):
        """
        Validate Security Mode Command NAS message and its IEs.
        """
        logger.info("Validating Security Mode Command NAS message.")
        assert nas_msg.get('messageType') == 'Security Mode Command', "NAS message is not Security Mode Command"
        security_algorithms = nas_msg.get('securityAlgorithms')
        assert security_algorithms is not None, "Missing security algorithms IE"
        logger.debug(f"Security Algorithms: {security_algorithms}")

    def validate_security_mode_complete(self, nas_msg):
        """
        Validate Security Mode Complete NAS message.
        """
        logger.info("Validating Security Mode Complete NAS message.")
        assert nas_msg.get('messageType') == 'Security Mode Complete', "NAS message is not Security Mode Complete"
        logger.debug("Security Mode Complete received successfully.")

    def validate_esm_information_request(self, nas_msg):
        """
        Validate ESM Information Request NAS message.
        """
        logger.info("Validating ESM Information Request NAS message.")
        assert nas_msg.get('messageType') == 'ESM Information Request', "NAS message is not ESM Information Request"
        logger.debug("ESM Information Request received.")

    def validate_esm_information_response(self, nas_msg):
        """
        Validate ESM Information Response NAS message.
        """
        logger.info("Validating ESM Information Response NAS message.")
        assert nas_msg.get('messageType') == 'ESM Information Response', "NAS message is not ESM Information Response"
        apn = nas_msg.get('apn')
        assert apn is not None, "Missing APN IE in ESM Information Response"
        logger.debug(f"APN: {apn}")

    def validate_attach_accept(self, nas_msg):
        """
        Validate Attach Accept NAS message and its IEs.
        """
        logger.info("Validating Attach Accept NAS message.")
        assert nas_msg.get('messageType') == 'Attach Accept', "NAS message is not Attach Accept"
        # Validate critical IEs in Attach Accept
        ie_required = ['emmCause', 't3412Value', 'guti', 'assignedIpAddress']
        for ie in ie_required:
            assert ie in nas_msg, f"Missing IE {ie} in Attach Accept"
            logger.debug(f"{ie}: {nas_msg[ie]}")

    def validate_rrc_security_mode_command(self, msg):
        """
        Validate RRC Security Mode Command message and its IEs.
        """
        logger.info("Validating RRC Security Mode Command message.")
        security_cfg = msg.get('securityConfig')
        assert security_cfg is not None, "Missing Security Config IE"
        logger.debug(f"Security Config: {security_cfg}")

    def validate_rrc_security_mode_complete(self, msg):
        """
        Validate RRC Security Mode Complete message.
        """
        logger.info("Validating RRC Security Mode Complete message.")
        assert msg.get('messageType') == 'RRC Security Mode Complete', "Invalid RRC message type"
        logger.debug("RRC Security Mode Complete received.")

    def validate_rrc_ue_capability_information(self, msg):
        """
        Validate RRC UE Capability Information message and its IEs.
        """
        logger.info("Validating RRC UE Capability Information message.")
        capabilities = msg.get('ueCapabilities')
        assert capabilities is not None, "Missing UE Capabilities IE"
        logger.debug(f"UE Capabilities: {capabilities}")

    def validate_rrc_ue_information_response(self, msg):
        """
        Validate RRC UE Information Response message.
        """
        logger.info("Validating RRC UE Information Response message.")
        info = msg.get('ueInformation')
        assert info is not None, "Missing UE Information IE"
        logger.debug(f"UE Information: {info}")

    def validate_rrc_measurement_report(self, msg):
        """
        Validate RRC Measurement Report message.
        """
        logger.info("Validating RRC Measurement Report message.")
        meas_results = msg.get('measurementResults')
        assert meas_results is not None, "Missing Measurement Results IE"
        logger.debug(f"Measurement Results: {meas_results}")

    def validate_secondary_node_addition(self, msg):
        """
        Validate Secondary Node Addition procedure messages per 3GPP TS 37.340 Clause 10.2.1.
        """
        logger.info("Validating Secondary Node Addition procedure messages.")
        # Validate SgNB Addition Request
        sgnb_req = msg.get('sgnbAdditionRequest')
        assert sgnb_req is not None, "Missing SgNB Addition Request IE"
        logger.debug(f"SgNB Addition Request: {sgnb_req}")
        # Validate SgNB Reconfiguration Complete
        sgnb_reconf = msg.get('sgnbReconfigurationComplete')
        assert sgnb_reconf is not None, "Missing SgNB Reconfiguration Complete IE"
        logger.debug(f"SgNB Reconfiguration Complete: {sgnb_reconf}")

    def validate_detach_request(self, nas_msg):
        """
        Validate Detach Request NAS message and its IEs.
        """
        logger.info("Validating Detach Request NAS message.")
        assert nas_msg.get('messageType') == 'Detach Request', "NAS message is not Detach Request"
        detach_type = nas_msg.get('detachType')
        assert detach_type is not None, "Missing Detach Type IE"
        logger.debug(f"Detach Type: {detach_type}")

    def validate_detach_accept(self, nas_msg):
        """
        Validate Detach Accept NAS message.
        """
        logger.info("Validating Detach Accept NAS message.")
        assert nas_msg.get('messageType') == 'Detach Accept', "NAS message is not Detach Accept"
        logger.debug("Detach Accept received.")

    def validate_rrc_connection_release(self, msg):
        """
        Validate RRC Connection Release message and its IEs.
        """
        logger.info("Validating RRC Connection Release message.")
        release_cause = msg.get('releaseCause')
        assert release_cause is not None, "Missing Release Cause IE"
        logger.debug(f"Release Cause: {release_cause}")

    def validate_ue_context_release(self, msg):
        """
        Validate UE Context Release message.
        """
        logger.info("Validating UE Context Release message.")
        context_release_cause = msg.get('cause')
        assert context_release_cause is not None, "Missing Cause IE in UE Context Release"
        logger.debug(f"Cause: {context_release_cause}")

    def run_attach_detach_test(self):
        """
        Execute attach-detach test for configured number of iterations.
        """
        logger.info(f"Starting attach-detach test for {self.attach_iterations} iterations.")
        for i in range(self.attach_iterations):
            logger.info(f"Iteration {i+1} starting.")
            start_time = time.time()
            self.trigger_attach()

            # Simulate and validate attach procedure messages sequence

            # 1. RRC Connection Request
            rrc_conn_req = self.ue_attach_utils.wait_for_message('RRCConnectionRequest')
            self.validate_rrc_connection_request(rrc_conn_req)

            # 2. RRC Connection Setup
            rrc_conn_setup = self.ue_attach_utils.wait_for_message('RRCConnectionSetup')
            self.validate_rrc_connection_setup(rrc_conn_setup)

            # 3. RRC Connection Setup Complete
            rrc_conn_setup_comp = self.ue_attach_utils.wait_for_message('RRCConnectionSetupComplete')
            self.validate_rrc_connection_setup_complete(rrc_conn_setup_comp)

            # Extract NAS Attach Request from the RRC Connection Setup Complete
            nas_attach_req = self.ue_attach_utils.extract_nas_message(rrc_conn_setup_comp)
            self.validate_attach_request(nas_attach_req)

            # 4. Authentication Request
            nas_auth_req = self.ue_attach_utils.wait_for_message('AuthenticationRequest')
            self.validate_authentication_request(nas_auth_req)

            # 5. Authentication Response
            nas_auth_resp = self.ue_attach_utils.wait_for_message('AuthenticationResponse')
            self.validate_authentication_response(nas_auth_resp)

            # 6. Security Mode Command
            nas_sec_mode_cmd = self.ue_attach_utils.wait_for_message('SecurityModeCommand')
            self.validate_security_mode_command(nas_sec_mode_cmd)

            # 7. Security Mode Complete
            nas_sec_mode_comp = self.ue_attach_utils.wait_for_message('SecurityModeComplete')
            self.validate_security_mode_complete(nas_sec_mode_comp)

            # 8. ESM Information Request (Optional)
            nas_esm_info_req = self.ue_attach_utils.wait_for_message('ESMInformationRequest', optional=True)
            if nas_esm_info_req is not None:
                self.validate_esm_information_request(nas_esm_info_req)
                # 9. ESM Information Response
                nas_esm_info_resp = self.ue_attach_utils.wait_for_message('ESMInformationResponse')
                self.validate_esm_information_response(nas_esm_info_resp)

            # 10. Attach Accept
            nas_attach_accept = self.ue_attach_utils.wait_for_message('AttachAccept')
            self.validate_attach_accept(nas_attach_accept)

            attach_latency = time.time() - start_time
            self.attach_latencies.append(attach_latency)
            self.attach_success_count += 1
            logger.info(f"Attach successful iteration {i+1}, latency {attach_latency:.3f} seconds.")

            # 11. RRC Security Mode Command
            rrc_sec_mode_cmd = self.ue_attach_utils.wait_for_message('RRCSecurityModeCommand')
            self.validate_rrc_security_mode_command(rrc_sec_mode_cmd)

            # 12. RRC Security Mode Complete
            rrc_sec_mode_comp = self.ue_attach_utils.wait_for_message('RRCSecurityModeComplete')
            self.validate_rrc_security_mode_complete(rrc_sec_mode_comp)

            # 13. RRC UE Capability Information
            rrc_ue_cap_info = self.ue_attach_utils.wait_for_message('RRCUECapabilityInformation')
            self.validate_rrc_ue_capability_information(rrc_ue_cap_info)

            # 14. RRC UE Information Response
            rrc_ue_info_resp = self.ue_attach_utils.wait_for_message('RRCUEInformationResponse')
            self.validate_rrc_ue_information_response(rrc_ue_info_resp)

            # 15. RRC Measurement Report
            rrc_meas_report = self.ue_attach_utils.wait_for_message('RRCMeasurementReport')
            self.validate_rrc_measurement_report(rrc_meas_report)

            # 16. Secondary Node Addition for 5G NSA
            sgnb_add_msg = self.ue_attach_utils.wait_for_message('SecondaryNodeAddition', optional=True)
            if sgnb_add_msg is not None:
                self.validate_secondary_node_addition(sgnb_add_msg)
                self.secondary_node_add_success_count += 1

            # Detach Procedure

            self.trigger_detach()

            # 17. Detach Request
            nas_detach_req = self.ue_attach_utils.wait_for_message('DetachRequest')
            self.validate_detach_request(nas_detach_req)

            # 18. Detach Accept
            nas_detach_accept = self.ue_attach_utils.wait_for_message('DetachAccept')
            self.validate_detach_accept(nas_detach_accept)

            # 19. RRC Connection Release
            rrc_conn_release = self.ue_attach_utils.wait_for_message('RRCConnectionRelease')
            self.validate_rrc_connection_release(rrc_conn_release)

            # 20. UE Context Release
            ue_ctx_release = self.ue_attach_utils.wait_for_message('UEContextRelease')
            self.validate_ue_context_release(ue_ctx_release)

            self.detach_success_count += 1
            logger.info(f"Detach successful iteration {i+1}.")

        self.summarize_results()

    def summarize_results(self):
        """
        Print and log summary of KPI results.
        """
        logger.info("Attach-Detach Test Summary:")
        logger.info(f"Total iterations: {self.attach_iterations}")
        logger.info(f"Attach Success Count: {self.attach_success_count}")
        logger.info(f"Detach Success Count: {self.detach_success_count}")
        logger.info(f"Secondary Node Addition Success Count: {self.secondary_node_add_success_count}")

        if self.attach_latencies:
            lat_sorted = sorted(self.attach_latencies)
            min_lat = lat_sorted[0]
            max_lat = lat_sorted[-1]
            avg_lat = sum(self.attach_latencies)/len(self.attach_latencies)
            logger.info(f"Attach Latency (s): min={min_lat:.3f}, avg={avg_lat:.3f}, max={max_lat:.3f}")
        else:
            logger.warning("No attach latencies recorded.")

        # Validate success rates against expected 100%
        attach_success_rate = (self.attach_success_count / self.attach_iterations) * 100
        detach_success_rate = (self.detach_success_count / self.attach_iterations) * 100
        secondary_node_add_rate = (self.secondary_node_add_success_count / self.attach_iterations) * 100

        logger.info(f"Attach Success Rate: {attach_success_rate:.1f}%")
        logger.info(f"Detach Success Rate: {detach_success_rate:.1f}%")
        logger.info(f"Secondary Node Addition Success Rate: {secondary_node_add_rate:.1f}%")

        assert attach_success_rate == 100, "Attach success rate below 100%"
        assert detach_success_rate == 100, "Detach success rate below 100%"
        # Secondary Node Addition may be optional, but if done must be 100%
        if self.secondary_node_add_success_count > 0:
            assert secondary_node_add_rate == 100, "Secondary Node Addition success rate below 100%"
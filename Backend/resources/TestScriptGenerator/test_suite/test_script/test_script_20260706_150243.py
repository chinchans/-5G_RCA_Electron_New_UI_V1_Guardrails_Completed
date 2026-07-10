import logging
import time

logger = logging.getLogger("UEAttachTest")
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

class UEAttachTest:
    # TC_POS_001: Validate successful LTE/5G NSA Attach and Detach of single UE

    def __init__(self, ue_interface, test_config):
        """
        ue_interface: object to interact with UE emulator or real UE
        test_config: dictionary containing test config params (PCI, eNB ID, ARFCN etc)
        """
        self.ue = ue_interface
        self.config = test_config
        self.attach_latencies = []
        self.attach_success_count = 0
        self.detach_success_count = 0
        self.secondary_node_add_success_count = 0

    def trigger_ue_power_on(self):
        logger.info("Powering ON the UE to start attach procedure")
        self.ue.power_on()
        logger.debug("UE power ON command sent")

    def trigger_ue_power_off(self):
        logger.info("Powering OFF the UE to start detach procedure")
        self.ue.power_off()
        logger.debug("UE power OFF command sent")

    def start_logging(self):
        logger.info("Starting logs to capture call flow and signalling messages")
        self.ue.start_logging()

    def stop_logging(self):
        logger.info("Stopping and saving logs")
        self.ue.stop_logging()
        self.ue.save_logs()

    def validate_rrc_connection_request(self, msg):
        logger.info("Validating RRCConnectionRequest message")
        # Validate message type
        assert msg['message_type'] == "RRCConnectionRequest", "Invalid message type"
        # Validate establishment cause IE
        assert 'establishmentCause' in msg, "establishmentCause IE missing"
        valid_causes = ['mo-Signalling', 'mo-Data', 'emergency', 'highPriorityAccess', 'mt-Access']
        assert msg['establishmentCause'] in valid_causes, f"Invalid establishmentCause: {msg['establishmentCause']}"
        logger.debug(f"RRCConnectionRequest establishmentCause: {msg['establishmentCause']}")
        logger.info("RRCConnectionRequest message validated successfully")

    def validate_rrc_connection_setup(self, msg):
        logger.info("Validating RRCConnectionSetup message")
        assert msg['message_type'] == "RRCConnectionSetup", "Invalid message type"
        # Validate radio resource config IE presence
        assert 'radioResourceConfigDedicated' in msg, "radioResourceConfigDedicated IE missing"
        rrc_cfg = msg['radioResourceConfigDedicated']
        # Validate some mandatory IE inside radioResourceConfigDedicated (example: pdcp_Config)
        assert 'pdcp_Config' in rrc_cfg, "pdcp_Config IE missing in radioResourceConfigDedicated"
        logger.debug(f"RRCConnectionSetup pdcp_Config: {rrc_cfg['pdcp_Config']}")
        logger.info("RRCConnectionSetup message validated successfully")

    def validate_rrc_connection_setup_complete(self, msg):
        logger.info("Validating RRCConnectionSetupComplete message")
        assert msg['message_type'] == "RRCConnectionSetupComplete", "Invalid message type"
        # Validate NAS PDU presence
        assert 'nasPdu' in msg, "nasPdu IE missing"
        nas_msg = msg['nasPdu']
        self.validate_attach_request(nas_msg)
        logger.info("RRCConnectionSetupComplete message validated successfully")

    def validate_attach_request(self, nas_msg):
        logger.info("Validating AttachRequest NAS message")
        assert nas_msg['message_type'] == "AttachRequest", "Invalid NAS message type"
        # Validate EPS attach type IE
        assert 'epsAttachType' in nas_msg, "epsAttachType IE missing"
        valid_attach_types = ['EPS_ATTACH_TYPE_EPS_ATTACH', 'EPS_ATTACH_TYPE_COMBINED_EPS_IMS_ATTACH']
        assert nas_msg['epsAttachType'] in valid_attach_types, f"Invalid epsAttachType: {nas_msg['epsAttachType']}"
        # Validate UE network capability IE
        assert 'ueNetworkCapability' in nas_msg, "ueNetworkCapability IE missing"
        ue_net_cap = nas_msg['ueNetworkCapability']
        assert isinstance(ue_net_cap, dict), "ueNetworkCapability must be a dict"
        # Example validate presence of EUTRAN capability IE fields
        assert 'ue_EUTRAN_Capabilities' in ue_net_cap, "ue_EUTRAN_Capabilities missing in ueNetworkCapability"
        logger.debug(f"AttachRequest epsAttachType: {nas_msg['epsAttachType']}")
        logger.debug(f"AttachRequest ueNetworkCapability fields: {list(ue_net_cap.keys())}")
        logger.info("AttachRequest NAS message validated successfully")

    def validate_attach_accept(self, nas_msg):
        logger.info("Validating AttachAccept NAS message")
        assert nas_msg['message_type'] == "AttachAccept", "Invalid NAS message type"
        # Validate EPS mobile identity IE presence
        assert 'epsMobileIdentity' in nas_msg, "epsMobileIdentity IE missing"
        eps_id = nas_msg['epsMobileIdentity']
        assert 'mme_ue_s1ap_id' in eps_id and 'gutiorimsi' in eps_id, "Required EPS mobile identity components missing"
        # Validate T3412 timer IE presence and validity
        assert 't3412Value' in nas_msg, "t3412Value IE missing"
        assert isinstance(nas_msg['t3412Value'], int), "t3412Value must be int"
        logger.debug(f"AttachAccept epsMobileIdentity: {eps_id}")
        logger.debug(f"AttachAccept T3412 timer: {nas_msg['t3412Value']}")
        logger.info("AttachAccept NAS message validated successfully")

    def validate_security_mode_command(self, nas_msg):
        logger.info("Validating SecurityModeCommand NAS message")
        assert nas_msg['message_type'] == "SecurityModeCommand", "Invalid NAS message type"
        # Validate security algorithms IE presence
        assert 'securityAlgorithms' in nas_msg, "securityAlgorithms IE missing"
        algorithms = nas_msg['securityAlgorithms']
        assert set(algorithms.keys()) >= {'encryptionAlgorithm', 'integrityProtectionAlgorithm'}, \
            "Missing encryption or integrity protection algorithm"
        logger.debug(f"SecurityModeCommand algorithms: {algorithms}")
        logger.info("SecurityModeCommand NAS message validated successfully")

    def validate_security_mode_complete(self, nas_msg):
        logger.info("Validating SecurityModeComplete NAS message")
        assert nas_msg['message_type'] == "SecurityModeComplete", "Invalid NAS message type"
        logger.info("SecurityModeComplete NAS message validated successfully")

    def validate_esm_information_request(self, nas_msg):
        logger.info("Validating ESMInformationRequest NAS message")
        assert nas_msg['message_type'] == "ESMInformationRequest", "Invalid NAS message type"
        logger.info("ESMInformationRequest NAS message validated successfully")

    def validate_esm_information_response(self, nas_msg):
        logger.info("Validating ESMInformationResponse NAS message")
        assert nas_msg['message_type'] == "ESMInformationResponse", "Invalid NAS message type"
        # Validate PDN connectivity IE presence
        assert 'apn' in nas_msg, "APN IE missing"
        logger.debug(f"ESMInformationResponse APN: {nas_msg['apn']}")
        logger.info("ESMInformationResponse NAS message validated successfully")

    def validate_initial_context_setup_request(self, msg):
        logger.info("Validating InitialContextSetupRequest message")
        assert msg['message_type'] == "InitialContextSetupRequest", "Invalid message type"
        # Validate E-RAB setup list IE presence
        assert 'eRABSetupList' in msg, "eRABSetupList IE missing"
        setup_list = msg['eRABSetupList']
        assert isinstance(setup_list, list) and len(setup_list) > 0, "eRABSetupList must be a non-empty list"
        for e_rab in setup_list:
            assert 'eRABID' in e_rab and 'transportLayerAddress' in e_rab and 'gtp_teid' in e_rab, \
                "Mandatory IE missing in eRAB setup"
            logger.debug(f"eRAB setup: ID {e_rab['eRABID']}, Address {e_rab['transportLayerAddress']}")
        logger.info("InitialContextSetupRequest validated successfully")

    def validate_rrc_connection_reconfiguration(self, msg):
        logger.info("Validating RRCConnectionReconfiguration message")
        assert msg['message_type'] == "RRCConnectionReconfiguration", "Invalid message type"
        # Validate presence of radio resource config IE
        assert 'radioResourceConfigDedicated' in msg, "radioResourceConfigDedicated IE missing"
        rrc_cfg = msg['radioResourceConfigDedicated']
        # Validate presence of SRB and DRB config
        assert 'srb_ToAddModList' in rrc_cfg and 'drb_ToAddModList' in rrc_cfg, "SRB or DRB add/mod list missing"
        logger.debug(f"RRCConnectionReconfiguration SRBs: {rrc_cfg['srb_ToAddModList']}")
        logger.debug(f"RRCConnectionReconfiguration DRBs: {rrc_cfg['drb_ToAddModList']}")
        logger.info("RRCConnectionReconfiguration message validated successfully")

    def validate_rrc_connection_reconfiguration_complete(self, msg):
        logger.info("Validating RRCConnectionReconfigurationComplete message")
        assert msg['message_type'] == "RRCConnectionReconfigurationComplete", "Invalid message type"
        logger.info("RRCConnectionReconfigurationComplete message validated successfully")

    def validate_attach_complete(self, nas_msg):
        logger.info("Validating AttachComplete NAS message")
        assert nas_msg['message_type'] == "AttachComplete", "Invalid NAS message type"
        logger.info("AttachComplete NAS message validated successfully")

    def validate_secondary_node_addition(self, msg):
        logger.info("Validating secondary node addition procedure messages")
        # Validate SgNB Addition Request message
        assert msg['message_type'] == "SgNBAdditionRequest", "Invalid message type for secondary node addition"
        # Validate critical IEs
        assert 'secondaryCellGroupConfig' in msg, "secondaryCellGroupConfig IE missing"
        scg_cfg = msg['secondaryCellGroupConfig']
        assert 'rlc_Config' in scg_cfg and 'mac_Config' in scg_cfg, "rlc_Config or mac_Config missing in SCG config"
        logger.debug(f"SgNBAdditionRequest secondaryCellGroupConfig keys: {list(scg_cfg.keys())}")
        logger.info("SgNBAdditionRequest message validated successfully")

    def validate_secondary_node_reconfiguration_complete(self, msg):
        logger.info("Validating SgNBReconfigurationComplete message")
        assert msg['message_type'] == "SgNBReconfigurationComplete", "Invalid message type"
        logger.info("SgNBReconfigurationComplete message validated successfully")

    def validate_detach_request(self, nas_msg):
        logger.info("Validating DetachRequest NAS message")
        assert nas_msg['message_type'] == "DetachRequest", "Invalid NAS message type"
        # Validate detach type IE
        assert 'detachType' in nas_msg, "detachType IE missing"
        valid_detach_types = ['switchOff', 'reAttach', 'EPSDetach']
        assert nas_msg['detachType'] in valid_detach_types, f"Invalid detachType: {nas_msg['detachType']}"
        logger.debug(f"DetachRequest detachType: {nas_msg['detachType']}")
        logger.info("DetachRequest NAS message validated successfully")

    def validate_detach_accept(self, nas_msg):
        logger.info("Validating DetachAccept NAS message")
        assert nas_msg['message_type'] == "DetachAccept", "Invalid NAS message type"
        logger.info("DetachAccept NAS message validated successfully")

    def validate_ue_context_release_command(self, msg):
        logger.info("Validating UEContextReleaseCommand message")
        assert msg['message_type'] == "UEContextReleaseCommand", "Invalid message type"
        # Validate cause IE presence
        assert 'cause' in msg, "cause IE missing"
        cause = msg['cause']
        valid_causes = ['release_due_to_reconfiguration', 'release_due_to_handover', 'release_due_to_detach']
        assert cause in valid_causes, f"Invalid cause: {cause}"
        logger.debug(f"UEContextReleaseCommand cause: {cause}")
        logger.info("UEContextReleaseCommand message validated successfully")

    def validate_rrc_connection_release(self, msg):
        logger.info("Validating RRCConnectionRelease message")
        assert msg['message_type'] == "RRCConnectionRelease", "Invalid message type"
        # Validate release config IE presence
        assert 'releaseConfig' in msg, "releaseConfig IE missing"
        release_cfg = msg['releaseConfig']
        logger.debug(f"RRCConnectionRelease releaseConfig: {release_cfg}")
        logger.info("RRCConnectionRelease message validated successfully")

    def run_attach_detach_test(self):
        logger.info("Starting the 10 iteration attach-detach test")
        total_iterations = 10
        for i in range(total_iterations):
            logger.info(f"Iteration {i+1} - Attach procedure start")
            self.start_logging()
            self.trigger_ue_power_on()

            # Simulate waiting and retrieving the messages from UE or network side
            rrc_conn_req = self.ue.wait_for_message('RRCConnectionRequest')
            self.validate_rrc_connection_request(rrc_conn_req)

            rrc_conn_setup = self.ue.wait_for_message('RRCConnectionSetup')
            self.validate_rrc_connection_setup(rrc_conn_setup)

            rrc_conn_setup_complete = self.ue.wait_for_message('RRCConnectionSetupComplete')
            self.validate_rrc_connection_setup_complete(rrc_conn_setup_complete)

            attach_req_nas = rrc_conn_setup_complete['nasPdu']
            self.validate_attach_request(attach_req_nas)

            attach_accept_nas = self.ue.wait_for_message('AttachAccept')
            self.validate_attach_accept(attach_accept_nas)

            sec_mode_cmd = self.ue.wait_for_message('SecurityModeCommand')
            self.validate_security_mode_command(sec_mode_cmd)

            sec_mode_comp = self.ue.wait_for_message('SecurityModeComplete')
            self.validate_security_mode_complete(sec_mode_comp)

            esm_info_req = self.ue.wait_for_message('ESMInformationRequest')
            self.validate_esm_information_request(esm_info_req)

            esm_info_resp = self.ue.wait_for_message('ESMInformationResponse')
            self.validate_esm_information_response(esm_info_resp)

            initial_context_setup = self.ue.wait_for_message('InitialContextSetupRequest')
            self.validate_initial_context_setup_request(initial_context_setup)

            rrc_conn_reconfig = self.ue.wait_for_message('RRCConnectionReconfiguration')
            self.validate_rrc_connection_reconfiguration(rrc_conn_reconfig)

            rrc_conn_reconfig_comp = self.ue.wait_for_message('RRCConnectionReconfigurationComplete')
            self.validate_rrc_connection_reconfiguration_complete(rrc_conn_reconfig_comp)

            attach_complete_nas = self.ue.wait_for_message('AttachComplete')
            self.validate_attach_complete(attach_complete_nas)

            # Secondary node addition for 5G NSA
            if self.config.get('mode') == '5G NSA':
                sgnb_add_req = self.ue.wait_for_message('SgNBAdditionRequest')
                self.validate_secondary_node_addition(sgnb_add_req)

                sgnb_reconfig_comp = self.ue.wait_for_message('SgNBReconfigurationComplete')
                self.validate_secondary_node_reconfiguration_complete(sgnb_reconfig_comp)
                self.secondary_node_add_success_count += 1

            self.attach_success_count += 1
            attach_latency = self.ue.get_attach_latency()
            self.attach_latencies.append(attach_latency)
            logger.info(f"Attach latency for iteration {i+1}: {attach_latency} ms")

            logger.info(f"Iteration {i+1} - Detach procedure start")
            self.trigger_ue_power_off()

            detach_req = self.ue.wait_for_message('DetachRequest')
            self.validate_detach_request(detach_req)

            detach_accept = self.ue.wait_for_message('DetachAccept')
            self.validate_detach_accept(detach_accept)

            ue_ctx_rel_cmd = self.ue.wait_for_message('UEContextReleaseCommand')
            self.validate_ue_context_release_command(ue_ctx_rel_cmd)

            rrc_conn_rel = self.ue.wait_for_message('RRCConnectionRelease')
            self.validate_rrc_connection_release(rrc_conn_rel)

            self.detach_success_count += 1

            self.stop_logging()

        # Summary and KPI calculations
        attach_success_rate = (self.attach_success_count / total_iterations) * 100
        detach_success_rate = (self.detach_success_count / total_iterations) * 100
        sec_node_add_success_rate = (self.secondary_node_add_success_count / total_iterations) * 100 if self.config.get('mode') == '5G NSA' else None

        sorted_latencies = sorted(self.attach_latencies)
        min_latency = sorted_latencies[0]
        max_latency = sorted_latencies[-1]
        avg_latency = sum(sorted_latencies) / total_iterations

        logger.info(f"Attach success rate: {attach_success_rate}%")
        logger.info(f"Detach success rate: {detach_success_rate}%")
        if sec_node_add_success_rate is not None:
            logger.info(f"Secondary Node Addition success rate: {sec_node_add_success_rate}%")
        logger.info(f"Attach latency (ms) - Min: {min_latency}, Avg: {avg_latency:.2f}, Max: {max_latency}")

        assert attach_success_rate == 100.0, "Attach success rate < 100%"
        assert detach_success_rate == 100.0, "Detach success rate < 100%"
        if sec_node_add_success_rate is not None:
            assert sec_node_add_success_rate == 100.0, "Secondary Node Addition success rate < 100%"
        assert len(self.attach_latencies) == total_iterations, "Latency samples count mismatch"

        logger.info("Attach-Detach test completed successfully with all iterations passing.")
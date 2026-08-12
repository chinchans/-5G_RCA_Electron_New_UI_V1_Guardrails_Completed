import logging
import time
from statistics import mean

class UEAttachUtils:
    def __init__(self, ue_interface):
        """
        ue_interface: Interface to interact with the UE and network (emulator or real)
        This class provides methods to trigger attach, power on/off UE, capture logs,
        and parse messages/signaling for validation.
        """
        self.ue = ue_interface
        self.logger = logging.getLogger('UEAttachUtils')
        self.logger.setLevel(logging.DEBUG)

    def power_on_ue(self):
        self.logger.debug("Powering ON UE")
        self.ue.power_on()
        time.sleep(1)  # Allow UE to start attach process

    def power_off_ue(self):
        self.logger.debug("Powering OFF UE")
        self.ue.power_off()
        time.sleep(1)  # Allow UE to start detach process

    def start_logging(self):
        self.logger.debug("Starting log capture")
        self.ue.start_log_capture()

    def stop_logging(self):
        self.logger.debug("Stopping log capture")
        self.ue.stop_log_capture()

    def get_latest_logs(self):
        logs = self.ue.fetch_logs()
        self.logger.debug("Fetched latest logs for analysis")
        return logs

    def extract_messages(self, logs, msg_type):
        """
        Extract messages of type msg_type from logs
        """
        extracted_msgs = []
        for entry in logs:
            if entry.get('message_type') == msg_type:
                extracted_msgs.append(entry)
        self.logger.debug(f"Extracted {len(extracted_msgs)} messages of type {msg_type}")
        return extracted_msgs

    def validate_ie(self, ie_name, ie_value, expected_value):
        if ie_value != expected_value:
            self.logger.error(f"Validation failed for IE '{ie_name}': expected {expected_value}, got {ie_value}")
            raise AssertionError(f"IE {ie_name} value mismatch")
        self.logger.debug(f"Validated IE '{ie_name}': {ie_value}")

    def validate_ie_in_range(self, ie_name, ie_value, min_val, max_val):
        if not (min_val <= ie_value <= max_val):
            self.logger.error(f"Validation failed for IE '{ie_name}': expected in range [{min_val}, {max_val}], got {ie_value}")
            raise AssertionError(f"IE {ie_name} value out of range")
        self.logger.debug(f"Validated IE '{ie_name}' in range [{min_val}, {max_val}]: {ie_value}")

    def measure_latency(self, start_time, end_time):
        latency = end_time - start_time
        self.logger.debug(f"Measured latency: {latency:.3f} seconds")
        return latency

    def validate_rrc_connection_request(self, msg):
        self.logger.debug("Validating RRC Connection Request message")
        # Extract and validate IEs
        ies = msg.get('information_elements', {})
        self.validate_ie('ue_identity', ies.get('ue_identity'), 'expected_ue_id')
        self.validate_ie('establishment_cause', ies.get('establishment_cause'), 'mo_signalling')

    def validate_rrc_connection_setup(self, msg):
        self.logger.debug("Validating RRC Connection Setup message")
        ies = msg.get('information_elements', {})
        self.validate_ie('radio_bearer_config', ies.get('radio_bearer_config'), 'expected_rb_config')
        self.validate_ie('physical_config', ies.get('physical_config'), 'expected_phy_config')

    def validate_rrc_connection_setup_complete(self, msg):
        self.logger.debug("Validating RRC Connection Setup Complete message")
        ies = msg.get('information_elements', {})
        self.validate_ie('ue_capabilities', ies.get('ue_capabilities'), 'expected_capabilities')

    def validate_attach_request(self, msg):
        self.logger.debug("Validating NAS Attach Request message")
        ies = msg.get('information_elements', {})
        self.validate_ie('eps_attach_type', ies.get('eps_attach_type'), 'initial')
        self.validate_ie('ue_network_capability', ies.get('ue_network_capability'), 'expected_capability')
        self.validate_ie('ue_id', ies.get('ue_id'), 'expected_ue_id')

    def validate_authentication_request(self, msg):
        self.logger.debug("Validating NAS Authentication Request message")
        ies = msg.get('information_elements', {})
        self.validate_ie('rand', ies.get('rand'), 'expected_rand')
        self.validate_ie('autn', ies.get('autn'), 'expected_autn')

    def validate_authentication_response(self, msg):
        self.logger.debug("Validating NAS Authentication Response message")
        ies = msg.get('information_elements', {})
        self.validate_ie('res', ies.get('res'), 'expected_res')

    def validate_security_mode_command(self, msg):
        self.logger.debug("Validating NAS Security Mode Command message")
        ies = msg.get('information_elements', {})
        self.validate_ie('selected_algorithms', ies.get('selected_algorithms'), 'expected_algorithms')
        self.validate_ie('nas_security_params', ies.get('nas_security_params'), 'expected_params')

    def validate_security_mode_complete(self, msg):
        self.logger.debug("Validating NAS Security Mode Complete message")
        # Usually no IE to validate but log presence
        self.logger.debug("Security Mode Complete message received")

    def validate_esm_information_request(self, msg):
        self.logger.debug("Validating NAS ESM Information Request message")
        ies = msg.get('information_elements', {})
        self.validate_ie('request_type', ies.get('request_type'), 'pdn_address')

    def validate_esm_information_response(self, msg):
        self.logger.debug("Validating NAS ESM Information Response message")
        ies = msg.get('information_elements', {})
        self.validate_ie('apn', ies.get('apn'), 'expected_apn')

    def validate_attach_accept(self, msg):
        self.logger.debug("Validating NAS Attach Accept message")
        ies = msg.get('information_elements', {})
        self.validate_ie('t3412', ies.get('t3412'), 'expected_t3412')
        self.validate_ie('assigned_ue_ip', ies.get('assigned_ue_ip'), 'expected_ip')

    def validate_attach_complete(self, msg):
        self.logger.debug("Validating NAS Attach Complete message")
        # Usually no IEs to validate, just confirm receipt
        self.logger.debug("Attach Complete message received")

    def validate_detach_request(self, msg):
        self.logger.debug("Validating NAS Detach Request message")
        ies = msg.get('information_elements', {})
        self.validate_ie('detach_type', ies.get('detach_type'), 'switch_off')

    def validate_detach_accept(self, msg):
        self.logger.debug("Validating NAS Detach Accept message")
        # Usually no IEs to validate, just confirm receipt
        self.logger.debug("Detach Accept message received")

    def validate_secondary_node_addition(self, msg):
        self.logger.debug("Validating Secondary Node Addition (EN-DC) messages")
        ies = msg.get('information_elements', {})
        self.validate_ie('sgnb_addition_request', ies.get('sgnb_addition_request'), True)
        self.validate_ie('sgnb_reconfiguration_complete', ies.get('sgnb_reconfiguration_complete'), True)

    def validate_secondary_node_release(self, msg):
        self.logger.debug("Validating Secondary Node Release (EN-DC) messages")
        ies = msg.get('information_elements', {})
        self.validate_ie('sgnb_release_request', ies.get('sgnb_release_request'), True)
        self.validate_ie('sgnb_release_acknowledge', ies.get('sgnb_release_acknowledge'), True)


# POSITIVE TESTING: LTE Single UE Attach and Detach Procedure Validation
class LTEAttachDetachTest:
    # POSITIVE_001_LTE_Single_UE_Attach_Detach
    def __init__(self, ue_interface):
        self.utils = UEAttachUtils(ue_interface)
        self.logger = logging.getLogger('LTEAttachDetachTest')
        self.iterations = 10
        self.attach_successes = 0
        self.detach_successes = 0
        self.attach_latencies = []

    def configure_test_setup(self):
        self.logger.debug("Configuring test setup for LTE Attach/Detach")
        # Configuration: single cell activated, others powered off
        self.utils.ue.configure_single_cell()
        self.utils.ue.power_off_other_cells()
        self.utils.ue.activate_serving_cell()
        self.utils.ue.set_radio_conditions('excellent', technology='LTE')
        self.logger.info("Test setup configured and recorded")

    def start_logging(self):
        self.utils.start_logging()

    def stop_logging(self):
        self.utils.stop_logging()

    def power_on_ue_and_attach(self):
        self.logger.debug("Powering ON UE and initiating attach")
        self.utils.power_on_ue()
        attach_start = time.time()
        # Wait for attach complete indication or timeout
        attach_complete = self.utils.ue.wait_for_attach_complete(timeout=30)
        attach_end = time.time()
        if attach_complete:
            latency = self.utils.measure_latency(attach_start, attach_end)
            self.attach_latencies.append(latency)
            self.attach_successes += 1
            self.logger.info(f"Attach successful, latency: {latency:.3f}s")
            return True
        else:
            self.logger.error("Attach failed or timed out")
            return False

    def verify_attach_signaling(self):
        logs = self.utils.get_latest_logs()
        # Validate RRC and NAS messages for attach as per 3GPP TS 23.401
        rrc_conn_req = self.utils.extract_messages(logs, 'RRCConnectionRequest')
        rrc_conn_setup = self.utils.extract_messages(logs, 'RRCConnectionSetup')
        rrc_conn_setup_comp = self.utils.extract_messages(logs, 'RRCConnectionSetupComplete')
        attach_req = self.utils.extract_messages(logs, 'AttachRequest')
        auth_req = self.utils.extract_messages(logs, 'AuthenticationRequest')
        auth_resp = self.utils.extract_messages(logs, 'AuthenticationResponse')
        sec_mode_cmd = self.utils.extract_messages(logs, 'SecurityModeCommand')
        sec_mode_comp = self.utils.extract_messages(logs, 'SecurityModeComplete')
        esm_info_req = self.utils.extract_messages(logs, 'ESMInformationRequest')
        esm_info_resp = self.utils.extract_messages(logs, 'ESMInformationResponse')
        attach_accept = self.utils.extract_messages(logs, 'AttachAccept')
        attach_complete = self.utils.extract_messages(logs, 'AttachComplete')

        # Validate messages and IEs
        self.utils.validate_rrc_connection_request(rrc_conn_req[0])
        self.utils.validate_rrc_connection_setup(rrc_conn_setup[0])
        self.utils.validate_rrc_connection_setup_complete(rrc_conn_setup_comp[0])
        self.utils.validate_attach_request(attach_req[0])
        self.utils.validate_authentication_request(auth_req[0])
        self.utils.validate_authentication_response(auth_resp[0])
        self.utils.validate_security_mode_command(sec_mode_cmd[0])
        self.utils.validate_security_mode_complete(sec_mode_comp[0])
        self.utils.validate_esm_information_request(esm_info_req[0])
        self.utils.validate_esm_information_response(esm_info_resp[0])
        self.utils.validate_attach_accept(attach_accept[0])
        self.utils.validate_attach_complete(attach_complete[0])
        self.logger.info("Attach signaling validated successfully")

    def power_off_ue_and_detach(self):
        self.logger.debug("Powering OFF UE to initiate detach")
        self.utils.power_off_ue()
        # Wait for detach accept indication or timeout
        detach_accepted = self.utils.ue.wait_for_detach_accept(timeout=30)
        if detach_accepted:
            self.detach_successes += 1
            self.logger.info("Detach successful")
            return True
        else:
            self.logger.error("Detach failed or timed out")
            return False

    def verify_detach_signaling(self):
        logs = self.utils.get_latest_logs()
        detach_req = self.utils.extract_messages(logs, 'DetachRequest')
        detach_accept = self.utils.extract_messages(logs, 'DetachAccept')
        ue_context_release = self.utils.extract_messages(logs, 'UEContextRelease')
        rrc_conn_release = self.utils.extract_messages(logs, 'RRCConnectionRelease')

        self.utils.validate_detach_request(detach_req[0])
        self.utils.validate_detach_accept(detach_accept[0])
        self.logger.debug("Validating UE Context Release and RRC Connection Release messages presence")
        if not ue_context_release or not rrc_conn_release:
            self.logger.error("Missing UE Context Release or RRC Connection Release messages")
            raise AssertionError("Detach signaling incomplete")
        self.logger.info("Detach signaling validated successfully")

    def calculate_and_report_kpis(self):
        min_latency = min(self.attach_latencies)
        max_latency = max(self.attach_latencies)
        avg_latency = mean(self.attach_latencies)
        attach_success_rate = (self.attach_successes / self.iterations) * 100
        detach_success_rate = (self.detach_successes / self.iterations) * 100

        self.logger.info("KPI Summary:")
        self.logger.info(f"Attach Success Rate: {attach_success_rate:.2f}%")
        self.logger.info(f"Detach Success Rate: {detach_success_rate:.2f}%")
        self.logger.info(f"Attach Latency (s): Min={min_latency:.3f}, Avg={avg_latency:.3f}, Max={max_latency:.3f}")

        # Here we would record KPIs to test report as per Table 5-2 and 5-3

    def run_test(self):
        self.configure_test_setup()
        self.start_logging()
        for i in range(self.iterations):
            self.logger.info(f"Iteration {i+1} starting")
            if not self.power_on_ue_and_attach():
                self.logger.error(f"Attach failed on iteration {i+1}, aborting test")
                break
            self.verify_attach_signaling()
            if not self.power_off_ue_and_detach():
                self.logger.error(f"Detach failed on iteration {i+1}, aborting test")
                break
            self.verify_detach_signaling()
            self.logger.info(f"Iteration {i+1} completed successfully")
        self.stop_logging()
        self.calculate_and_report_kpis()


# POSITIVE TESTING: 5G NSA Single UE Attach and Detach with Secondary Node Addition and Release
class FiveGNSAAttachDetachTest:
    # POSITIVE_002_5G_NSA_Single_UE_Attach_Detach
    def __init__(self, ue_interface):
        self.utils = UEAttachUtils(ue_interface)
        self.logger = logging.getLogger('FiveGNSAAttachDetachTest')
        self.iterations = 10
        self.attach_successes = 0
        self.detach_successes = 0
        self.secondary_node_addition_successes = 0

    def configure_test_setup(self):
        self.logger.debug("Configuring test setup for 5G NSA Attach/Detach")
        self.utils.ue.configure_single_cell()
        self.utils.ue.power_off_other_cells()
        self.utils.ue.activate_serving_cell()
        self.utils.ue.set_radio_conditions('excellent', technology='5G NSA')
        self.logger.info("Test setup configured and recorded")

    def start_logging(self):
        self.utils.start_logging()

    def stop_logging(self):
        self.utils.stop_logging()

    def power_on_ue_and_attach(self):
        self.logger.debug("Powering ON UE and initiating 5G NSA attach")
        self.utils.power_on_ue()
        attach_start = time.time()
        attach_complete = self.utils.ue.wait_for_attach_complete(timeout=40)
        attach_end = time.time()
        if attach_complete:
            latency = self.utils.measure_latency(attach_start, attach_end)
            self.attach_successes += 1
            self.logger.info(f"Attach successful, latency: {latency:.3f}s")
            return True
        else:
            self.logger.error("Attach failed or timed out")
            return False

    def verify_attach_signaling(self):
        logs = self.utils.get_latest_logs()
        # LTE attach messages
        rrc_conn_req = self.utils.extract_messages(logs, 'RRCConnectionRequest')
        rrc_conn_setup = self.utils.extract_messages(logs, 'RRCConnectionSetup')
        rrc_conn_setup_comp = self.utils.extract_messages(logs, 'RRCConnectionSetupComplete')
        attach_req = self.utils.extract_messages(logs, 'AttachRequest')
        auth_req = self.utils.extract_messages(logs, 'AuthenticationRequest')
        auth_resp = self.utils.extract_messages(logs, 'AuthenticationResponse')
        sec_mode_cmd = self.utils.extract_messages(logs, 'SecurityModeCommand')
        sec_mode_comp = self.utils.extract_messages(logs, 'SecurityModeComplete')
        esm_info_req = self.utils.extract_messages(logs, 'ESMInformationRequest')
        esm_info_resp = self.utils.extract_messages(logs, 'ESMInformationResponse')
        attach_accept = self.utils.extract_messages(logs, 'AttachAccept')
        attach_complete = self.utils.extract_messages(logs, 'AttachComplete')

        # 5G NSA Secondary Node Addition messages
        sgnb_add_req = self.utils.extract_messages(logs, 'SgNBAdditionRequest')
        sgnb_reconf_comp = self.utils.extract_messages(logs, 'SgNBReconfigurationComplete')

        # Validate LTE attach part
        self.utils.validate_rrc_connection_request(rrc_conn_req[0])
        self.utils.validate_rrc_connection_setup(rrc_conn_setup[0])
        self.utils.validate_rrc_connection_setup_complete(rrc_conn_setup_comp[0])
        self.utils.validate_attach_request(attach_req[0])
        self.utils.validate_authentication_request(auth_req[0])
        self.utils.validate_authentication_response(auth_resp[0])
        self.utils.validate_security_mode_command(sec_mode_cmd[0])
        self.utils.validate_security_mode_complete(sec_mode_comp[0])
        self.utils.validate_esm_information_request(esm_info_req[0])
        self.utils.validate_esm_information_response(esm_info_resp[0])
        self.utils.validate_attach_accept(attach_accept[0])
        self.utils.validate_attach_complete(attach_complete[0])

        # Validate secondary node addition
        if sgnb_add_req and sgnb_reconf_comp:
            self.utils.validate_secondary_node_addition({'information_elements': {
                'sgnb_addition_request': True,
                'sgnb_reconfiguration_complete': True
            }})
            self.secondary_node_addition_successes += 1
            self.logger.info("Secondary node addition signaling validated")
        else:
            self.logger.error("Missing secondary node addition messages")
            raise AssertionError("Secondary node addition signaling incomplete")

        self.logger.info("Attach signaling for 5G NSA validated successfully")

    def power_off_ue_and_detach(self):
        self.logger.debug("Powering OFF UE to initiate 5G NSA detach")
        self.utils.power_off_ue()
        detach_accepted = self.utils.ue.wait_for_detach_accept(timeout=40)
        if detach_accepted:
            self.detach_successes += 1
            self.logger.info("Detach successful")
            return True
        else:
            self.logger.error("Detach failed or timed out")
            return False

    def verify_detach_signaling(self):
        logs = self.utils.get_latest_logs()
        detach_req = self.utils.extract_messages(logs, 'DetachRequest')
        detach_accept = self.utils.extract_messages(logs, 'DetachAccept')
        ue_context_release = self.utils.extract_messages(logs, 'UEContextRelease')
        rrc_conn_release = self.utils.extract_messages(logs, 'RRCConnectionRelease')
        sgnb_release_req = self.utils.extract_messages(logs, 'SgNBReleaseRequest')
        sgnb_release_ack = self.utils.extract_messages(logs, 'SgNBReleaseRequestAcknowledge')

        self.utils.validate_detach_request(detach_req[0])
        self.utils.validate_detach_accept(detach_accept[0])

        if not ue_context_release or not rrc_conn_release:
            self.logger.error("Missing UE Context Release or RRC Connection Release messages")
            raise AssertionError("Detach signaling incomplete")

        if sgnb_release_req and sgnb_release_ack:
            self.utils.validate_secondary_node_release({'information_elements': {
                'sgnb_release_request': True,
                'sgnb_release_acknowledge': True
            }})
            self.logger.info("Secondary node release signaling validated")
        else:
            self.logger.error("Missing secondary node release messages")
            raise AssertionError("Secondary node release signaling incomplete")

        self.logger.info("Detach signaling for 5G NSA validated successfully")

    def calculate_and_report_kpis(self):
        attach_success_rate = (self.attach_successes / self.iterations) * 100
        detach_success_rate = (self.detach_successes / self.iterations) * 100
        secondary_node_addition_success_rate = (self.secondary_node_addition_successes / self.iterations) * 100

        self.logger.info("KPI Summary:")
        self.logger.info(f"Attach Success Rate: {attach_success_rate:.2f}%")
        self.logger.info(f"Detach Success Rate: {detach_success_rate:.2f}%")
        self.logger.info(f"Secondary Node Addition Success Rate: {secondary_node_addition_success_rate:.2f}%")

    def run_test(self):
        self.configure_test_setup()
        self.start_logging()
        for i in range(self.iterations):
            self.logger.info(f"Iteration {i+1} starting")
            if not self.power_on_ue_and_attach():
                self.logger.error(f"Attach failed on iteration {i+1}, aborting test")
                break
            self.verify_attach_signaling()
            if not self.power_off_ue_and_detach():
                self.logger.error(f"Detach failed on iteration {i+1}, aborting test")
                break
            self.verify_detach_signaling()
            self.logger.info(f"Iteration {i+1} completed successfully")
        self.stop_logging()
        self.calculate_and_report_kpis()


# REGISTRATION TEST: 5G NSA UE Registration Request to Complete
class FiveGNSARegistrationTest:
    # REGISTRATION_001_5G_NSA_Registration_Success
    def __init__(self, ue_interface):
        self.utils = UEAttachUtils(ue_interface)
        self.logger = logging.getLogger('FiveGNSARegistrationTest')

    def configure_test_setup(self):
        self.logger.debug("Configuring test setup for 5G NSA registration")
        self.utils.ue.configure_integrated_lte_5g_cells()
        self.utils.ue.power_off_other_cells()
        self.utils.ue.activate_serving_cells()
        self.utils.ue.set_radio_conditions('excellent', technology='5G NSA')
        self.logger.info("Test setup configured and recorded")

    def start_logging(self):
        self.utils.start_logging()

    def stop_logging(self):
        self.utils.stop_logging()

    def power_on_ue_and_register(self):
        self.logger.debug("Powering ON UE and initiating registration")
        self.utils.power_on_ue()
        registration_complete = self.utils.ue.wait_for_registration_complete(timeout=30)
        if registration_complete:
            self.logger.info("Registration completed successfully")
            return True
        else:
            self.logger.error("Registration failed or timed out")
            return False

    def verify_registration_signaling(self):
        logs = self.utils.get_latest_logs()
        reg_req = self.utils.extract_messages(logs, 'RegistrationRequest')
        reg_accept = self.utils.extract_messages(logs, 'RegistrationAccept')
        reg_complete = self.utils.extract_messages(logs, 'RegistrationComplete')

        self.utils.validate_ie('registration_type', reg_req[0].get('information_elements', {}).get('registration_type'), 'initial')
        self.utils.validate_ie('access_type', reg_req[0].get('information_elements', {}).get('access_type'), '3GPP')
        self.utils.validate_ie('registration_result', reg_accept[0].get('information_elements', {}).get('registration_result'), 'accepted')

        if not reg_complete:
            self.logger.error("Missing Registration Complete message")
            raise AssertionError("Registration signaling incomplete")
        self.logger.info("Registration signaling validated successfully")

    def run_test(self):
        self.configure_test_setup()
        self.start_logging()
        if self.power_on_ue_and_register():
            self.verify_registration_signaling()
        self.stop_logging()


# PDU SESSION TEST: 5G NSA UE PDU Session Establishment and User Plane Setup
class FiveGNSAPDUSessionTest:
    # PDU_SESSION_001_5G_NSA_PDU_Session_Establishment
    def __init__(self, ue_interface):
        self.utils = UEAttachUtils(ue_interface)
        self.logger = logging.getLogger('FiveGNSAPDUSessionTest')

    def start_logging(self):
        self.utils.start_logging()

    def stop_logging(self):
        self.utils.stop_logging()

    def initiate_pdu_session(self):
        self.logger.debug("UE initiating PDU Session Establishment Request")
        self.utils.ue.initiate_pdu_session()
        pdu_session_established = self.utils.ue.wait_for_pdu_session_established(timeout=30)
        if pdu_session_established:
            self.logger.info("PDU Session established successfully")
            return True
        else:
            self.logger.error("PDU Session establishment failed or timed out")
            return False

    def verify_pdu_session_signaling(self):
        logs = self.utils.get_latest_logs()
        pdu_sess_req = self.utils.extract_messages(logs, 'PDUSessionEstablishmentRequest')
        pdu_sess_auth = self.utils.extract_messages(logs, 'PDUSessionAuthentication')
        pdu_sess_accept = self.utils.extract_messages(logs, 'PDUSessionAccept')
        n3_tunnel_setup = self.utils.extract_messages(logs, 'N3TunnelSetup')
        qos_flow_setup = self.utils.extract_messages(logs, 'QoSFlowSetup')

        self.utils.validate_ie('pdu_session_id', pdu_sess_req[0].get('information_elements', {}).get('pdu_session_id'), 'expected_pdu_session_id')
        self.utils.validate_ie('auth_required', pdu_sess_auth[0].get('information_elements', {}).get('auth_required'), True)
        self.utils.validate_ie('pdu_session_status', pdu_sess_accept[0].get('information_elements', {}).get('status'), 'accepted')

        self.logger.debug("Validating N3 Tunnel and QoS Flow setup")
        if not n3_tunnel_setup or not qos_flow_setup:
            self.logger.error("Missing N3 Tunnel or QoS Flow setup messages")
            raise AssertionError("User plane setup incomplete")

        self.logger.info("PDU Session signaling and user plane setup validated successfully")

    def run_test(self):
        self.start_logging()
        if self.initiate_pdu_session():
            self.verify_pdu_session_signaling()
        self.stop_logging()


# HANDOVER TEST: 5G NSA Xn Handover Procedure Validation
class FiveGNSAXnHandoverTest:
    # HANDOVER_001_Xn_Handover_5G_NSA_Procedure
    def __init__(self, ue_interface):
        self.utils = UEAttachUtils(ue_interface)
        self.logger = logging.getLogger('FiveGNSAXnHandoverTest')

    def start_logging(self):
        self.utils.start_logging()

    def stop_logging(self):
        self.utils.stop_logging()

    def trigger_handover(self):
        self.logger.debug("Triggering UE measurement report for handover")
        self.utils.ue.send_measurement_report()
        ho_required = self.utils.ue.wait_for_message('HandoverRequired', timeout=10)
        if not ho_required:
            self.logger.error("No Handover Required message received")
            raise AssertionError("Handover initiation failed")

        self.logger.debug("Waiting for Handover Request and Ack from target gNB")
        ho_request = self.utils.ue.wait_for_message('HandoverRequest', timeout=10)
        ho_request_ack = self.utils.ue.wait_for_message('HandoverRequestAck', timeout=10)
        if not (ho_request and ho_request_ack):
            self.logger.error("Missing Handover Request or Acknowledge messages")
            raise AssertionError("Handover signaling incomplete")

        self.logger.debug("Waiting for RRC Reconfiguration message for handover")
        rrc_reconf = self.utils.ue.wait_for_message('RRCConnectionReconfiguration', timeout=10)
        if not rrc_reconf:
            self.logger.error("Missing RRC Connection Reconfiguration message")
            raise AssertionError("Handover reconfiguration missing")

        self.logger.debug("Waiting for Path Switch procedure and UE Handover Complete message")
        path_switch = self.utils.ue.wait_for_message('PathSwitchRequest', timeout=10)
        ho_complete = self.utils.ue.wait_for_message('HandoverComplete', timeout=10)
        if not (path_switch and ho_complete):
            self.logger.error("Missing Path Switch or Handover Complete messages")
            raise AssertionError("Handover finalization incomplete")

    def verify_handover_signaling(self):
        logs = self.utils.get_latest_logs()
        # Validate all handover related messages in logs
        required_msgs = ['HandoverRequired', 'HandoverRequest', 'HandoverRequestAck', 'RRCConnectionReconfiguration', 'PathSwitchRequest', 'HandoverComplete']
        for msg_type in required_msgs:
            msgs = self.utils.extract_messages(logs, msg_type)
            if not msgs:
                self.logger.error(f"Missing {msg_type} message in logs")
                raise AssertionError(f"Handover message {msg_type} missing")
        self.logger.info("All handover signaling messages validated successfully")

    def run_test(self):
        self.start_logging()
        self.trigger_handover()
        self.verify_handover_signaling()
        self.stop_logging()


# SN RELEASE TEST: MN Initiated Secondary Node Release Procedure
class MNInitiatedSNReleaseTest:
    # SN_RELEASE_001_MN_Initiated_Secondary_Node_Release
    def __init__(self, ue_interface):
        self.utils = UEAttachUtils(ue_interface)
        self.logger = logging.getLogger('MNInitiatedSNReleaseTest')

    def start_logging(self):
        self.utils.start_logging()

    def stop_logging(self):
        self.utils.stop_logging()

    def initiate_mn_initiated_sn_release(self):
        self.logger.debug("MN initiating Secondary Node Release")
        self.utils.ue.send_sgnb_release_request()
        sgnb_release_ack = self.utils.ue.wait_for_message('SgNBReleaseRequestAcknowledge', timeout=10)
        if not sgnb_release_ack:
            self.logger.error("No SgNB Release Request Acknowledge received")
            raise AssertionError("SN release acknowledge missing")

        rrc_reconf = self.utils.ue.wait_for_message('RRCConnectionReconfiguration', timeout=10)
        if not rrc_reconf:
            self.logger.error("No RRC Connection Reconfiguration message for SCG release received")
            raise AssertionError("RRC reconfiguration missing")

        # Verify UE processes reconfiguration successfully
        self.logger.debug("Waiting for UE to process RRC reconfiguration")
        rrc_reconf_success = self.utils.ue.wait_for_rrc_reconf_success(timeout=10)
        if not rrc_reconf_success:
            self.logger.error("UE failed to process RRC reconfiguration")
            raise AssertionError("UE RRC reconfiguration failure")

        sn_status_transfer = self.utils.ue.wait_for_message('SNStatusTransfer', timeout=10)
        if not sn_status_transfer:
            self.logger.error("No SN Status Transfer message received")
            raise AssertionError("SN Status Transfer missing")

        secondary_rat_report = self.utils.ue.wait_for_message('SecondaryRATDataUsageReport', timeout=10)
        if not secondary_rat_report:
            self.logger.error("No Secondary RAT Data Usage Report message received")
            raise AssertionError("Secondary RAT report missing")

        path_update = self.utils.ue.wait_for_message('PathUpdate', timeout=10)
        # Path update may be optional, just log presence
        if path_update:
            self.logger.debug("Path Update procedure initiated")

        ue_context_release = self.utils.ue.wait_for_message('UEContextRelease', timeout=10)
        if not ue_context_release:
            self.logger.error("No UE Context Release message received")
            raise AssertionError("UE Context Release missing")

        self.logger.info("MN initiated secondary node release procedure completed successfully")

    def run_test(self):
        self.start_logging()
        self.initiate_mn_initiated_sn_release()
        self.stop_logging()


# SN RELEASE TEST: SN Initiated Secondary Node Release Procedure
class SNInitiatedSNReleaseTest:
    # SN_RELEASE_002_SN_Initiated_Secondary_Node_Release
    def __init__(self, ue_interface):
        self.utils = UEAttachUtils(ue_interface)
        self.logger = logging.getLogger('SNInitiatedSNReleaseTest')

    def start_logging(self):
        self.utils.start_logging()

    def stop_logging(self):
        self.utils.stop_logging()

    def process_sn_initiated_sn_release(self):
        self.logger.debug("SN initiating Secondary Node Release")
        sgnb_release_req = self.utils.ue.wait_for_message('SgNBReleaseRequired', timeout=10)
        if not sgnb_release_req:
            self.logger.error("No SgNB Release Required message received")
            raise AssertionError("SN release required missing")

        sgnb_release_confirm = self.utils.ue.wait_for_message('SgNBReleaseConfirm', timeout=10)
        if not sgnb_release_confirm:
            self.logger.error("No SgNB Release Confirm message received")
            raise AssertionError("SN release confirm missing")

        self.logger.debug("SN started data forwarding and stopped user data to UE")

        rrc_reconf = self.utils.ue.wait_for_message('RRCConnectionReconfiguration', timeout=10)
        if not rrc_reconf:
            self.logger.error("No RRC Connection Reconfiguration message for SCG release received")
            raise AssertionError("RRC reconfiguration missing")

        # Verify UE processes reconfiguration successfully
        rrc_reconf_success = self.utils.ue.wait_for_rrc_reconf_success(timeout=10)
        if not rrc_reconf_success:
            self.logger.error("UE failed to process RRC reconfiguration")
            raise AssertionError("UE RRC reconfiguration failure")

        sn_status_transfer = self.utils.ue.wait_for_message('SNStatusTransfer', timeout=10)
        if not sn_status_transfer:
            self.logger.error("No SN Status Transfer message received")
            raise AssertionError("SN Status Transfer missing")

        secondary_rat_report = self.utils.ue.wait_for_message('SecondaryRATDataUsageReport', timeout=10)
        if not secondary_rat_report:
            self.logger.error("No Secondary RAT Data Usage Report message received")
            raise AssertionError("Secondary RAT report missing")

        path_update = self.utils.ue.wait_for_message('PathUpdate', timeout=10)
        if path_update:
            self.logger.debug("Path Update procedure initiated")

        ue_context_release = self.utils.ue.wait_for_message('UEContextRelease', timeout=10)
        if not ue_context_release:
            self.logger.error("No UE Context Release message received")
            raise AssertionError("UE Context Release missing")

        self.logger.info("SN initiated secondary node release procedure completed successfully")

    def run_test(self):
        self.start_logging()
        self.process_sn_initiated_sn_release()
        self.stop_logging()
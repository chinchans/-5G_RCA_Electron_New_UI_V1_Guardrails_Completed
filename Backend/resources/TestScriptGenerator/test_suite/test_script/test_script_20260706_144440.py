import logging
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')


class UEAttachTest:
    # TC_POS_001: Validate successful LTE/5G NSA Attach and Detach of single UE

    def __init__(self, ue_interface, logger=None):
        """
        Initialize the test with a UE interface and optional logger.
        ue_interface: Object representing the UE control and log interface.
        logger: Optional logger object.
        """
        self.ue = ue_interface
        self.logger = logger or logging.getLogger(__name__)
        self.attach_latencies = []
        self.attach_success_count = 0
        self.detach_success_count = 0
        self.iterations = 10

    def trigger_attach(self):
        """
        Trigger the UE attach procedure by powering ON the UE and waiting for attach complete.
        Returns True if attach succeeded, False otherwise.
        """
        self.logger.info("Powering ON UE to start attach procedure.")
        self.ue.power_on()
        attach_start = time.time()
        if not self.wait_for_attach_complete(timeout=60):
            self.logger.error("Attach procedure failed or timed out.")
            return False
        attach_end = time.time()
        latency = attach_end - attach_start
        self.attach_latencies.append(latency)
        self.attach_success_count += 1
        self.logger.info(f"Attach successful. Latency: {latency:.2f} seconds.")
        return True

    def wait_for_attach_complete(self, timeout=60):
        """
        Wait for UE attach complete indication within timeout.
        Returns True if attach complete received, False otherwise.
        """
        self.logger.info("Waiting for attach complete message in UE logs.")
        start_time = time.time()
        while time.time() - start_time < timeout:
            msg = self.ue.get_next_log_message()
            if msg and self.is_attach_complete(msg):
                self.logger.info("Attach complete message received.")
                return True
            time.sleep(1)
        return False

    def is_attach_complete(self, msg):
        """
        Detect if the given log message corresponds to attach complete.
        """
        # Example detection logic based on NAS message type and content
        return "Attach Complete" in msg

    def validate_attach_request(self, msg):
        """
        Validate the Attach Request message and its IEs.
        """
        self.logger.info("Validating Attach Request message and IEs.")
        # Extract expected IEs from msg
        ie_imsi = self.extract_ie(msg, "IMSI")
        ie_eps_attach_type = self.extract_ie(msg, "EPS Attach Type")
        ie_ue_network_capability = self.extract_ie(msg, "UE Network Capability")
        ie_nas_security = self.extract_ie(msg, "NAS Security Parameters")
        # Validate IMSI format
        assert ie_imsi and ie_imsi.isdigit(), f"Invalid IMSI: {ie_imsi}"
        self.logger.info(f"IMSI validated: {ie_imsi}")
        # Validate EPS Attach Type presence and correctness
        assert ie_eps_attach_type in ["EPS Attach", "Combined EPS/IMSI Attach"], f"Invalid Attach Type: {ie_eps_attach_type}"
        self.logger.info(f"EPS Attach Type validated: {ie_eps_attach_type}")
        # Validate UE Network Capability presence
        assert ie_ue_network_capability is not None, "UE Network Capability IE missing"
        self.logger.info("UE Network Capability IE validated.")
        # Validate NAS Security Parameters presence
        assert ie_nas_security is not None, "NAS Security Parameters IE missing"
        self.logger.info("NAS Security Parameters IE validated.")

    def validate_rrc_connection_setup(self, msg):
        """
        Validate RRC Connection Setup message and all mandatory IEs.
        """
        self.logger.info("Validating RRC Connection Setup message and IEs.")
        ie_rrc_transaction_id = self.extract_ie(msg, "RRC Transaction Identifier")
        ie_radio_config = self.extract_ie(msg, "Radio Resource Config")
        # Validate transaction identifier presence and range
        assert ie_rrc_transaction_id is not None and 0 <= int(ie_rrc_transaction_id) <= 3, \
            f"Invalid RRC Transaction Identifier: {ie_rrc_transaction_id}"
        self.logger.info(f"RRC Transaction Identifier validated: {ie_rrc_transaction_id}")
        # Validate Radio Resource Config presence
        assert ie_radio_config is not None, "Radio Resource Config IE missing"
        self.logger.info("Radio Resource Config IE validated.")

    def validate_rrc_connection_setup_complete(self, msg):
        """
        Validate RRC Connection Setup Complete message and its IEs.
        """
        self.logger.info("Validating RRC Connection Setup Complete message and IEs.")
        ie_rrc_transaction_id = self.extract_ie(msg, "RRC Transaction Identifier")
        ie_nas_message = self.extract_ie(msg, "NAS Message Container")
        # Validate transaction identifier presence
        assert ie_rrc_transaction_id is not None, "RRC Transaction Identifier IE missing"
        self.logger.info(f"RRC Transaction Identifier validated: {ie_rrc_transaction_id}")
        # Validate NAS Message Container presence
        assert ie_nas_message is not None, "NAS Message Container IE missing"
        self.logger.info("NAS Message Container IE validated.")

    def validate_attach_accept(self, msg):
        """
        Validate Attach Accept NAS message and all IEs.
        """
        self.logger.info("Validating Attach Accept NAS message and IEs.")
        ie_emm_cause = self.extract_ie(msg, "EMM Cause")
        ie_eps_mobile_identity = self.extract_ie(msg, "EPS Mobile Identity")
        ie_t3412_timer = self.extract_ie(msg, "T3412 Timer")
        ie_eps_update_result = self.extract_ie(msg, "EPS Update Result")
        # Validate cause is success (0)
        assert ie_emm_cause == "0", f"Attach Accept EMM Cause not success: {ie_emm_cause}"
        self.logger.info("EMM Cause validated as success (0).")
        # Validate EPS Mobile Identity presence and format
        assert ie_eps_mobile_identity is not None, "EPS Mobile Identity IE missing"
        self.logger.info("EPS Mobile Identity IE validated.")
        # Validate T3412 Timer presence
        assert ie_t3412_timer is not None, "T3412 Timer IE missing"
        self.logger.info("T3412 Timer IE validated.")
        # Validate EPS Update Result presence
        assert ie_eps_update_result is not None, "EPS Update Result IE missing"
        self.logger.info("EPS Update Result IE validated.")

    def validate_security_mode_command(self, msg):
        """
        Validate Security Mode Command message and its IEs.
        """
        self.logger.info("Validating Security Mode Command message and IEs.")
        ie_selected_algorithms = self.extract_ie(msg, "Selected NAS Security Algorithms")
        ie_integrity_prot_algo = self.extract_ie(msg, "Integrity Protection Algorithm")
        ie_ciphering_algo = self.extract_ie(msg, "Ciphering Algorithm")
        ie_nas_mac = self.extract_ie(msg, "NAS MAC")
        # Validate presence of all security parameters
        assert ie_selected_algorithms is not None, "Selected NAS Security Algorithms IE missing"
        self.logger.info("Selected NAS Security Algorithms IE validated.")
        assert ie_integrity_prot_algo is not None, "Integrity Protection Algorithm IE missing"
        self.logger.info("Integrity Protection Algorithm IE validated.")
        assert ie_ciphering_algo is not None, "Ciphering Algorithm IE missing"
        self.logger.info("Ciphering Algorithm IE validated.")
        assert ie_nas_mac is not None, "NAS MAC IE missing"
        self.logger.info("NAS MAC IE validated.")

    def validate_security_mode_complete(self, msg):
        """
        Validate Security Mode Complete message.
        """
        self.logger.info("Validating Security Mode Complete message and IEs.")
        ie_nas_mac = self.extract_ie(msg, "NAS MAC")
        # Validate presence of NAS MAC
        assert ie_nas_mac is not None, "NAS MAC IE missing"
        self.logger.info("NAS MAC IE validated.")

    def validate_esm_information_request(self, msg):
        """
        Validate ESM Information Request message.
        """
        self.logger.info("Validating ESM Information Request message and IEs.")
        ie_esm_message_container = self.extract_ie(msg, "ESM Message Container")
        assert ie_esm_message_container is not None, "ESM Message Container IE missing"
        self.logger.info("ESM Message Container IE validated.")

    def validate_esm_information_response(self, msg):
        """
        Validate ESM Information Response message.
        """
        self.logger.info("Validating ESM Information Response message and IEs.")
        ie_apn = self.extract_ie(msg, "APN")
        assert ie_apn is not None, "APN IE missing"
        self.logger.info(f"APN IE validated: {ie_apn}")

    def validate_default_eps_bearer_context_accept(self, msg):
        """
        Validate Default EPS Bearer Context Accept message.
        """
        self.logger.info("Validating Default EPS Bearer Context Accept message and IEs.")
        ie_eps_bearer_id = self.extract_ie(msg, "EPS Bearer ID")
        ie_cause = self.extract_ie(msg, "Cause")
        assert ie_eps_bearer_id is not None, "EPS Bearer ID IE missing"
        self.logger.info(f"EPS Bearer ID IE validated: {ie_eps_bearer_id}")
        assert ie_cause == "0", f"Cause IE not success: {ie_cause}"
        self.logger.info("Cause IE validated as success (0).")

    def validate_secondary_node_addition(self, msg):
        """
        Validate the SgNB Addition Request and SgNB Reconfiguration Complete messages for EN-DC.
        """
        self.logger.info("Validating Secondary Node Addition messages and IEs.")
        ie_sgnb_add_req = self.extract_ie(msg, "SgNB Addition Request")
        ie_sgnb_reconfig_complete = self.extract_ie(msg, "SgNB Reconfiguration Complete")
        assert ie_sgnb_add_req is not None, "SgNB Addition Request IE missing"
        self.logger.info("SgNB Addition Request IE validated.")
        assert ie_sgnb_reconfig_complete is not None, "SgNB Reconfiguration Complete IE missing"
        self.logger.info("SgNB Reconfiguration Complete IE validated.")

    def validate_rrc_connection_release(self, msg):
        """
        Validate RRC Connection Release message and IEs.
        """
        self.logger.info("Validating RRC Connection Release message and IEs.")
        ie_rrc_release_cause = self.extract_ie(msg, "Release Cause")
        assert ie_rrc_release_cause is not None, "Release Cause IE missing"
        self.logger.info(f"Release Cause IE validated: {ie_rrc_release_cause}")

    def validate_ue_context_release(self, msg):
        """
        Validate UE Context Release message and IEs.
        """
        self.logger.info("Validating UE Context Release message and IEs.")
        ie_release_cause = self.extract_ie(msg, "Release Cause")
        assert ie_release_cause is not None, "Release Cause IE missing"
        self.logger.info(f"Release Cause IE validated: {ie_release_cause}")

    def validate_detach_request(self, msg):
        """
        Validate Detach Request NAS message and IEs.
        """
        self.logger.info("Validating Detach Request NAS message and IEs.")
        ie_detach_type = self.extract_ie(msg, "Detach Type")
        ie_nas_seq_num = self.extract_ie(msg, "Sequence Number")
        assert ie_detach_type in ["UE Initiated", "Switch Off"], f"Invalid Detach Type: {ie_detach_type}"
        self.logger.info(f"Detach Type validated: {ie_detach_type}")
        assert ie_nas_seq_num is not None, "Sequence Number IE missing"
        self.logger.info(f"Sequence Number IE validated: {ie_nas_seq_num}")

    def validate_detach_accept(self, msg):
        """
        Validate Detach Accept NAS message and IEs.
        """
        self.logger.info("Validating Detach Accept NAS message and IEs.")
        ie_emm_cause = self.extract_ie(msg, "EMM Cause")
        assert ie_emm_cause == "0", f"Detach Accept EMM Cause not success: {ie_emm_cause}"
        self.logger.info("EMM Cause validated as success (0).")

    def extract_ie(self, msg, ie_name):
        """
        Extract a specific Information Element (IE) from the message.
        This would parse the message structure/logs to extract IE values.
        """
        # Simplified example extraction logic:
        # Assuming msg is a dictionary or string containing IE info in a known format.
        if isinstance(msg, dict):
            return msg.get(ie_name)
        elif isinstance(msg, str):
            # Example: parse lines for 'IEName: value'
            for line in msg.splitlines():
                if line.startswith(ie_name + ":"):
                    return line.split(":", 1)[1].strip()
        return None

    def power_off_ue(self):
        """
        Power OFF the UE to trigger detach procedure.
        """
        self.logger.info("Powering OFF UE to start detach procedure.")
        self.ue.power_off()

    def wait_for_detach_accept(self, timeout=60):
        """
        Wait for Detach Accept message from UE logs within timeout.
        Returns True if detach accept received, False otherwise.
        """
        self.logger.info("Waiting for Detach Accept message in UE logs.")
        start_time = time.time()
        while time.time() - start_time < timeout:
            msg = self.ue.get_next_log_message()
            if msg and self.is_detach_accept(msg):
                self.logger.info("Detach Accept message received.")
                return True
            time.sleep(1)
        return False

    def is_detach_accept(self, msg):
        """
        Detect if the given log message corresponds to detach accept.
        """
        return "Detach Accept" in msg

    def run_attach_detach_test(self):
        """
        Run full attach-detach test for configured number of iterations.
        Collect KPIs and log results.
        """
        self.logger.info(f"Starting attach-detach test for {self.iterations} iterations.")
        for i in range(1, self.iterations + 1):
            self.logger.info(f"Iteration {i} start.")
            self.ue.clear_logs()
            # Start logging capture
            self.ue.start_logging()
            # Trigger attach
            if not self.trigger_attach():
                self.logger.error(f"Iteration {i}: Attach failed.")
                continue
            # Validate attach messages and IEs from logs
            attach_msgs = self.ue.get_attach_procedure_messages()
            for msg_type, msg in attach_msgs:
                if msg_type == "Attach Request":
                    self.validate_attach_request(msg)
                elif msg_type == "RRC Connection Setup":
                    self.validate_rrc_connection_setup(msg)
                elif msg_type == "RRC Connection Setup Complete":
                    self.validate_rrc_connection_setup_complete(msg)
                elif msg_type == "Attach Accept":
                    self.validate_attach_accept(msg)
                elif msg_type == "Security Mode Command":
                    self.validate_security_mode_command(msg)
                elif msg_type == "Security Mode Complete":
                    self.validate_security_mode_complete(msg)
                elif msg_type == "ESM Information Request":
                    self.validate_esm_information_request(msg)
                elif msg_type == "ESM Information Response":
                    self.validate_esm_information_response(msg)
                elif msg_type == "Default EPS Bearer Context Accept":
                    self.validate_default_eps_bearer_context_accept(msg)
                elif msg_type == "SgNB Addition Request":
                    self.validate_secondary_node_addition(msg)
                # Add other attach message validations as needed

            # Power off UE to trigger detach
            self.power_off_ue()
            if not self.wait_for_detach_accept(timeout=60):
                self.logger.error(f"Iteration {i}: Detach Accept not received.")
                continue
            # Validate detach messages and IEs from logs
            detach_msgs = self.ue.get_detach_procedure_messages()
            for msg_type, msg in detach_msgs:
                if msg_type == "Detach Request":
                    self.validate_detach_request(msg)
                elif msg_type == "Detach Accept":
                    self.validate_detach_accept(msg)
                elif msg_type == "RRC Connection Release":
                    self.validate_rrc_connection_release(msg)
                elif msg_type == "UE Context Release":
                    self.validate_ue_context_release(msg)
                # Add other detach message validations as needed
            self.detach_success_count += 1
            # Stop logging capture and save logs
            self.ue.stop_logging()
            self.logger.info(f"Iteration {i} complete.")

        self.report_results()

    def report_results(self):
        """
        Report test KPIs including success rates and latency metrics.
        """
        attach_success_rate = (self.attach_success_count / self.iterations) * 100
        detach_success_rate = (self.detach_success_count / self.iterations) * 100
        latencies_sorted = sorted(self.attach_latencies)
        min_latency = latencies_sorted[0] if latencies_sorted else None
        max_latency = latencies_sorted[-1] if latencies_sorted else None
        avg_latency = sum(latencies_sorted) / len(latencies_sorted) if latencies_sorted else None

        self.logger.info("=== Attach-Detach Test Summary ===")
        self.logger.info(f"Total Iterations: {self.iterations}")
        self.logger.info(f"Attach Success Rate: {attach_success_rate:.2f}%")
        self.logger.info(f"Detach Success Rate: {detach_success_rate:.2f}%")
        if min_latency is not None:
            self.logger.info(f"Attach Latency - Min: {min_latency:.2f}s, Avg: {avg_latency:.2f}s, Max: {max_latency:.2f}s")
        else:
            self.logger.info("No attach latency data collected.")

# Usage example:
# Assuming ue_interface is an instantiated object with required methods:
# test = UEAttachTest(ue_interface)
# test.run_attach_detach_test()
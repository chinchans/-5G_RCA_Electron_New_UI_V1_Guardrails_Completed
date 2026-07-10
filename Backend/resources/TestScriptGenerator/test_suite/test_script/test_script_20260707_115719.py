import time
import logging

# TC_POS_001: Validate successful LTE/5G NSA Attach and Detach of single UE

class UEAttachDetachTest:
    def __init__(self, ue_interface, logger=None):
        """
        ue_interface: object providing methods to interact with UE and network,
                      expected methods:
                      - power_on_ue()
                      - power_off_ue()
                      - wait_for_attach_success(timeout)
                      - wait_for_detach_success(timeout)
                      - get_attach_request_message()
                      - get_attach_complete_message()
                      - get_detach_request_message()
                      - get_detach_accept_message()
                      - get_secondary_node_addition_messages()
                      - get_secondary_node_release_messages()
                      - get_rrc_connection_setup_message()
                      - get_rrc_connection_release_message()
                      - get_ue_logs()
                      - get_radio_parameters()
                      - get_signaling_logs()
                      - get_all_messages()
        logger: optional logger instance
        """
        self.ue = ue_interface
        self.logger = logger or logging.getLogger(__name__)
        # KPI tracking variables
        self.attach_success_count = 0
        self.detach_success_count = 0
        self.secondary_node_addition_success_count = 0
        self.attach_latencies = []

    def log_info(self, msg):
        self.logger.info(msg)

    def log_error(self, msg):
        self.logger.error(msg)

    # Trigger UE attach procedure by powering on UE and waiting for attach success
    def trigger_ue_attach(self):
        self.log_info("Powering ON UE to start attach procedure")
        self.ue.power_on_ue()
        start_time = time.time()
        attach_success = self.ue.wait_for_attach_success(timeout=30)
        end_time = time.time()
        latency = end_time - start_time
        if attach_success:
            self.log_info(f"UE attach succeeded in {latency:.3f} seconds")
            self.attach_success_count += 1
            self.attach_latencies.append(latency)
        else:
            self.log_error("UE attach failed")
        return attach_success, latency

    # Validate Attach Request NAS and RRC message and all IEs within
    def validate_attach_request(self):
        self.log_info("Validating Attach Request message and IEs")
        msg = self.ue.get_attach_request_message()
        assert msg is not None, "Attach Request message not found"

        # Validate NAS Attach Request IEs (simplified example)
        nas = msg.get("nas", {})
        assert nas.get("attach_type") in ["EPS_ATTACH", "IMSI_ATTACH"], f"Unexpected attach_type: {nas.get('attach_type')}"
        assert nas.get("ue_id") is not None, "UE ID missing in NAS Attach Request"
        assert nas.get("supported_eps_bearer_contexts") is not None, "EPS bearer contexts missing"
        self.log_info(f"NAS Attach Request IEs validated: attach_type={nas.get('attach_type')}")

        # Validate RRC IEs in Attach Request message
        rrc = msg.get("rrc", {})
        assert rrc.get("establishment_cause") in ["mo_Signalling", "mo_Data"], f"Unexpected RRC establishment_cause: {rrc.get('establishment_cause')}"
        assert rrc.get("ue_identity") is not None, "UE Identity missing in RRC Attach Request"
        self.log_info(f"RRC IEs validated in Attach Request: establishment_cause={rrc.get('establishment_cause')}")

    # Validate Attach Complete NAS message and all IEs within
    def validate_attach_complete(self):
        self.log_info("Validating Attach Complete message and IEs")
        msg = self.ue.get_attach_complete_message()
        assert msg is not None, "Attach Complete message not found"

        nas = msg.get("nas", {})
        assert nas.get("emm_msg_type") == "AttachComplete", f"Unexpected NAS message type: {nas.get('emm_msg_type')}"
        assert nas.get("ue_id") is not None, "UE ID missing in NAS Attach Complete"
        self.log_info("NAS Attach Complete IEs validated")

        # Optional RRC confirmation messages validation
        rrc = msg.get("rrc", {})
        if rrc:
            assert rrc.get("rrc_transaction_id") is not None, "RRC transaction ID missing in Attach Complete"
            self.log_info("RRC IEs validated in Attach Complete")

    # Validate Secondary Node Addition messages for 5G NSA
    def validate_secondary_node_addition(self):
        self.log_info("Validating Secondary Node Addition messages and IEs")
        messages = self.ue.get_secondary_node_addition_messages()
        assert messages is not None and len(messages) > 0, "Secondary Node Addition messages missing"

        for msg in messages:
            # Validate SgNB Addition Request
            if msg.get("msg_type") == "SgNBAdditionRequest":
                ie = msg.get("ies", {})
                assert ie.get("sgnb_id") is not None, "SgNB ID missing in SgNB Addition Request"
                assert ie.get("data_forwarding_addresses") is not None, "Data forwarding addresses missing"
                self.log_info("SgNB Addition Request IEs validated")

            # Validate SgNB Reconfiguration Complete
            elif msg.get("msg_type") == "SgNBReconfigurationComplete":
                ie = msg.get("ies", {})
                assert ie.get("reconfiguration_status") == "success", "SgNB Reconfiguration did not complete successfully"
                self.secondary_node_addition_success_count += 1
                self.log_info("SgNB Reconfiguration Complete successfully validated")

    # Validate Detach Request NAS message and all IEs within
    def validate_detach_request(self):
        self.log_info("Validating Detach Request message and IEs")
        msg = self.ue.get_detach_request_message()
        assert msg is not None, "Detach Request message not found"

        nas = msg.get("nas", {})
        assert nas.get("emm_msg_type") == "DetachRequest", f"Unexpected NAS message type: {nas.get('emm_msg_type')}"
        assert nas.get("detach_type") in ["switch_off", "normal"], f"Unexpected detach_type: {nas.get('detach_type')}"
        self.log_info(f"NAS Detach Request IEs validated: detach_type={nas.get('detach_type')}")

    # Validate Detach Accept NAS message and all IEs within
    def validate_detach_accept(self):
        self.log_info("Validating Detach Accept message and IEs")
        msg = self.ue.get_detach_accept_message()
        assert msg is not None, "Detach Accept message not found"

        nas = msg.get("nas", {})
        assert nas.get("emm_msg_type") == "DetachAccept", f"Unexpected NAS message type: {nas.get('emm_msg_type')}"
        self.log_info("NAS Detach Accept IEs validated")

    # Validate Secondary Node Release messages for 5G NSA
    def validate_secondary_node_release(self):
        self.log_info("Validating Secondary Node Release messages and IEs")
        messages = self.ue.get_secondary_node_release_messages()
        assert messages is not None and len(messages) > 0, "Secondary Node Release messages missing"

        for msg in messages:
            if msg.get("msg_type") == "SgNBReleaseRequest":
                ie = msg.get("ies", {})
                assert ie.get("sgnb_id") is not None, "SgNB ID missing in SgNB Release Request"
                self.log_info("SgNB Release Request IEs validated")

            elif msg.get("msg_type") == "SgNBReleaseRequestAcknowledge":
                ie = msg.get("ies", {})
                assert ie.get("release_status") == "confirmed", "SgNB Release not confirmed"
                self.log_info("SgNB Release Request Acknowledge IEs validated")

            elif msg.get("msg_type") == "RRCConnectionReconfiguration":
                ie = msg.get("ies", {})
                assert ie.get("scg_release") is True, "SCG release flag missing or false in RRCConnectionReconfiguration"
                self.log_info("RRC Connection Reconfiguration IEs validated for SN release")

    # Validate RRC Connection Setup message and all IEs
    def validate_rrc_connection_setup(self):
        self.log_info("Validating RRC Connection Setup message and IEs")
        msg = self.ue.get_rrc_connection_setup_message()
        assert msg is not None, "RRC Connection Setup message not found"

        rrc = msg.get("rrc", {})
        assert rrc.get("configuration") is not None, "RRC configuration missing"
        assert "physical_config" in rrc.get("configuration"), "Physical config missing in RRC Connection Setup"
        self.log_info("RRC Connection Setup IEs validated")

    # Validate RRC Connection Release message and all IEs
    def validate_rrc_connection_release(self):
        self.log_info("Validating RRC Connection Release message and IEs")
        msg = self.ue.get_rrc_connection_release_message()
        assert msg is not None, "RRC Connection Release message not found"

        rrc = msg.get("rrc", {})
        assert rrc.get("release_cause") in ["ueRequested", "networkRequested"], f"Unexpected RRC release cause: {rrc.get('release_cause')}"
        self.log_info("RRC Connection Release IEs validated")

    # Run full attach-detach test for 10 iterations as per test procedure
    def run_attach_detach_test(self, iterations=10):
        attach_attempts = 0
        detach_attempts = 0
        secondary_node_additions = 0

        for i in range(iterations):
            self.log_info(f"Starting iteration {i+1} of {iterations}")

            # Trigger attach procedure
            attach_success, latency = self.trigger_ue_attach()
            assert attach_success, f"Attach failed on iteration {i+1}"

            # Validate messages in attach sequence
            self.validate_attach_request()
            self.validate_rrc_connection_setup()
            self.validate_attach_complete()
            self.validate_secondary_node_addition()

            # Record attach KPI
            attach_attempts += 1

            # Power off UE to trigger detach
            self.log_info("Powering OFF UE to start detach procedure")
            self.ue.power_off_ue()
            detach_success = self.ue.wait_for_detach_success(timeout=30)
            assert detach_success, f"Detach failed on iteration {i+1}"

            # Validate detach messages
            self.validate_detach_request()
            self.validate_secondary_node_release()
            self.validate_detach_accept()
            self.validate_rrc_connection_release()

            detach_attempts += 1
            secondary_node_additions += self.secondary_node_addition_success_count

            # Reset secondary node addition count for next iteration
            self.secondary_node_addition_success_count = 0

            self.log_info(f"Iteration {i+1} passed successfully")

        # Calculate attach latency KPIs
        lat_min = min(self.attach_latencies)
        lat_max = max(self.attach_latencies)
        lat_avg = sum(self.attach_latencies) / len(self.attach_latencies)

        # Log KPIs summary
        self.log_info(f"Attach success rate: {attach_attempts / iterations * 100:.1f}%")
        self.log_info(f"Detach success rate: {detach_attempts / iterations * 100:.1f}%")
        self.log_info(f"Secondary node addition success rate: {secondary_node_additions / iterations * 100:.1f}%")
        self.log_info(f"Attach latency (seconds): min={lat_min:.3f}, avg={lat_avg:.3f}, max={lat_max:.3f}")

        # Final assertion to ensure 100% pass rate
        assert attach_attempts == iterations, "Not all attach attempts succeeded"
        assert detach_attempts == iterations, "Not all detach attempts succeeded"
        assert secondary_node_additions == iterations, "Not all secondary node additions succeeded"

        self.log_info("Attach-Detach test completed successfully for all iterations")
import time
import logging

class UEAttachDetachTest:
    def __init__(self, ue, logger=None):
        """
        ue: UE interface object with methods to power on/off, send/receive messages, and access logs
        logger: optional logger instance
        """
        self.ue = ue
        self.logger = logger or logging.getLogger(__name__)
        self.attach_iterations = 10
        self.attach_latencies = []
        self.attach_success_count = 0
        self.detach_success_count = 0
        self.sec_node_add_success_count = 0  # For 5G NSA
        self.sec_node_rel_success_count = 0  # For 5G NSA

    def log(self, msg):
        self.logger.info(msg)
        print(msg)

    def validate_ie(self, ie_name, ie_value, expected_value=None, mandatory=True):
        """
        Validate an Information Element (IE) value.
        If expected_value is given, assert equality.
        """
        if ie_value is None:
            if mandatory:
                self.log(f"ERROR: Mandatory IE '{ie_name}' is missing")
                raise AssertionError(f"Mandatory IE '{ie_name}' missing")
            else:
                self.log(f"WARNING: Optional IE '{ie_name}' is missing")
                return False
        else:
            self.log(f"IE '{ie_name}': '{ie_value}'")
            if expected_value is not None:
                assert ie_value == expected_value, f"IE '{ie_name}' value '{ie_value}' != expected '{expected_value}'"
            return True

    def start_logs(self):
        self.log("Starting logs to capture call flow and signalling messages")
        self.ue.start_logging()

    def stop_logs(self):
        self.log("Stopping and saving test logs")
        self.ue.stop_logging()
        self.ue.save_logs()

    def power_on_ue(self):
        self.log("Powering ON the UE to start attach procedure")
        self.ue.power_on()

    def power_off_ue(self):
        self.log("Powering OFF the UE to start detach procedure")
        self.ue.power_off()

    def wait_for_attach_complete(self, timeout=30):
        self.log("Waiting for attach complete confirmation")
        attach_complete = self.ue.wait_for_event("ATTACH_COMPLETE", timeout)
        if not attach_complete:
            self.log("Attach complete event NOT received within timeout")
            return False
        self.log("Attach complete event received")
        return True

    def wait_for_detach_complete(self, timeout=30):
        self.log("Waiting for detach complete confirmation")
        detach_complete = self.ue.wait_for_event("DETACH_COMPLETE", timeout)
        if not detach_complete:
            self.log("Detach complete event NOT received within timeout")
            return False
        self.log("Detach complete event received")
        return True

    # === Message validation functions ===
    # Each function simulates the exchange, extracts and validates all relevant IEs, and logs results.

    def send_attach_request(self):
        self.log("Sending Attach Request message")
        msg = self.ue.send_message("AttachRequest")
        # Validate IEs in Attach Request (example IEs)
        ies = msg.get("IEs", {})
        self.validate_ie("EPS Attach Type", ies.get("EPS Attach Type"))
        self.validate_ie("NAS Key Set Identifier", ies.get("NAS Key Set Identifier"))
        self.validate_ie("UE Network Capability", ies.get("UE Network Capability"))
        self.validate_ie("EPS Mobile Identity", ies.get("EPS Mobile Identity"))
        self.validate_ie("PDN Connectivity Request", ies.get("PDN Connectivity Request"), mandatory=False)
        self.log("Attach Request message validated successfully")

    def receive_attach_accept(self):
        self.log("Receiving Attach Accept message")
        msg = self.ue.receive_message("AttachAccept", timeout=30)
        assert msg is not None, "Attach Accept message not received"
        ies = msg.get("IEs", {})
        self.validate_ie("EPS Mobile Identity", ies.get("EPS Mobile Identity"))
        self.validate_ie("T3412 Value", ies.get("T3412 Value"))
        self.validate_ie("EPS Network Feature Support", ies.get("EPS Network Feature Support"), mandatory=False)
        self.validate_ie("PDN Address Allocation", ies.get("PDN Address Allocation"))
        self.validate_ie("ESM Message Container", ies.get("ESM Message Container"), mandatory=False)
        self.log("Attach Accept message validated successfully")

    def send_attach_complete(self):
        self.log("Sending Attach Complete message")
        msg = self.ue.send_message("AttachComplete")
        ie = msg.get("IEs", {})
        self.validate_ie("EPS Mobile Identity", ie.get("EPS Mobile Identity"))
        self.log("Attach Complete message validated successfully")

    def send_detach_request(self):
        self.log("Sending Detach Request message")
        msg = self.ue.send_message("DetachRequest")
        ies = msg.get("IEs", {})
        self.validate_ie("Detach Type", ies.get("Detach Type"))
        self.validate_ie("EPS Mobile Identity", ies.get("EPS Mobile Identity"))
        self.log("Detach Request message validated successfully")

    def receive_detach_accept(self):
        self.log("Receiving Detach Accept message")
        msg = self.ue.receive_message("DetachAccept", timeout=30)
        assert msg is not None, "Detach Accept message not received"
        ies = msg.get("IEs", {})
        self.validate_ie("EPS Mobile Identity", ies.get("EPS Mobile Identity"))
        self.log("Detach Accept message validated successfully")

    def validate_rrc_connection_setup(self, msg):
        self.log("Validating RRC Connection Setup message")
        ies = msg.get("IEs", {})
        self.validate_ie("RRC Transaction Identifier", ies.get("RRC Transaction Identifier"))
        self.validate_ie("Radio Resource Config", ies.get("Radio Resource Config"))
        self.log("RRC Connection Setup message validated successfully")

    def validate_rrc_connection_setup_complete(self, msg):
        self.log("Validating RRC Connection Setup Complete message")
        ies = msg.get("IEs", {})
        self.validate_ie("RRC Transaction Identifier", ies.get("RRC Transaction Identifier"))
        self.validate_ie("NAS Message", ies.get("NAS Message"))
        self.log("RRC Connection Setup Complete message validated successfully")

    def validate_secondary_node_addition(self, msg):
        self.log("Validating Secondary Node Addition (SgNB Addition Request and Reconfiguration Complete)")
        ies = msg.get("IEs", {})
        self.validate_ie("SgNB Addition Request", ies.get("SgNB Addition Request"))
        self.validate_ie("SgNB Reconfiguration Complete", ies.get("SgNB Reconfiguration Complete"))
        self.log("Secondary Node Addition validated successfully")

    def validate_secondary_node_release(self, msg):
        self.log("Validating Secondary Node Release (SgNB Release Request and Acknowledge)")
        ies = msg.get("IEs", {})
        self.validate_ie("SgNB Release Request", ies.get("SgNB Release Request"))
        self.validate_ie("SgNB Release Request Acknowledge", ies.get("SgNB Release Request Acknowledge"))
        self.log("Secondary Node Release validated successfully")

    def run_attach_detach_iteration(self, iteration):
        self.log(f"Starting iteration {iteration+1} of attach-detach procedure")

        # Start logs
        self.start_logs()

        # Power on UE and start attach
        self.power_on_ue()
        attach_start_time = time.time()

        # Send Attach Request
        self.send_attach_request()

        # Receive Attach Accept
        self.receive_attach_accept()

        # Send Attach Complete
        self.send_attach_complete()

        attached = self.wait_for_attach_complete()
        attach_end_time = time.time()

        attach_latency = attach_end_time - attach_start_time
        self.attach_latencies.append(attach_latency)
        self.log(f"Attach latency for iteration {iteration+1}: {attach_latency:.3f} seconds")

        if attached:
            self.attach_success_count += 1
        else:
            self.log(f"Attach failed at iteration {iteration+1}")
            self.stop_logs()
            raise AssertionError("Attach failed")

        # Simulate Secondary Node Addition for 5G NSA if applicable
        if self.ue.is_5g_nsa():
            sec_node_msg = self.ue.receive_message("SecondaryNodeAddition", timeout=10)
            assert sec_node_msg is not None, "Secondary Node Addition message not received"
            self.validate_secondary_node_addition(sec_node_msg)
            self.sec_node_add_success_count += 1

        # Power off UE to start detach
        self.power_off_ue()

        # Send Detach Request
        self.send_detach_request()

        # Receive Detach Accept
        self.receive_detach_accept()

        detached = self.wait_for_detach_complete()
        if detached:
            self.detach_success_count += 1
        else:
            self.log(f"Detach failed at iteration {iteration+1}")
            self.stop_logs()
            raise AssertionError("Detach failed")

        # Simulate Secondary Node Release for 5G NSA if applicable
        if self.ue.is_5g_nsa():
            sec_node_rel_msg = self.ue.receive_message("SecondaryNodeRelease", timeout=10)
            assert sec_node_rel_msg is not None, "Secondary Node Release message not received"
            self.validate_secondary_node_release(sec_node_rel_msg)
            self.sec_node_rel
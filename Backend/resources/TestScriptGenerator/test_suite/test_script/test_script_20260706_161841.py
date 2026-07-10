import logging
import time

# Configure logger for test traceability and debug
logger = logging.getLogger("UEAttachTest")
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
ch.setFormatter(formatter)
logger.addHandler(ch)


class UEAttachTest:
    # TC_POS_001: Validate successful LTE/5G NSA Attach and Detach of single UE

    def __init__(self, ue_interface, test_config):
        """
        Initialize test with UE interface and test configuration parameters.
        :param ue_interface: Object controlling the UE power and log retrieval.
        :param test_config: Configuration dictionary including expected cell info and parameters.
        """
        self.ue = ue_interface
        self.config = test_config
        self.attach_latencies = []
        self.attach_success_count = 0
        self.detach_success_count = 0
        self.secondary_node_add_success_count = 0

    def trigger_ue_power_on(self):
        logger.info("Power ON UE to start attach procedure")
        self.ue.power_on()
        logger.debug("UE powered ON")

    def trigger_ue_power_off(self):
        logger.info("Power OFF UE to start detach procedure")
        self.ue.power_off()
        logger.debug("UE powered OFF")

    def start_logging(self):
        logger.info("Starting logs capture for call flow and signaling")
        self.ue.start_logs()

    def stop_logging(self):
        logger.info("Stopping logs capture and saving logs")
        logs = self.ue.stop_logs()
        logger.debug("Logs captured and saved")
        return logs

    # Validation methods for each signaling message and IE extraction/validation

    # Attach Request message validation
    def validate_attach_request(self, message):
        """
        Validate Attach Request NAS message IEs.
        Expected IEs:
            - UE Network Capability
            - EPS Attach Type
            - Old GUTI or IMSI
            - PDN Connectivity Request
        """
        logger.info("Validating Attach Request message")
        try:
            ie_ue_network_capability = message.get("UE Network Capability")
            ie_eps_attach_type = message.get("EPS Attach Type")
            ie_identity = message.get("Identity")  # IMSI or GUTI
            ie_pdn_conn_req = message.get("PDN Connectivity Request")

            assert ie_ue_network_capability is not None, "Missing UE Network Capability IE"
            assert ie_eps_attach_type in ["EPS Attach", "Combined EPS/IMSI Attach"], "Invalid EPS Attach Type"
            assert ie_identity is not None, "Missing Identity IE"
            assert ie_pdn_conn_req is not None, "Missing PDN Connectivity Request IE"

            logger.debug(f"Attach Request IEs validated: UE Network Capability={ie_ue_network_capability},"
                         f" EPS Attach Type={ie_eps_attach_type}, Identity={ie_identity}, PDN Connectivity Request={ie_pdn_conn_req}")
            return True
        except AssertionError as e:
            logger.error(f"Attach Request validation failed: {str(e)}")
            return False

    # Attach Accept message validation
    def validate_attach_accept(self, message):
        """
        Validate Attach Accept NAS message IEs.
        Expected IEs:
            - EPS Mobile Identity (GUTI)
            - T3412 timer value
            - PDN Address Allocation
            - ESM message container (PDN connectivity accept)
        """
        logger.info("Validating Attach Accept message")
        try:
            ie_eps_mobile_identity = message.get("EPS Mobile Identity")
            ie_t3412 = message.get("T3412 value")
            ie_pdn_address = message.get("PDN Address Allocation")
            ie_esm_msg_container = message.get("ESM message container")

            assert ie_eps_mobile_identity is not None, "Missing EPS Mobile Identity IE"
            assert ie_t3412 is not None, "Missing T3412 timer IE"
            assert ie_pdn_address is not None, "Missing PDN Address Allocation IE"
            assert ie_esm_msg_container is not None, "Missing ESM message container IE"

            logger.debug(f"Attach Accept IEs validated: EPS Mobile Identity={ie_eps_mobile_identity},"
                         f" T3412={ie_t3412}, PDN Address={ie_pdn_address}, ESM msg container present")
            return True
        except AssertionError as e:
            logger.error(f"Attach Accept validation failed: {str(e)}")
            return False

    # Secondary Node Addition Request validation for 5G NSA (EN-DC)
    def validate_secondary_node_addition_request(self, message):
        """
        Validate Secondary Node Addition Request (SgNB Addition Request) message IEs.
        Expected IEs:
            - SgNB ID
            - NR Cell ID
            - RRC Reconfiguration parameters
        """
        logger.info("Validating Secondary Node Addition Request message")
        try:
            ie_sgnb_id = message.get("SgNB ID")
            ie_nr_cell_id = message.get("NR Cell ID")
            ie_rrc_reconfig = message.get("RRC Reconfiguration")

            assert ie_sgnb_id is not None, "Missing SgNB ID IE"
            assert ie_nr_cell_id is not None, "Missing NR Cell ID IE"
            assert ie_rrc_reconfig is not None, "Missing RRC Reconfiguration IE"

            logger.debug(f"SgNB Addition Request IEs validated: SgNB ID={ie_sgnb_id}, NR Cell ID={ie_nr_cell_id}, RRC Reconfiguration present")
            return True
        except AssertionError as e:
            logger.error(f"Secondary Node Addition Request validation failed: {str(e)}")
            return False

    # Secondary Node Addition Complete validation
    def validate_secondary_node_addition_complete(self, message):
        """
        Validate Secondary Node Addition Complete (SgNB Reconfiguration Complete) message IEs.
        Expected IEs:
            - Confirmation of SgNB Addition
        """
        logger.info("Validating Secondary Node Addition Complete message")
        try:
            ie_confirmation = message.get("SgNB Addition Confirmation")

            assert ie_confirmation is True, "SgNB Addition not confirmed"

            logger.debug("Secondary Node Addition Complete validated: Addition confirmed")
            return True
        except AssertionError as e:
            logger.error(f"Secondary Node Addition Complete validation failed: {str(e)}")
            return False

    # Detach Request message validation
    def validate_detach_request(self, message):
        """
        Validate Detach Request NAS message IEs.
        Expected IEs:
            - Detach Type
            - EPS Mobile Identity or IMSI
        """
        logger.info("Validating Detach Request message")
        try:
            ie_detach_type = message.get("Detach Type")
            ie_identity = message.get("Identity")

            assert ie_detach_type in ["EPS Detach", "Combined EPS/IMSI Detach"], "Invalid Detach Type"
            assert ie_identity is not None, "Missing Identity IE"

            logger.debug(f"Detach Request IEs validated: Detach Type={ie_detach_type}, Identity={ie_identity}")
            return True
        except AssertionError as e:
            logger.error(f"Detach Request validation failed: {str(e)}")
            return False

    # Detach Accept message validation
    def validate_detach_accept(self, message):
        """
        Validate Detach Accept NAS message IEs.
        Expected IE:
            - Detach Accept confirmation
        """
        logger.info("Validating Detach Accept message")
        try:
            ie_detach_accept = message.get("Detach Accept")

            assert ie_detach_accept is True, "Detach Accept not confirmed"

            logger.debug("Detach Accept validated: Detach confirmed")
            return True
        except AssertionError as e:
            logger.error(f"Detach Accept validation failed: {str(e)}")
            return False

    # Validate UE context release and RRC connection release signaling messages for detach
    def validate_rrc_connection_release(self, message):
        """
        Validate RRC Connection Release message.
        Expected IEs:
            - Release cause
            - UE Context Release indication
        """
        logger.info("Validating RRC Connection Release message")
        try:
            ie_release_cause = message.get("Release Cause")
            ie_ue_context_release = message.get("UE Context Release")

            assert ie_release_cause is not None, "Missing Release Cause IE"
            assert ie_ue_context_release is True, "UE Context Release indication missing"

            logger.debug(f"RRC Connection Release validated: Release Cause={ie_release_cause}, UE Context Release confirmed")
            return True
        except AssertionError as e:
            logger.error(f"RRC Connection Release validation failed: {str(e)}")
            return False

    # Validate SN Release Request and Acknowledge for Secondary Node Release (5G NSA Detach)
    def validate_secondary_node_release(self, request_msg, acknowledge_msg):
        """
        Validate SN Release Request and Acknowledge messages.
        Expected IEs in request:
            - SgNB Release Request message
        Expected IEs in acknowledge:
            - SgNB Release Request Acknowledge message
        """
        logger.info("Validating Secondary Node Release procedure messages")
        try:
            ie_request = request_msg.get("SgNB Release Request")
            ie_ack = acknowledge_msg.get("SgNB Release Request Acknowledge")

            assert ie_request is True, "Missing or invalid SgNB Release Request message"
            assert ie_ack is True, "Missing or invalid SgNB Release Request Acknowledge message"

            logger.debug("Secondary Node Release validated: Request and Acknowledge confirmed")
            return True
        except AssertionError as e:
            logger.error(f"Secondary Node Release validation failed: {str(e)}")
            return False

    # Utility to measure attach latency from attach request to attach complete
    def measure_attach_latency(self, start_time, end_time):
        latency = end_time - start_time
        self.attach_latencies.append(latency)
        logger.info(f"Measured attach latency: {latency:.3f} seconds")
        return latency

    # Run one iteration of attach-detach procedure with full validations
    def run_single_attach_detach_iteration(self):
        self.start_logging()

        self.trigger_ue_power_on()
        attach_start_time = time.time()

        attach_request_msg = self.ue.wait_for_message("Attach Request")
        if not self.validate_attach_request(attach_request_msg):
            logger.error("Attach Request validation failed")
            self.trigger_ue_power_off()
            self.stop_logging()
            return False

        attach_accept_msg = self.ue.wait_for_message("Attach Accept")
        if not self.validate_attach_accept(attach_accept_msg):
            logger.error("Attach Accept validation failed")
            self.trigger_ue_power_off()
            self.stop_logging()
            return False

        secondary_node_add_req_msg = self.ue.wait_for_message("Secondary Node Addition Request")
        if not self.validate_secondary_node_addition_request(secondary_node_add_req_msg):
            logger.error("Secondary Node Addition Request validation failed")
            self.trigger_ue_power_off()
            self.stop_logging()
            return False

        secondary_node_add_complete_msg = self.ue.wait_for_message("Secondary Node Addition Complete")
        if not self.validate_secondary_node_addition_complete(secondary_node_add_complete_msg):
            logger.error("Secondary Node Addition Complete validation failed")
            self.trigger_ue_power_off()
            self.stop_logging()
            return False

        attach_end_time = time.time()
        self.measure_attach_latency(attach_start_time, attach_end_time)
        self.attach_success_count += 1
        logger.info("Attach procedure completed successfully")

        self.trigger_ue_power_off()

        detach_request_msg = self.ue.wait_for_message("Detach Request")
        if not self.validate_detach_request(detach_request_msg):
            logger.error("Detach Request validation failed")
            self.stop_logging()
            return False

        detach_accept_msg = self.ue.wait_for_message("Detach Accept")
        if not self.validate_detach_accept(detach_accept_msg):
            logger.error("Detach Accept validation failed")
            self.stop_logging()
            return False

        rrc_conn_release_msg = self.ue.wait_for_message("RRC Connection Release")
        if not self.validate_rrc_connection_release(rrc_conn_release_msg):
            logger.error("RRC Connection Release validation failed")
            self.stop_logging()
            return False

        # Validate Secondary Node Release messages for 5G NSA
        sn_release_req_msg = self.ue.wait_for_message("Secondary Node Release Request")
        sn_release_ack_msg = self.ue.wait_for_message("Secondary Node Release Acknowledge")
        if not self.validate_secondary_node_release(sn_release_req_msg, sn_release_ack_msg):
            logger.error("Secondary Node Release validation failed")
            self.stop_logging()
            return False

        self.detach_success_count += 1
        logger.info("Detach procedure completed successfully")

        self.stop_logging()

        return True

    def run_test(self, iterations=10):
        logger.info(f"Starting attach-detach test for {iterations} iterations under excellent radio conditions")
        for i in range(1, iterations + 1):
            logger.info(f"Starting iteration {i}")
            success = self.run_single_attach_detach_iteration()
            if not success:
                logger.error(f"Iteration {i} failed. Test case marked as FAIL")
                break
            logger.info(f"Iteration {i} passed")

        # Calculate latency KPIs
        if self.attach_latencies:
            sorted_latencies = sorted(self.attach_latencies)
            min_latency = sorted_latencies[0]
            max_latency = sorted_latencies[-1]
            avg_latency = sum(sorted_latencies) / len(sorted_latencies)
            logger.info(f"Attach Latency (s) - Min: {min_latency:.3f}, Avg: {avg_latency:.3f}, Max: {max_latency:.3f}")
        else:
            logger.warning("No attach latencies recorded")

        # Calculate success rates
        attach_success_rate = (self.attach_success_count / iterations) * 100
        detach_success_rate = (self.detach_success_count / iterations) * 100

        logger.info(f"Attach Success Rate: {attach_success_rate:.2f}%")
        logger.info(f"Detach Success Rate: {detach_success_rate:.2f}%")

        if attach_success_rate == 100 and detach_success_rate == 100:
            logger.info("Test case PASSED: All iterations successful")
        else:
            logger.warning("Test case FAILED: Some iterations failed")

        return {
            "attach_success_rate": attach_success_rate,
            "detach_success_rate": detach_success_rate,
            "attach_latency_min": min_latency if self.attach_latencies else None,
            "attach_latency_avg": avg_latency if self.attach_latencies else None,
            "attach_latency_max": max_latency if self.attach_latencies else None,
        }
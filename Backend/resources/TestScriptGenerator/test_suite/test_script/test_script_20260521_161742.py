import logging
import unittest

# Assume ue_attach_utils provides utilities for triggering attach and validating messages
from ue_attach_utils import (
    trigger_ue_attach,
    send_message,
    receive_message,
    extract_ies,
    validate_ie,
    log_step,
    assert_ie_equal,
)

logger = logging.getLogger("SecondaryNodeReleaseTest")
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)


class SecondaryNodeReleaseTest(unittest.TestCase):

    def setUp(self):
        # Trigger the initial UE attach procedure using the reference code
        logger.info("Triggering UE Attach procedure")
        attach_result = trigger_ue_attach()
        self.assertTrue(attach_result, "UE Attach procedure failed")
        logger.info("UE Attach procedure completed successfully")

    def test_mn_initiated_sn_release(self):
        """
        Test MN initiated Secondary Node Release procedure according to Figure 10.4.1-1
        """

        # Step 1: MN sends SgNB Release Request message
        logger.info("Step 1: MN sends SgNB Release Request message")
        sgNB_release_request_msg = self._build_sgnb_release_request()
        send_message(sgNB_release_request_msg)
        log_step("Sent SgNB Release Request message")

        # Step 2: SN responds with SgNB Release Request Acknowledge message
        logger.info("Step 2: SN sends SgNB Release Request Acknowledge message")
        ack_msg = receive_message("SgNB Release Request Acknowledge")
        self._validate_sgnb_release_request_acknowledge(ack_msg)
        log_step("Received and validated SgNB Release Request Acknowledge message")

        # Step 3/4: MN sends RRCConnectionReconfiguration to UE indicating SCG release
        logger.info("Step 3/4: MN sends RRCConnectionReconfiguration message to UE")
        rrc_reconfig_msg = self._build_rrc_connection_reconfiguration(release_scg=True)
        send_message(rrc_reconfig_msg)
        log_step("Sent RRCConnectionReconfiguration message to UE")

        # Here we would wait for UE response or failure procedure if UE unable to comply
        ue_response_msg = receive_message("UE RRC Reconfiguration Response or Failure", timeout=5)
        self._validate_rrc_reconfiguration_response(ue_response_msg)
        log_step("Validated UE RRC Reconfiguration Response or Failure")

        # Step 5: SN sends SN Status Transfer message for RLC AM bearers
        logger.info("Step 5: SN sends SN Status Transfer message")
        sn_status_transfer_msg = receive_message("SN Status Transfer")
        self._validate_sn_status_transfer(sn_status_transfer_msg)
        log_step("Validated SN Status Transfer message")

        # Step 6: Data forwarding from SN to MN starts
        logger.info("Step 6: Data forwarding from SN to MN starts")
        data_forwarding_started = self._check_data_forwarding_started()
        self.assertTrue(data_forwarding_started, "Data forwarding did not start as expected")
        log_step("Data forwarding started confirmed")

        # Step 7: SN sends Secondary RAT Data Usage Report message
        logger.info("Step 7: SN sends Secondary RAT Data Usage Report message")
        rat_data_usage_report_msg = receive_message("Secondary RAT Data Usage Report")
        self._validate_secondary_rat_data_usage_report(rat_data_usage_report_msg)
        log_step("Validated Secondary RAT Data Usage Report message")

        # Step 8: If applicable, path update procedure initiated
        logger.info("Step 8: Path update procedure")
        path_update_msg = receive_message("Path Update Procedure", optional=True)
        if path_update_msg:
            self._validate_path_update(path_update_msg)
            log_step("Validated Path Update Procedure message")
        else:
            logger.info("No Path Update Procedure message received - optional step")

        # Step 9: SN receives UE Context Release message and releases resources
        logger.info("Step 9: SN receives UE Context Release message")
        ue_context_release_msg = receive_message("UE Context Release")
        self._validate_ue_context_release(ue_context_release_msg)
        log_step("Validated UE Context Release message")

    def test_sn_initiated_sn_release(self):
        """
        Test SN initiated Secondary Node Release procedure according to Figure 10.4.1-2
        """

        # Step 1: SN sends SgNB Release Required message
        logger.info("Step 1: SN sends SgNB Release Required message")
        sgnb_release_required_msg = receive_message("SgNB Release Required")
        self._validate_sgnb_release_required(sgnb_release_required_msg)
        log_step("Validated SgNB Release Required message")

        # Step 2: MN sends SgNB Release Confirm message with data forwarding addresses
        logger.info("Step 2: MN sends SgNB Release Confirm message")
        sgnb_release_confirm_msg = self._build_sgnb_release_confirm()
        send_message(sgnb_release_confirm_msg)
        log_step("Sent SgNB Release Confirm message")

        # SN may start data forwarding and stop providing user data to UE
        logger.info("SN starts data forwarding and stops user data to UE")

        # Step 3/4: MN sends RRCConnectionReconfiguration message towards UE
        logger.info("Step 3/4: MN sends RRCConnectionReconfiguration message to UE")
        rrc_reconfig_msg = self._build_rrc_connection_reconfiguration(release_scg=True)
        send_message(rrc_reconfig_msg)
        log_step("Sent RRCConnectionReconfiguration message to UE")

        # Wait for UE response or failure procedure
        ue_response_msg = receive_message("UE RRC Reconfiguration Response or Failure", timeout=5)
        self._validate_rrc_reconfiguration_response(ue_response_msg)
        log_step("Validated UE RRC Reconfiguration Response or Failure")

        # Step 5: SN sends SN Status Transfer message
        logger.info("Step 5: SN sends SN Status Transfer message")
        sn_status_transfer_msg = receive_message("SN Status Transfer")
        self._validate_sn_status_transfer(sn_status_transfer_msg)
        log_step("Validated SN Status Transfer message")

        # Step 6: Data forwarding from SN to MN starts
        logger.info("Step 6: Data forwarding from SN to MN starts")
        data_forwarding_started = self._check_data_forwarding_started()
        self.assertTrue(data_forwarding_started, "Data forwarding did not start as expected")
        log_step("Data forwarding started confirmed")

        # Step 7: SN sends Secondary RAT Data Usage Report message
        logger.info("Step 7: SN sends Secondary RAT Data Usage Report message")
        rat_data_usage_report_msg = receive_message("Secondary RAT Data Usage Report")
        self._validate_secondary_rat_data_usage_report(rat_data_usage_report_msg)
        log_step("Validated Secondary RAT Data Usage Report message")

        # Step 8: If applicable, path update procedure initiated
        logger.info("Step 8: Path update procedure")
        path_update_msg = receive_message("Path Update Procedure", optional=True)
        if path_update_msg:
            self._validate_path_update(path_update_msg)
            log_step("Validated Path Update Procedure message")
        else:
            logger.info("No Path Update Procedure message received - optional step")

        # Step 9: SN receives UE Context Release message and releases resources
        logger.info("Step 9: SN receives UE Context Release message")
        ue_context_release_msg = receive_message("UE Context Release")
        self._validate_ue_context_release(ue_context_release_msg)
        log_step("Validated UE Context Release message")

    # Helper functions to build and validate messages and IEs

    def _build_sgnb_release_request(self):
        """
        Build SgNB Release Request message with mandatory IEs including optional data forwarding addresses
        """
        msg = {
            "message_type": "SgNB Release Request",
            "data_forwarding_addresses": {
                "address_type": "IPv4",
                "address": "192.168.1.1"
            },
            "additional_info": "MN initiated release"
        }
        # Validate all IEs before sending
        self._validate_sgnb_release_request(msg)
        return msg

    def _validate_sgnb_release_request(self, msg):
        ies = extract_ies(msg)
        # Validate message type
        assert_ie_equal(ies.get("message_type"), "SgNB Release Request", "Message Type")
        # Validate data forwarding addresses IE presence and format
        dfa = ies.get("data_forwarding_addresses")
        self.assertIsNotNone(dfa, "Data Forwarding Addresses IE missing")
        validate_ie(dfa, {"address_type": str, "address": str}, "Data Forwarding Addresses")
        # Additional IE checks as per spec can be added here
        logger.info("Validated all IEs in SgNB Release Request message")

    def _validate_sgnb_release_request_acknowledge(self, msg):
        ies = extract_ies(msg)
        assert_ie_equal(ies.get("message_type"), "SgNB Release Request Acknowledge", "Message Type")
        # Check if SN rejects release
        reject_flag = ies.get("reject_flag", False)
        self.assertIn(reject_flag, [True, False], "Reject Flag IE invalid")
        # If reject_flag true, ensure reason IE present
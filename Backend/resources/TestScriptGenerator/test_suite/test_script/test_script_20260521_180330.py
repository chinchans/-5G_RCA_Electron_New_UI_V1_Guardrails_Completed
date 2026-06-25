import logging
import unittest

class UEAttachTest(unittest.TestCase):
    def setUp(self):
        # Setup logger
        self.logger = logging.getLogger("UEAttachTest")
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.DEBUG)

        # Initialize UE attach utilities from provided reference code
        from ue_attach_utils import UEAttachUtils
        self.attach_utils = UEAttachUtils()
        self.logger.info("Test setup complete.")

    def test_ue_attach_procedure(self):
        self.logger.info("Starting UE Attach Procedure Test")

        # Trigger UE Attach
        attach_response = self.attach_utils.trigger_ue_attach()
        self.logger.info("Attach triggered. Validating Attach Accept message")
        self.validate_attach_accept(attach_response)

        # Validate RRC Connection Setup
        rrc_conn_setup = self.attach_utils.get_rrc_connection_setup()
        self.logger.info("Validating RRC Connection Setup message")
        self.validate_rrc_connection_setup(rrc_conn_setup)

        # Validate RRC Connection Setup Complete
        rrc_conn_setup_complete = self.attach_utils.get_rrc_connection_setup_complete()
        self.logger.info("Validating RRC Connection Setup Complete message")
        self.validate_rrc_connection_setup_complete(rrc_conn_setup_complete)

        # Validate Initial UE Context Setup Request
        ue_ctx_setup_req = self.attach_utils.get_ue_context_setup_request()
        self.logger.info("Validating Initial UE Context Setup Request message")
        self.validate_ue_context_setup_request(ue_ctx_setup_req)

        # Validate Initial Context Setup Response
        ue_ctx_setup_resp = self.attach_utils.get_ue_context_setup_response()
        self.logger.info("Validating Initial Context Setup Response message")
        self.validate_ue_context_setup_response(ue_ctx_setup_resp)

        # Validate Attach Complete NAS message from UE
        attach_complete = self.attach_utils.get_attach_complete()
        self.logger.info("Validating NAS Attach Complete message")
        self.validate_attach_complete(attach_complete)

        # Validate Attach Accept Completion in MME
        attach_accept_complete = self.attach_utils.get_mme_attach_accept_complete()
        self.logger.info("Validating MME Attach Accept Completion")
        self.validate_mme_attach_accept_complete(attach_accept_complete)

        self.logger.info("UE Attach Procedure Test completed successfully")

    def validate_attach_accept(self, msg):
        # Validate NAS Attach Accept message IEs
        self.assertIn('emm_cause', msg, "EMM Cause IE missing")
        self.assertEqual(msg['emm_cause'], 0, "EMM Cause indicates failure")
        self.logger.info(f"EMM Cause IE validated: {msg['emm_cause']}")

        self.assertIn('t3412_timer', msg, "T3412 Timer IE missing")
        self.logger.info(f"T3412 Timer IE validated: {msg['t3412_timer']}")

        self.assertIn('tai_list', msg, "TAI List IE missing")
        self.assertTrue(len(msg['tai_list']) > 0, "TAI List IE is empty")
        self.logger.info(f"TAI List IE contains {len(msg['tai_list'])} items")

        self.assertIn('esm_message_container', msg, "ESM Message Container IE missing")
        esm_container = msg['esm_message_container']
        self.assertIn('pdn_address', esm_container, "PDN Address missing in ESM container")
        self.logger.info(f"PDN Address in ESM Message Container validated: {esm_container['pdn_address']}")

    def validate_rrc_connection_setup(self, msg):
        # Validate RRC Connection Setup message IEs
        self.assertIn('rrc_transaction_identifier', msg, "RRC Transaction Identifier missing")
        self.assertIsInstance(msg['rrc_transaction_identifier'], int, "Invalid RRC Transaction Identifier")
        self.logger.info(f"RRC Transaction Identifier: {msg['rrc_transaction_identifier']}")

        self.assertIn('radio_bearer_config', msg, "Radio Bearer Config missing")
        rb_cfg = msg['radio_bearer_config']
        self.assertIn('signalling_radio_bearers', rb_cfg, "Signalling Radio Bearers missing")
        self.assertTrue(len(rb_cfg['signalling_radio_bearers']) > 0, "No Signalling Radio Bearers configured")
        self.logger.info(f"Signalling Radio Bearers count: {len(rb_cfg['signalling_radio_bearers'])}")

        self.assertIn('meas_config', msg, "Measurement Configuration missing")
        self.logger.info("Measurement Configuration IE validated")

    def validate_rrc_connection_setup_complete(self, msg):
        # Validate RRC Connection Setup Complete message IEs
        self.assertIn('rrc_transaction_identifier', msg, "RRC Transaction Identifier missing")
        self.logger.info(f"RRC Transaction Identifier: {msg['rrc_transaction_identifier']}")

        self.assertIn('nas_pdu', msg, "NAS PDU missing in RRC Connection Setup Complete")
        nas_pdu = msg['nas_pdu']
        self.assertIn('attach_request', nas_pdu, "Attach Request missing in NAS PDU")
        self.logger.info("NAS Attach Request IE validated in RRC Connection Setup Complete")

    def validate_ue_context_setup_request(self, msg):
        # Validate Initial UE Context Setup Request IEs
        self.assertIn('mme_ue_s1ap_id', msg, "MME UE S1AP ID missing")
        self.assertIsInstance(msg['mme_ue_s1ap_id'], int, "Invalid MME UE S1AP ID")
        self.logger.info(f"MME UE S1AP ID: {msg['mme_ue_s1ap_id']}")

        self.assertIn('enb_ue_s1ap_id', msg, "eNB UE S1AP ID missing")
        self.assertIsInstance(msg['enb_ue_s1ap_id'], int, "Invalid eNB UE S1AP ID")
        self.logger.info(f"eNB UE S1AP ID: {msg['enb_ue_s1ap_id']}")

        self.assertIn('nas_pdu', msg, "NAS PDU missing")
        self.logger.info("NAS PDU IE present in UE Context Setup Request")

        self.assertIn('ue_aggregate_maximum_bitrate', msg, "UE Aggregate Maximum Bitrate missing")
        self.logger.info(f"UE Aggregate Maximum Bitrate validated: {msg['ue_aggregate_maximum_bitrate']}")

    def validate_ue_context_setup_response(self, msg):
        # Validate Initial UE Context Setup Response IEs
        self.assertIn('mme_ue_s1ap_id', msg, "MME UE S1AP ID missing")
        self.assertIn('enb_ue_s1ap_id', msg, "eNB UE S1AP ID missing")
        self.logger.info(f"UE Context Setup Response IDs: MME={msg['mme_ue_s1ap_id']}, eNB={msg['enb_ue_s1ap_id']}")

        self.assertIn('security_key', msg, "Security Key missing in UE Context Setup Response")
        self.logger.info("Security Key IE validated")

    def validate_attach_complete(self, msg):
        # Validate NAS Attach Complete message IEs
        self.assertIn('emm_cause', msg, "EMM Cause missing in Attach Complete")
        self.assertEqual(msg['emm_cause'], 0, "EMM Cause indicates failure in Attach Complete")
        self.logger.info("NAS Attach Complete EMM Cause validated")

        self.assertIn('ue_network_capability', msg, "UE Network Capability missing in Attach Complete")
        self.logger.info(f"UE Network Capability validated: {msg['ue_network_capability']}")

    def validate_mme_attach_accept_complete(self, msg):
        # Validate MME Attach Accept Completion IEs
        self.assertIn('mme_status', msg, "MME status missing")
        self.assertEqual(msg['mme_status'], 'success', "MME Attach Accept Completion failed")
        self.logger.info("MME Attach Accept Completion status: success")

if __name__ == "__main__":
    unittest.main()
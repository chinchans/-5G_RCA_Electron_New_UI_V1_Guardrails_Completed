import logging
import unittest

# Assume ue_attach_utils is a module that provides the reference attach procedure trigger and validation functions
from ue_attach_utils import (
    trigger_attach_procedure,
    validate_attach_accept,
    validate_rrc_setup_request,
    validate_rrc_setup_response,
    validate_rrc_connection_reconfiguration,
    validate_nas_attach_request,
    validate_nas_attach_accept,
    validate_security_mode_command,
    validate_security_mode_complete,
    validate_esm_information_response,
)

logger = logging.getLogger('AttachProcedureTest')
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)


class Test5GNsaAttachProcedure(unittest.TestCase):

    def test_ue_attach_procedure(self):
        logger.info("Starting UE Attach Procedure Test")

        # Step 1: Trigger UE Attach Procedure
        logger.info("Triggering UE Attach Procedure")
        attach_result = trigger_attach_procedure()
        self.assertTrue(attach_result['success'], "UE Attach procedure failed at trigger stage")
        logger.info("UE Attach Procedure triggered successfully")

        # Step 2: RRC Setup Request
        logger.info("Validating RRC Setup Request message and its IEs")
        rrc_setup_req = attach_result['rrc_setup_request']
        self.validate_rrc_setup_request(rrc_setup_req)

        # Step 3: RRC Setup Response
        logger.info("Validating RRC Setup Response message and its IEs")
        rrc_setup_resp = attach_result['rrc_setup_response']
        self.validate_rrc_setup_response(rrc_setup_resp)

        # Step 4: RRC Connection Reconfiguration
        logger.info("Validating RRC Connection Reconfiguration message and its IEs")
        rrc_conn_reconfig = attach_result['rrc_connection_reconfiguration']
        self.validate_rrc_connection_reconfiguration(rrc_conn_reconfig)

        # Step 5: NAS Attach Request
        logger.info("Validating NAS Attach Request message and its IEs")
        nas_attach_req = attach_result['nas_attach_request']
        self.validate_nas_attach_request(nas_attach_req)

        # Step 6: NAS Attach Accept
        logger.info("Validating NAS Attach Accept message and its IEs")
        nas_attach_accept = attach_result['nas_attach_accept']
        self.validate_nas_attach_accept(nas_attach_accept)

        # Step 7: Security Mode Command
        logger.info("Validating Security Mode Command message and its IEs")
        sec_mode_cmd = attach_result['security_mode_command']
        self.validate_security_mode_command(sec_mode_cmd)

        # Step 8: Security Mode Complete
        logger.info("Validating Security Mode Complete message and its IEs")
        sec_mode_complete = attach_result['security_mode_complete']
        self.validate_security_mode_complete(sec_mode_complete)

        # Step 9: ESM Information Response
        logger.info("Validating ESM Information Response message and its IEs")
        esm_info_resp = attach_result['esm_information_response']
        self.validate_esm_information_response(esm_info_resp)

        # Final validation of Attach Accept status
        logger.info("Validating overall Attach Accept status")
        attach_accept_status = validate_attach_accept(attach_result)
        self.assertTrue(attach_accept_status, "Attach Accept validation failed")
        logger.info("Attach Accept validated successfully")

    def validate_rrc_setup_request(self, message):
        # Extract and validate all IEs from RRC Setup Request
        logger.debug(f"RRC Setup Request Message: {message}")
        self.assertIn('rrcTransactionIdentifier', message, "Missing rrcTransactionIdentifier IE")
        self.assertIsInstance(message['rrcTransactionIdentifier'], int, "rrcTransactionIdentifier IE is not int")

        self.assertIn('criticalExtensions', message, "Missing criticalExtensions IE")
        self.assertIsInstance(message['criticalExtensions'], dict, "criticalExtensions IE is not dict")

        # Validate nested IEs inside criticalExtensions
        crit_ext = message['criticalExtensions']
        self.assertIn('rrcSetup', crit_ext, "Missing rrcSetup in criticalExtensions")
        self.assertIsInstance(crit_ext['rrcSetup'], dict, "rrcSetup IE is not dict")

        rrc_setup = crit_ext['rrcSetup']
        self.assertIn('radioBearerConfig', rrc_setup, "Missing radioBearerConfig IE")
        self.assertIsInstance(rrc_setup['radioBearerConfig'], dict, "radioBearerConfig IE is not dict")

        self.assertIn('ue_Identity', rrc_setup, "Missing ue_Identity IE")
        self.assertIsInstance(rrc_setup['ue_Identity'], str, "ue_Identity IE is not string")

        logger.info("RRC Setup Request IEs validated successfully")

    def validate_rrc_setup_response(self, message):
        logger.debug(f"RRC Setup Response Message: {message}")
        self.assertIn('rrcTransactionIdentifier', message, "Missing rrcTransactionIdentifier IE")
        self.assertIsInstance(message['rrcTransactionIdentifier'], int, "rrcTransactionIdentifier IE is not int")

        self.assertIn('criticalExtensions', message, "Missing criticalExtensions IE")
        self.assertIsInstance(message['criticalExtensions'], dict, "criticalExtensions IE is not dict")

        crit_ext = message['criticalExtensions']
        self.assertIn('rrcSetupComplete', crit_ext, "Missing rrcSetupComplete in criticalExtensions")
        self.assertIsInstance(crit_ext['rrcSetupComplete'], dict, "rrcSetupComplete IE is not dict")

        rrc_setup_complete = crit_ext['rrcSetupComplete']
        self.assertIn('nasPdu', rrc_setup_complete, "Missing nasPdu IE")
        self.assertIsInstance(rrc_setup_complete['nasPdu'], bytes, "nasPdu IE is not bytes")

        logger.info("RRC Setup Response IEs validated successfully")

    def validate_rrc_connection_reconfiguration(self, message):
        logger.debug(f"RRC Connection Reconfiguration Message: {message}")
        self.assertIn('rrcTransactionIdentifier', message, "Missing rrcTransactionIdentifier IE")
        self.assertIsInstance(message['rrcTransactionIdentifier'], int, "rrcTransactionIdentifier IE is not int")

        self.assertIn('criticalExtensions', message, "Missing criticalExtensions IE")
        self.assertIsInstance(message['criticalExtensions'], dict, "criticalExtensions IE is not dict")

        crit_ext = message['criticalExtensions']
        self.assertIn('rrcConnectionReconfiguration', crit_ext, "Missing rrcConnectionReconfiguration in criticalExtensions")
        self.assertIsInstance(crit_ext['rrcConnectionReconfiguration'], dict, "rrcConnectionReconfiguration IE is not dict")

        rrc_conn_reconfig = crit_ext['rrcConnectionReconfiguration']
        self.assertIn('radioBearerConfig', rrc_conn_reconfig, "Missing radioBearerConfig IE")
        self.assertIsInstance(rrc_conn_reconfig['radioBearerConfig'], dict, "radioBearerConfig IE is not dict")

        self.assertIn('measConfig', rrc_conn_reconfig, "Missing measConfig IE")
        self.assertIsInstance(rrc_conn_reconfig['measConfig'], dict, "measConfig IE is not dict")

        logger.info("RRC Connection Reconfiguration IEs validated successfully")

    def validate_nas_attach_request(self, message):
        logger.debug(f"NAS Attach Request Message: {message}")
        self.assertIn('epsAttachType', message, "Missing epsAttachType IE")
        self.assertIn(message['epsAttachType'], ['EPS_ATTACH_TYPE_EPS', 'EPS_ATTACH_TYPE_COMBINED_EPS_IMS'], "Invalid epsAttachType IE")

        self.assertIn('ueNetworkCapability', message, "Missing ueNetworkCapability IE")
        self.assertIsInstance(message['ueNetworkCapability'], bytes, "ueNetworkCapability IE is not bytes")

        self.assertIn('ueSecurityCapability', message, "Missing ueSecurityCapability IE")
        self.assertIsInstance(message['ueSecurityCapability'], bytes, "ueSecurityCapability IE is not bytes")

        self.assertIn('nasKeySetIdentifier', message, "Missing nasKeySetIdentifier IE")
        self.assertIsInstance(message['nasKeySetIdentifier'], int, "nasKeySetIdentifier IE is not int")

        self.assertIn('mobileIdentity', message, "Missing mobileIdentity IE")
        self.assertIsInstance(message['mobileIdentity'], dict, "mobileIdentity IE is not dict")
        self.assertIn('imsi', message['mobileIdentity'], "Missing imsi in mobileIdentity")
        self.assertIsInstance(message['mobileIdentity']['imsi'], str, "imsi IE is not string")

        self.assertIn('lastVisitedRegisteredTai', message, "Missing lastVisitedRegisteredTai IE")
        self.assertIsInstance(message['lastVisitedRegisteredTai'], dict, "lastVisitedRegisteredTai IE is not dict")
        self.assertIn('plmnId', message['lastVisitedRegisteredTai'], "Missing plmnId in lastVisitedRegisteredTai")
        self.assertIn('tac', message['lastVisitedRegisteredTai'], "Missing tac in lastVisitedRegisteredTai")

        logger.info("NAS Attach Request IEs validated successfully")

    def validate_nas_attach_accept(self, message):
        logger.debug(f"NAS Attach Accept Message: {message}")
        self.assertIn('emmCause', message, "Missing emmCause IE")
        self.assertEqual(message['emmCause'], 0, "EMM cause is not 'success'")

        self.assertIn('guti', message,
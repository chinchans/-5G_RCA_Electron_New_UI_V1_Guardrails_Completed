import logging
from ue_attach_utils import (
    trigger_ue_attach,
    receive_rrc_message,
    receive_nas_message,
    validate_ie,
    assert_true,
    log_step,
)

logger = logging.getLogger("5GAttachTest")
logger.setLevel(logging.INFO)
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
ch.setFormatter(formatter)
logger.addHandler(ch)


def validate_rrc_setup_request(msg):
    log_step(logger, "Validating RRC Setup Request")
    ie_mappings = {
        "ue_identity": str,
        "establishment_cause": str,
        "rrc_setup_cause": str,
    }
    for ie, ie_type in ie_mappings.items():
        value = msg.get(ie)
        validate_ie(logger, ie, value, ie_type)
        assert_true(value is not None, f"{ie} must be present")
    logger.info("RRC Setup Request validation passed")


def validate_rrc_setup(msg):
    log_step(logger, "Validating RRC Setup")
    ie_mappings = {
        "rrc_transaction_identifier": int,
        "critical_extensions": dict,
        "radio_bearer_config": dict,
    }
    for ie, ie_type in ie_mappings.items():
        value = msg.get(ie)
        validate_ie(logger, ie, value, ie_type)
        assert_true(value is not None, f"{ie} must be present")
    logger.info("RRC Setup validation passed")


def validate_rrc_security_mode_command(msg):
    log_step(logger, "Validating RRC Security Mode Command")
    ie_mappings = {
        "security_algorithms": dict,
        "integrity_prot_algorithm": str,
        "ciphering_algorithm": str,
        "nas_security_params": dict,
    }
    for ie, ie_type in ie_mappings.items():
        value = msg.get(ie)
        validate_ie(logger, ie, value, ie_type)
        assert_true(value is not None, f"{ie} must be present")
    logger.info("RRC Security Mode Command validation passed")


def validate_rrc_security_mode_complete(msg):
    log_step(logger, "Validating RRC Security Mode Complete")
    ie_mappings = {
        "rrc_transaction_identifier": int,
        "critical_extensions": dict,
    }
    for ie, ie_type in ie_mappings.items():
        value = msg.get(ie)
        validate_ie(logger, ie, value, ie_type)
        assert_true(value is not None, f"{ie} must be present")
    logger.info("RRC Security Mode Complete validation passed")


def validate_rrc_rrc_connection_reconfiguration(msg):
    log_step(logger, "Validating RRC Connection Reconfiguration")
    ie_mappings = {
        "rrc_transaction_identifier": int,
        "critical_extensions": dict,
        "radio_bearer_config": dict,
        "meas_config": dict,
    }
    for ie, ie_type in ie_mappings.items():
        value = msg.get(ie)
        validate_ie(logger, ie, value, ie_type)
        assert_true(value is not None, f"{ie} must be present")
    logger.info("RRC Connection Reconfiguration validation passed")


def validate_rrc_rrc_connection_reconfiguration_complete(msg):
    log_step(logger, "Validating RRC Connection Reconfiguration Complete")
    ie_mappings = {
        "rrc_transaction_identifier": int,
        "critical_extensions": dict,
    }
    for ie, ie_type in ie_mappings.items():
        value = msg.get(ie)
        validate_ie(logger, ie, value, ie_type)
        assert_true(value is not None, f"{ie} must be present")
    logger.info("RRC Connection Reconfiguration Complete validation passed")


def validate_nas_registration_request(msg):
    log_step(logger, "Validating NAS Registration Request")
    ie_mappings = {
        "registration_type": str,
        "ue_identity": dict,
        "security_capabilities": dict,
        "ue_network_capability": dict,
        "requested_nssai": list,
        "ue_usage_setting": str,
    }
    for ie, ie_type in ie_mappings.items():
        value = msg.get(ie)
        validate_ie(logger, ie, value, ie_type)
        assert_true(value is not None, f"{ie} must be present")
    logger.info("NAS Registration Request validation passed")


def validate_nas_authentication_request(msg):
    log_step(logger, "Validating NAS Authentication Request")
    ie_mappings = {
        "authentication_parameter_rand": bytes,
        "authentication_parameter_autn": bytes,
    }
    for ie, ie_type in ie_mappings.items():
        value = msg.get(ie)
        validate_ie(logger, ie, value, ie_type)
        assert_true(value is not None, f"{ie} must be present")
    logger.info("NAS Authentication Request validation passed")


def validate_nas_authentication_response(msg):
    log_step(logger, "Validating NAS Authentication Response")
    ie_mappings = {
        "authentication_response": bytes,
    }
    for ie, ie_type in ie_mappings.items():
        value = msg.get(ie)
        validate_ie(logger, ie, value, ie_type)
        assert_true(value is not None, f"{ie} must be present")
    logger.info("NAS Authentication Response validation passed")


def validate_nas_security_mode_command(msg):
    log_step(logger, "Validating NAS Security Mode Command")
    ie_mappings = {
        "selected_nas_security_algorithms": dict,
        "nas_integrity_prot_algorithm": str,
        "nas_ciphering_algorithm": str,
        "nas_security_key": bytes,
    }
    for ie, ie_type in ie_mappings.items():
        value = msg.get(ie)
        validate_ie(logger, ie, value, ie_type)
        assert_true(value is not None, f"{ie} must be present")
    logger.info("NAS Security Mode Command validation passed")


def validate_nas_security_mode_complete(msg):
    log_step(logger, "Validating NAS Security Mode Complete")
    ie_mappings = {
        "security_header_type": str,
    }
    for ie, ie_type in ie_mappings.items():
        value = msg.get(ie)
        validate_ie(logger, ie, value, ie_type)
        assert_true(value is not None, f"{ie} must be present")
    logger.info("NAS Security Mode Complete validation passed")


def validate_nas_registration_accept(msg):
    log_step(logger, "Validating NAS Registration Accept")
    ie_mappings = {
        "registration_result": str,
        "guti": dict,
        "tai_list": list,
        "active_default_eps_bearer_context": dict,
        "nas_config_params": dict,
    }
    for ie, ie_type in ie_mappings.items():
        value = msg.get(ie)
        validate_ie(logger, ie, value, ie_type)
        assert_true(value is not None, f"{ie} must be present")
    logger.info("NAS Registration Accept validation passed")


def validate_nas_registration_complete(msg):
    log_step(logger, "Validating NAS Registration Complete")
    ie_mappings = {
        "registration_status": str,
    }
    for ie, ie_type in ie_mappings.items():
        value = msg.get(ie)
        validate_ie(logger, ie, value, ie_type)
        assert_true(value is not None, f"{ie} must be present")
    logger.info("NAS Registration Complete validation passed")


def run_ue_attach_procedure():
    logger.info("Starting UE Attach Procedure")

    trigger_ue_attach()

    rrc_msg = receive_rrc_message("RRCSetupRequest")
    validate_rrc_setup_request(rrc_msg)

    rrc_msg = receive_rrc_message("RRCSetup")
    validate_rrc_setup(rrc_msg)

    rrc_msg = receive_rrc_message("RRCSecurityModeCommand")
    validate_rrc_security_mode_command(rrc_msg)

    rrc_msg = receive_rrc_message("RRCSecurityModeComplete")
    validate_rrc_security_mode_complete(rrc_msg)

    rrc_msg = receive_rrc_message("RRCConnectionReconfiguration")
    validate_rrc_rrc_connection_reconfiguration(rrc_msg)

    rrc_msg = receive_rrc_message("RRCConnectionReconfigurationComplete")
    validate_rrc_rrc_connection_reconfiguration_complete(rrc_msg)

    nas_msg = receive_nas_message("RegistrationRequest")
    validate_nas_registration_request(nas_msg)

    nas_msg = receive_nas_message("AuthenticationRequest")
    validate_nas_authentication_request(nas_msg)

    nas_msg = receive_nas_message("AuthenticationResponse")
    validate_nas_authentication_response(nas_msg)

    nas_msg = receive_nas_message("SecurityModeCommand")
    validate_nas_security_mode_command(nas_msg)

    nas_msg = receive_nas_message("SecurityModeComplete")
    validate_nas_security_mode_complete(nas_msg)

    nas_msg = receive_nas_message("RegistrationAccept")
    validate_nas_registration_accept(nas_msg)

    nas_msg = receive_nas_message("RegistrationComplete")
    validate_nas_registration_complete(nas_msg)

    logger.info("UE Attach Procedure completed successfully")


if __name__ == "__main__":
    run_ue_attach_procedure()
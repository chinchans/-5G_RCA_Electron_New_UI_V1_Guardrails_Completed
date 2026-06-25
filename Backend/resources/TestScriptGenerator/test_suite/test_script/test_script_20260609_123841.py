import time
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')


class UEAttachTest:
    def __init__(self, ue_interface):
        """
        ue_interface: An object/interface providing methods to interact with the UE and network.
        Expected methods:
          - power_on_ue()
          - power_off_ue()
          - start_logging()
          - stop_logging()
          - get_log()
          - send_rrc_message(msg_name, params)
          - receive_rrc_message(expected_msg_name, timeout)
          - send_nas_message(msg_name, params)
          - receive_nas_message(expected_msg_name, timeout)
          - get_radio_parameters()
          - get_attach_latency()
          - validate_attach_response()
          - validate_detach_response()
          - get_secondary_node_addition_status()
          - get_secondary_node_release_status()
          - get_ue_context_release_status()
        """
        self.ue = ue_interface
        self.attach_latencies = []
        self.attach_success_count = 0
        self.detach_success_count = 0
        self.secondary_node_addition_success_count = 0
        self.iterations = 10

    def log_and_assert(self, condition, success_msg, failure_msg):
        if condition:
            logging.info(success_msg)
        else:
            logging.error(failure_msg)
            raise AssertionError(failure_msg)

    # Trigger UE power ON and attach procedure
    def trigger_attach(self):
        logging.info("Starting UE power ON to initiate attach procedure.")
        self.ue.power_on_ue()
        attach_start_time = time.time()
        # Wait for attach complete indication
        attach_success = self.ue.validate_attach_response()
        attach_end_time = time.time()
        attach_latency = attach_end_time - attach_start_time
        self.attach_latencies.append(attach_latency)
        self.log_and_assert(attach_success,
                            "Attach procedure succeeded.",
                            "Attach procedure failed.")
        logging.info(f"Attach latency for this iteration: {attach_latency:.3f} seconds")
        return attach_success, attach_latency

    # Trigger UE power OFF and detach procedure
    def trigger_detach(self):
        logging.info("Starting UE power OFF to initiate detach procedure.")
        self.ue.power_off_ue()
        # Wait for detach complete indication
        detach_success = self.ue.validate_detach_response()
        self.log_and_assert(detach_success,
                            "Detach procedure succeeded.",
                            "Detach procedure failed.")
        return detach_success

    # Validate RRC Setup Request message and IEs
    def validate_rrc_setup_request(self, msg):
        logging.info("Validating RRC Setup Request message and IEs.")
        required_ies = ['ue-Identity', 'establishmentCause']
        for ie in required_ies:
            self.log_and_assert(ie in msg,
                                f"IE {ie} found in RRC Setup Request.",
                                f"IE {ie} missing in RRC Setup Request.")
        # Example validation: establishmentCause should be 'mo-Signalling'
        est_cause = msg.get('establishmentCause', None)
        self.log_and_assert(est_cause == 'mo-Signalling',
                            "establishmentCause IE has expected value 'mo-Signalling'.",
                            f"establishmentCause IE has unexpected value '{est_cause}'.")

    # Validate RRC Setup message and IEs
    def validate_rrc_setup(self, msg):
        logging.info("Validating RRC Setup message and IEs.")
        required_ies = ['radioResourceConfigDedicated']
        for ie in required_ies:
            self.log_and_assert(ie in msg,
                                f"IE {ie} found in RRC Setup.",
                                f"IE {ie} missing in RRC Setup.")

    # Validate RRC Setup Complete message and IEs
    def validate_rrc_setup_complete(self, msg):
        logging.info("Validating RRC Setup Complete message and IEs.")
        required_ies = ['nas-PDU']
        for ie in required_ies:
            self.log_and_assert(ie in msg,
                                f"IE {ie} found in RRC Setup Complete.",
                                f"IE {ie} missing in RRC Setup Complete.")

    # Validate NAS Attach Request message and IEs
    def validate_nas_attach_request(self, msg):
        logging.info("Validating NAS Attach Request message and IEs.")
        required_ies = ['EPS Attach Type', 'NAS Key Set Identifier', 'UE Network Capability']
        for ie in required_ies:
            self.log_and_assert(ie in msg,
                                f"IE {ie} found in NAS Attach Request.",
                                f"IE {ie} missing in NAS Attach Request.")

    # Validate NAS Authentication Request message and IEs
    def validate_nas_authentication_request(self, msg):
        logging.info("Validating NAS Authentication Request message and IEs.")
        required_ies = ['RAND', 'AUTN']
        for ie in required_ies:
            self.log_and_assert(ie in msg,
                                f"IE {ie} found in NAS Authentication Request.",
                                f"IE {ie} missing in NAS Authentication Request.")

    # Validate NAS Authentication Response message and IEs
    def validate_nas_authentication_response(self, msg):
        logging.info("Validating NAS Authentication Response message and IEs.")
        required_ies = ['RES']
        for ie in required_ies:
            self.log_and_assert(ie in msg,
                                f"IE {ie} found in NAS Authentication Response.",
                                f"IE {ie} missing in NAS Authentication Response.")

    # Validate NAS Security Mode Command message and IEs
    def validate_nas_security_mode_command(self, msg):
        logging.info("Validating NAS Security Mode Command message and IEs.")
        required_ies = ['Selected NAS Algorithm', 'Security Parameters']
        for ie in required_ies:
            self.log_and_assert(ie in msg,
                                f"IE {ie} found in NAS Security Mode Command.",
                                f"IE {ie} missing in NAS Security Mode Command.")

    # Validate NAS Security Mode Complete message and IEs
    def validate_nas_security_mode_complete(self, msg):
        logging.info("Validating NAS Security Mode Complete message and IEs.")
        required_ies = ['Security Header Type']
        for ie in required_ies:
            self.log_and_assert(ie in msg,
                                f"IE {ie} found in NAS Security Mode Complete.",
                                f"IE {ie} missing in NAS Security Mode Complete.")

    # Validate NAS Attach Accept message and IEs
    def validate_nas_attach_accept(self, msg):
        logging.info("Validating NAS Attach Accept message and IEs.")
        required_ies = ['T3412 timer', 'Assigned GUTI', 'EPS bearer context status']
        for ie in required_ies:
            self.log_and_assert(ie in msg,
                                f"IE {ie} found in NAS Attach Accept.",
                                f"IE {ie} missing in NAS Attach Accept.")

    # Validate NAS ESM Information Request message and IEs
    def validate_nas_esm_information_request(self, msg):
        logging.info("Validating NAS ESM Information Request message and IEs.")
        required_ies = ['Requested PCO']
        for ie in required_ies:
            self.log_and_assert(ie in msg,
                                f"IE {ie} found in NAS ESM Information Request.",
                                f"IE {ie} missing in NAS ESM Information Request.")

    # Validate NAS ESM Information Response message and IEs
    def validate_nas_esm_information_response(self, msg):
        logging.info("Validating NAS ESM Information Response message and IEs.")
        required_ies = ['PCO']
        for ie in required_ies:
            self.log_and_assert(ie in msg,
                                f"IE {ie} found in NAS ESM Information Response.",
                                f"IE {ie} missing in NAS ESM Information Response.")

    # Validate NAS Attach Complete message and IEs
    def validate_nas_attach_complete(self, msg):
        logging.info("Validating NAS Attach Complete message and IEs.")
        required_ies = ['EPS bearer context status']
        for ie in required_ies:
            self.log_and_assert(ie in msg,
                                f"IE {ie} found in NAS Attach Complete.",
                                f"IE {ie} missing in NAS Attach Complete.")

    # Validate Secondary Node Addition signaling (5G NSA)
    def validate_secondary_node_addition(self, msg):
        logging.info("Validating Secondary Node Addition messages and IEs.")
        required_ies = ['SgNB addition request', 'SgNB reconfiguration complete']
        for ie in required_ies:
            self.log_and_assert(ie in msg,
                                f"IE {ie} found in Secondary Node Addition.",
                                f"IE {ie} missing in Secondary Node Addition.")

    # Validate UE Context Release and RRC Connection Release messages (Detach)
    def validate_ue_context_release_and_rrc_release(self, msg):
        logging.info("Validating UE Context Release and RRC Connection Release messages and IEs.")
        required_ies = ['UE Context Release', 'RRC Connection Release']
        for ie in required_ies:
            self.log_and_assert(ie in msg,
                                f"IE {ie} found in UE Context and RRC Connection Release.",
                                f"IE {ie} missing in UE Context and RRC Connection Release.")

    # Full attach-detach test iteration
    def run_attach_detach_iteration(self):
        logging.info("Starting attach-detach iteration.")

        self.ue.start_logging()
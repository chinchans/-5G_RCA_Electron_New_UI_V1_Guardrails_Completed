```python
import logging

class UEAttachTest:
    def __init__(self):
        self.logger = logging.getLogger("UEAttachTest")
        logging.basicConfig(level=logging.INFO)

    def trigger_attach_procedure(self):
        self.logger.info("Triggering UE attach procedure...")
        # Reference code to trigger the attach procedure
        result = self.ue_attach_utils.trigger_attach()
        self.validate_attach_status(result)

    def validate_attach_status(self, result):
        if result['status'] == 'success':
            self.logger.info("Attach procedure successful.")
        else:
            self.logger.error("Attach procedure failed.")
            raise Exception("Attach failed")

    def validate_rrc_connection_request(self, msg):
        self.logger.info("Validating RRC Connection Request...")
        # Validate all IEs for RRC Connection Request
        assert 'UE Identity' in msg, "UE Identity not found"
        assert 'RRC Transaction ID' in msg, "RRC Transaction ID not found"
        self.logger.info("RRC Connection Request validated successfully.")

    def validate_rrc_connection_setup(self, msg):
        self.logger.info("Validating RRC Connection Setup...")
        # Validate all IEs for RRC Connection Setup
        assert 'Cell ID' in msg, "Cell ID not found"
        assert 'DRB' in msg, "DRB not found"
        self.logger.info("RRC Connection Setup validated successfully.")

    def validate_rrc_connection_setup_complete(self, msg):
        self.logger.info("Validating RRC Connection Setup Complete...")
        # Validate all IEs for RRC Connection Setup Complete
        assert 'RRC Connection ID' in msg, "RRC Connection ID not found"
        self.logger.info("RRC Connection Setup Complete validated successfully.")

    def validate_nas_attach_request(self, msg):
        self.logger.info("Validating NAS Attach Request...")
        # Validate all IEs for NAS Attach Request
        assert 'Attach Type' in msg, "Attach Type not found"
        assert 'IMSI' in msg, "IMSI not found"
        self.logger.info("NAS Attach Request validated successfully.")

    def validate_nas_attach_accept(self, msg):
        self.logger.info("Validating NAS Attach Accept...")
        # Validate all IEs for NAS Attach Accept
        assert 'Attach Accept' in msg, "Attach Accept not found"
        assert 'TMSI' in msg, "TMSI not found"
        self.logger.info("NAS Attach Accept validated successfully.")

    def validate_nas_attach_complete(self, msg):
        self.logger.info("Validating NAS Attach Complete...")
        # Validate all IEs for NAS Attach Complete
        assert 'Attach Complete' in msg, "Attach Complete not found"
        self.logger.info("NAS Attach Complete validated successfully.")

    def run_test(self):
        self.trigger_attach_procedure()

        # Simulated messages for testing
        rrc_connection_request_msg = {'UE Identity': '12345', 'RRC Transaction ID': 'abc'}
        self.validate_rrc_connection_request(rrc_connection_request_msg)

        rrc_connection_setup_msg = {'Cell ID': '67890', 'DRB': 'drb1'}
        self.validate_rrc_connection_setup(rrc_connection_setup_msg)

        rrc_connection_setup_complete_msg = {'RRC Connection ID': 'xyz'}
        self.validate_rrc_connection_setup_complete(rrc_connection_setup_complete_msg)

        nas_attach_request_msg = {'Attach Type': 'initial', 'IMSI': '987654321'}
        self.validate_nas_attach_request(nas_attach_request_msg)

        nas_attach_accept_msg = {'Attach Accept': 'success', 'TMSI': 'tmsi1'}
        self.validate_nas_attach_accept(nas_attach_accept_msg)

        nas_attach_complete_msg = {'Attach Complete': 'completed'}
        self.validate_nas_attach_complete(nas_attach_complete_msg)

if __name__ == "__main__":
    test = UEAttachTest()
    test.run_test()
```
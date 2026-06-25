```python
import logging
from ue_attach_utils import UEAttachUtils

class Test5GAttachProcedure:
    def __init__(self):
        self.attach_utils = UEAttachUtils()
        logging.basicConfig(level=logging.INFO)

    def trigger_attach(self):
        logging.info("Triggering UE attach procedure.")
        attach_status = self.attach_utils.trigger_attach()
        assert attach_status == "SUCCESS", "Attach procedure failed"
        logging.info("Attach procedure completed successfully.")

    def validate_rrc_connection_request(self, message):
        logging.info("Validating RRC Connection Request.")
        # Extract and validate IEs
        assert 'MessageType' in message and message['MessageType'] == 'RRCConnectionRequest', "Invalid RRC Connection Request"
        assert 'UEIdentity' in message, "UEIdentity IE missing"
        # Log results
        logging.info("RRC Connection Request validated successfully.")

    def validate_rrc_connection_setup(self, message):
        logging.info("Validating RRC Connection Setup.")
        # Extract and validate IEs
        assert 'MessageType' in message and message['MessageType'] == 'RRCConnectionSetup', "Invalid RRC Connection Setup"
        assert 'CellIdentity' in message, "CellIdentity IE missing"
        # Log results
        logging.info("RRC Connection Setup validated successfully.")

    def validate_rrc_connection_setup_complete(self, message):
        logging.info("Validating RRC Connection Setup Complete.")
        # Extract and validate IEs
        assert 'MessageType' in message and message['MessageType'] == 'RRCConnectionSetupComplete', "Invalid RRC Connection Setup Complete"
        # Log results
        logging.info("RRC Connection Setup Complete validated successfully.")

    def validate_nas_attach_request(self, message):
        logging.info("Validating NAS Attach Request.")
        # Extract and validate IEs
        assert 'MessageType' in message and message['MessageType'] == 'AttachRequest', "Invalid NAS Attach Request"
        assert 'IMSI' in message, "IMSI IE missing"
        # Log results
        logging.info("NAS Attach Request validated successfully.")

    def validate_nas_authentication_request(self, message):
        logging.info("Validating NAS Authentication Request.")
        # Extract and validate IEs
        assert 'MessageType' in message and message['MessageType'] == 'AuthenticationRequest', "Invalid NAS Authentication Request"
        assert 'RAND' in message, "RAND IE missing"
        # Log results
        logging.info("NAS Authentication Request validated successfully.")

    def validate_nas_authentication_response(self, message):
        logging.info("Validating NAS Authentication Response.")
        # Extract and validate IEs
        assert 'MessageType' in message and message['MessageType'] == 'AuthenticationResponse', "Invalid NAS Authentication Response"
        # Log results
        logging.info("NAS Authentication Response validated successfully.")

    def validate_nas_attach_accept(self, message):
        logging.info("Validating NAS Attach Accept.")
        # Extract and validate IEs
        assert 'MessageType' in message and message['MessageType'] == 'AttachAccept', "Invalid NAS Attach Accept"
        # Log results
        logging.info("NAS Attach Accept validated successfully.")

    def validate_nas_complete(self, message):
        logging.info("Validating NAS Attach Complete.")
        # Extract and validate IEs
        assert 'MessageType' in message and message['MessageType'] == 'AttachComplete', "Invalid NAS Attach Complete"
        # Log results
        logging.info("NAS Attach Complete validated successfully.")

    def run_test(self):
        self.trigger_attach()
        
        # Simulate message exchanges and validate
        rrc_connection_request = self.attach_utils.get_rrc_connection_request()
        self.validate_rrc_connection_request(rrc_connection_request)

        rrc_connection_setup = self.attach_utils.get_rrc_connection_setup()
        self.validate_rrc_connection_setup(rrc_connection_setup)

        rrc_connection_setup_complete = self.attach_utils.get_rrc_connection_setup_complete()
        self.validate_rrc_connection_setup_complete(rrc_connection_setup_complete)

        nas_attach_request = self.attach_utils.get_nas_attach_request()
        self.validate_nas_attach_request(nas_attach_request)

        nas_authentication_request = self.attach_utils.get_nas_authentication_request()
        self.validate_nas_authentication_request(nas_authentication_request)

        nas_authentication_response = self.attach_utils.get_nas_authentication_response()
        self.validate_nas_authentication_response(nas_authentication_response)

        nas_attach_accept = self.attach_utils.get_nas_attach_accept()
        self.validate_nas_attach_accept(nas_attach_accept)

        nas_attach_complete = self.attach_utils.get_nas_attach_complete()
        self.validate_nas_complete(nas_attach_complete)

if __name__ == "__main__":
    test = Test5GAttachProcedure()
    test.run_test()
```
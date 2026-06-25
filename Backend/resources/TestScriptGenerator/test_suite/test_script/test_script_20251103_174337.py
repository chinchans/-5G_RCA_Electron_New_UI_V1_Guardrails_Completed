```python
import logging
from ue_attach_utils import initiate_attach_procedure, validate_attach_status

class UEAttachTest:
    def __init__(self):
        self.logger = logging.getLogger("UEAttachTest")
        self.logger.setLevel(logging.INFO)

    def run_test(self):
        self.logger.info("Starting UE Attach Test")
        self.trigger_attach_procedure()

    def trigger_attach_procedure(self):
        # Trigger the UE attach procedure
        response = initiate_attach_procedure()
        self.validate_attach_status(response)

    def validate_attach_status(self, response):
        # Validate attach status
        if response['status'] == 'success':
            self.logger.info("Attach procedure successful")
            self.validate_rrc_connection_request(response['messages']['RRCConnectionRequest'])
        else:
            self.logger.error("Attach procedure failed")
            raise Exception("Attach procedure failed")

    def validate_rrc_connection_request(self, message):
        self.logger.info("Validating RRC Connection Request")
        assert 'TransactionID' in message, "TransactionID missing"
        assert 'CellID' in message, "CellID missing"
        assert 'UEIdentity' in message, "UEIdentity missing"
        self.logger.info("RRC Connection Request validated successfully")
        
        self.validate_rrc_connection_setup(message['RRCConnectionSetup'])

    def validate_rrc_connection_setup(self, message):
        self.logger.info("Validating RRC Connection Setup")
        assert 'TransactionID' in message, "TransactionID missing"
        assert 'SecurityConfig' in message, "SecurityConfig missing"
        assert 'RRCTransaction' in message, "RRCTransaction missing"
        self.logger.info("RRC Connection Setup validated successfully")

        self.validate_nas_registration_request(message['NASRegistrationRequest'])

    def validate_nas_registration_request(self, message):
        self.logger.info("Validating NAS Registration Request")
        assert 'RegistrationType' in message, "RegistrationType missing"
        assert 'PLMNID' in message, "PLMNID missing"
        assert 'UEIdentity' in message, "UEIdentity missing"
        self.logger.info("NAS Registration Request validated successfully")

        self.validate_nas_registration_accept(message['NASRegistrationAccept'])

    def validate_nas_registration_accept(self, message):
        self.logger.info("Validating NAS Registration Accept")
        assert 'RegistrationResult' in message, "RegistrationResult missing"
        assert 'AllowedNSSAI' in message, "AllowedNSSAI missing"
        assert '5G-GUTI' in message, "5G-GUTI missing"
        self.logger.info("NAS Registration Accept validated successfully")

        self.validate_nas_registration_complete(message['NASRegistrationComplete'])

    def validate_nas_registration_complete(self, message):
        self.logger.info("Validating NAS Registration Complete")
        assert 'TransactionID' in message, "TransactionID missing"
        assert 'Result' in message, "Result missing"
        self.logger.info("NAS Registration Complete validated successfully")

if __name__ == "__main__":
    attach_test = UEAttachTest()
    attach_test.run_test()
```
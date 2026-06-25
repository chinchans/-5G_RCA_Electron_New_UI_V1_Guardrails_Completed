```python
import logging

class UEAttachTest:
    def __init__(self):
        self.testcases_name = "5G NSA Attach Procedure"
        self.logger = logging.getLogger(__name__)
        logging.basicConfig(level=logging.INFO)

    def trigger_attach(self):
        # Trigger the UE attach procedure
        response = self.ue_attach_utils.trigger_attach()
        self.validate_attach_response(response)

    def validate_attach_response(self, response):
        assert response['status'] == 'success', "Attach procedure failed"
        self.logger.info("Attach procedure triggered successfully.")

    def validate_rrc_connection_request(self, message):
        assert 'RRCConnectionRequest' in message, "RRCConnectionRequest missing"
        assert 'ueIdentity' in message['RRCConnectionRequest'], "ueIdentity missing"
        self.logger.info("RRCConnectionRequest validated successfully.")

    def validate_rrc_connection_setup(self, message):
        assert 'RRCConnectionSetup' in message, "RRCConnectionSetup missing"
        assert 'RadioResourceConfig' in message['RRCConnectionSetup'], "RadioResourceConfig missing"
        self.logger.info("RRCConnectionSetup validated successfully.")

    def validate_rrc_connection_reconfiguration(self, message):
        assert 'RRCConnectionReconfiguration' in message, "RRCConnectionReconfiguration missing"
        assert 'SecurityConfig' in message['RRCConnectionReconfiguration'], "SecurityConfig missing"
        self.logger.info("RRCConnectionReconfiguration validated successfully.")

    def validate_nas_attach_request(self, message):
        assert 'AttachRequest' in message, "AttachRequest missing"
        assert 'nasKey' in message['AttachRequest'], "nasKey missing"
        self.logger.info("AttachRequest validated successfully.")

    def validate_nas_attach_accept(self, message):
        assert 'AttachAccept' in message, "AttachAccept missing"
        assert 'securityContext' in message['AttachAccept'], "securityContext missing"
        self.logger.info("AttachAccept validated successfully.")

    def validate_nas_service_request(self, message):
        assert 'ServiceRequest' in message, "ServiceRequest missing"
        assert 'requestType' in message['ServiceRequest'], "requestType missing"
        self.logger.info("ServiceRequest validated successfully.")

    def run_attach_procedure(self):
        self.trigger_attach()
        messages = self.ue_attach_utils.get_messages()

        for message in messages:
            if message['type'] == 'RRCConnectionRequest':
                self.validate_rrc_connection_request(message)
            elif message['type'] == 'RRCConnectionSetup':
                self.validate_rrc_connection_setup(message)
            elif message['type'] == 'RRCConnectionReconfiguration':
                self.validate_rrc_connection_reconfiguration(message)
            elif message['type'] == 'AttachRequest':
                self.validate_nas_attach_request(message)
            elif message['type'] == 'AttachAccept':
                self.validate_nas_attach_accept(message)
            elif message['type'] == 'ServiceRequest':
                self.validate_nas_service_request(message)

if __name__ == "__main__":
    test = UEAttachTest()
    test.run_attach_procedure()
```
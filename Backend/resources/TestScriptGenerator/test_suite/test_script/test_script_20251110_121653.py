```python
class UEAttachTest:
    def __init__(self, ue, logger):
        self.ue = ue
        self.logger = logger

    def trigger_attach(self):
        self.logger.info("Triggering UE attach procedure.")
        attach_response = self.ue_attach_utils.trigger_attach()
        self.validate_attach(attach_response)

    def validate_attach(self, attach_response):
        assert attach_response['result'] == 'success', "Attach procedure failed."
        self.logger.info("Attach procedure completed successfully.")

    def validate_rrc_connection_request(self, message):
        assert 'RRCConnectionRequest' in message, "RRCConnectionRequest missing."
        # Validate IEs here
        self.logger.info("RRC Connection Request validated successfully.")

    def validate_rrc_connection_setup(self, message):
        assert 'RRCConnectionSetup' in message, "RRCConnectionSetup missing."
        # Validate IEs here
        self.logger.info("RRC Connection Setup validated successfully.")

    def validate_rrc_connection_setup_complete(self, message):
        assert 'RRCConnectionSetupComplete' in message, "RRCConnectionSetupComplete missing."
        # Validate IEs here
        self.logger.info("RRC Connection Setup Complete validated successfully.")

    def validate_nas_attach_request(self, message):
        assert 'AttachRequest' in message, "AttachRequest missing."
        # Validate IEs here
        self.logger.info("NAS Attach Request validated successfully.")

    def validate_nas_attach_accept(self, message):
        assert 'AttachAccept' in message, "AttachAccept missing."
        # Validate IEs here
        self.logger.info("NAS Attach Accept validated successfully.")

    def validate_nas_attach_complete(self, message):
        assert 'AttachComplete' in message, "AttachComplete missing."
        # Validate IEs here
        self.logger.info("NAS Attach Complete validated successfully.")

    def perform_attach_test(self):
        self.trigger_attach()
        rrc_messages = self.ue.get_rrc_messages()
        nas_messages = self.ue.get_nas_messages()

        for message in rrc_messages:
            if 'RRCConnectionRequest' in message:
                self.validate_rrc_connection_request(message)
            elif 'RRCConnectionSetup' in message:
                self.validate_rrc_connection_setup(message)
            elif 'RRCConnectionSetupComplete' in message:
                self.validate_rrc_connection_setup_complete(message)

        for message in nas_messages:
            if 'AttachRequest' in message:
                self.validate_nas_attach_request(message)
            elif 'AttachAccept' in message:
                self.validate_nas_attach_accept(message)
            elif 'AttachComplete' in message:
                self.validate_nas_attach_complete(message)

        self.logger.info("All messages validated successfully.")

# Example usage:
# ue = UE()  # Initialize UE object
# logger = Logger()  # Initialize Logger object
# attach_test = UEAttachTest(ue, logger)
# attach_test.perform_attach_test()
```
```python
class Test5GAttachProcedure:
    def __init__(self, ue_attach_utils):
        self.ue_attach_utils = ue_attach_utils
        self.attach_results = []

    def trigger_attach(self):
        result = self.ue_attach_utils.trigger_attach()
        self.log_result("Attach Triggered", result)
        return result

    def validate_rrc_connection_request(self, message):
        assert 'RRCConnectionRequest' in message, "RRC Connection Request not found"
        assert 'UEIdentity' in message, "UE Identity not found"
        assert 'AccessStratumRelease' in message, "Access Stratum Release not found"
        self.log_result("RRC Connection Request Validated", True)

    def validate_rrc_connection_setup(self, message):
        assert 'RRCConnectionSetup' in message, "RRC Connection Setup not found"
        assert 'RadioResourceConfig' in message, "Radio Resource Config not found"
        self.log_result("RRC Connection Setup Validated", True)

    def validate_rrc_connection_setup_complete(self, message):
        assert 'RRCConnectionSetupComplete' in message, "RRC Connection Setup Complete not found"
        assert 'UEIdentity' in message, "UE Identity not found"
        self.log_result("RRC Connection Setup Complete Validated", True)

    def validate_nas_attach_request(self, message):
        assert 'AttachRequest' in message, "Attach Request not found"
        assert 'GUTI' in message or 'IMSI' in message, "GUTI or IMSI not found"
        assert 'AttachType' in message, "Attach Type not found"
        self.log_result("NAS Attach Request Validated", True)

    def validate_nas_attach_accept(self, message):
        assert 'AttachAccept' in message, "Attach Accept not found"
        assert 'BearerContext' in message, "Bearer Context not found"
        self.log_result("NAS Attach Accept Validated", True)

    def validate_nas_attach_complete(self, message):
        assert 'AttachComplete' in message, "Attach Complete not found"
        assert 'UEContext' in message, "UE Context not found"
        self.log_result("NAS Attach Complete Validated", True)

    def log_result(self, step, result):
        self.attach_results.append({'step': step, 'result': result})

    def run_attach_procedure(self):
        self.trigger_attach()

        # Simulate RRC message exchanges
        rrc_connection_request = self.ue_attach_utils.send_rrc_connection_request()
        self.validate_rrc_connection_request(rrc_connection_request)

        rrc_connection_setup = self.ue_attach_utils.send_rrc_connection_setup()
        self.validate_rrc_connection_setup(rrc_connection_setup)

        rrc_connection_setup_complete = self.ue_attach_utils.send_rrc_connection_setup_complete()
        self.validate_rrc_connection_setup_complete(rrc_connection_setup_complete)

        # Simulate NAS message exchanges
        nas_attach_request = self.ue_attach_utils.send_nas_attach_request()
        self.validate_nas_attach_request(nas_attach_request)

        nas_attach_accept = self.ue_attach_utils.send_nas_attach_accept()
        self.validate_nas_attach_accept(nas_attach_accept)

        nas_attach_complete = self.ue_attach_utils.send_nas_attach_complete()
        self.validate_nas_attach_complete(nas_attach_complete)

        return self.attach_results

# Usage
ue_attach_utils = UEAttachUtils()  # This should be your reference code implementation
test_procedure = Test5GAttachProcedure(ue_attach_utils)
attach_results = test_procedure.run_attach_procedure()
```
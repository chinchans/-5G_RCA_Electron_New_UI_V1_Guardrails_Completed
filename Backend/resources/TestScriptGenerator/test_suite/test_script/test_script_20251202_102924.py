```python
class UEAttachTest:
    def __init__(self):
        self.logs = []

    def trigger_ue_attach(self):
        self.logs.append("Triggering UE attach procedure.")
        attach_result = self.ue_attach_utils.trigger_attach()
        assert attach_result, "Attach procedure failed."
        self.logs.append("Attach procedure initiated successfully.")

    def validate_attach_request(self, attach_request):
        self.logs.append("Validating Attach Request.")
        assert 'IMSI' in attach_request, "IMSI not found in Attach Request."
        assert 'Old GUTI' in attach_request, "Old GUTI not found in Attach Request."
        assert 'Attach Type' in attach_request, "Attach Type not found in Attach Request."
        # Additional IEs validation...
        self.logs.append("Attach Request validated successfully.")

    def validate_attach_accept(self, attach_accept):
        self.logs.append("Validating Attach Accept.")
        assert 'GUTI' in attach_accept, "GUTI not found in Attach Accept."
        assert 'TAI List' in attach_accept, "TAI List not found in Attach Accept."
        # Additional IEs validation...
        self.logs.append("Attach Accept validated successfully.")

    def validate_security_mode_command(self, security_mode_command):
        self.logs.append("Validating Security Mode Command.")
        assert 'KSIASME' in security_mode_command, "KSIASME not found in Security Mode Command."
        assert 'NAS sequence number' in security_mode_command, "NAS sequence number not found."
        # Additional IEs validation...
        self.logs.append("Security Mode Command validated successfully.")

    def validate_security_mode_complete(self, security_mode_complete):
        self.logs.append("Validating Security Mode Complete.")
        assert 'UE Radio Capability ID' in security_mode_complete, "UE Radio Capability ID not found."
        # Additional IEs validation...
        self.logs.append("Security Mode Complete validated successfully.")

    def validate_attach_complete(self, attach_complete):
        self.logs.append("Validating Attach Complete.")
        assert 'EPS Bearer Identity' in attach_complete, "EPS Bearer Identity not found in Attach Complete."
        assert 'NAS sequence number' in attach_complete, "NAS sequence number not found."
        # Additional IEs validation...
        self.logs.append("Attach Complete validated successfully.")

    def detach_ue(self):
        self.logs.append("Triggering UE Detach procedure.")
        detach_result = self.ue_attach_utils.trigger_detach()
        assert detach_result, "Detach procedure failed."
        self.logs.append("Detach procedure completed successfully.")

    def run_test(self):
        self.trigger_ue_attach()
        attach_request = self.ue_attach_utils.get_attach_request()
        self.validate_attach_request(attach_request)

        attach_accept = self.ue_attach_utils.get_attach_accept()
        self.validate_attach_accept(attach_accept)

        security_mode_command = self.ue_attach_utils.get_security_mode_command()
        self.validate_security_mode_command(security_mode_command)

        security_mode_complete = self.ue_attach_utils.get_security_mode_complete()
        self.validate_security_mode_complete(security_mode_complete)

        attach_complete = self.ue_attach_utils.get_attach_complete()
        self.validate_attach_complete(attach_complete)

        self.detach_ue()
        self.logs.append("Test run completed.")

    def print_logs(self):
        for log in self.logs:
            print(log)

# Create test instance and run the test
test_instance = UEAttachTest()
test_instance.run_test()
test_instance.print_logs()
```
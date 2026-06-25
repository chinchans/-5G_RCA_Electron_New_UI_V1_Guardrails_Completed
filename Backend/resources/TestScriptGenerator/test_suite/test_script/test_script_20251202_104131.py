```python
class UEAttachTest:
    def __init__(self):
        self.testcase_name = "UE Attach and Detach Test"
        self.attach_status = None
        self.log = []

    def log_result(self, message):
        self.log.append(message)
        print(message)

    def trigger_attach_procedure(self):
        self.attach_status = self.ue_attach_utils.trigger_attach()
        self.log_result(f"Attach Procedure Triggered: {self.attach_status}")

    def validate_attach_request(self, attach_request):
        assert attach_request is not None, "Attach Request is None"
        # Validate Information Elements in the Attach Request
        # Example: assert attach_request['IMSI'] == expected_imsi
        self.log_result("Attach Request validated successfully.")

    def validate_attach_accept(self, attach_accept):
        assert attach_accept is not None, "Attach Accept is None"
        # Validate Information Elements in the Attach Accept
        # Example: assert attach_accept['GUTI'] == expected_guti
        self.log_result("Attach Accept validated successfully.")

    def validate_detach_request(self, detach_request):
        assert detach_request is not None, "Detach Request is None"
        # Validate Information Elements in the Detach Request
        # Example: assert detach_request['Cause'] == expected_cause
        self.log_result("Detach Request validated successfully.")

    def validate_detach_accept(self, detach_accept):
        assert detach_accept is not None, "Detach Accept is None"
        # Validate Information Elements in the Detach Accept
        # Example: assert detach_accept['DetachType'] == expected_detach_type
        self.log_result("Detach Accept validated successfully.")

    def run_attach_test(self):
        self.trigger_attach_procedure()
        attach_request = self.ue_attach_utils.get_attach_request()
        self.validate_attach_request(attach_request)

        attach_accept = self.ue_attach_utils.get_attach_accept()
        self.validate_attach_accept(attach_accept)

    def run_detach_test(self):
        detach_request = self.ue_attach_utils.get_detach_request()
        self.validate_detach_request(detach_request)

        detach_accept = self.ue_attach_utils.get_detach_accept()
        self.validate_detach_accept(detach_accept)

    def execute_test(self):
        self.run_attach_test()
        self.run_detach_test()
        self.log_result("All tests executed successfully.")

# Assuming ue_attach_utils is defined and has the appropriate methods
ue_attach_test = UEAttachTest()
ue_attach_test.execute_test()
```
```python
class UETestAutomation:
    def __init__(self):
        self.testcases_name = "Attach and Detach Test Cases"
        self.attach_success = False
        self.detach_success = False

    def trigger_attach(self):
        self.ue_attach_utils.send_attach_request()
        self.validate_attach_procedure()

    def validate_attach_procedure(self):
        self.validate_attach_request()
        self.validate_attach_accept()
        self.validate_attach_complete()

    def validate_attach_request(self):
        attach_request = self.ue_attach_utils.get_attach_request()
        assert attach_request is not None, "Attach Request is None"
        assert self.validate_information_elements(attach_request), "Attach Request IEs validation failed"
        self.log_result("Attach Request validated successfully")

    def validate_attach_accept(self):
        attach_accept = self.ue_attach_utils.get_attach_accept()
        assert attach_accept is not None, "Attach Accept is None"
        assert self.validate_information_elements(attach_accept), "Attach Accept IEs validation failed"
        self.log_result("Attach Accept validated successfully")

    def validate_attach_complete(self):
        attach_complete = self.ue_attach_utils.get_attach_complete()
        assert attach_complete is not None, "Attach Complete is None"
        assert self.validate_information_elements(attach_complete), "Attach Complete IEs validation failed"
        self.log_result("Attach Complete validated successfully")
        self.attach_success = True

    def validate_detach_procedure(self):
        self.validate_detach_request()
        self.validate_detach_accept()

    def validate_detach_request(self):
        detach_request = self.ue_attach_utils.get_detach_request()
        assert detach_request is not None, "Detach Request is None"
        assert self.validate_information_elements(detach_request), "Detach Request IEs validation failed"
        self.log_result("Detach Request validated successfully")

    def validate_detach_accept(self):
        detach_accept = self.ue_attach_utils.get_detach_accept()
        assert detach_accept is not None, "Detach Accept is None"
        assert self.validate_information_elements(detach_accept), "Detach Accept IEs validation failed"
        self.log_result("Detach Accept validated successfully")
        self.detach_success = True

    def validate_information_elements(self, message):
        # Implement logic to validate all IEs for the message
        # This is a placeholder for actual validation logic
        return True  # Assume validation always passes for demonstration

    def log_result(self, message):
        print(message)  # Replace with a proper logging mechanism

# Usage
ue_test = UETestAutomation()
ue_test.trigger_attach()
if ue_test.attach_success:
    ue_test.validate_detach_procedure()
```
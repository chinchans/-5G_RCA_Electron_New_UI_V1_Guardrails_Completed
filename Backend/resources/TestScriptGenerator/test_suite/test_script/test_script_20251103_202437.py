```python
class UEAttachTest:
    def __init__(self, ue_attach_utils):
        self.ue_attach_utils = ue_attach_utils
        self.testcase_name = "5G SA Registration and Deregistration Test"
    
    def trigger_attach(self):
        self.ue_attach_utils.trigger_attach()
    
    def validate_registration_request(self, message):
        assert message['type'] == 'REGISTRATION_REQUEST', "Incorrect message type"
        assert 'RegistrationType' in message, "Missing Registration Type"
        assert 'NSSAI' in message, "Missing NSSAI"
        # Validate other IEs as per specification
        self.log_result("Registration Request validated successfully.")

    def validate_registration_accept(self, message):
        assert message['type'] == 'REGISTRATION_ACCEPT', "Incorrect message type"
        assert '5G-GUTI' in message, "Missing 5G-GUTI"
        assert 'AllowedNSSAI' in message, "Missing Allowed NSSAI"
        # Validate other IEs as per specification
        self.log_result("Registration Accept validated successfully.")

    def validate_registration_complete(self, message):
        assert message['type'] == 'REGISTRATION_COMPLETE', "Incorrect message type"
        # Validate other IEs as per specification
        self.log_result("Registration Complete validated successfully.")

    def log_result(self, result):
        print(result)  # Replace with proper logging in production

    def run_test(self):
        self.trigger_attach()
        
        # Simulated message flow
        registration_request = self.ue_attach_utils.get_message("REGISTRATION_REQUEST")
        self.validate_registration_request(registration_request)

        registration_accept = self.ue_attach_utils.get_message("REGISTRATION_ACCEPT")
        self.validate_registration_accept(registration_accept)

        registration_complete = self.ue_attach_utils.get_message("REGISTRATION_COMPLETE")
        self.validate_registration_complete(registration_complete)

# Usage
ue_attach_utils = YourUEAttachUtils()  # Replace with actual utility instantiation
test = UEAttachTest(ue_attach_utils)
test.run_test()
```
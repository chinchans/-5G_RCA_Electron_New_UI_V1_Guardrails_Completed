```python
class Test5GAttach:
    def __init__(self):
        self.ue_attach_utils = UEAttachUtils()
        self.attach_procedure_messages = [
            "Registration Request",
            "Registration Accept",
            "Registration Complete",
            # Add all messages in the attach procedure here
        ]

    def test_attach_procedure(self):
        self.ue_attach_utils.trigger_attach()
        for message in self.attach_procedure_messages:
            if message == "Registration Request":
                self.validate_registration_request()
            elif message == "Registration Accept":
                self.validate_registration_accept()
            elif message == "Registration Complete":
                self.validate_registration_complete()
            # Add elif for other messages as necessary

    def validate_registration_request(self):
        message = self.ue_attach_utils.get_last_message("Registration Request")
        self.assert_IEs(message, ["Registration Type", "SUCI", "5G-GUTI", "Requested NSSAI"])
        self.log_results("Registration Request", message)

    def validate_registration_accept(self):
        message = self.ue_attach_utils.get_last_message("Registration Accept")
        self.assert_IEs(message, ["5GS Registration Result", "5G-GUTI", "Allowed NSSAI"])
        self.log_results("Registration Accept", message)

    def validate_registration_complete(self):
        message = self.ue_attach_utils.get_last_message("Registration Complete")
        self.assert_IEs(message, ["PDU Session Status"])
        self.log_results("Registration Complete", message)

    def assert_IEs(self, message, expected_ies):
        for ie in expected_ies:
            if ie not in message:
                raise AssertionError(f"Missing IE: {ie} in message: {message}")

    def log_results(self, step_name, message):
        print(f"{step_name} validated successfully. Message: {message}")


class UEAttachUtils:
    def trigger_attach(self):
        # Logic to trigger UE attach procedure
        pass

    def get_last_message(self, message_type):
        # Logic to retrieve the last message of a specified type
        pass


if __name__ == "__main__":
    test_case = Test5GAttach()
    test_case.test_attach_procedure()
```
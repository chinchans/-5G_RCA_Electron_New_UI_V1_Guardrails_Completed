```python
import logging
import time

class UEAttachTest:
    def __init__(self, ue, network):
        self.ue = ue
        self.network = network
        self.results = []

    def log_result(self, step, message):
        logging.info(f"{step}: {message}")
        self.results.append((step, message))

    def validate_ie(self, ie, expected_value):
        if ie == expected_value:
            self.log_result("Validation", f"IE validated successfully: {ie}")
        else:
            self.log_result("Validation", f"IE validation failed: {ie} (Expected: {expected_value})")

    def trigger_ue_attach(self):
        # Trigger the UE attach procedure using reference code
        attach_response = self.ue.trigger_attach(self.network)
        self.log_result("Attach Trigger", f"Attach response: {attach_response}")

    def validate_registration_request(self):
        self.log_result("Step 1", "Sending Registration Request")
        registration_request = self.ue.send_registration_request()
        self.log_result("Step 1", f"Registration Request sent: {registration_request}")

        # Validate Information Elements (IEs)
        self.validate_ie(registration_request['registration_type'], 'Initial Registration')
        self.validate_ie(registration_request['security_parameters'], 'Valid Security Parameters')

    def validate_registration_accept(self):
        self.log_result("Step 2", "Receiving Registration Accept")
        registration_accept = self.network.receive_registration_accept()
        self.log_result("Step 2", f"Registration Accept received: {registration_accept}")

        # Validate Information Elements (IEs)
        self.validate_ie(registration_accept['5G-GUTI'], 'Assigned GUTI')
        self.validate_ie(registration_accept['allowed_nssai'], 'Valid NSSAI')

    def validate_registration_complete(self):
        self.log_result("Step 3", "Sending Registration Complete")
        registration_complete = self.ue.send_registration_complete()
        self.log_result("Step 3", f"Registration Complete sent: {registration_complete}")

        # Validate Information Elements (IEs)
        self.validate_ie(registration_complete['registration_id'], 'Valid Registration ID')

    def run_test(self):
        self.trigger_ue_attach()
        self.validate_registration_request()
        self.validate_registration_accept()
        self.validate_registration_complete()
        self.log_result("Test Complete", f"Results: {self.results}")

# Example usage:
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    ue = UE()  # Instantiate UE class
    network = Network()  # Instantiate Network class
    test = UEAttachTest(ue, network)
    test.run_test()
```
```python
import time
import logging

class UEAttachTest:
    def __init__(self):
        self.log_file = 'ue_attach_test.log'
        logging.basicConfig(filename=self.log_file, level=logging.INFO)

    def trigger_attach_procedure(self):
        self.send_registration_request()
        self.validate_registration_response()

    def send_registration_request(self):
        logging.info("Sending Registration Request...")
        # Simulate sending of Registration Request
        response = self.simulate_message_exchange("Registration Request")
        self.validate_registration_request(response)

    def validate_registration_request(self, response):
        logging.info("Validating Registration Request...")
        # Validate Information Elements (IEs)
        # Example: Check for presence of mandatory IEs
        assert 'Registration Type' in response, "Missing Registration Type"
        assert 'UE Identity' in response, "Missing UE Identity"
        logging.info("Registration Request validated successfully.")

    def validate_registration_response(self):
        logging.info("Validating Registration Response...")
        response = self.simulate_message_exchange("Registration Response")
        assert 'Registration Accept' in response, "Registration failed"
        # Validate IEs in Registration Response
        assert 'Registered PLMN' in response, "Missing Registered PLMN"
        logging.info("Registration Response validated successfully.")
        
    def simulate_message_exchange(self, message_type):
        # Mocked response based on the message type
        responses = {
            "Registration Request": {
                'Registration Type': 'Initial',
                'UE Identity': 'UE123456',
            },
            "Registration Response": {
                'Registration Accept': True,
                'Registered PLMN': 'PLMN1',
            }
        }
        return responses.get(message_type, {})

    def start_data_transfer(self):
        logging.info("Starting bi-directional data transfer...")
        # Simulate data transfer
        time.sleep(180)  # Simulated time for data transfer
        logging.info("Data transfer completed.")

    def send_deregistration_request(self):
        logging.info("Sending Deregistration Request...")
        response = self.simulate_message_exchange("Deregistration Request")
        self.validate_deregistration_request(response)

    def validate_deregistration_request(self, response):
        logging.info("Validating Deregistration Request...")
        assert 'Deregistration Type' in response, "Missing Deregistration Type"
        logging.info("Deregistration Request validated successfully.")

    def validate_deregistration_response(self):
        logging.info("Validating Deregistration Response...")
        response = self.simulate_message_exchange("Deregistration Response")
        assert 'Deregistration Accept' in response, "Deregistration failed"
        logging.info("Deregistration Response validated successfully.")

    def run_test(self):
        for _ in range(10):  # Repeat for 10 iterations
            self.trigger_attach_procedure()
            self.start_data_transfer()
            self.send_deregistration_request()
            self.validate_deregistration_response()

if __name__ == "__main__":
    test = UEAttachTest()
    test.run_test()
```
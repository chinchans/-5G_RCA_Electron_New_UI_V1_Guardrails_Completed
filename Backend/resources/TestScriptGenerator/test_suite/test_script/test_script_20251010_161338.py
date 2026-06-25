```python
import logging
import time

class UEAttachTest:
    def __init__(self):
        self.testcase_name = "5G SA registration and deregistration of single UE"
        self.logging_setup()

    def logging_setup(self):
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    def trigger_ue_attach(self):
        logging.info("Triggering UE attach procedure")
        # Logic to send REGISTRATION REQUEST
        response = self.send_registration_request()
        self.validate_registration_response(response)

    def send_registration_request(self):
        # Simulate sending the REGISTRATION REQUEST message
        logging.info("Sending REGISTRATION REQUEST")
        # Return a mock response
        return {"status": "success", "IEs": {"registration_type": "initial", "ue_identity": "mock_identity"}}

    def validate_registration_response(self, response):
        logging.info("Validating registration response")
        assert response["status"] == "success", "Registration failed"
        self.validate_IEs(response["IEs"])

    def validate_IEs(self, IEs):
        logging.info("Validating Information Elements")
        expected_IEs = ["registration_type", "ue_identity"]
        for ie in expected_IEs:
            assert ie in IEs, f"Missing IE: {ie}"
        logging.info("All IEs validated successfully")

    def initiate_data_transmission(self):
        logging.info("Initiating bi-directional UDP data transmission")
        # Simulate data transmission and measure throughput
        time.sleep(180)  # Simulate 3 minutes of data transmission
        logging.info("Data transmission completed")

    def deregister_ue(self):
        logging.info("Powering off UE and sending DEREGISTRATION REQUEST")
        response = self.send_deregistration_request()
        self.validate_deregistration_response(response)

    def send_deregistration_request(self):
        logging.info("Sending DEREGISTRATION REQUEST")
        # Return a mock response
        return {"status": "success", "IEs": {"deregistration_type": "ue_initiated"}}

    def validate_deregistration_response(self, response):
        logging.info("Validating deregistration response")
        assert response["status"] == "success", "Deregistration failed"
        self.validate_IEs(response["IEs"])

    def run_test(self):
        for iteration in range(10):
            logging.info(f"Test iteration {iteration + 1}")
            self.trigger_ue_attach()
            self.initiate_data_transmission()
            self.deregister_ue()

if __name__ == "__main__":
    test = UEAttachTest()
    test.run_test()
```
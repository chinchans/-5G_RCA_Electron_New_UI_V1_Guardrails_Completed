```python
import logging
import time

class UEAttachTest:
    def __init__(self):
        self.logger = self.setup_logger()
        self.attach_procedure_steps = [
            self.send_registration_request,
            self.receive_registration_accept,
            self.send_registration_complete,
            self.send_pdu_session_establishment_request,
            self.receive_pdu_session_establishment_response,
            self.send_deregistration_request,
            self.receive_deregistration_accept
        ]
    
    def setup_logger(self):
        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger("5GAttachTest")
        handler = logging.FileHandler("5GAttachTest.log")
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        return logger
    
    def simulate_message_exchange(self, message):
        self.logger.info(f"Simulating message exchange: {message}")
        time.sleep(1)  # Simulate network delay
    
    def validate_information_elements(self, message, expected_ies):
        for ie in expected_ies:
            if ie not in message:
                self.logger.error(f"IE {ie} not found in message {message}")
                assert False
        self.logger.info(f"All expected IEs validated in message: {message}")
    
    def send_registration_request(self):
        message = "Registration Request with IEs"
        self.simulate_message_exchange(message)
        expected_ies = ["Registration Type", "Security Parameters", "Requested NSSAI"]
        self.validate_information_elements(message, expected_ies)
        self.logger.info("Sent Registration Request successfully.")
    
    def receive_registration_accept(self):
        message = "Registration Accept with IEs"
        self.simulate_message_exchange(message)
        expected_ies = ["5G-GUTI", "Registration Area", "Allowed NSSAI"]
        self.validate_information_elements(message, expected_ies)
        self.logger.info("Received Registration Accept successfully.")
    
    def send_registration_complete(self):
        message = "Registration Complete with IEs"
        self.simulate_message_exchange(message)
        expected_ies = []
        self.validate_information_elements(message, expected_ies)
        self.logger.info("Sent Registration Complete successfully.")
    
    def send_pdu_session_establishment_request(self):
        message = "PDU Session Establishment Request with IEs"
        self.simulate_message_exchange(message)
        expected_ies = ["PDU Session ID", "QoS Flow Description"]
        self.validate_information_elements(message, expected_ies)
        self.logger.info("Sent PDU Session Establishment Request successfully.")
    
    def receive_pdu_session_establishment_response(self):
        message = "PDU Session Establishment Response with IEs"
        self.simulate_message_exchange(message)
        expected_ies = ["PDU Session ID", "User Plane Resource Information"]
        self.validate_information_elements(message, expected_ies)
        self.logger.info("Received PDU Session Establishment Response successfully.")
    
    def send_deregistration_request(self):
        message = "Deregistration Request with IEs"
        self.simulate_message_exchange(message)
        expected_ies = ["Deregistration Type", "Reason"]
        self.validate_information_elements(message, expected_ies)
        self.logger.info("Sent Deregistration Request successfully.")
    
    def receive_deregistration_accept(self):
        message = "Deregistration Accept with IEs"
        self.simulate_message_exchange(message)
        expected_ies = []
        self.validate_information_elements(message, expected_ies)
        self.logger.info("Received Deregistration Accept successfully.")

    def run_test(self):
        for step in self.attach_procedure_steps:
            step()

if __name__ == "__main__":
    test = UEAttachTest()
    test.run_test()
```
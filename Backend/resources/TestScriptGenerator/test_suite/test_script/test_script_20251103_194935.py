```python
import logging
import time

class UEAttachTest:
    def __init__(self):
        self.attach_procedure_steps = [
            self.send_registration_request,
            self.receive_registration_accept,
            self.send_registration_complete,
            self.send_pdu_session_establishment_request,
            self.receive_pdu_session_establishment_response,
            self.send_deregistration_request,
            self.receive_deregistration_accept,
            self.send_signaling_connection_release
        ]
        self.latencies = []

    def log_result(self, message):
        logging.info(message)

    def assert_condition(self, condition, message):
        assert condition, message

    def validate_information_elements(self, message, expected_ies):
        for ie in expected_ies:
            self.assert_condition(ie in message, f"Missing IE: {ie} in message: {message}")

    def send_registration_request(self):
        start_time = time.time()
        message = self.ue_attach_utils.trigger_registration_request()
        self.log_result("Sent Registration Request")
        self.validate_information_elements(message, ["Registration Request IE1", "Registration Request IE2"])
        latency = time.time() - start_time
        self.latencies.append(latency)

    def receive_registration_accept(self):
        message = self.ue_attach_utils.wait_for_registration_accept()
        self.log_result("Received Registration Accept")
        self.validate_information_elements(message, ["Registration Accept IE1", "Registration Accept IE2"])

    def send_registration_complete(self):
        start_time = time.time()
        message = self.ue_attach_utils.trigger_registration_complete()
        self.log_result("Sent Registration Complete")
        self.validate_information_elements(message, ["Registration Complete IE1", "Registration Complete IE2"])
        latency = time.time() - start_time
        self.latencies.append(latency)

    def send_pdu_session_establishment_request(self):
        start_time = time.time()
        message = self.ue_attach_utils.trigger_pdu_session_establishment_request()
        self.log_result("Sent PDU Session Establishment Request")
        self.validate_information_elements(message, ["PDU Session Establishment Request IE1", "PDU Session Establishment Request IE2"])
        latency = time.time() - start_time
        self.latencies.append(latency)

    def receive_pdu_session_establishment_response(self):
        message = self.ue_attach_utils.wait_for_pdu_session_establishment_response()
        self.log_result("Received PDU Session Establishment Response")
        self.validate_information_elements(message, ["PDU Session Establishment Response IE1", "PDU Session Establishment Response IE2"])

    def send_deregistration_request(self):
        start_time = time.time()
        message = self.ue_attach_utils.trigger_deregistration_request()
        self.log_result("Sent Deregistration Request")
        self.validate_information_elements(message, ["Deregistration Request IE1", "Deregistration Request IE2"])
        latency = time.time() - start_time
        self.latencies.append(latency)

    def receive_deregistration_accept(self):
        message = self.ue_attach_utils.wait_for_deregistration_accept()
        self.log_result("Received Deregistration Accept")
        self.validate_information_elements(message, ["Deregistration Accept IE1", "Deregistration Accept IE2"])

    def send_signaling_connection_release(self):
        start_time = time.time()
        message = self.ue_attach_utils.trigger_signaling_connection_release()
        self.log_result("Sent Signaling Connection Release")
        self.validate_information_elements(message, ["Signaling Connection Release IE1", "Signaling Connection Release IE2"])
        latency = time.time() - start_time
        self.latencies.append(latency)

    def run_test(self):
        for step in self.attach_procedure_steps:
            step()
        self.log_result("Test completed. Latencies: " + str(self.latencies))
        self.log_result("Minimum Latency: " + str(min(self.latencies)))
        self.log_result("Average Latency: " + str(sum(self.latencies) / len(self.latencies)))
        self.log_result("Maximum Latency: " + str(max(self.latencies)))

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    test = UEAttachTest()
    test.run_test()
```
```python
import time
import logging

class UETestAutomation:
    def __init__(self):
        self.attach_success_count = 0
        self.detach_success_count = 0
        self.attach_latencies = []
        self.test_iterations = 10
        logging.basicConfig(level=logging.INFO)

    def trigger_ue_attach(self):
        logging.info("Triggering UE attach procedure...")
        # Trigger the attach procedure here using self.ue_attach_utils
        # Simulate the attach process and capture the start time
        start_time = time.time()
        
        # Placeholder for triggering the actual attach operation
        self.ue_attach_utils.trigger_attach()
        
        # Wait for attach confirmation
        if self.validate_attach():
            elapsed_time = time.time() - start_time
            self.attach_success_count += 1
            self.attach_latencies.append(elapsed_time)
            logging.info(f"Attach successful. Latency: {elapsed_time:.2f} seconds")
        else:
            logging.error("Attach failed.")

    def validate_attach(self):
        # Simulate message exchange and validate each IE in the attach procedure
        return self.validate_rrc_connection_request() and self.validate_nas_attach_request()

    def validate_rrc_connection_request(self):
        logging.info("Validating RRC Connection Request...")
        # Simulate receiving RRC Connection Request
        rrc_message = self.ue_attach_utils.get_rrc_connection_request()
        # Validate all IEs in the RRC Connection Request
        if self.validate_ies(rrc_message, expected_ies=['Transaction ID', 'UE Identity']):
            logging.info("RRC Connection Request validated successfully.")
            return True
        logging.error("RRC Connection Request validation failed.")
        return False

    def validate_nas_attach_request(self):
        logging.info("Validating NAS Attach Request...")
        # Simulate receiving NAS Attach Request
        nas_message = self.ue_attach_utils.get_nas_attach_request()
        # Validate all IEs in the NAS Attach Request
        if self.validate_ies(nas_message, expected_ies=['Transaction ID', 'Security Context']):
            logging.info("NAS Attach Request validated successfully.")
            return True
        logging.error("NAS Attach Request validation failed.")
        return False

    def validate_ies(self, message, expected_ies):
        for ie in expected_ies:
            if ie not in message:
                logging.error(f"Missing IE: {ie} in message.")
                return False
        return True

    def trigger_ue_detach(self):
        logging.info("Triggering UE detach procedure...")
        # Trigger the detach procedure here using self.ue_attach_utils
        self.ue_attach_utils.trigger_detach()
        
        if self.validate_detach():
            self.detach_success_count += 1
            logging.info("Detach successful.")
        else:
            logging.error("Detach failed.")

    def validate_detach(self):
        # Simulate message exchange and validate detach
        return self.validate_rrc_connection_release() and self.validate_nas_detach_request()

    def validate_rrc_connection_release(self):
        logging.info("Validating RRC Connection Release...")
        rrc_message = self.ue_attach_utils.get_rrc_connection_release()
        if self.validate_ies(rrc_message, expected_ies=['Transaction ID']):
            logging.info("RRC Connection Release validated successfully.")
            return True
        logging.error("RRC Connection Release validation failed.")
        return False

    def validate_nas_detach_request(self):
        logging.info("Validating NAS Detach Request...")
        nas_message = self.ue_attach_utils.get_nas_detach_request()
        if self.validate_ies(nas_message, expected_ies=['Transaction ID']):
            logging.info("NAS Detach Request validated successfully.")
            return True
        logging.error("NAS Detach Request validation failed.")
        return False

    def run_test(self):
        for _ in range(self.test_iterations):
            self.trigger_ue_attach()
            self.trigger_ue_detach()
        
        logging.info(f"Attach Success Rate: {self.attach_success_count}/{self.test_iterations}")
        logging.info(f"Detach Success Rate: {self.detach_success_count}/{self.test_iterations}")
        if self.attach_latencies:
            logging.info(f"Attach Latencies: Min: {min(self.attach_latencies)}, "
                         f"Avg: {sum(self.attach_latencies)/len(self.attach_latencies)}, "
                         f"Max: {max(self.attach_latencies)}")

# Initialize the test automation
test_automation = UETestAutomation()
test_automation.run_test()
```
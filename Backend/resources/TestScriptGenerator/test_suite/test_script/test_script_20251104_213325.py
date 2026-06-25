```python
import logging
from ue_attach_utils import UEAttachUtils

class UETestAutomation:
    def __init__(self):
        self.ue = UEAttachUtils()
        self.logger = logging.getLogger(__name__)
        logging.basicConfig(level=logging.INFO)

    def attach_procedure(self):
        self.logger.info("Starting UE Attach procedure")
        attach_response = self.ue.trigger_attach()
        self.validate_attach_response(attach_response)

    def validate_attach_response(self, response):
        assert response['status'] == 'success', "Attach procedure failed"
        self.logger.info("Attach procedure successful")
        self.validate_nas_message(response['nas_message'])
        self.validate_rrc_message(response['rrc_message'])

    def validate_nas_message(self, nas_message):
        self.logger.info("Validating NAS message")
        # Validate specific Information Elements (IEs) in NAS message
        assert 'Detach Request' in nas_message, "Detach Request not found"
        assert 'GUTI' in nas_message, "GUTI IE not found"
        assert 'Switch Off' in nas_message, "Switch Off IE not found"
        self.logger.info("NAS message validated successfully")

    def validate_rrc_message(self, rrc_message):
        self.logger.info("Validating RRC message")
        # Validate specific Information Elements (IEs) in RRC message
        assert 'RRC Connection Request' in rrc_message, "RRC Connection Request not found"
        assert 'Cell ID' in rrc_message, "Cell ID IE not found"
        assert 'RRC Transaction ID' in rrc_message, "RRC Transaction ID IE not found"
        self.logger.info("RRC message validated successfully")

    def detach_procedure(self):
        self.logger.info("Starting UE Detach procedure")
        detach_response = self.ue.trigger_detach()
        self.validate_detach_response(detach_response)

    def validate_detach_response(self, response):
        assert response['status'] == 'success', "Detach procedure failed"
        self.logger.info("Detach procedure successful")
        self.validate_detach_nas_message(response['nas_message'])
        self.validate_detach_rrc_message(response['rrc_message'])

    def validate_detach_nas_message(self, nas_message):
        self.logger.info("Validating detach NAS message")
        assert 'Detach Accept' in nas_message, "Detach Accept not found"
        assert 'Detach Cause' in nas_message, "Detach Cause not found"
        self.logger.info("Detach NAS message validated successfully")

    def validate_detach_rrc_message(self, rrc_message):
        self.logger.info("Validating detach RRC message")
        assert 'RRC Connection Release' in rrc_message, "RRC Connection Release not found"
        assert 'Release Cause' in rrc_message, "Release Cause IE not found"
        self.logger.info("Detach RRC message validated successfully")

if __name__ == "__main__":
    test_automation = UETestAutomation()
    test_automation.attach_procedure()
    test_automation.detach_procedure()
```
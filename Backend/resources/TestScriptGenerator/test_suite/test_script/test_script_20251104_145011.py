```python
class UEAttachTest:
    def __init__(self):
        self.ue_attach_utils = UEAttachUtils()

    def trigger_attach(self):
        self.ue_attach_utils.initiate_attach()
        self.validate_attach_status()

    def validate_attach_status(self):
        assert self.ue_attach_utils.is_attached(), "Attach procedure failed."

    def validate_attach_request(self, attach_request):
        assert attach_request.get('IMSI'), "IMSI missing in Attach Request."
        assert attach_request.get('Old GUTI'), "Old GUTI missing in Attach Request."
        assert attach_request.get('Attach Type') in ['EPS Attach', 'Emergency Attach'], "Invalid Attach Type."
        # Validate other IEs...
        self.ue_attach_utils.log("Attach Request validated successfully.")

    def validate_attach_accept(self, attach_accept):
        assert attach_accept.get('GUTI'), "GUTI missing in Attach Accept."
        assert attach_accept.get('TMSI'), "TMSI missing in Attach Accept."
        # Validate other IEs...
        self.ue_attach_utils.log("Attach Accept validated successfully.")

    def validate_security_mode_command(self, security_mode_command):
        assert security_mode_command.get('KSIASME'), "KSIASME missing in Security Mode Command."
        assert security_mode_command.get('NAS Security Algorithm'), "NAS Security Algorithm missing."
        # Validate other IEs...
        self.ue_attach_utils.log("Security Mode Command validated successfully.")

    def validate_security_mode_complete(self, security_mode_complete):
        assert security_mode_complete.get('Security Context'), "Security Context missing in Security Mode Complete."
        # Validate other IEs...
        self.ue_attach_utils.log("Security Mode Complete validated successfully.")

    def validate_update_location_request(self, update_location_request):
        assert update_location_request.get('IMSI'), "IMSI missing in Update Location Request."
        assert update_location_request.get('ME Identity'), "ME Identity missing in Update Location Request."
        # Validate other IEs...
        self.ue_attach_utils.log("Update Location Request validated successfully.")

    def validate_update_location_response(self, update_location_response):
        assert update_location_response.get('Subscription Data'), "Subscription Data missing in Update Location Response."
        # Validate other IEs...
        self.ue_attach_utils.log("Update Location Response validated successfully.")

    def validate_create_session_request(self, create_session_request):
        assert create_session_request.get('PDN Type'), "PDN Type missing in Create Session Request."
        assert create_session_request.get('APN'), "APN missing in Create Session Request."
        # Validate other IEs...
        self.ue_attach_utils.log("Create Session Request validated successfully.")

    def validate_create_session_response(self, create_session_response):
        assert create_session_response.get('PDN Address'), "PDN Address missing in Create Session Response."
        # Validate other IEs...
        self.ue_attach_utils.log("Create Session Response validated successfully.")

    def run_test(self):
        self.trigger_attach()
        # Simulate and validate each step in the attach procedure
        attach_request = self.ue_attach_utils.send_attach_request()
        self.validate_attach_request(attach_request)

        attach_accept = self.ue_attach_utils.receive_attach_accept()
        self.validate_attach_accept(attach_accept)

        security_mode_command = self.ue_attach_utils.send_security_mode_command()
        self.validate_security_mode_command(security_mode_command)

        security_mode_complete = self.ue_attach_utils.receive_security_mode_complete()
        self.validate_security_mode_complete(security_mode_complete)

        update_location_request = self.ue_attach_utils.send_update_location_request()
        self.validate_update_location_request(update_location_request)

        update_location_response = self.ue_attach_utils.receive_update_location_response()
        self.validate_update_location_response(update_location_response)

        create_session_request = self.ue_attach_utils.send_create_session_request()
        self.validate_create_session_request(create_session_request)

        create_session_response = self.ue_attach_utils.receive_create_session_response()
        self.validate_create_session_response(create_session_response)

        self.ue_attach_utils.log("UE Attach Test completed successfully.")

if __name__ == "__main__":
    test = UEAttachTest()
    test.run_test()
```
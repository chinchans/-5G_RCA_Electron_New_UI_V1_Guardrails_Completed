```python
class Test5GAttachProcedure:
    def __init__(self, ue_attach_utils):
        self.ue_attach_utils = ue_attach_utils

    def trigger_attach(self):
        result = self.ue_attach_utils.trigger_attach_procedure()
        assert result['status'] == 'success', "Attach procedure failed"
        self.log_result("Attach procedure triggered successfully.")

    def validate_attach_request(self, attach_request):
        assert 'GUTI' in attach_request, "GUTI is missing in Attach Request"
        assert 'Requested IMSI' in attach_request, "Requested IMSI is missing in Attach Request"
        self.log_result("Attach Request validated successfully.")

    def validate_attach_accept(self, attach_accept):
        assert 'GUTI' in attach_accept, "GUTI is missing in Attach Accept"
        assert 'EPS Bearer QoS' in attach_accept, "EPS Bearer QoS is missing in Attach Accept"
        self.log_result("Attach Accept validated successfully.")

    def validate_attach_complete(self, attach_complete):
        assert 'EPS Bearer Identity' in attach_complete, "EPS Bearer Identity is missing in Attach Complete"
        self.log_result("Attach Complete validated successfully.")

    def log_result(self, message):
        print(message)

    def run(self):
        self.trigger_attach()
        attach_request = self.ue_attach_utils.get_attach_request()
        self.validate_attach_request(attach_request)

        attach_accept = self.ue_attach_utils.get_attach_accept()
        self.validate_attach_accept(attach_accept)

        attach_complete = self.ue_attach_utils.get_attach_complete()
        self.validate_attach_complete(attach_complete)

# Example usage
ue_attach_utils = self.ue_attach_utils  # Assuming this is defined in the test context
test_case = Test5GAttachProcedure(ue_attach_utils)
test_case.run()
```
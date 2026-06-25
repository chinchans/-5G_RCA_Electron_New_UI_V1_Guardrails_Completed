# Use python-jenkins (the correct package)
# Install with: pip install python-jenkins
# Version: 1.8.3 or later (supports Python 3.4+)
import jenkins
from jenkins import JenkinsException
import time
import sys
import json
import requests
from requests.auth import HTTPBasicAuth

def emit_progress(value, message=None):
    """Emit structured progress markers consumed by backend parser."""
    try:
        pct = max(0, min(100, int(value)))
    except Exception:
        pct = 0
    print(f"PROGRESS:{pct}", flush=True)
    if message:
        print(f"STATUS:{message}", flush=True)

def trigger_and_monitor_job(server_url, username, password, job_name):
    """Trigger a Jenkins job and monitor its execution until completion."""
    try:
        emit_progress(10, "Connecting to Jenkins server...")
        # Connect to Jenkins server
        server = jenkins.Jenkins(server_url, username=username, password=password)
        
        # Check if the job exists
        if not server.job_exists(job_name):
            print(f"Error: Job '{job_name}' does not exist.")
            return {"result": None, "console_output": f"Error: Job '{job_name}' does not exist.", "build_number": None}
        
        emit_progress(20, f"Triggering Jenkins job: {job_name}")
        # Trigger a build for the job
        queue_number = server.build_job(job_name)
        print(f"Build triggered for job '{job_name}', queue number: {queue_number}", flush=True)
        
        # Wait for the job to start (executable may be missing or null while queued)
        queue_item = server.get_queue_item(queue_number)
        wait_ticks = 0
        max_queue_wait_ticks = 150  # ~5 minutes at 2s per tick
        while not queue_item.get('executable'):
            if queue_item.get('cancelled'):
                reason = queue_item.get('why') or 'Build was cancelled in queue'
                return {"result": None, "console_output": f"Error: {reason}", "build_number": None}
            wait_ticks += 1
            if wait_ticks > max_queue_wait_ticks:
                return {
                    "result": None,
                    "console_output": "Error: Timed out waiting for Jenkins build to start.",
                    "build_number": None,
                }
            emit_progress(min(35, 22 + wait_ticks * 2), "Waiting for Jenkins executor...")
            print("Waiting for the job to start...", flush=True)
            time.sleep(2)
            queue_item = server.get_queue_item(queue_number)

        executable = queue_item['executable']
        if not isinstance(executable, dict) or executable.get('number') is None:
            return {
                "result": None,
                "console_output": "Error: Jenkins queue item has no build number yet.",
                "build_number": None,
            }

        # Get build number
        build_number = executable['number']
        emit_progress(40, f"Job started with build number: {build_number}")
        print(f"Job started with build number: {build_number}", flush=True)
        
        # Monitor the build status
        build_info = server.get_build_info(job_name, build_number)
        build_start_time = time.time()
        poll_count = 0
        last_progress = 40
        while build_info['building']:
            poll_count += 1
            estimated_ms = int(build_info.get('estimatedDuration') or 0)
            elapsed_ms = int((time.time() - build_start_time) * 1000)

            # Estimated progress from Jenkins build duration (fallback ramp if unavailable).
            if estimated_ms > 0:
                computed = 40 + int(min(55, (elapsed_ms / estimated_ms) * 55))
                # Ensure visible movement even when estimatedDuration is large.
                live_progress = min(95, max(last_progress + 1, computed))
            else:
                live_progress = min(95, 40 + poll_count * 4)

            if live_progress > last_progress:
                last_progress = live_progress
                emit_progress(last_progress, "Jenkins build running...")

            print("Job is still running...", flush=True)
            time.sleep(2)
            build_info = server.get_build_info(job_name, build_number)
        
        # Job completed, fetch result
        result = build_info['result']
        emit_progress(99, f"Jenkins build completed with result: {result}")
        print(f"Job completed with result: {result}", flush=True)
        
        # Fetch console output from the exact build that was triggered
        console_output = ""
        try:
            console_output = server.get_build_console_output(job_name, build_number)
            print(
                f"Console output fetched successfully from build #{build_number} ({len(console_output)} characters)",
                flush=True,
            )
        except Exception as api_err:
            print(f"Warning: Jenkins API console fetch failed: {api_err}", flush=True)
            try:
                server_url_clean = server_url.rstrip('/')
                console_url = f"{server_url_clean}/job/{job_name}/{build_number}/consoleText"
                response = requests.get(
                    console_url,
                    auth=HTTPBasicAuth(username, password),
                    timeout=30,
                )
                if response.status_code == 200:
                    console_output = response.text
                    print(
                        f"Console output fetched via HTTP from build #{build_number} ({len(console_output)} characters)",
                        flush=True,
                    )
                else:
                    console_output = f"Could not fetch console output. Status code: {response.status_code}"
            except Exception as http_err:
                print(f"Warning: Error fetching console output: {http_err}", flush=True)
                console_output = f"Error fetching console output: {http_err}"
        
        # Return both result and console output
        return {"result": result, "console_output": console_output, "build_number": build_number}
        
    except JenkinsException as e:
        print(f"Jenkins Error: {e}", flush=True)
        return {"result": None, "console_output": f"Jenkins Error: {e}", "build_number": None}
    except Exception as e:
        print(f"Error: {e}", flush=True)
        return {"result": None, "console_output": f"Error: {e}", "build_number": None}

def main():
    """Main function to handle test execution with configuration."""
    # Default values (fallback)
    jenkins_server_url = "http://10.138.77.71:8080/"
    jenkins_username = "chandu"
    jenkins_password = "tcs@12345"
    job_name = "GenAI_Phase1_Demo_Script"
    
    # Get configuration from command line arguments
    if len(sys.argv) > 1:
        # First argument is JSON config string
        try:
            config = json.loads(sys.argv[1])
            jenkins_server_url = config.get('jenkins_server_url', jenkins_server_url)
            jenkins_username = config.get('jenkins_username', jenkins_username)
            jenkins_password = config.get('jenkins_password', jenkins_password)
            job_name = config.get('job_name', job_name)
        except json.JSONDecodeError:
            print("Warning: Could not parse config JSON, using defaults")
    
    print(f"Jenkins Server: {jenkins_server_url}")
    print(f"Job Name: {job_name}")
    print(f"Username: {jenkins_username}")
    
    # Trigger and monitor Jenkins job build
    job_result = trigger_and_monitor_job(jenkins_server_url, jenkins_username, jenkins_password, job_name)
    
    # Always ensure job_result is a dict
    if not job_result:
        job_result = {"result": None, "console_output": "Failed to fetch Jenkins job result.", "build_number": None}
    
    result = job_result.get("result")
    console_output = job_result.get("console_output", "")
    build_number = job_result.get("build_number")
    
    # Print console output (this will be captured by subprocess)
    if console_output:
        print("=== JENKINS CONSOLE OUTPUT START ===")
        print(console_output)
        print("=== JENKINS CONSOLE OUTPUT END ===")
    
    # Always print result line (even if None) so backend can extract it
    if result:
        print(f"Job completed with result: {result}")
    else:
        print(f"Job completed with result: FAILED")
        result = "FAILED"
    
    if build_number:
        print(f"Build number: {build_number}")
    
    # Exit with 0 for SUCCESS, 1 for FAILURE/UNSTABLE/etc
    sys.exit(0 if result == "SUCCESS" else 1)

if __name__ == "__main__":
    main()


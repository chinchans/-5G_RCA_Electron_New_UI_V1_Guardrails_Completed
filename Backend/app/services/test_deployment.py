import os
import sys
import json
import paramiko

def get_latest_file(directory):
    """Get the most recently modified file in the directory."""
    if not os.path.exists(directory):
        print(f"Error: Source directory does not exist: {directory}")
        return None
        
    files = [os.path.join(directory, f) for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]
    files = [f for f in files if os.path.isfile(f)]
        
    if not files:
        print(f"No files found in directory: {directory}")
        return None
        
    latest_file = max(files, key=os.path.getmtime)
    return latest_file

def transfer_file(local_file, remote_host, remote_user, remote_password, remote_path):
    """Transfer file to Ubuntu machine using SCP."""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(remote_host, username=remote_user, password=remote_password, timeout=10)

        sftp = ssh.open_sftp()
        remote_file = os.path.join(remote_path, os.path.basename(local_file))
        sftp.put(local_file, remote_file)
        
        print(f"Transferred {local_file} to {remote_host}:{remote_file}")

        sftp.close()
        ssh.close()
        return True
    except Exception as e:
        print(f"Error transferring file: {e}")
        return False

def main():
    """Main function to handle deployment with configuration."""
    # Default values (fallback)
    source_dir = "/home/tcs/genai_setups/5G_RCA_Electron-main/Backend/resources/TestScriptGenerator/test_suite/test_script"
    ubuntu_host = "10.138.77.131"
    ubuntu_user = "tcs"
    ubuntu_password = "tcs@12345"
    destination_dir = "/home/tcs/chandu/"
    
    # Get configuration from command line arguments or environment
    if len(sys.argv) > 1:
        # First argument is source directory
        source_dir = sys.argv[1]
    
    if len(sys.argv) > 2:
        # Second argument is JSON config string
        try:
            config = json.loads(sys.argv[2])
            source_dir = config.get('source_directory', source_dir)
            ubuntu_host = config.get('ubuntu_host', ubuntu_host)
            ubuntu_user = config.get('ubuntu_user', ubuntu_user)
            ubuntu_password = config.get('ubuntu_password', ubuntu_password)
            destination_dir = config.get('destination_directory', destination_dir)
        except json.JSONDecodeError:
            print("Warning: Could not parse config JSON, using defaults")
    
    # Ensure source_dir is absolute path
    if not os.path.isabs(source_dir):
        source_dir = os.path.abspath(source_dir)
    
    print(f"Source directory: {source_dir}")
    print(f"Destination: {ubuntu_user}@{ubuntu_host}:{destination_dir}")
    
    # Get latest file from source directory
    latest_file = get_latest_file(source_dir)
    if latest_file:
        print(f"Latest file found: {latest_file}")
        # Transfer the file
        success = transfer_file(latest_file, ubuntu_host, ubuntu_user, ubuntu_password, destination_dir)
        if success:
            print(f"Successfully transferred {os.path.basename(latest_file)} to {ubuntu_user}@{ubuntu_host}:{destination_dir}")
        else:
            print(f"Failed to transfer file")
            sys.exit(1)
    else:
        print("No files found in the source directory.")
        sys.exit(1)

if __name__ == "__main__":
    main()



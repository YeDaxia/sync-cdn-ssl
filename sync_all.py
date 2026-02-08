import subprocess
import sys
import os

def run_script(script_name):
    """
    Run a python script and return True if successful, False otherwise.
    """
    script_path = os.path.join(os.path.dirname(__file__), script_name)
    print(f"============================================================")
    print(f"🚀 Starting {script_name}...")
    print(f"============================================================")
    
    # flush output to ensure order
    sys.stdout.flush()
    
    try:
        # Pass the current environment to the subprocess
        env = os.environ.copy()
        
        # Run the script
        result = subprocess.run(
            [sys.executable, script_path], 
            env=env,
            capture_output=False, # Let stdout/stderr go directly to terminal
            check=False 
        )
        
        print(f"\n============================================================")
        if result.returncode == 0:
            print(f"✅ Finished {script_name} successfully.")
        else:
            print(f"❌ Finished {script_name} with error (Exit Code: {result.returncode}).")
        print(f"============================================================\n")
        
        return result.returncode == 0
        
    except Exception as e:
        print(f"❌ Failed to execute {script_name}: {e}")
        return False

def main():
    scripts = ["sync_ssl_aliyun.py", "sync_ssl_qiniu.py"]
    
    failed_scripts = []
    
    print("Starting SSL Sync for all providers...\n")
    
    for script in scripts:
        if not run_script(script):
            failed_scripts.append(script)
    
    if failed_scripts:
        print(f"⚠️  Summary: The following scripts failed: {', '.join(failed_scripts)}")
        sys.exit(1)
    else:
        print("🎉 All scripts executed successfully!")
        sys.exit(0)

if __name__ == "__main__":
    main()

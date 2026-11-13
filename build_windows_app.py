"""
Parkinova Windows Standalone Application Builder
Packages Parkinova using PyInstaller and Parkinova.spec into dist/Parkinova/
"""

import os
import sys
import subprocess
import shutil

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def check_prerequisites():
    print("[1/4] Checking build prerequisites...")
    spec_path = os.path.join(BASE_DIR, "Parkinova.spec")
    if not os.path.exists(spec_path):
        print(f"[ERROR] Specification file not found: {spec_path}")
        return False

    model_path = os.path.join(BASE_DIR, "models", "parkinson_cnn.keras")
    if not os.path.exists(model_path):
        print(f"[ERROR] CNN Model file not found: {model_path}")
        return False

    print(f"  ✓ Spec file: {spec_path}")
    print(f"  ✓ Model file: {model_path}")
    print(f"  ✓ Base directory: {BASE_DIR}")
    return True

def run_pyinstaller():
    print("\n[2/4] Invoking PyInstaller with Parkinova.spec...")
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "Parkinova.spec",
        "--noconfirm",
        "--clean"
    ]
    print(f"  Command: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=BASE_DIR)
    return result.returncode == 0

def verify_build():
    print("\n[3/4] Verifying generated build artifacts...")
    dist_dir = os.path.join(BASE_DIR, "dist", "Parkinova")
    exe_path = os.path.join(dist_dir, "Parkinova.exe")

    if not os.path.exists(exe_path):
        print(f"[ERROR] Executable not found at {exe_path}")
        return False

    size_mb = os.path.getsize(exe_path) / (1024 * 1024)
    print(f"  ✓ Found executable: {exe_path} ({size_mb:.2f} MB)")

    # Verify bundled assets
    critical_assets = [
        os.path.join(dist_dir, "_internal", "models", "parkinson_cnn.keras"),
        os.path.join(dist_dir, "_internal", "assets"),
        os.path.join(dist_dir, "_internal", "web"),
    ]
    for asset in critical_assets:
        if os.path.exists(asset):
            print(f"  ✓ Verified bundled asset: {os.path.relpath(asset, dist_dir)}")
        else:
            print(f"  [WARNING] Expected asset check: {os.path.relpath(asset, dist_dir)}")

    return True

def main():
    print("=========================================================")
    print("  Parkinova Standalone Windows Packaging Build")
    print("=========================================================")

    if not check_prerequisites():
        sys.exit(1)

    success = run_pyinstaller()
    if not success:
        print("\n[ERROR] PyInstaller build failed. Inspect the logs above.")
        sys.exit(1)

    if verify_build():
        print("\n[4/4] Build Complete!")
        print(f"Executable is ready at:")
        print(f"  {os.path.join(BASE_DIR, 'dist', 'Parkinova', 'Parkinova.exe')}")
        print("\nDouble-click Parkinova.exe or create a desktop shortcut to launch.")
    else:
        print("\n[ERROR] Build verification failed.")
        sys.exit(1)

if __name__ == "__main__":
    main()

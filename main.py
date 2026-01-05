#!/usr/bin/env python3
"""
PersonalUI - 个性化GUI Agent系统

基于AutoGLM框架的个性化GUI agent，使用GraphRAG存储用户习惯，
通过learning mode学习用户行为并更新到GraphRAG，支持语音指令操作。

Usage:
    python main.py [OPTIONS]
"""

import argparse
import os
import sys
import json
import time
import threading
from typing import Dict, Any, Optional

# 添加子模块路径
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Open-AutoGLM'))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'learning_mode'))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'graphrag'))

# 导入AutoGLM相关模块
from Open_AutoGLM.phone_agent import PhoneAgent
from Open_AutoGLM.phone_agent.agent import AgentConfig
from Open_AutoGLM.phone_agent.device_factory import DeviceType, get_device_factory, set_device_type
from Open_AutoGLM.phone_agent.model import ModelConfig

# 导入learning_mode相关模块
from learning_mode.behavior_analyzer import BehaviorAnalyzer
from learning_mode.vlm_analyzer import VLMAnalyzer

# 导入graphrag相关模块
from graphrag.simple_graphrag.simplegraph import SimpleGraph

# 导入本地模块
from observer import UserObserver
from refiner import InstructionRefiner
from knowledge_base import KnowledgeBase


def check_system_requirements(
    device_type: DeviceType = DeviceType.ADB, wda_url: str = "http://localhost:8100"
) -> bool:
    """
    Check system requirements before running the agent.

    Checks:
    1. ADB/HDC/iOS tools installed
    2. At least one device connected
    3. ADB Keyboard installed on the device (for ADB only)
    4. WebDriverAgent running (for iOS only)

    Args:
        device_type: Type of device tool (ADB, HDC, or IOS).
        wda_url: WebDriverAgent URL (for iOS only).

    Returns:
        True if all checks pass, False otherwise.
    """
    print("🔍 Checking system requirements...")
    print("-" * 50)

    all_passed = True

    # Determine tool name and command
    if device_type == DeviceType.IOS:
        tool_name = "libimobiledevice"
        tool_cmd = "idevice_id"
    else:
        tool_name = "ADB" if device_type == DeviceType.ADB else "HDC"
        tool_cmd = "adb" if device_type == DeviceType.ADB else "hdc"

    # Check 1: Tool installed
    print(f"1. Checking {tool_name} installation...", end=" ")
    if shutil.which(tool_cmd) is None:
        print("❌ FAILED")
        print(f"   Error: {tool_name} is not installed or not in PATH.")
        print(f"   Solution: Install {tool_name}:")
        if device_type == DeviceType.ADB:
            print("     - macOS: brew install android-platform-tools")
            print("     - Linux: sudo apt install android-tools-adb")
            print(
                "     - Windows: Download from https://developer.android.com/studio/releases/platform-tools"
            )
        elif device_type == DeviceType.HDC:
            print(
                "     - Download from HarmonyOS SDK or https://gitee.com/openharmony/docs"
            )
            print("     - Add to PATH environment variable")
        else:  # IOS
            print("     - macOS: brew install libimobiledevice")
            print("     - Linux: sudo apt-get install libimobiledevice-utils")
        all_passed = False
    else:
        # Double check by running version command
        try:
            if device_type == DeviceType.ADB:
                version_cmd = [tool_cmd, "version"]
            elif device_type == DeviceType.HDC:
                version_cmd = [tool_cmd, "-v"]
            else:  # IOS
                version_cmd = [tool_cmd, "-ln"]

            result = subprocess.run(
                version_cmd, capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                version_line = result.stdout.strip().split("\n")[0]
                print(f"✅ OK ({version_line if version_line else 'installed'})")
            else:
                print("❌ FAILED")
                print(f"   Error: {tool_name} command failed to run.")
                all_passed = False
        except FileNotFoundError:
            print("❌ FAILED")
            print(f"   Error: {tool_name} command not found.")
            all_passed = False
        except subprocess.TimeoutExpired:
            print("❌ FAILED")
            print(f"   Error: {tool_name} command timed out.")
            all_passed = False

    # If ADB is not installed, skip remaining checks
    if not all_passed:
        print("-" * 50)
        print("❌ System check failed. Please fix the issues above.")
        return False

    # Check 2: Device connected
    print("2. Checking connected devices...", end=" ")
    try:
        if device_type == DeviceType.ADB:
            result = subprocess.run(
                ["adb", "devices"], capture_output=True, text=True, timeout=10
            )
            lines = result.stdout.strip().split("\n")
            # Filter out header and empty lines, look for 'device' status
            devices = [
                line for line in lines[1:] if line.strip() and "\tdevice" in line
            ]
        elif device_type == DeviceType.HDC:
            result = subprocess.run(
                ["hdc", "list", "targets"], capture_output=True, text=True, timeout=10
            )
            lines = result.stdout.strip().split("\n")
            devices = [line for line in lines if line.strip()]
        else:  # IOS
            ios_devices = list_ios_devices()
            devices = [d.device_id for d in ios_devices]

        if not devices:
            print("❌ FAILED")
            print("   Error: No devices connected.")
            print("   Solution:")
            if device_type == DeviceType.ADB:
                print("     1. Enable USB debugging on your Android device")
                print("     2. Connect via USB and authorize the connection")
                print(
                    "     3. Or connect remotely: python main.py --connect <ip>:<port>"
                )
            elif device_type == DeviceType.HDC:
                print("     1. Enable USB debugging on your HarmonyOS device")
                print("     2. Connect via USB and authorize the connection")
                print(
                    "     3. Or connect remotely: python main.py --device-type hdc --connect <ip>:<port>"
                )
            else:  # IOS
                print("     1. Connect your iOS device via USB")
                print("     2. Unlock device and tap 'Trust This Computer'")
                print("     3. Verify: idevice_id -l")
                print("     4. Or connect via WiFi using device IP")
            all_passed = False
        else:
            if device_type == DeviceType.ADB:
                device_ids = [d.split("\t")[0] for d in devices]
            elif device_type == DeviceType.HDC:
                device_ids = [d.strip() for d in devices]
            else:  # IOS
                device_ids = devices
            print(
                f"✅ OK ({len(devices)} device(s): {', '.join(device_ids[:2])}{'...' if len(device_ids) > 2 else ''})"
            )
    except subprocess.TimeoutExpired:
        print("❌ FAILED")
        print(f"   Error: {tool_name} command timed out.")
        all_passed = False
    except Exception as e:
        print("❌ FAILED")
        print(f"   Error: {e}")
        all_passed = False

    # If no device connected, skip ADB Keyboard check
    if not all_passed:
        print("-" * 50)
        print("❌ System check failed. Please fix the issues above.")
        return False

    # Check 3: ADB Keyboard installed (only for ADB) or WebDriverAgent (for iOS)
    if device_type == DeviceType.ADB:
        print("3. Checking ADB Keyboard...", end=" ")
        try:
            result = subprocess.run(
                ["adb", "shell", "ime", "list", "-s"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            ime_list = result.stdout.strip()

            if "com.android.adbkeyboard/.AdbIME" in ime_list:
                print("✅ OK")
            else:
                print("❌ FAILED")
                print("   Error: ADB Keyboard is not installed on the device.")
                print("   Solution:")
                print("     1. Download ADB Keyboard APK from:")
                print(
                    "        https://github.com/senzhk/ADBKeyBoard/blob/master/ADBKeyboard.apk"
                )
                print("     2. Install it on your device: adb install ADBKeyboard.apk")
                print(
                    "     3. Enable it in Settings > System > Languages & Input > Virtual Keyboard"
                )
                all_passed = False
        except subprocess.TimeoutExpired:
            print("❌ FAILED")
            print("   Error: ADB command timed out.")
            all_passed = False
        except Exception as e:
            print("❌ FAILED")
            print(f"   Error: {e}")
            all_passed = False
    elif device_type == DeviceType.HDC:
        # For HDC, skip keyboard check as it uses different input method
        print("3. Skipping keyboard check for HarmonyOS...", end=" ")
        print("✅ OK (using native input)")
    else:  # IOS
        # Check WebDriverAgent
        print(f"3. Checking WebDriverAgent ({wda_url})...", end=" ")
        try:
            conn = XCTestConnection(wda_url=wda_url)

            if conn.is_wda_ready():
                print("✅ OK")
                # Get WDA status for additional info
                status = conn.get_wda_status()
                if status:
                    session_id = status.get("sessionId", "N/A")
                    print(f"   Session ID: {session_id}")
            else:
                print("❌ FAILED")
                print("   Error: WebDriverAgent is not running or not accessible.")
                print("   Solution:")
                print("     1. Run WebDriverAgent on your iOS device via Xcode")
                print("     2. For USB: Set up port forwarding: iproxy 8100 8100")
                print(
                    "     3. For WiFi: Use device IP, e.g., --wda-url http://192.168.1.100:8100"
                )
                print("     4. Verify in browser: open http://localhost:8100/status")
                all_passed = False
        except Exception as e:
            print("❌ FAILED")
            print(f"   Error: {e}")
            all_passed = False

    print("-" * 50)

    if all_passed:
        print("✅ All system checks passed!\n")
    else:
        print("❌ System check failed. Please fix the issues above.")

    return all_passed


def check_model_api(base_url: str, model_name: str, api_key: str = "EMPTY") -> bool:
    """
    Check if the model API is accessible and the specified model exists.

    Checks:
    1. Network connectivity to the API endpoint
    2. Model exists in the available models list

    Args:
        base_url: The API base URL
        model_name: The model name to check
        api_key: The API key for authentication

    Returns:
        True if all checks pass, False otherwise.
    """
    print("🔍 Checking model API...")
    print("-" * 50)

    all_passed = True

    # Check 1: Network connectivity using chat API
    print(f"1. Checking API connectivity ({base_url})...", end=" ")
    try:
        # Create OpenAI client
        client = OpenAI(base_url=base_url, api_key=api_key, timeout=30.0)

        # Use chat completion to test connectivity (more universally supported than /models)
        response = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": "Hi"}],
            max_tokens=5,
            temperature=0.0,
            stream=False,
        )

        # Check if we got a valid response
        if response.choices and len(response.choices) > 0:
            print("✅ OK")
        else:
            print("❌ FAILED")
            print("   Error: Received empty response from API")
            all_passed = False

    except Exception as e:
        print("❌ FAILED")
        error_msg = str(e)

        # Provide more specific error messages
        if "Connection refused" in error_msg or "Connection error" in error_msg:
            print(f"   Error: Cannot connect to {base_url}")
            print("   Solution:")
            print("     1. Check if the model server is running")
            print("     2. Verify the base URL is correct")
            print(f"     3. Try: curl {base_url}/chat/completions")
        elif "timed out" in error_msg.lower() or "timeout" in error_msg.lower():
            print(f"   Error: Connection to {base_url} timed out")
            print("   Solution:")
            print("     1. Check your network connection")
            print("     2. Verify the server is responding")
        elif (
            "Name or service not known" in error_msg
            or "nodename nor servname" in error_msg
        ):
            print(f"   Error: Cannot resolve hostname")
            print("   Solution:")
            print("     1. Check the URL is correct")
            print("     2. Verify DNS settings")
        else:
            print(f"   Error: {error_msg}")

        all_passed = False

    print("-" * 50)

    if all_passed:
        print("✅ Model API checks passed!\n")
    else:
        print("❌ Model API check failed. Please fix the issues above.")

    return all_passed


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Phone Agent - AI-powered phone automation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Run with default settings (Android)
    python main.py

    # Specify model endpoint
    python main.py --base-url http://localhost:8000/v1

    # Use API key for authentication
    python main.py --apikey sk-xxxxx

    # Run with specific device
    python main.py --device-id emulator-5554

    # Connect to remote device
    python main.py --connect 192.168.1.100:5555

    # List connected devices
    python main.py --list-devices

    # Enable TCP/IP on USB device and get connection info
    python main.py --enable-tcpip

    # List supported apps
    python main.py --list-apps

    # iOS specific examples
    # Run with iOS device
    python main.py --device-type ios "Open Safari and search for iPhone tips"

    # Use WiFi connection for iOS
    python main.py --device-type ios --wda-url http://192.168.1.100:8100

    # List connected iOS devices
    python main.py --device-type ios --list-devices

    # Check WebDriverAgent status
    python main.py --device-type ios --wda-status

    # Pair with iOS device
    python main.py --device-type ios --pair
        """,
    )

    # Model options
    parser.add_argument(
        "--base-url",
        type=str,
        default=os.getenv("PHONE_AGENT_BASE_URL", "http://localhost:8000/v1"),
        help="Model API base URL",
    )

    parser.add_argument(
        "--model",
        type=str,
        default=os.getenv("PHONE_AGENT_MODEL", "autoglm-phone-9b"),
        help="Model name",
    )

    parser.add_argument(
        "--apikey",
        type=str,
        default=os.getenv("PHONE_AGENT_API_KEY", "EMPTY"),
        help="API key for model authentication",
    )

    parser.add_argument(
        "--max-steps",
        type=int,
        default=int(os.getenv("PHONE_AGENT_MAX_STEPS", "100")),
        help="Maximum steps per task",
    )

    # Device options
    parser.add_argument(
        "--device-id",
        "-d",
        type=str,
        default=os.getenv("PHONE_AGENT_DEVICE_ID"),
        help="ADB device ID",
    )

    parser.add_argument(
        "--connect",
        "-c",
        type=str,
        metavar="ADDRESS",
        help="Connect to remote device (e.g., 192.168.1.100:5555)",
    )

    parser.add_argument(
        "--disconnect",
        type=str,
        nargs="?",
        const="all",
        metavar="ADDRESS",
        help="Disconnect from remote device (or 'all' to disconnect all)",
    )

    parser.add_argument(
        "--list-devices", action="store_true", help="List connected devices and exit"
    )

    parser.add_argument(
        "--enable-tcpip",
        type=int,
        nargs="?",
        const=5555,
        metavar="PORT",
        help="Enable TCP/IP debugging on USB device (default port: 5555)",
    )

    # iOS specific options
    parser.add_argument(
        "--wda-url",
        type=str,
        default=os.getenv("PHONE_AGENT_WDA_URL", "http://localhost:8100"),
        help="WebDriverAgent URL for iOS (default: http://localhost:8100)",
    )

    parser.add_argument(
        "--pair",
        action="store_true",
        help="Pair with iOS device (required for some operations)",
    )

    parser.add_argument(
        "--wda-status",
        action="store_true",
        help="Show WebDriverAgent status and exit (iOS only)",
    )

    # Other options
    parser.add_argument(
        "--quiet", "-q", action="store_true", help="Suppress verbose output"
    )

    parser.add_argument(
        "--list-apps", action="store_true", help="List supported apps and exit"
    )

    parser.add_argument(
        "--lang",
        type=str,
        choices=["cn", "en"],
        default=os.getenv("PHONE_AGENT_LANG", "cn"),
        help="Language for system prompt (cn or en, default: cn)",
    )

    parser.add_argument(
        "--device-type",
        type=str,
        choices=["adb", "hdc", "ios"],
        default=os.getenv("PHONE_AGENT_DEVICE_TYPE", "adb"),
        help="Device type: adb for Android, hdc for HarmonyOS, ios for iPhone (default: adb)",
    )

    parser.add_argument(
        "task",
        nargs="?",
        type=str,
        help="Task to execute (interactive mode if not provided)",
    )
    # add
    parser.add_argument(
        "--voice", 
        action="store_true", 
        help="Enable voice input mode (requires microphone)"
    )
    # add
    parser.add_argument(
        "--learn", 
        action="store_true", 
        help="Enable Observer Mode to learn user habits"
    )

    return parser.parse_args()


def handle_ios_device_commands(args) -> bool:
    """
    Handle iOS device-related commands.

    Returns:
        True if a device command was handled (should exit), False otherwise.
    """
    conn = XCTestConnection(wda_url=args.wda_url)

    # Handle --list-devices
    if args.list_devices:
        devices = list_ios_devices()
        if not devices:
            print("No iOS devices connected.")
            print("\nTroubleshooting:")
            print("  1. Connect device via USB")
            print("  2. Unlock device and trust this computer")
            print("  3. Run: idevice_id -l")
        else:
            print("Connected iOS devices:")
            print("-" * 70)
            for device in devices:
                conn_type = device.connection_type.value
                model_info = f"{device.model}" if device.model else "Unknown"
                ios_info = f"iOS {device.ios_version}" if device.ios_version else ""
                name_info = device.device_name or "Unnamed"

                print(f"  ✓ {name_info}")
                print(f"    UUID: {device.device_id}")
                print(f"    Model: {model_info}")
                print(f"    OS: {ios_info}")
                print(f"    Connection: {conn_type}")
                print("-" * 70)
        return True

    # Handle --pair
    if args.pair:
        print("Pairing with iOS device...")
        success, message = conn.pair_device(args.device_id)
        print(f"{'✓' if success else '✗'} {message}")
        return True

    # Handle --wda-status
    if args.wda_status:
        print(f"Checking WebDriverAgent status at {args.wda_url}...")
        print("-" * 50)

        if conn.is_wda_ready():
            print("✓ WebDriverAgent is running")

            status = conn.get_wda_status()
            if status:
                print(f"\nStatus details:")
                value = status.get("value", {})
                print(f"  Session ID: {status.get('sessionId', 'N/A')}")
                print(f"  Build: {value.get('build', {}).get('time', 'N/A')}")

                current_app = value.get("currentApp", {})
                if current_app:
                    print(f"\nCurrent App:")
                    print(f"  Bundle ID: {current_app.get('bundleId', 'N/A')}")
                    print(f"  Process ID: {current_app.get('pid', 'N/A')}")
        else:
            print("✗ WebDriverAgent is not running")
            print("\nPlease start WebDriverAgent on your iOS device:")
            print("  1. Open WebDriverAgent.xcodeproj in Xcode")
            print("  2. Select your device")
            print("  3. Run WebDriverAgentRunner (Product > Test or Cmd+U)")
            print(f"  4. For USB: Run port forwarding: iproxy 8100 8100")

        return True

    return False


def handle_device_commands(args) -> bool:
    """
    Handle device-related commands.

    Returns:
        True if a device command was handled (should exit), False otherwise.
    """
    device_type = (
        DeviceType.ADB
        if args.device_type == "adb"
        else (DeviceType.HDC if args.device_type == "hdc" else DeviceType.IOS)
    )

    # Handle iOS-specific commands
    if device_type == DeviceType.IOS:
        return handle_ios_device_commands(args)

    device_factory = get_device_factory()
    ConnectionClass = device_factory.get_connection_class()
    conn = ConnectionClass()

    # Handle --list-devices
    if args.list_devices:
        devices = device_factory.list_devices()
        if not devices:
            print("No devices connected.")
        else:
            print("Connected devices:")
            print("-" * 60)
            for device in devices:
                status_icon = "✓" if device.status == "device" else "✗"
                conn_type = device.connection_type.value
                model_info = f" ({device.model})" if device.model else ""
                print(
                    f"  {status_icon} {device.device_id:<30} [{conn_type}]{model_info}"
                )
        return True

    # Handle --connect
    if args.connect:
        print(f"Connecting to {args.connect}...")
        success, message = conn.connect(args.connect)
        print(f"{'✓' if success else '✗'} {message}")
        if success:
            # Set as default device
            args.device_id = args.connect
        return not success  # Continue if connection succeeded

    # Handle --disconnect
    if args.disconnect:
        if args.disconnect == "all":
            print("Disconnecting all remote devices...")
            success, message = conn.disconnect()
        else:
            print(f"Disconnecting from {args.disconnect}...")
            success, message = conn.disconnect(args.disconnect)
        print(f"{'✓' if success else '✗'} {message}")
        return True

    # Handle --enable-tcpip
    if args.enable_tcpip:
        port = args.enable_tcpip
        print(f"Enabling TCP/IP debugging on port {port}...")

        success, message = conn.enable_tcpip(port, args.device_id)
        print(f"{'✓' if success else '✗'} {message}")

        if success:
            # Try to get device IP
            ip = conn.get_device_ip(args.device_id)
            if ip:
                print(f"\nYou can now connect remotely using:")
                print(f"  python main.py --connect {ip}:{port}")
                print(f"\nOr via ADB directly:")
                print(f"  adb connect {ip}:{port}")
            else:
                print("\nCould not determine device IP. Check device WiFi settings.")
        return True

    return False


def main():
    """Main entry point."""
    args = parse_args()

    # Set device type globally based on args
    if args.device_type == "adb":
        device_type = DeviceType.ADB
    elif args.device_type == "hdc":
        device_type = DeviceType.HDC
    else:  # ios
        device_type = DeviceType.IOS

    # Set device type globally for non-iOS devices
    if device_type != DeviceType.IOS:
        set_device_type(device_type)

    # Enable HDC verbose mode if using HDC
    if device_type == DeviceType.HDC:
        from phone_agent.hdc import set_hdc_verbose

        set_hdc_verbose(True)

    # Handle --list-apps (no system check needed)
    if args.list_apps:
        if device_type == DeviceType.HDC:
            print("Supported HarmonyOS apps:")
            apps = list_harmonyos_apps()
        elif device_type == DeviceType.IOS:
            print("Supported iOS apps:")
            print("\nNote: For iOS apps, Bundle IDs are configured in:")
            print("  phone_agent/config/apps_ios.py")
            print("\nCurrently configured apps:")
            apps = list_ios_apps()
        else:
            print("Supported Android apps:")
            apps = list_supported_apps()

        for app in sorted(apps):
            print(f"  - {app}")

        if device_type == DeviceType.IOS:
            print(
                "\nTo add iOS apps, find the Bundle ID and add to APP_PACKAGES_IOS dictionary."
            )
        return

    # Handle device commands (these may need partial system checks)
    if handle_device_commands(args):
        return

    # Run system requirements check before proceeding
    if not check_system_requirements(
        device_type,
        wda_url=args.wda_url
        if device_type == DeviceType.IOS
        else "http://localhost:8100",
    ):
        sys.exit(1)

    # Check model API connectivity and model availability
    if not check_model_api(args.base_url, args.model, args.apikey):
        sys.exit(1)

    # Create configurations and agent based on device type
    model_config = ModelConfig(
        base_url=args.base_url,
        model_name=args.model,
        api_key=args.apikey,
        lang=args.lang,
    )

    if device_type == DeviceType.IOS:
        # Create iOS agent
        agent_config = IOSAgentConfig(
            max_steps=args.max_steps,
            wda_url=args.wda_url,
            device_id=args.device_id,
            verbose=not args.quiet,
            lang=args.lang,
        )

        agent = IOSPhoneAgent(
            model_config=model_config,
            agent_config=agent_config,
        )
    else:
        # Create Android/HarmonyOS agent
        agent_config = AgentConfig(
            max_steps=args.max_steps,
            device_id=args.device_id,
            verbose=not args.quiet,
            lang=args.lang,
        )

        agent = PhoneAgent(
            model_config=model_config,
            agent_config=agent_config,
        )
    # add
    refiner = InstructionRefiner(model_config=model_config)

    # Print header
    print("=" * 50)
    if device_type == DeviceType.IOS:
        print("Phone Agent iOS - AI-powered iOS automation")
    else:
        print("Phone Agent - AI-powered phone automation")
    print("=" * 50)
    print(f"Model: {model_config.model_name}")
    print(f"Base URL: {model_config.base_url}")
    print(f"Max Steps: {agent_config.max_steps}")
    print(f"Language: {agent_config.lang}")
    print(f"Device Type: {args.device_type.upper()}")

    # Show iOS-specific config
    if device_type == DeviceType.IOS:
        print(f"WDA URL: {args.wda_url}")

    # Show device info
    if device_type == DeviceType.IOS:
        devices = list_ios_devices()
        if agent_config.device_id:
            print(f"Device: {agent_config.device_id}")
        elif devices:
            device = devices[0]
            print(f"Device: {device.device_name or device.device_id[:16]}")
            if device.model and device.ios_version:
                print(f"        {device.model}, iOS {device.ios_version}")
    else:
        device_factory = get_device_factory()
        devices = device_factory.list_devices()
        if agent_config.device_id:
            print(f"Device: {agent_config.device_id}")
        elif devices:
            print(f"Device: {devices[0].device_id} (auto-detected)")

    print("=" * 50)


    # add
    if args.learn:
        # 检查设备连接
        if not check_system_requirements(device_type):
            sys.exit(1)
            
        observer = UserObserver(
            device_id=args.device_id, 
            model_config=model_config
        )
        observer.start_learning_loop()
        return

    # Run with provided task or enter interactive mode
    if args.task:
        final_task = refiner.refine_task(args.task) # add
        print(f"\nTask: {final_task}\n")
        result = agent.run(final_task)
        print(f"\nResult: {result}")
    else:
        # Interactive mode

        # add
        # === 初始化语音模块 ===
        voice_manager = None
        if hasattr(args, 'voice') and args.voice:
            try:
                # 确保你已经创建了 phone_agent/voice.py 文件
                from phone_agent.voice import VoiceManager
                voice_manager = VoiceManager()
                print("🎤 语音模式已就绪！")
            except ImportError:
                print("❌ 错误: 未找到 phone_agent/voice.py 模块，无法启动语音模式。")
                sys.exit(1)
        # =============================

        print("\nEntering interactive mode. Type 'quit' to exit.\n")
    
        while True:
            try:
                # task = input("Enter your task: ").strip()

                # add
                # === 判断是语音输入还是文字输入 ===
                if args.voice and voice_manager:
                    # 1. 语音模式逻辑
                    user_input = input("\n[按回车键开始说话] (输入 'q' 退出) >> ").strip()
                    
                    if user_input.lower() in ("quit", "exit", "q"):
                        print("Goodbye!")
                        break
                    
                    # 调用语音识别
                    task = voice_manager.listen_and_transcribe()
                    
                    if not task:
                        print("⚠️ 未检测到语音，请重试")
                        continue
                        
                    print(f"🗣️ 识别到指令: {task}")
                    
                    # (可选) 让用户确认一下识别是否准确
                    confirm = input("确认执行? [Y/n]: ").strip().lower()
                    if confirm == 'n':
                        print("已取消，请重新录入。")
                        continue

                else:
                    # 2. 原有的文字输入逻辑
                    task = input("Enter your task: ").strip()
                # ==========================================
                if task.lower() in ("quit", "exit", "q"):
                    print("Goodbye!")
                    break

                if not task:
                    continue

                print()
                final_task = refiner.refine_task(task) # add
                result = agent.run(final_task)
                print(f"\nResult: {result}\n")
                agent.reset()

            except KeyboardInterrupt:
                print("\n\nInterrupted. Goodbye!")
                break
            except Exception as e:
                print(f"\nError: {e}\n")


if __name__ == "__main__":
    main()

class PersonalUI:
    """PersonalUI系统主类，整合所有功能模块"""
    
    def __init__(self, config_path: str = "config.json"):
        """
        初始化PersonalUI系统
        
        Args:
            config_path: 配置文件路径
        """
        self.config = self._load_config(config_path)
        self.knowledge_base = KnowledgeBase()
        self.refiner = InstructionRefiner()
        self.observer = UserObserver()
        self.phone_agent = None
        self.behavior_analyzer = BehaviorAnalyzer()
        self.vlm_analyzer = None
        self.graphrag = None
        self._init_modules()
    
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """加载配置文件"""
        default_config = {
            "model_config": {
                "base_url": "http://localhost:8000/v1",
                "model": "autoglm-phone-9b",
                "api_key": ""
            },
            "agent_config": {
                "max_steps": 100,
                "device_id": None,
                "lang": "cn"
            },
            "learning_config": {
                "api_key": "",
                "model": "glm-4.1v-thinking-flash",
                "output_dir": "data"
            },
            "graphrag_config": {
                "config_path": "graphrag/config.yaml",
                "max_concurrent_tasks": 3
            }
        }
        
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    user_config = json.load(f)
                    # 递归合并配置
                    self._deep_update(default_config, user_config)
            except Exception as e:
                print(f"加载配置文件失败: {e}, 使用默认配置")
        
        return default_config
    
    def _deep_update(self, base_dict: Dict[str, Any], update_dict: Dict[str, Any]) -> None:
        """递归更新字典"""
        for key, value in update_dict.items():
            if key in base_dict and isinstance(base_dict[key], dict) and isinstance(value, dict):
                self._deep_update(base_dict[key], value)
            else:
                base_dict[key] = value
    
    def _init_modules(self):
        """初始化各个模块"""
        # 初始化PhoneAgent
        model_config = ModelConfig(
            base_url=self.config["model_config"]["base_url"],
            model=self.config["model_config"]["model"],
            api_key=self.config["model_config"]["api_key"]
        )
        
        agent_config = AgentConfig(
            max_steps=self.config["agent_config"]["max_steps"],
            device_id=self.config["agent_config"]["device_id"],
            lang=self.config["agent_config"]["lang"]
        )
        
        self.phone_agent = PhoneAgent(model_config=model_config, agent_config=agent_config)
        
        # 初始化VLM分析器
        if self.config["learning_config"]["api_key"]:
            self.vlm_analyzer = VLMAnalyzer(
                api_key=self.config["learning_config"]["api_key"],
                model=self.config["learning_config"]["model"]
            )
        
        # 初始化GraphRAG
        graphrag_config_path = self.config["graphrag_config"]["config_path"]
        if os.path.exists(graphrag_config_path):
            try:
                self.graphrag = SimpleGraph(
                    config_path=graphrag_config_path,
                    max_concurrent_tasks=self.config["graphrag_config"]["max_concurrent_tasks"]
                )
            except Exception as e:
                print(f"初始化GraphRAG失败: {e}")
    
    def start_learning_mode(self, duration: Optional[int] = None, background: bool = False):
        """启动学习模式"""
        print("🎓 启动学习模式...")
        
        if background:
            # 后台学习模式
            self.behavior_analyzer.start_background_learning()
            print("后台学习模式已启动，按Ctrl+C停止")
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\n接收到停止信号，正在停止后台学习模式...")
                self.behavior_analyzer.stop_background_learning()
        else:
            # 前台学习模式
            sessions = self.behavior_analyzer.collect_and_process(duration_seconds=duration)
            
            if sessions and self.vlm_analyzer:
                # 分析收集到的数据
                print("🔍 分析用户行为数据...")
                output_dir = self.config["learning_config"]["output_dir"]
                sessions_dir = os.path.join(output_dir, "processed")
                
                result = self.vlm_analyzer.analyze_latest_session(sessions_dir)
                
                if "error" not in result and self.graphrag:
                    # 将分析结果存储到GraphRAG
                    self._store_analysis_to_graphrag(result)
    
    def _store_analysis_to_graphrag(self, analysis_result: Dict[str, Any]):
        """将分析结果存储到GraphRAG"""
        if not self.graphrag:
            print("GraphRAG未初始化，跳过存储")
            return
        
        try:
            # 提取分析结果中的关键信息
            if "analysis" in analysis_result and "analysis" in analysis_result["analysis"]:
                analysis = analysis_result["analysis"]["analysis"]
                
                # 构建任务描述
                task_description = f"用户行为分析: {analysis.get('main_action', '未知行为')}"
                if "intent" in analysis:
                    task_description += f", 意图: {analysis['intent']}"
                
                # 提交到GraphRAG
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                task_id = loop.run_until_complete(self.graphrag.submit_task(task_description))
                print(f"分析结果已提交到GraphRAG，任务ID: {task_id}")
                loop.close()
        except Exception as e:
            print(f"存储分析结果到GraphRAG失败: {e}")
    
    def start_execution_mode(self, task: str):
        """启动执行模式"""
        print(f"🚀 启动执行模式，任务: {task}")
        
        # 1. 使用InstructionRefiner优化指令
        refined_task = self.refiner.refine_task(task)
        
        # 2. 使用PhoneAgent执行任务
        result = self.phone_agent.run(refined_task)
        print(f"任务执行结果: {result}")
        
        return result
    
    def start_observer_mode(self):
        """启动观察模式"""
        print("👁️ 启动观察模式...")
        self.observer.start_learning_loop()
    
    def check_system_requirements(self) -> bool:
        """检查系统要求"""
        # 这里可以复用Open-AutoGLM中的系统检查逻辑
        print("🔍 检查系统要求...")
        # 简化版检查，实际可以更详细
        try:
            import subprocess
            result = subprocess.run(["adb", "devices"], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                lines = result.stdout.strip().split("\n")
                devices = [line for line in lines[1:] if line.strip() and "\tdevice" in line]
                if devices:
                    print(f"✅ 找到 {len(devices)} 个已连接设备")
                    return True
                else:
                    print("❌ 未找到已连接设备")
                    return False
            else:
                print("❌ ADB命令执行失败")
                return False
        except Exception as e:
            print(f"❌ 系统检查失败: {e}")
            return False


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="PersonalUI - 个性化GUI Agent系统")
    subparsers = parser.add_subparsers(dest="command", help="可用命令")
    
    # 学习模式命令
    learn_parser = subparsers.add_parser("learn", help="启动学习模式")
    learn_parser.add_argument("--duration", "-d", type=int, default=300, 
                             help="学习持续时间（秒），默认为300秒（5分钟）")
    learn_parser.add_argument("--background", "-b", action="store_true",
                             help="启动后台学习模式")
    
    # 执行模式命令
    exec_parser = subparsers.add_parser("exec", help="启动执行模式")
    exec_parser.add_argument("task", help="要执行的任务")
    
    # 观察模式命令
    obs_parser = subparsers.add_parser("observe", help="启动观察模式")
    
    # 系统检查命令
    check_parser = subparsers.add_parser("check", help="检查系统要求")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # 初始化PersonalUI系统
    personal_ui = PersonalUI()
    
    if args.command == "learn":
        personal_ui.start_learning_mode(duration=args.duration, background=args.background)
    elif args.command == "exec":
        personal_ui.start_execution_mode(args.task)
    elif args.command == "observe":
        personal_ui.start_observer_mode()
    elif args.command == "check":
        if personal_ui.check_system_requirements():
            print("✅ 系统检查通过")
        else:
            print("❌ 系统检查失败")
            sys.exit(1)


if __name__ == "__main__":
    main()
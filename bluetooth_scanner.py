import asyncio
import json
from bleak import BleakScanner

async def main():
    print("Scanning for Bluetooth devices...")
    try:
        devices = await BleakScanner.discover()
    except Exception as e:
        print(f"Error: {e}")
        print("Please make sure your Bluetooth is turned on and try again.")
        return
    
    if not devices:
        print("No Bluetooth devices found.")
        return

    print("Found devices:")
    for i, device in enumerate(devices):
        print(f"{i}: {device.name} ({device.address})")

    while True:
        try:
            selection = int(input("Select a device to save: "))
            if 0 <= selection < len(devices):
                break
            else:
                print("Invalid selection.")
        except ValueError:
            print("Invalid input.")

    selected_device = devices[selection]
    mac_address = selected_device.address

    with open('config.json', 'r+') as f:
        config = json.load(f)
        config['bluetooth_mac_address'] = mac_address
        f.seek(0)
        json.dump(config, f, indent=4)
        f.truncate()

    print(f"Saved {mac_address} to config.json")

if __name__ == "__main__":
    asyncio.run(main())

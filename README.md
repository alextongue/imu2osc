### Setup
- Install uv: [Installation | uv](https://docs.astral.sh/uv/getting-started/installation/)
- Clone this repo: `git clone `
- Go to directory set up your environment
    - `cd IMU2OSC/`
    - `uv sync`

### Instructions
- Turn on your IMU and make sure it is in pairing mode (table below).
    - Note: Do not pair the device in your Windows/macOS settings! The script handles Bluetooth pairing. If the IMU shows as connected, you must unpair it from your devices (check if other instances of this script are running).
- Run the main script: `uv run python run.sh`
    - The script will search for 5 seconds and report the list of devices. If the pairing device does not broadcast in time, press `r` to rescan.
    - Note: If using the WT9011DCL, the IMU will power off if it does not connect after a minute of broadcasting in pairing mode. Make sure it is turned on.
- Once the IMU is connected and sending OSC, open the port with any OSC compatible program from your destination computer.
    - By default, the script sends data to its own network bus (localhost, port 45531). This means any program on the same computer can easily pick up the stream.
    - Demo Max patch that listens on localhost:45531 on startup: `demo.maxpat`
- Press Ctrl+C to quit the script.

### OSC Addresses

The script sends data using the OSC convention, which specifies a tree-like address and typed data, over a UDP packet. Currently, the script sends out nine values: Acceleration, angular velocity, and integrated angle about the Cartesian axes. 

|Address|Value|Unit|
|---|---|---|
|`/imu/A*`|Acceleration along a cartesian axis, `*=[X,Y,Z]`, normalized to g (9.8 m/s^2)|$1$|
|`/imu/G*`|Rotational velocity about a Cartesian axis, `*=[X,Y,Z]`| $\mathrm{m/s}$|
|`/imu/ang*`|Estimated angle[^1] about a Cartesian axis, `*=[X,Y,Z]`|$^\circ$|

For example, your program may receive the message

```/imu/angZ 30.3```

corresponding with an estimated angle about the Z-axis. When the IMU is laying on the table with the logo facing up, this corresponds with Cartesian yaw.

[^1]: Angle is referenced to the last position recorded when the IMU begins sending data. It's recommended to set some logic that resets the angle in your live computer, or use a non-positional quantity instead (e.g. velocity, acceleration).

### IMU Behavior
|Device|Pairing|Connected|
|---|---|---|
|WT9011DCL|Light blinks twice, repeatedly | Light blinks slowly|
|BWT901CL|Blue light blinks quickly and continuously|Solid blue light|

### Todo
- Add step to connect wired COM and query MAC address/UUID, for easier pairing in a room full of devices

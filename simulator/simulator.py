#!/usr/bin/env python3
# python teste.py --ant "10,0" "0,0" "0,10" "10,10" --delay 0.5 --speed 1 --noise 0.2 --mqtt-broker 192.168.0.41 --mqtt-topic mottag/feed --mode mqtt
import argparse
import math
import random
import sys
import time
from collections import deque
import requests
import json
import paho.mqtt.client as mqtt

import matplotlib.pyplot as plt

# -------------------------------
# Your "center4" positioning algo
# -------------------------------
def estimate_center4(antenna_positions, antenna_rssi, config=None):
    if config is None:
        config = {}
    if len(antenna_positions) < 4:
        raise ValueError("center4 strategy requires at least 4 antennas")
    # Get indices of top 4 RSSI values
    top_indices = sorted(range(len(antenna_rssi)), key=lambda i: antenna_rssi[i], reverse=True)[:4]
    top_positions = [antenna_positions[i] for i in top_indices]
    top_rssi = [antenna_rssi[i] for i in top_indices]
    # Calculate center (average) of the 4 positions
    center_x = sum(pos[0] for pos in top_positions) / 4
    center_y = sum(pos[1] for pos in top_positions) / 4
    # Check if RSSI values are close
    rssi_range = max(top_rssi) - min(top_rssi)
    threshold = config.get("center4_rssi_threshold", 2.0)  # dBm, tunable
    if rssi_range <= threshold:
        return (center_x, center_y)
    else:
        # Weighted average toward stronger RSSI
        min_rssi = min(top_rssi)
        norm_rssi = [r - min_rssi + 1e-6 for r in top_rssi]  # avoid zero
        total = sum(norm_rsii for norm_rsii in norm_rssi)
        weighted_x = sum(pos[0] * w for pos, w in zip(top_positions, norm_rssi)) / total
        weighted_y = sum(pos[1] * w for pos, w in zip(top_positions, norm_rssi)) / total
        alpha = min(rssi_range / (threshold * 2), 1.0)  # 0=center, 1=weighted
        x = center_x * (1 - alpha) + weighted_x * alpha
        y = center_y * (1 - alpha) + weighted_y * alpha
        return (x, y)

# -------------------------------
# Motion + RSSI simulation
# -------------------------------
def clamp(v, lo, hi):
    return max(lo, min(hi, v))

def reflect_if_outside(x, y, vx, vy, xmin, xmax, ymin, ymax):
    # Reflect off walls to keep motion inside bounds
    if x < xmin:
        x = xmin + (xmin - x)
        vx = abs(vx)
    elif x > xmax:
        x = xmax - (x - xmax)
        vx = -abs(vx)
    if y < ymin:
        y = ymin + (ymin - y)
        vy = abs(vy)
    elif y > ymax:
        y = ymax - (y - ymax)
        vy = -abs(vy)
    # Clamp after reflection just in case
    x = clamp(x, xmin, xmax)
    y = clamp(y, ymin, ymax)
    return x, y, vx, vy

def smooth_random_velocity(vx, vy, accel_std, drag, dt):
    """Ornstein-Uhlenbeck-like update for smooth velocity."""
    ax = random.gauss(0, accel_std)
    ay = random.gauss(0, accel_std)
    vx = (1 - drag) * vx + ax * dt
    vy = (1 - drag) * vy + ay * dt
    return vx, vy

def rssi_from_distance(d, rssi_at_1m=-40.0, pathloss_n=2.0, noise_std=1.0):
    d = max(d, 0.1)  # avoid log(0); floor at 10 cm
    mean = rssi_at_1m - 10.0 * pathloss_n * math.log10(d / 1.0)
    return random.gauss(mean, noise_std)

def parse_ant_pair(s):
    # Accept formats like "0,0" or "(0,0)"
    s = s.strip().replace("(", "").replace(")", "")
    x_str, y_str = s.split(",")
    return float(x_str), float(y_str)

def send_rssi_to_server(rssis, mode="firebase", mqtt_client=None, mqtt_topic="rssi/feed"):
    timestamp = time.time()
    if mode == "firebase":
        data = {}
        for i, rssi in enumerate(rssis):
            # round to 2 decimal places
            data[f"scan{i+1}"] = {
                "rssi": round(rssi, 2),
                "server_timestamp": round(timestamp * 1000)  # milliseconds
            }
        payload = json.dumps(data)
        headers = {
        'Content-Type': 'application/json'
        }
        response = requests.request("PUT", "https://mottag-acbda-default-rtdb.firebaseio.com/feed/F0:24:F9:0D:4A:DA.json", headers=headers, data=payload)
    elif mode == "mqtt":
        if mqtt_client is None:
            print("Error: MQTT client not provided", file=sys.stderr)
            return
        for i, rssi in enumerate(rssis):
            # round to 2 decimal places
            data = {
                "aid": f"scan{i+1}",
                "events": [
                    {
                        "rssi": round(rssi, 2),
                        "addr": "7c:ec:79:47:89:bb",
                        "t": round(timestamp * 1000)  # milliseconds
                    }
                ],
                "time": round(timestamp * 1000)  # milliseconds
            }
            payload = json.dumps(data)
            mqtt_client.publish(mqtt_topic, payload)



def main():
    parser = argparse.ArgumentParser(
        description="Simulate RSSI for 4 antennas and live-plot estimated position via center4."
    )
    parser.add_argument(
        "--ant",
        dest="ants",
        metavar="X,Y",
        type=parse_ant_pair,
        nargs=4,
        required=True,
        help='Four antenna coords, e.g. --ant "0,0" "10,0" "10,10" "0,10"',
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.2,
        help="Delay between generations (seconds). Default: 0.2",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=2.0,
        help="center4 RSSI closeness threshold (dBm). Default: 2.0",
    )
    parser.add_argument(
        "--rssi1m",
        type=float,
        default=-40.0,
        help="RSSI at 1 m (dBm). Default: -40",
    )
    parser.add_argument(
        "--n",
        dest="pathloss_n",
        type=float,
        default=2.0,
        help="Path-loss exponent. Default: 2.0",
    )
    parser.add_argument(
        "--noise",
        type=float,
        default=1.0,
        help="RSSI noise std dev (dB). Default: 1.0",
    )
    parser.add_argument(
        "--speed",
        type=float,
        default=2.0,
        help="Target nominal speed (units/sec) for scaling motion. Default: 2.0",
    )
    parser.add_argument(
        "--trail",
        type=int,
        default=400,
        help="Number of recent points to keep in the plotted trace. Default: 400",
    )
    parser.add_argument(
        "--mode",
        type=str,
        choices=["firebase", "mqtt"],
        default="firebase",
        help="Data transmission mode: firebase or mqtt. Default: firebase",
    )
    parser.add_argument(
        "--mqtt-broker",
        type=str,
        default="localhost",
        help="MQTT broker address. Default: localhost",
    )
    parser.add_argument(
        "--mqtt-port",
        type=int,
        default=1883,
        help="MQTT broker port. Default: 1883",
    )
    parser.add_argument(
        "--mqtt-topic",
        type=str,
        default="rssi/feed",
        help="MQTT topic to publish to. Default: rssi/feed",
    )
    parser.add_argument(
        "--mqtt-username",
        type=str,
        default=None,
        help="MQTT username (optional)",
    )
    parser.add_argument(
        "--mqtt-password",
        type=str,
        default=None,
        help="MQTT password (optional)",
    )

    args = parser.parse_args()

    antennas = list(args.ants)
    if len(antennas) != 4:
        print("Please provide exactly 4 antenna coordinates.", file=sys.stderr)
        sys.exit(1)

    # Initialize MQTT client if mode is mqtt
    mqtt_client = None
    if args.mode == "mqtt":
        mqtt_client = mqtt.Client()
        if args.mqtt_username and args.mqtt_password:
            mqtt_client.username_pw_set(args.mqtt_username, args.mqtt_password)
        try:
            mqtt_client.connect(args.mqtt_broker, args.mqtt_port, 60)
            mqtt_client.loop_start()
            print(f"Connected to MQTT broker at {args.mqtt_broker}:{args.mqtt_port}")
        except Exception as e:
            print(f"Failed to connect to MQTT broker: {e}", file=sys.stderr)
            sys.exit(1)

    # Compute square-ish bounds from provided antennas
    xs = [a[0] for a in antennas]
    ys = [a[1] for a in antennas]
    xmin, xmax = min(xs), max(xs)
    ymin, ymax = min(ys), max(ys)

    # Start near the center
    x = sum(xs) / 4.0
    y = sum(ys) / 4.0

    # Initialize smooth motion
    vx, vy = 0.0, 0.0
    accel_std = args.speed * 3.0      # random acceleration scale
    drag = 0.15                        # velocity damping
    dt = max(args.delay, 1e-3)

    # Live plot setup
    plt.ion()
    fig, ax = plt.subplots()
    ax.set_title("Simulated Tracking (true vs. estimated)")
    ax.set_xlim(xmin - 0.1 * (xmax - xmin), xmax + 0.1 * (xmax - xmin))
    ax.set_ylim(ymin - 0.1 * (ymax - ymin), ymax + 0.1 * (ymax - ymin))
    ax.set_aspect("equal", adjustable="box")
    ax.grid(True, linestyle="--", linewidth=0.5)

    # Plot antennas
    ant_scatter = ax.scatter([a[0] for a in antennas], [a[1] for a in antennas], marker="^", s=100, label="Antennas")
    # True and estimated points
    true_pt = ax.scatter([x], [y], s=50, label="True")
    est_pt = ax.scatter([x], [y], s=50, marker="x", label="Estimated")

    # Path trace
    trail_true = deque(maxlen=args.trail)
    trail_est = deque(maxlen=args.trail)
    trail_true.append((x, y))
    trail_est.append((x, y))
    true_line, = ax.plot([x], [y], linewidth=1.0)
    est_line, = ax.plot([x], [y], linewidth=1.0, linestyle=":")

    ax.legend(loc="upper right")

    # Main loop
    try:
        while True:
            # Smooth random velocity update
            vx, vy = smooth_random_velocity(vx, vy, accel_std=accel_std, drag=drag, dt=dt)

            # Normalize to keep average speed near the target
            speed = math.hypot(vx, vy)
            if speed > 1e-6:
                scale = (args.speed / speed)
                vx *= scale
                vy *= scale

            # Integrate position
            x += vx * dt
            y += vy * dt

            # Reflect off walls, keep inside
            x, y, vx, vy = reflect_if_outside(x, y, vx, vy, xmin, xmax, ymin, ymax)

            # Generate RSSIs for each antenna
            rssis = []
            for (ax_, ay_) in antennas:
                d = math.hypot(x - ax_, y - ay_)
                rssi = rssi_from_distance(d, rssi_at_1m=args.rssi1m, pathloss_n=args.pathloss_n, noise_std=args.noise)
                rssis.append(rssi)

            # Estimate position via center4
            est_x, est_y = estimate_center4(antennas, rssis, config={"center4_rssi_threshold": args.threshold})

            # Print RSSIs
            rssi_str = " | ".join(f"A{i}:{rssis[i]:6.1f} dBm" for i in range(4))
            print(rssi_str)
            send_rssi_to_server(rssis, mode=args.mode, mqtt_client=mqtt_client, mqtt_topic=args.mqtt_topic)

            # Update plot
            trail_true.append((x, y))
            trail_est.append((est_x, est_y))

            true_pt.set_offsets([[x, y]])
            est_pt.set_offsets([[est_x, est_y]])

            if len(trail_true) > 1:
                tx, ty = zip(*trail_true)
                true_line.set_data(tx, ty)
            if len(trail_est) > 1:
                ex, ey = zip(*trail_est)
                est_line.set_data(ex, ey)

            fig.canvas.draw()
            fig.canvas.flush_events()
            time.sleep(args.delay)

    except KeyboardInterrupt:
        print("\nStopped by user.")
    finally:
        if mqtt_client is not None:
            mqtt_client.loop_stop()
            mqtt_client.disconnect()
        plt.ioff()
        plt.show()

if __name__ == "__main__":
    main()

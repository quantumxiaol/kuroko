"""PRC Server smoke test: Ping -> DescribeLibrary -> SetupRobot -> AddRobotTask (PTP axis motion).

Usage:
    uv run python scripts/test_prc_client.py

Requires the PRC Server running (scripts/start-prc-server.cmd).
Env overrides: PRC_ADDRESS (default 127.0.0.1:5001), PRC_SERVER_HOME (for the root certificate).
"""

import os
import sys
import time
from pathlib import Path

import grpc

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src" / "prc_client"))

import prc_pb2
import prc_pb2_grpc
import prc_library_pb2
import prc_library_pb2_grpc

ADDRESS = os.environ.get("PRC_ADDRESS", "127.0.0.1:5001")
SERVER_HOME = Path(os.environ.get("PRC_SERVER_HOME", ROOT / "third_service" / "prc-server"))
ROOT_CERT = SERVER_HOME / "Certificates" / "PRCRootCertificate.pem"


def connect() -> grpc.Channel:
    root_certs = ROOT_CERT.read_bytes() if ROOT_CERT.exists() else None
    if root_certs is None:
        print(f"WARNING: root certificate not found at {ROOT_CERT}, trying system roots")
    credentials = grpc.ssl_channel_credentials(root_certificates=root_certs)
    return grpc.secure_channel(
        ADDRESS,
        credentials,
        options=[
            ("grpc.max_receive_message_length", -1),
            ("grpc.max_send_message_length", -1),
        ],
    )


def main() -> int:
    channel = connect()
    grpc.channel_ready_future(channel).result(timeout=10)
    print(f"[1/4] Connected to {ADDRESS}")

    # --- Ping ---
    stub = prc_pb2_grpc.ParametricRobotControlServiceStub(channel)
    t0 = time.time()
    reply = stub.SendPing(prc_pb2.Ping(payload="kuroko"))
    rtt = (time.time() - t0) * 1000
    print(f"[2/4] Ping OK: server time_ms={reply.time_ms}, rtt={rtt:.0f} ms")

    # --- DescribeLibrary: pick a KUKA robot + free offline driver ---
    lib = prc_library_pb2_grpc.ParametricRobotControlLibraryServiceStub(channel)
    catalog = lib.DescribeLibrary(prc_library_pb2.DescribeLibraryRequest())
    print(f"      license_state: {catalog.license_state}")
    kuka_robots = [r for r in catalog.robots if r.vendor == "KUKA"]
    free_drivers = [d for d in catalog.drivers if not d.requires_license]
    print(f"[3/4] Library: {len(catalog.robots)} robots ({len(kuka_robots)} KUKA), "
          f"{len(catalog.drivers)} drivers ({len(free_drivers)} license-free)")

    robot_preset = next((r for r in kuka_robots if "KR50" in r.preset_robot_class), kuka_robots[0])
    driver = next((d for d in free_drivers if d.robot_driver_class == "KUKA.KSS_KRL_Driver"), free_drivers[0])
    print(f"      robot:  {robot_preset.preset_robot_class} ({robot_preset.name})")
    print(f"      driver: {driver.robot_driver_class} (requires_license={driver.requires_license})")

    # --- SetupRobot ---
    identity = prc_pb2.CartesianPosition(
        euler=prc_pb2.Euler(x=0, y=0, z=0, a=0, b=0, c=0, format=prc_pb2.ZYX)
    )
    setup = stub.SetupRobot(prc_pb2.SetupRobotRequest(
        client_id="kuroko-test",
        robot_setup=prc_pb2.Robot(
            preset_robot_class=robot_preset.preset_robot_class,
            robot_driver_class=driver.robot_driver_class,
            tool_dictionary={
                "0": prc_pb2.Tool(tool_type=prc_pb2.FIXED, tcp=identity, tool_id="0"),
            },
            initial_base=prc_pb2.Base(base_type=prc_pb2.FIXED, base_frame=identity, base_id="0"),
        ),
    ))
    print(f"      SetupRobot -> id={setup.id}, status={setup.status!r}")
    if not setup.id:
        print("SetupRobot FAILED")
        return 1

    # --- AddRobotTask: one PTP axis motion (values from the vvvv help patch) ---
    task = prc_pb2.Task(
        type=prc_pb2.SIMULATE_TASK,
        name="kuroko-smoke-test",
        payload=[prc_pb2.TaskPayload(
            motion_group_task=prc_pb2.MotionGroup(
                motion_group_type=prc_pb2.PTP,
                tool_id="0",
                commands=[prc_pb2.MotionCommand(
                    axis_motion=prc_pb2.AxisMotion(
                        target=prc_pb2.JointTarget(
                            axis_values=[110.0, -91.0, 88.0, 32.0, 38.0, 0.0],
                            speed=[15.0],
                        )
                    )
                )],
            )
        )],
    )
    result = stub.AddRobotTask(prc_pb2.AddRobotTaskRequest(
        id=setup.id, robot_task=task, robot_settings=setup.robot_settings,
    ))
    sim = result.simulation_result_data
    print(f"[4/4] AddRobotTask -> status={result.status!r}")
    print(f"      is_valid={sim.is_valid}, time={sim.time:.2f}s, steps={len(sim.simulation_results)}")
    if sim.simulation_results:
        last = sim.simulation_results[-1]
        print(f"      final axes: {[round(v, 2) for v in last.axis_values]}")
    if sim.code:
        lines = sim.code.splitlines()
        print(f"      generated program ({len(lines)} lines), first lines:")
        for line in lines[:6]:
            print(f"        {line}")

    ok = bool(setup.id) and sim.is_valid
    print("SMOKE TEST", "PASSED" if ok else "FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

"""Evaluate candidate "shy fold" joint poses for the KUKA LBR iiwa 7 R800 (7 axes).

Constraints from the installation design:
- TCP (with a strap/scarf attached) must stay well above the floor
- TCP should stay OUTSIDE the arm silhouette (no curling back -> tangling risk)

Reports TCP position (mm, Z-up, PRC convention) for each candidate so we can pick
a compact fold that keeps the end effector out and up.

Run:  uv run python scripts/eval_iiwa_pose.py   (PRC Server must be running)
"""

import sys
from pathlib import Path

import grpc

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src" / "prc_client"))

import prc_pb2
import prc_pb2_grpc
import prc_library_pb2
import prc_library_pb2_grpc

CANDIDATES = {
    "D4 ref [0,70,0,100,0,0,0]": [0, 70, 0, 100, 0, 0, 0],
    "F1 [0,70,0,100,0,90,0]": [0, 70, 0, 100, 0, 90, 0],
    "F2 [0,65,0,110,0,85,0]": [0, 65, 0, 110, 0, 85, 0],
    "F3 [0,75,0,95,0,90,0]": [0, 75, 0, 95, 0, 90, 0],
    "F4 [0,60,0,115,0,80,0]": [0, 60, 0, 115, 0, 80, 0],
    "F5 [0,55,0,120,0,90,0]": [0, 55, 0, 120, 0, 90, 0],
    "F6 [0,80,0,90,0,95,0]": [0, 80, 0, 90, 0, 95, 0],
}


def main() -> int:
    root_cert = (ROOT / "third_service/prc-server/Certificates/PRCRootCertificate.pem").read_bytes()
    channel = grpc.secure_channel("127.0.0.1:5001", grpc.ssl_channel_credentials(root_certificates=root_cert))
    grpc.channel_ready_future(channel).result(timeout=10)
    stub = prc_pb2_grpc.ParametricRobotControlServiceStub(channel)

    lib = prc_library_pb2_grpc.ParametricRobotControlLibraryServiceStub(channel)
    catalog = lib.DescribeLibrary(prc_library_pb2.DescribeLibraryRequest())
    iiwa = [r for r in catalog.robots if "LBR7R800" in r.preset_robot_class.upper()]
    print("iiwa presets on server:", [(r.preset_robot_class, r.name) for r in iiwa])
    preset = iiwa[0]
    print("using:", preset.preset_robot_class)

    identity = prc_pb2.CartesianPosition(euler=prc_pb2.Euler(format=prc_pb2.ZYX))
    setup = stub.SetupRobot(prc_pb2.SetupRobotRequest(
        client_id="kuroko-iiwa-eval",
        robot_setup=prc_pb2.Robot(
            preset_robot_class=preset.preset_robot_class,
            robot_driver_class="KUKA.KUKA_Sunrise_Driver",
            tool_dictionary={"0": prc_pb2.Tool(tool_type=prc_pb2.FIXED, tcp=identity, tool_id="0")},
            initial_base=prc_pb2.Base(base_type=prc_pb2.FIXED, base_frame=identity, base_id="0"),
        ),
    ))
    assert setup.id, setup.status

    print(f"{'pose':34s} {'valid':6s} {'TCP x':>7s} {'TCP y':>7s} {'TCP z(up)':>9s} {'radius':>7s}  axes echo")
    for name, axes in CANDIDATES.items():
        task = prc_pb2.Task(
            type=prc_pb2.SIMULATE_TASK,
            payload=[prc_pb2.TaskPayload(motion_group_task=prc_pb2.MotionGroup(
                motion_group_type=prc_pb2.PTP, tool_id="0",
                commands=[prc_pb2.MotionCommand(axis_motion=prc_pb2.AxisMotion(
                    target=prc_pb2.JointTarget(axis_values=axes, speed=[15.0])))],
            ))],
        )
        reply = stub.AddRobotTask(prc_pb2.AddRobotTaskRequest(
            id=setup.id, robot_task=task, robot_settings=setup.robot_settings))
        sim = reply.simulation_result_data
        if not sim.simulation_results:
            print(f"{name:34s} FAILED: {reply.status}")
            continue
        last = sim.simulation_results[-1]
        m = last.position
        x, y, z = m.m41, m.m42, m.m43
        radius = (x * x + y * y) ** 0.5
        alarms = any(u.alarm for u in sim.simulation_results)
        echo = [round(v) for v in last.axis_values]
        print(f"{name:34s} {str(sim.is_valid and not alarms):6s} {x:7.0f} {y:7.0f} {z:9.0f} {radius:7.0f}  {echo}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

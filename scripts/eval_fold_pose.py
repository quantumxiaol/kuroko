"""Evaluate candidate "shy fold" joint poses for the KR50 R2500 via the PRC gRPC API.

Sends each candidate as a SIMULATE_TASK axis motion and reports the resulting TCP
position (from the last simulation sample) so we can pick a compact, valid fold.

Run:  uv run python scripts/eval_fold_pose.py   (PRC Server must be running)
"""

import sys
from pathlib import Path

import grpc

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src" / "prc_client"))

import prc_pb2
import prc_pb2_grpc

CANDIDATES = {
    "P0 current [0,-95,95,0,75,0]": [0, -95, 95, 0, 75, 0],
    "P1 [0,-45,110,0,60,0]": [0, -45, 110, 0, 60, 0],
    "P2 [0,-25,125,0,75,0]": [0, -25, 125, 0, 75, 0],
    "P3 [0,-15,140,0,85,0]": [0, -15, 140, 0, 85, 0],
    "P4 [0,-60,120,0,80,0]": [0, -60, 120, 0, 80, 0],
    "P5 [0,-35,135,0,95,0]": [0, -35, 135, 0, 95, 0],
    "P6 [0,-70,130,0,70,0]": [0, -70, 130, 0, 70, 0],
}


def main() -> int:
    root_cert = (ROOT / "third_service/prc-server/Certificates/PRCRootCertificate.pem").read_bytes()
    channel = grpc.secure_channel("127.0.0.1:5001", grpc.ssl_channel_credentials(root_certificates=root_cert))
    grpc.channel_ready_future(channel).result(timeout=10)
    stub = prc_pb2_grpc.ParametricRobotControlServiceStub(channel)

    identity = prc_pb2.CartesianPosition(euler=prc_pb2.Euler(format=prc_pb2.ZYX))
    setup = stub.SetupRobot(prc_pb2.SetupRobotRequest(
        client_id="kuroko-fold-eval",
        robot_setup=prc_pb2.Robot(
            preset_robot_class="KUKA.KUKA_KR50R2500",
            robot_driver_class="KUKA.KSS_KRL_Driver",
            tool_dictionary={"0": prc_pb2.Tool(tool_type=prc_pb2.FIXED, tcp=identity, tool_id="0")},
            initial_base=prc_pb2.Base(base_type=prc_pb2.FIXED, base_frame=identity, base_id="0"),
        ),
    ))
    assert setup.id, setup.status

    print(f"{'pose':34s} {'valid':6s} {'TCP x (mm)':>10s} {'TCP y':>8s} {'TCP z(up)':>9s} {'radius':>8s}  axes echo")
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
        print(f"{name:34s} {str(sim.is_valid and not alarms):6s} {x:10.0f} {y:8.0f} {z:9.0f} {radius:8.0f}  {echo}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

import pytest
import grpc
import math
# from proto import sensing_pb2, sensing_pb2_grpc, common_pb2
from control_stubs import sensing_pb2, sensing_pb2_grpc, common_pb2


# -------------------------- 全局配置 --------------------------
SERVICE_ADDR = "localhost:50051"  # 替换为你的服务地址+端口
VALID_SENSORS = {  # 假设已知服务支持的传感器（黑盒可通过 ListSensors 动态获取，此处预定义简化用例）
    "camera": "camera_1341357758048443961",
    "lidar": "lidar_9702400832541927802",
    "imu": "imu_9602039028105126575"
}
INVALID_SENSOR = "invalid_sensor_999"
EMPTY_SENSOR = ""
LONG_SENSOR_NAME = "a" * 1024  # 超长传感器名称（边界测试）

# -------------------------- 测试夹具（复用资源） --------------------------
@pytest.fixture(scope="session")
def grpc_channel():
    """创建 gRPC 通道（会话级复用）"""
    channel = grpc.insecure_channel(SERVICE_ADDR)
    try:
        grpc.channel_ready_future(channel).result(timeout=5)
    except grpc.FutureTimeoutError:
        pytest.fail(f"服务 {SERVICE_ADDR} 未启动或网络不可达")
    yield channel
    channel.close()

@pytest.fixture(scope="session")
def sensing_stub(grpc_channel):
    """创建 SensingService 客户端存根"""
    return sensing_pb2_grpc.SensingServiceStub(grpc_channel)

@pytest.fixture(scope="session")
def supported_sensors(sensing_stub):
    """动态获取服务支持的传感器列表（通过参数注入使用）"""
    response = sensing_stub.ListSensors(common_pb2.Empty())
    assert isinstance(response, sensing_pb2.SensorMetaList)
    sensor_names: list[str] = []
    for meta in response.entries:
        assert isinstance(meta, sensing_pb2.SensorMetaList.SensorMeta)
        sensor_names.append(meta.name)
    return sensor_names

# -------------------------- 通用断言工具 --------------------------
def assert_header_valid(header: common_pb2.Header):
    assert isinstance(header.seq, int) and header.seq >= 0, "seq 必须是非负整数"
    assert isinstance(header.timestamp, float) and header.timestamp > 0, "timestamp 必须是有效时间戳"
    assert isinstance(header.frame_id, str) and header.frame_id.strip() != "", "frame_id 不能为空字符串"

def assert_quaternion_valid(quat: common_pb2.Quaternion):
    quat_norm = math.sqrt(quat.x**2 + quat.y**2 + quat.z**2 + quat.w**2)
    assert math.isclose(quat_norm, 1.0, abs_tol=1e-3), f"四元数模长={quat_norm}，应接近1.0"

def assert_camera_image_valid(image: sensing_pb2.CameraImage, expected_name: str):
    assert_header_valid(image.header)
    assert image.name == expected_name, f"传感器名称不匹配：预期 {expected_name}，实际 {image.name}"
    assert isinstance(image.height, int) and image.height > 0, "height 必须是正整数"
    assert isinstance(image.width, int) and image.width > 0, "width 必须是正整数"
    assert image.encoding in ["rgb8", "bgr8", "mono8", "32FC1"], f"不支持的编码格式：{image.encoding}"
    assert isinstance(image.step, int) and image.step > 0, "step 必须是正整数"
    assert len(image.data) == image.step * image.height, f"图像数据不完整：预期 {image.step*image.height} 字节，实际 {len(image.data)} 字节"

def assert_lidar_scan_valid(lidar: sensing_pb2.LidarScan, expected_name: str):
    assert_header_valid(lidar.header)
    assert lidar.name == expected_name, f"传感器名称不匹配：预期 {expected_name}，实际 {lidar.name}"
    assert lidar.angle_min < lidar.angle_max, "angle_min 必须小于 angle_max"
    assert isinstance(lidar.angle_increment, float) and lidar.angle_increment > 0, "angle_increment 必须是正浮点数"
    assert len(lidar.ranges) > 0, "ranges 列表不能为空"
    assert all(isinstance(r, float) and r >= 0 for r in lidar.ranges), "ranges 必须是非负浮点数"

def assert_imu_data_valid(imu: sensing_pb2.ImuData, expected_name: str):
    assert_header_valid(imu.header)
    assert imu.name == expected_name, f"传感器名称不匹配：预期 {expected_name}，实际 {imu.name}"
    assert_quaternion_valid(imu.orientation)
    assert isinstance(imu.angular_velocity.x, float)
    assert isinstance(imu.linear_acceleration.x, float)

def assert_sensor_meta_valid(ms: sensing_pb2.SensorMetaList):
    # assert isinstance(ms.entries, list), f"entries 必须是列表 (目前：{ms}: {type(ms)})"
    assert len(ms.entries) > 0, "服务应返回至少一个支持的传感器"
    for meta in ms.entries:
        assert isinstance(meta, sensing_pb2.SensorMetaList.SensorMeta)
        # assert isinstance(meta.type, sensing_pb2.SensorType)
        assert isinstance(meta.name, str) and meta.name.strip() != "", "传感器名称不能为空字符串"

# -------------------------- 测试用例：ListSensors --------------------------
def test_list_sensors_basic(sensing_stub):
    """正常调用 ListSensors，校验返回格式"""
    request = common_pb2.Empty()
    response = sensing_stub.ListSensors(request)

    assert isinstance(response, sensing_pb2.SensorMetaList), "返回类型必须是 SensorMetaList"
    assert_sensor_meta_valid(response)

def test_list_sensors_multiple_calls(sensing_stub):
    """多次调用 ListSensors，校验一致性"""
    request = common_pb2.Empty()
    for _ in range(10):
        response = sensing_stub.ListSensors(request)
        assert_sensor_meta_valid(response)

# -------------------------- 测试用例：GetSensors --------------------------
@pytest.mark.parametrize("sensor_names, expected_count", [
    # 正常场景：单个/多个/跨类型传感器
    ([VALID_SENSORS["camera"]], {"images": 1, "lidars": 0, "imus": 0}),
    ([VALID_SENSORS["lidar"]], {"images": 0, "lidars": 1, "imus": 0}),
    ([VALID_SENSORS["imu"]], {"images": 0, "lidars": 0, "imus": 1}),
    ([VALID_SENSORS["camera"], VALID_SENSORS["lidar"], VALID_SENSORS["imu"]], {"images": 1, "lidars": 1, "imus": 1}),
    # 边界场景：空列表（返回空数据）
    ([], {"images": 0, "lidars": 0, "imus": 0}),
])
def test_get_sensors_valid_cases(sensing_stub, sensor_names, expected_count):
    """GetSensors 合法输入场景"""
    request = sensing_pb2.SensorRequest(sensor_names=sensor_names)
    response = sensing_stub.GetSensors(request)

    assert(isinstance(response, sensing_pb2.SensorData))
    assert len(response.images) == expected_count["images"]
    assert len(response.lidars) == expected_count["lidars"]
    assert len(response.imus) == expected_count["imus"]

    for img in response.images:
        assert_camera_image_valid(img, img.name)
    for lidar in response.lidars:
        assert_lidar_scan_valid(lidar, lidar.name)
    for imu in response.imus:
        assert_imu_data_valid(imu, imu.name)

# 单独拆分：超长传感器名称用例（避免在 parametrize 中调用 fixture）
def test_get_sensors_long_name(sensing_stub, supported_sensors):
    """GetSensors 边界场景：超长传感器名称"""
    # 先判断服务是否支持超长名称传感器，不支持则跳过
    if LONG_SENSOR_NAME not in supported_sensors:
        pytest.skip(f"服务不支持超长名称传感器 {LONG_SENSOR_NAME}")

    # 支持则执行测试
    request = sensing_pb2.SensorRequest(sensor_names=[LONG_SENSOR_NAME])
    response = sensing_stub.GetSensors(request)

    assert(isinstance(response, sensing_pb2.SensorData))
    # 假设超长名称传感器是相机类型（根据实际调整）
    assert len(response.images) == 1
    assert_camera_image_valid(response.images[0], LONG_SENSOR_NAME)

# @pytest.mark.parametrize("invalid_sensor_names, expected_code", [
#     # 异常场景：非法传感器名称
#     ([INVALID_SENSOR], grpc.StatusCode.INVALID_ARGUMENT),
#     # 异常场景：空字符串传感器名称
#     ([EMPTY_SENSOR], grpc.StatusCode.INVALID_ARGUMENT),
#     # 异常场景：合法+非法混合
#     ([VALID_SENSORS["camera"], INVALID_SENSOR], grpc.StatusCode.INVALID_ARGUMENT),
# ])
# def test_get_sensors_invalid_cases(sensing_stub, invalid_sensor_names, expected_code):
#     """GetSensors 非法输入场景"""
#     request = sensing_pb2.SensorRequest(sensor_names=invalid_sensor_names)
#     with pytest.raises(grpc.RpcError) as excinfo:
#         sensing_stub.GetSensors(request)
    
#     assert excinfo.value.code() == expected_code, f"预期错误码 {expected_code}，实际 {excinfo.value.code()}"
#     exd = excinfo.value.details()
#     assert exd is not None
#     assert len(exd) > 0, "错误信息不能为空"

# 当前实现方案是，传感器名称无效则返回空数据而非报错
@pytest.mark.parametrize("invalid_sensor_names, expected_count", [
    # 场景：非法传感器名称
    ([INVALID_SENSOR], {"images": 0, "lidars": 0, "imus": 0}),
    # 场景：空字符串传感器名称
    ([EMPTY_SENSOR], {"images": 0, "lidars": 0, "imus": 0}),
    # 场景：合法+非法混合
    ([VALID_SENSORS["camera"], INVALID_SENSOR], {"images": 1, "lidars": 0, "imus": 0}),
])
def test_get_sensors_invalid_cases(sensing_stub, invalid_sensor_names, expected_count):
    """GetSensors 非法名称输入场景"""
    request = sensing_pb2.SensorRequest(sensor_names=invalid_sensor_names)
    response = sensing_stub.GetSensors(request)

    assert(isinstance(response, sensing_pb2.SensorData))
    assert(len(response.images) == expected_count["images"])
    if (expected_count["images"] == 1):
        assert_camera_image_valid(response.images[0], VALID_SENSORS["camera"])
    assert(len(response.lidars) == expected_count["lidars"])
    assert(len(response.imus) == expected_count["imus"])

# -------------------------- 测试用例：StreamSensors --------------------------
def test_stream_sensors_basic(sensing_stub):
    """StreamSensors 正常流式传输"""
    request = sensing_pb2.SensorRequest(sensor_names=[VALID_SENSORS["camera"], VALID_SENSORS["lidar"]])
    stream = sensing_stub.StreamSensors(request)

    frame_count = 0
    last_seq = -1
    for response in stream:
        # assert response.header.seq > last_seq, f"seq 未递增：上一帧 {last_seq}，当前帧 {response.header.seq}"
        # last_seq = response.header.seq

        assert len(response.images) == 1
        assert len(response.lidars) == 1
        assert_camera_image_valid(response.images[0], VALID_SENSORS["camera"])
        assert_lidar_scan_valid(response.lidars[0], VALID_SENSORS["lidar"])

        frame_count += 1
        if frame_count >= 10:
            break

    assert frame_count == 10, f"预期接收10帧，实际接收 {frame_count} 帧"

def test_stream_sensors_cancel_midway(sensing_stub):
    """StreamSensors 客户端中途取消流"""
    request = sensing_pb2.SensorRequest(sensor_names=[VALID_SENSORS["camera"]])
    stream = sensing_stub.StreamSensors(request)

    frame_count = 0
    for response in stream:
        frame_count += 1
        if frame_count == 3:
            stream.cancel()
            break

    assert frame_count == 3
    with pytest.raises(grpc.RpcError) as excinfo:
        next(stream)
    assert excinfo.value.code() == grpc.StatusCode.CANCELLED

# def test_stream_sensors_invalid_sensor(sensing_stub):
#     """StreamSensors 非法传感器请求"""
#     request = sensing_pb2.SensorRequest(sensor_names=[INVALID_SENSOR])
#     with pytest.raises(grpc.RpcError) as excinfo:
#         stream = sensing_stub.StreamSensors(request)
#         next(stream)

#     assert excinfo.value.code() == grpc.StatusCode.INVALID_ARGUMENT
#     exd = excinfo.value.details()
#     assert exd is not None
#     assert len(exd) > 0

# -------------------------- 测试用例：边界场景 --------------------------
def test_get_sensors_large_list(sensing_stub, supported_sensors):
    """GetSensors 边界场景：请求所有支持的传感器"""
    request = sensing_pb2.SensorRequest(sensor_names=supported_sensors)
    response = sensing_stub.GetSensors(request)

    assert isinstance(response, sensing_pb2.SensorData)
    returned_sensor_names = (
        [img.name for img in response.images] +
        [lidar.name for lidar in response.lidars] +
        [imu.name for imu in response.imus]
    )
    assert set(returned_sensor_names) == set(supported_sensors), "返回的传感器与支持的列表不一致"

def test_camera_large_data(sensing_stub, supported_sensors):
    """GetSensors 边界场景：超大图像数据（4K）"""
    _4k_sensor = "4k_camera"
    if _4k_sensor not in supported_sensors:
        pytest.skip(f"服务不支持 {_4k_sensor}，跳过该用例")

    request = sensing_pb2.SensorRequest(sensor_names=[_4k_sensor])
    response = sensing_stub.GetSensors(request)

    img = response.images[0]
    assert img.width == 3840 and img.height == 2160, "4K 图像分辨率不匹配"
    assert img.encoding == "rgb8", "编码格式不匹配"
    assert img.step == 3840 * 3, "step 计算错误（rgb8 编码：width*3）"
    assert len(img.data) == img.step * img.height, "4K 图像数据不完整"
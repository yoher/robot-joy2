# Video Streaming Implementation - joy2 v1.2.0

## Overview

This document describes the low-latency WebRTC video streaming implementation for the joy2 robot teleoperation system. The implementation focuses on minimizing latency for responsive remote control while maintaining acceptable video quality.

## Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────────┐
│                    Video Streaming Pipeline                      │
└─────────────────────────────────────────────────────────────────┘

USB Camera (/dev/video0)
    │
    ├─ Hardware MJPEG encoder (in camera)
    │
    ▼
camera_node (V4L2 + OpenCV)
    │
    ├─ Decodes MJPEG to BGR8 numpy arrays
    ├─ Re-encodes to JPEG (60% quality)
    │
    ▼
ROS2 Topics:
    ├─ /camera/image_raw (sensor_msgs/Image)
    └─ /camera/image_raw/compressed (sensor_msgs/CompressedImage)
         │
         ▼
webrtc_node (aiortc)
    │
    ├─ Decodes JPEG
    ├─ Converts BGR → RGB
    ├─ Encodes to VP8/H.264 (software on RPi)
    │
    ▼
WebRTC Stream (port 8080)
    │
    ▼
Web Browser
    │
    ├─ Decodes VP8/H.264
    └─ Renders video
```

### Message Flow

```
Camera → MJPEG → camera_node → JPEG → webrtc_node → VP8 → Browser
         HW enc   (5-10ms)    ROS2      (50-100ms)   WebRTC  (50-100ms)
                  decode+encode         decode+encode          decode+render
```

## Implementation Details

### camera_node

**File**: [`joy2/nodes/camera_node.py`](../joy2/nodes/camera_node.py)

**Key Features:**
- V4L2 backend for direct camera access (no GStreamer overhead)
- MJPEG format selection for hardware encoding
- Single-frame buffer (minimal latency)
- Dual publishing: raw + compressed
- QoS: BEST_EFFORT, VOLATILE, depth=1

**Low-Latency Optimizations:**

1. **V4L2 Backend** (line 88)
   ```python
   self.cap = cv2.VideoCapture(self.device_path, cv2.CAP_V4L2)
   ```
   - Direct V4L2 access
   - Avoids GStreamer initialization overhead
   - Eliminates "pipeline not created" warnings

2. **MJPEG Format** (line 100)
   ```python
   self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
   ```
   - Uses camera's hardware JPEG encoder
   - Reduces CPU load on Raspberry Pi
   - Faster than YUYV conversion

3. **Minimal Buffering** (line 107)
   ```python
   self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
   ```
   - Only keeps latest frame
   - Prevents queue buildup
   - Reduces buffering latency

4. **Optimized JPEG Quality** (line 155)
   ```python
   encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 60]
   ```
   - Balance between quality and speed
   - 60% quality ~25% smaller than 80%
   - Faster encoding and transmission

5. **Publishing Priority** (line 142)
   - Compressed image published before raw
   - Ensures WebRTC gets frames ASAP
   - Raw publishing doesn't delay compressed

### webrtc_node

**File**: [`joy2/nodes/webrtc_node.py`](../joy2/nodes/webrtc_node.py)

**Key Features:**
- Inherits from `aiortc.MediaStreamTrack`
- Asyncio-based web server in separate thread
- Frame age monitoring for latency analysis
- Standard WebRTC signaling (offer/answer)

**Low-Latency Optimizations:**

1. **No Artificial Delays** (line 57-84)
   ```python
   async def recv(self) -> VideoFrame:
       # No await asyncio.sleep() - let WebRTC pace naturally
   ```
   - Removed 33ms sleep
   - WebRTC handles frame pacing
   - Minimal latency

2. **Monotonic Timestamps** (line 70, 95)
   ```python
   video_frame.pts = int(time.monotonic() * 90000)
   ```
   - Consistent timing without clock jumps
   - 90kHz clock (WebRTC standard)
   - Reduces jitter

3. **Direct JPEG Decoding** (line 46)
   ```python
   np_arr = np.frombuffer(compressed_msg.data, np.uint8)
   frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
   ```
   - Bypasses cv_bridge overhead
   - Faster than compressed_imgmsg_to_cv2
   - Direct numpy/cv2 path

4. **Frame Age Monitoring** (line 74-81)
   ```python
   frame_age_ms = (current_time - self.frame_timestamp) * 1000
   if frame_age_ms > self.max_frame_age_ms:
       # Log but don't drop (prevents flickering)
   ```
   - Tracks latency through pipeline
   - Logs frames exceeding threshold
   - Monitoring without disruption

5. **Proper MediaStreamTrack Inheritance** (line 29)
   ```python
   class WebRTCVideoStreamTrack(MediaStreamTrack):
   ```
   - Uses aiortc's base class
   - Proper SDP direction handling
   - Eliminates "None is not in list" errors

6. **Thread-based Server** (line 137-161)
   ```python
   def run_server():
       loop = asyncio.new_event_loop()
       asyncio.set_event_loop(loop)
       # Run server in dedicated event loop
   ```
   - Separate event loop from ROS2
   - Avoids conflicts with rclpy.spin()
   - Stable server operation

7. **Client-Side Optimizations** (line 293-308)
   ```javascript
   video.playsInline = true;
   video.muted = true;
   video.play(); // Immediate playback
   ```
   - Immediate playback on track arrival
   - Minimizes browser buffering
   - Reduces display latency

## Latency Analysis

### Current Performance (v1.2.0)

**Total End-to-End Latency: ~500ms**

| Stage | Duration | Optimization Status |
|-------|----------|---------------------|
| Camera capture | ~5ms | ✅ Optimized (MJPEG hardware) |
| Camera → ROS2 | ~10ms | ✅ Optimized (single buffer) |
| ROS2 transport | <1ms | ✅ Optimized (BEST_EFFORT QoS) |
| JPEG decode | ~5ms | ✅ Optimized (direct cv2) |
| VP8/H.264 encode | ~50-100ms | ⚠️ **BOTTLENECK** (software) |
| WebRTC transport | ~20-50ms | ✅ Acceptable |
| Browser decode | ~50-100ms | ✅ Acceptable |
| Browser render | ~50-100ms | ✅ Acceptable |
| Network (LAN) | ~1-5ms | ✅ Minimal |
| Network (WiFi) | ~5-20ms | ✅ Acceptable |

### Bottleneck Identification

**Primary Bottleneck**: VP8/H.264 software encoding on Raspberry Pi

The webrtc_node must:
1. Decode incoming JPEG (5ms)
2. Convert BGR → RGB (1ms)
3. Create VideoFrame (1ms)
4. **Encode to VP8/H.264** (50-100ms) ← **Main delay**

The aiortc library uses software encoding which is slow on ARM processors.

### Optimization History

| Optimization | Latency Saved | Version |
|--------------|---------------|---------|
| Remove sleep delay | ~33ms | v1.2.0 |
| MJPEG hardware | ~20ms | v1.2.0 |
| Single buffers | ~10ms | v1.2.0 |
| Lower JPEG quality | ~5ms | v1.2.0 |
| V4L2 backend | ~3ms | v1.2.0 |
| **Total** | **~71ms** | **v1.2.0** |

## Future Improvements

### Hardware H.264 Encoding

**Raspberry Pi has hardware H.264 encoder** available at `/dev/video11` (bcm2835-codec)

**Approach**:
1. Use GStreamer pipeline or direct V4L2 to encode H.264
2. Pass encoded H.264 packets directly to WebRTC
3. Eliminate software VP8/H.264 encoding stage

**Expected Improvement**: ~80-150ms reduction (total latency <200ms)

**Implementation Complexity**: High
- Requires GStreamer integration or V4L2 encoding API
- Must handle H.264 packetization
- More complex than current JPEG approach

### Resolution Reduction

**Quick Win**: Reduce resolution to 320x240

**Expected Improvement**: ~30-50ms reduction
- Less data to process at every stage
- Faster encoding/decoding
- Lower bandwidth

**Trade-off**: Reduced visual clarity for teleoperation

### Alternative Approaches

1. **Raw Frame Transport**
   - Send raw YUYV frames via ROS2
   - Single VP8/H.264 encode in webrtc_node
   - Eliminates double JPEG coding
   - Higher ROS2 bandwidth (~10x)

2. **Direct RTSP Streaming**
   - Bypass WebRTC entirely
   - Use GStreamer RTSP server
   - Hardware H.264 encoding
   - Higher latency than WebRTC but simpler

3. **UV4L WebRTC**
   - Replace custom implementation with UV4L
   - Hardware-accelerated on Raspberry Pi
   - Commercial solution

## Configuration Reference

### camera_config.yaml

```yaml
camera_node:
  ros__parameters:
    # Hardware
    device_path: "/dev/video0"
    device_id: 0
    
    # Resolution & Performance
    width: 640                    # 320 for ultra-low latency
    height: 480                   # 240 for ultra-low latency
    fps: 30
    
    # Format
    encoding: "bgr8"
    frame_id: "camera_optical_frame"
    
    # Publishing
    publish_camera_info: true
    buffer_size: 1                # Minimal buffering
```

### webrtc_node Parameters

```yaml
webrtc_node:
  ros__parameters:
    host: "0.0.0.0"              # Listen on all interfaces
    port: 8080                    # WebRTC server port
    camera_topic: "camera/image_raw/compressed"
    qos_depth: 10                 # Subscription queue
```

## Troubleshooting

### No Video in Browser

1. **Check camera is publishing:**
   ```bash
   ros2 topic hz /camera/image_raw/compressed
   ```

2. **Check WebRTC node logs:**
   ```bash
   ros2 run joy2 webrtc_node --ros-args --log-level debug
   ```

3. **Verify browser console** for JavaScript errors

4. **Check network firewall** allows port 8080

### High Latency

1. **Check frame age in logs:**
   ```bash
   # Enable debug logging
   ros2 run joy2 webrtc_node --ros-args --log-level debug
   # Look for "Frame age exceeds threshold" warnings
   ```

2. **Verify camera is using MJPEG:**
   ```bash
   v4l2-ctl --device=/dev/video0 --get-fmt-video
   # Should show "Pixel Format: 'MJPG'"
   ```

3. **Check CPU usage:**
   ```bash
   top
   # webrtc_node should use 20-40% on RPi4
   # Higher usage indicates software encoding bottleneck
   ```

4. **Try lower resolution:**
   - Edit camera_config.yaml
   - Set width: 320, height: 240
   - Rebuild and test

### GStreamer Warnings

If you see GStreamer warnings:
```
[ WARN] global ./modules/videoio/src/cap_gstreamer.cpp (2401) handleMessage...
```

**Solution**: Already fixed in v1.2.0
- camera_node forces V4L2 backend
- No GStreamer initialization
- Warnings eliminated

### Black Screen or Flickering

**Cause**: Frame dropping too aggressive

**Solution**: Already fixed in v1.2.0
- Frame age monitoring only logs, doesn't drop
- Prevents black frame insertion
- Smooth video even with high latency

## Performance Benchmarks

### Raspberry Pi 4 (4GB)

| Resolution | JPEG Quality | FPS | Latency | CPU Usage |
|------------|--------------|-----|---------|-----------|
| 320x240 | 60% | 30 | ~300ms | 15-25% |
| 640x480 | 60% | 30 | ~500ms | 25-35% |
| 640x480 | 80% | 30 | ~550ms | 30-40% |
| 1280x720 | 60% | 20 | ~800ms | 45-60% |

### Network Impact

| Network Type | Additional Latency | Notes |
|--------------|-------------------|-------|
| Ethernet (local) | <5ms | Recommended |
| WiFi (same room) | 5-20ms | Good |
| WiFi (different room) | 20-50ms | Acceptable |
| WiFi (weak signal) | 50-200ms | May drop frames |

## Code Structure

### camera_node.py

```python
class CameraNode(Node):
    def _initialize_camera(self):
        # V4L2 backend selection
        self.cap = cv2.VideoCapture(path, cv2.CAP_V4L2)
        
        # MJPEG format for hardware encoding  
        self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
        
        # Minimal buffering
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        
    def _timer_callback(self):
        ret, frame = self.cap.read()
        
        # Publish compressed FIRST (priority)
        compressed_msg = CompressedImage()
        compressed_msg.format = "jpeg"
        _, encoded = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 60])
        compressed_msg.data = encoded.tobytes()
        self.compressed_pub.publish(compressed_msg)
        
        # Then publish raw (for other uses)
        img_msg = self.bridge.cv2_to_imgmsg(frame)
        self.image_pub.publish(img_msg)
```

### webrtc_node.py

```python
class WebRTCVideoStreamTrack(MediaStreamTrack):
    kind = "video"
    
    def update_frame(self, compressed_msg):
        # Direct JPEG decode
        np_arr = np.frombuffer(compressed_msg.data, np.uint8)
        frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        self.latest_frame = frame
        
    async def recv(self) -> VideoFrame:
        # No delay - minimal latency
        rgb = cv2.cvtColor(self.latest_frame, cv2.COLOR_BGR2RGB)
        frame = VideoFrame.from_ndarray(rgb, format="rgb24")
        
        # Monotonic timestamps
        frame.pts = int(time.monotonic() * 90000)
        frame.time_base = Fraction(1, 90000)
        return frame

class WebRTCNode(Node):
    async def _offer(self, request):
        # Standard WebRTC signaling
        pc = RTCPeerConnection()
        await pc.setRemoteDescription(offer)
        
        # Add video track with proper direction
        transceiver = pc.addTransceiver(self.video_track, direction="sendonly")
        
        answer = await pc.createAnswer()
        await pc.setLocalDescription(answer)
        return answer
```

## Key Design Decisions

### Why JPEG Intermediate Format?

**Decision**: Use JPEG compression between camera_node and webrtc_node

**Reasoning:**
1. **Bandwidth**: Compressed ROS2 messages (10KB vs 900KB)
2. **Compatibility**: Works with image_transport ecosystem
3. **Simplicity**: Standard ROS2 CompressedImage messages
4. **Hardware**: MJPEG cameras provide hardware encoding

**Trade-off**: Double encoding (MJPEG → JPEG → VP8/H.264)

**Future**: Raw frame transport or direct H.264 would eliminate this

### Why aiortc Instead of GStreamer?

**Decision**: Use aiortc Python library for WebRTC

**Reasoning:**
1. **Integration**: Pure Python, integrates with rclpy
2. **Simplicity**: Easier than GStreamer pipelines
3. **Flexibility**: Full control over encoding parameters
4. **Portability**: Works on any platform with Python

**Trade-off**: Software encoding slower than GStreamer hardware plugins

**Future**: GStreamer with hardware H.264 encoding for ultimate performance

### Why Separate camera_node and webrtc_node?

**Decision**: Two separate nodes instead of monolithic solution

**Reasoning:**
1. **Modularity**: Camera useful for other applications (SLAM, OpenCV)
2. **Standard topics**: Follows ROS2 conventions
3. **Flexibility**: Easy to add alternative streaming methods
4. **Testing**: Can test camera independently

**Trade-off**: Extra hop in pipeline adds minimal latency (<1ms)

### Why Not image_transport Plugins?

**Decision**: Manual compressed image publishing vs image_transport plugins

**Reasoning:**
1. **Control**: Direct control over JPEG quality
2. **Simplicity**: Less configuration, fewer dependencies
3. **Performance**: Inline encoding faster than plugin system

**Trade-off**: Doesn't integrate with image_transport ecosystem

## Testing and Validation

### Latency Measurement

**Method 1: Timestamp Comparison**
```python
# Add to webrtc_node recv():
capture_time = compressed_msg.header.stamp
current_time = time.time()
latency_ms = (current_time - capture_time) * 1000
print(f"Pipeline latency: {latency_ms}ms")
```

**Method 2: Visual Test**
1. Display timer on robot
2. Record video stream
3. Compare timestamps frame-by-frame

**Method 3: Frame Age Logs**
```bash
ros2 run joy2 webrtc_node --ros-args --log-level debug
# Look for "Frame X: age=XXms" messages
```

### Quality Validation

**Metrics to Monitor:**
- Frame rate consistency
- Dropped frame count
- Video quality perception
- Network bandwidth usage

**Tools:**
```bash
# Check frame rate
ros2 topic hz /camera/image_raw/compressed

# Monitor bandwidth
iftop -i wlan0  # or eth0

# Check CPU usage
htop
```

## Common Issues and Solutions

### Issue: GStreamer Warnings

**Symptoms:**
```
[ WARN] OpenCV | GStreamer warning: unable to start pipeline
```

**Root Cause**: OpenCV tries GStreamer before V4L2

**Solution**: Force V4L2 backend (implemented in v1.2.0)
```python
self.cap = cv2.VideoCapture(device, cv2.CAP_V4L2)
```

### Issue: WebRTC "None is not in list"

**Symptoms:**
```
ValueError: None is not in list (in and_direction function)
```

**Root Cause**: Missing SDP direction in transceiver

**Solution**: Proper MediaStreamTrack inheritance + explicit transceiver direction
```python
class WebRTCVideoStreamTrack(MediaStreamTrack):  # Inherit properly
    ...

pc.addTransceiver('video', direction='recvonly')  # Client side
pc.addTransceiver(track, direction='sendonly')    # Server side
```

### Issue: Server Not Starting

**Symptoms:**
```
curl: (7) Failed to connect to 127.0.0.1 port 8080
```

**Root Cause**: Event loop conflicts between asyncio and rclpy

**Solution**: Run server in dedicated thread with own event loop
```python
def run_server():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(start_server())
    loop.run_forever()

threading.Thread(target=run_server, daemon=True).start()
```

### Issue: Black Frames / Flickering

**Symptoms**: Video intermittently shows black frames

**Root Cause**: Aggressive frame dropping when frames are "old"

**Solution**: Monitor frame age but don't drop frames
```python
if frame_age_ms > threshold:
    logging.warning(f"Old frame: {frame_age_ms}ms")
    # But still send the frame - don't return black frame
```

## Version History

- **v1.2.0** (2025-09-30) - Low-latency optimizations, frame monitoring
- **v1.1.0** (2025-09-30) - Initial camera and WebRTC implementation
- **v1.0.0** (2025-09-30) - Core mecanum system

## References

- [aiortc Documentation](https://aiortc.readthedocs.io/)
- [ROS2 Image Transport](https://github.com/ros-perception/image_common/tree/ros2/image_transport)
- [WebRTC Specification](https://www.w3.org/TR/webrtc/)
- [V4L2 API](https://www.kernel.org/doc/html/latest/userspace-api/media/v4l/v4l2.html)
- [Raspberry Pi Camera](https://www.raspberrypi.com/documentation/computers/camera_software.html)

## Author

Yoann Hervieux (yoann.hervieux@gmail.com)

## License

Apache License 2.0
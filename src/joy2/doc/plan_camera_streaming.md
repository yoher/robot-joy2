# Camera Streaming Architecture Plan for ROS2

**Date**: 2025-09-30  
**Version**: v1.1.0 Planning  
**Status**: Architecture Design Phase  
**Goal**: Implement camera streaming for teleoperation and future VSLAM integration

---

## Requirements

### Primary Use Cases

1. **Teleoperation via Webapp**
   - Low-latency video streaming
   - Frame dropping acceptable under load
   - Mobile-friendly (iOS/Android browsers)
   - Interactive controls integration

2. **Future VSLAM Implementation**
   - High-quality timestamped frames
   - Camera calibration data (camera_info)
   - Stable, reliable stream
   - No audio required

---

## ROS2 Camera Best Practices Research

### Standard ROS2 Camera Stack

```
Camera Hardware
    ↓
camera_node (publishes sensor_msgs/Image + sensor_msgs/CameraInfo)
    ↓
image_transport (compression plugins: raw, compressed, theora)
    ↓
Multiple consumers (SLAM, visualization, recording, etc.)
```

### Key ROS2 Packages

1. **image_transport** - Efficient image transmission with compression
2. **cv_bridge** - OpenCV ↔ ROS message conversion
3. **camera_calibration** - Camera calibration tools
4. **image_pipeline** - Image processing nodes
5. **usb_cam** - USB camera driver (v4l2)
6. **v4l2_camera** - Alternative USB camera driver
7. **web_video_server** - HTTP/WebSocket video streaming
8. **foxglove_bridge** - Modern WebSocket bridge with WebRTC support

### Standard Message Types

- `sensor_msgs/Image` - Uncompressed image data
- `sensor_msgs/CompressedImage` - JPEG/PNG compressed images
- `sensor_msgs/CameraInfo` - Camera calibration and parameters

---

## Proposed Architecture

### Option 1: Full ROS2 Native (Recommended)

```mermaid
graph TB
    CAM[USB Camera<br>/dev/video0] --> CN[camera_node]
    
    CN -->|sensor_msgs/Image| IT[image_transport]
    CN -->|sensor_msgs/CameraInfo| CI[/camera/camera_info]
    
    IT -->|/camera/image_raw| RAW[Raw topic]
    IT -->|/camera/image_raw/compressed| COMP[Compressed topic]
    
    COMP --> FB[foxglove_bridge]
    FB -->|WebSocket + WebRTC| WEB[Web Teleoperation<br>Foxglove Studio]
    
    RAW --> SLAM[Future VSLAM Nodes]
    CI --> SLAM
    
    COMP --> WVS[web_video_server<br>Optional]
    WVS -->|HTTP MJPEG| BROWSER[Simple Browser View]
```

**Components:**
1. **camera_node** - Captures and publishes images
2. **image_transport** - Automatic compression/decompression
3. **foxglove_bridge** - Modern teleoperation with WebRTC
4. **web_video_server** (optional) - Simple HTTP streaming

**Benefits:**
- ✅ Standard ROS2 ecosystem integration
- ✅ Multiple consumers can subscribe simultaneously
- ✅ Automatic compression negotiation
- ✅ Camera calibration support
- ✅ Works with existing ROS2 SLAM packages
- ✅ Foxglove provides modern, mobile-friendly interface

### Option 2: Hybrid Approach

```mermaid
graph TB
    CAM[USB Camera] --> CN[camera_node]
    
    CN -->|sensor_msgs/Image| RAW[/camera/image_raw]
    CN -->|sensor_msgs/CameraInfo| CI[/camera/camera_info]
    
    RAW --> WN[webrtc_node<br>Custom]
    WN -->|aiortc| WEB[Web Teleoperation<br>Custom Webapp]
    
    RAW --> RN[rtsp_node<br>Custom]
    RN -->|GStreamer RTSP| RTSP[rtsp://pi:8554/vslam]
    
    RAW --> SLAM[Future VSLAM]
    CI --> SLAM
```

**Components:**
1. **camera_node** - Standard ROS2 camera publisher
2. **webrtc_node** - Custom WebRTC bridge (from old system)
3. **rtsp_node** - Custom RTSP server (from old system)

**Benefits:**
- ✅ Maintains existing webapp functionality
- ✅ Low-latency WebRTC for teleoperation
- ✅ Dedicated RTSP stream for VSLAM
- ⚠️ More custom code to maintain

### Option 3: Progressive Implementation (Recommended Start)

**Phase 1: Core Camera Node**
```
camera_node → /camera/image_raw (sensor_msgs/Image)
           → /camera/camera_info (sensor_msgs/CameraInfo)
```

**Phase 2: Add Compression**
```
camera_node → image_transport → /camera/image_raw/compressed
```

**Phase 3: Add Teleoperation**
```
+ foxglove_bridge OR custom webrtc_node
```

**Phase 4: Add VSLAM Support**
```
+ Camera calibration
+ Integration with SLAM packages
```

---

## Recommended Architecture (Detailed)

### Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────┐
│                    ROS2 Camera Streaming System                  │
└──────────────────────────────────────────────────────────────────┘

┌─────────────────┐
│  USB Camera     │
│  /dev/video0    │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│         camera_node                     │
│  • OpenCV VideoCapture                  │
│  • Configurable resolution/FPS          │
│  • Publishes Image + CameraInfo         │
│  • image_transport support              │
└─────┬──────────────────────┬────────────┘
      │                      │
      │ sensor_msgs/Image    │ sensor_msgs/CameraInfo
      │ /camera/image_raw    │ /camera/camera_info
      │                      │
      ├──────────────────────┼────────────────────────┐
      │                      │                        │
      ▼                      ▼                        ▼
┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│image_transport│      │foxglove_bridge│     │ VSLAM nodes  │
│ (compressed) │      │   (WebRTC)    │     │  (future)    │
└──────┬───────┘      └──────┬───────┘      └──────────────┘
       │                     │
       │ /camera/image_raw/  │ WebSocket
       │ compressed          │ + WebRTC
       │                     │
       ▼                     ▼
┌──────────────┐      ┌──────────────┐
│web_video_    │      │  Webapp      │
│server        │      │  Teleoperation│
│(optional)    │      │  + Video     │
└──────────────┘      └──────────────┘
```

---

## Proposed Implementation

### 1. camera_node (Core)

**File**: `src/joy2/joy2/nodes/camera_node.py`

**Responsibilities:**
- Capture video from USB camera using OpenCV
- Publish `sensor_msgs/Image` on `/camera/image_raw`
- Publish `sensor_msgs/CameraInfo` on `/camera/camera_info`
- Support image_transport for compression
- Configurable resolution, FPS, device

**Parameters:**
```yaml
camera_node:
  ros__parameters:
    device_id: 0                    # /dev/video0
    frame_id: "camera_optical_frame"
    width: 640
    height: 480
    fps: 30
    encoding: "bgr8"                # or "rgb8"
    publish_camera_info: true
    # Camera calibration (if available)
    camera_name: "usb_camera"
    camera_info_url: ""             # URL to calibration file
```

**Key Features:**
- OpenCV-based capture (VideoCapture)
- Rate-limited publishing (matches FPS)
- Proper header timestamps and frame_id
- Graceful error handling
- Resource cleanup on shutdown

**Dependencies:**
- `opencv-python` (cv2)
- `cv_bridge`
- `sensor_msgs`
- `camera_info_manager` (for calibration)

### 2. Teleoperation Streaming

### ⚠️ IMPORTANT: Foxglove vs Custom WebRTC

**Foxglove Bridge Limitation:**
- Foxglove bridge uses a **proprietary WebSocket protocol**
- It does NOT provide standard WebRTC streams
- Custom webapps CANNOT easily connect to it
- Only works with Foxglove Studio application

**For Custom Webapp:** You MUST use Option C (Custom WebRTC Node)

---

**Option A: Foxglove Bridge (Development/Debugging Only)**

Use official `foxglove_bridge` package:

```bash
sudo apt install ros-jazzy-foxglove-bridge
```

**Advantages:**
- ✅ Official ROS2 package, well-maintained
- ✅ Modern web interface (Foxglove Studio)
- ✅ Supports all ROS2 message types
- ✅ Great for development and debugging

**Limitations:**
- ❌ Cannot be used with custom webapps
- ❌ Requires Foxglove Studio (not a standard WebRTC client)

**Launch:**
```python
Node(
    package='foxglove_bridge',
    executable='foxglove_bridge',
    name='foxglove_bridge',
    parameters=[
        {'port': 8765},
        {'address': '0.0.0.0'},
        {'send_buffer_limit': 10000000}
    ]
)
```

**Access:**
- Foxglove Studio: `ws://<pi_ip>:8765`
- Web: https://studio.foxglove.dev (connect to ws://<pi_ip>:8765)

**Option B: web_video_server**

Simple HTTP MJPEG streaming:

```bash
sudo apt install ros-jazzy-web-video-server
```

**Launch:**
```python
Node(
    package='web_video_server',
    executable='web_video_server',
    name='web_video_server',
    parameters=[
        {'port': 8080},
        {'server_threads': 2}
    ]
)
```

**Access:**
- Stream: `http://<pi_ip>:8080/stream?topic=/camera/image_raw/compressed`

**Option C: Custom WebRTC Node** ⭐ **REQUIRED FOR CUSTOM WEBAPP**

Port the old `webrtc_stream.py` to ROS2 as a separate node:

**File**: `src/joy2/joy2/nodes/webrtc_node.py`

**Approach:**
- Subscribe to `/camera/image_raw/compressed` (ROS2 topic)
- Use aiortc for standard WebRTC peer connections
- Serve custom webapp via aiohttp HTTP server
- WebRTC signaling via HTTP endpoints (/offer, /ice, etc.)
- Your custom webapp can:
  - Display video via standard WebRTC (RTCPeerConnection)
  - Send robot commands via WebSocket or HTTP
  - Use virtual joysticks
  - Custom UI/UX

**Pros:**
- ✅ **Works with your custom webapp** (standard WebRTC protocol)
- ✅ Full control over implementation
- ✅ Can integrate robot controls in same interface
- ✅ Matches old system functionality
- ✅ Standard web technologies (any browser)

**Cons:**
- More code to maintain (~300-400 lines)
- Requires aiortc, aiohttp dependencies
- Need to maintain webapp separately

### 3. VSLAM Support

**Standard ROS2 Approach:**

VSLAM packages (like ORB-SLAM3, RTAB-Map) typically need:
- `sensor_msgs/Image` on a standard topic
- `sensor_msgs/CameraInfo` for calibration
- Proper timestamp synchronization

**Recommended Setup:**
```
camera_node → /camera/image_raw (sensor_msgs/Image)
           → /camera/camera_info (sensor_msgs/CameraInfo)
                    ↓
              VSLAM Package (e.g., rtabmap_ros, orb_slam3_ros)
```

**No need for separate RTSP server** - VSLAM packages subscribe to ROS topics directly.

---

## Recommended Solution: Hybrid Best-of-Both

### Architecture

```
┌─────────────┐
│ USB Camera  │
└──────┬──────┘
       │
       ▼
┌──────────────────────────────┐
│      camera_node             │
│  • OpenCV VideoCapture       │
│  • Publishes Image+CameraInfo│
└───┬──────────────────────┬───┘
    │                      │
    │ Image                │ CameraInfo
    ▼                      ▼
┌───────────────┐    ┌──────────────┐
│image_transport│    │/camera/      │
│               │    │camera_info   │
└───┬───────────┘    └──────┬───────┘
    │                       │
    ├─→ /image_raw          │
    ├─→ /image_raw/compressed
    └─→ /image_raw/theora   │
         │                  │
         ├──────────────────┼───────────────┐
         │                  │               │
         ▼                  ▼               ▼
    ┌────────────┐   ┌────────────┐  ┌──────────┐
    │foxglove_   │   │ VSLAM      │  │Recording │
    │bridge      │   │ (future)   │  │/playback │
    │(WebRTC)    │   │            │  │          │
    └─────┬──────┘   └────────────┘  └──────────┘
          │
          ▼
    ┌────────────┐
    │  Webapp    │
    │Teleoperation│
    └────────────┘
```

### Components

1. **camera_node** - Custom ROS2 node
   - OpenCV-based capture
   - Publishes sensor_msgs/Image + CameraInfo
   - image_transport integration
   - Configurable via parameters

2. **foxglove_bridge** - Official package (sudo apt install)
   - WebRTC streaming
   - WebSocket protocol
   - Works with Foxglove Studio or custom webapp

3. **image_transport** - Standard ROS2 (comes with ros-jazzy-image-transport)
   - Automatic compression plugins
   - Bandwidth optimization

4. **Optional: web_video_server** - For simple HTTP MJPEG viewing

### Why This Approach?

✅ **ROS2 Native**: Uses standard ROS2 patterns and tools  
✅ **Flexible**: Multiple consumers can subscribe  
✅ **VSLAM Ready**: Standard Image+CameraInfo topics  
✅ **Modern Teleoperation**: Foxglove provides excellent mobile/web interface  
✅ **Bandwidth Efficient**: image_transport compression  
✅ **Maintainable**: Minimal custom code  
✅ **Scalable**: Easy to add more consumers  

---

## Implementation Plan

### Phase 1: Core Camera Node ✅ PRIORITY

**Task 1.1: Create camera_node.py**

```python
#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image, CameraInfo
from cv_bridge import CvBridge
import cv2

class CameraNode(Node):
    """ROS2 camera node using OpenCV VideoCapture."""
    
    def __init__(self):
        super().__init__('camera_node')
        
        # Parameters
        self.declare_parameter('device_id', 0)
        self.declare_parameter('width', 640)
        self.declare_parameter('height', 480)
        self.declare_parameter('fps', 30)
        self.declare_parameter('frame_id', 'camera_optical_frame')
        
        # Publishers
        self.image_pub = self.create_publisher(Image, 'camera/image_raw', 10)
        self.info_pub = self.create_publisher(CameraInfo, 'camera/camera_info', 10)
        
        # OpenCV bridge
        self.bridge = CvBridge()
        
        # Initialize camera
        self.cap = cv2.VideoCapture(device_id)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        self.cap.set(cv2.CAP_PROP_FPS, fps)
        
        # Timer for publishing
        self.timer = self.create_timer(1.0/fps, self.timer_callback)
    
    def timer_callback(self):
        ret, frame = self.cap.read()
        if ret:
            msg = self.bridge.cv2_to_imgmsg(frame, encoding="bgr8")
            msg.header.stamp = self.get_clock().now().to_msg()
            msg.header.frame_id = self.frame_id
            self.image_pub.publish(msg)
            
            # Publish camera info
            info_msg = CameraInfo()
            info_msg.header = msg.header
            info_msg.width = width
            info_msg.height = height
            self.info_pub.publish(info_msg)
```

**Files to create:**
- `src/joy2/joy2/nodes/camera_node.py`
- `src/joy2/config/camera_config.yaml`

**Task 1.2: Add dependencies**

Update `package.xml`:
```xml
<depend>sensor_msgs</depend>
<depend>cv_bridge</depend>
<depend>image_transport</depend>
<depend>camera_info_manager</depend>
```

**Task 1.3: Update setup.py**
```python
'camera_node = joy2.nodes.camera_node:main',
```

**Task 1.4: Update launch file**
```python
Node(
    package='joy2',
    executable='camera_node',
    name='camera_node',
    parameters=[
        {'device_id': 0},
        {'width': 640},
        {'height': 480},
        {'fps': 30},
        {'frame_id': 'camera_optical_frame'}
    ]
)
```

### Phase 2: Teleoperation Streaming

**Option A: Use Foxglove Bridge (Quick, Recommended)**

```bash
# Install
sudo apt install ros-jazzy-foxglove-bridge

# Add to launch file
Node(
    package='foxglove_bridge',
    executable='foxglove_bridge',
    name='foxglove_bridge',
    parameters=[
        {'port': 8765},
        {'address': '0.0.0.0'}
    ]
)
```

**Access:**
1. Open https://studio.foxglove.dev
2. Connect to `ws://<raspberry_pi_ip>:8765`
3. Add camera panel showing `/camera/image_raw/compressed`
4. Can also view other topics (/cmd_vel, /joy, etc.)

**Option B: Custom WebRTC Node**

Port the old `webrtc_stream.py` to ROS2:

**File**: `src/joy2/joy2/nodes/webrtc_node.py`

```python
#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import CompressedImage
from aiortc import RTCPeerConnection, VideoStreamTrack
import asyncio

class WebRTCNode(Node):
    """WebRTC streaming node for low-latency teleoperation."""
    
    def __init__(self):
        super().__init__('webrtc_node')
        
        # Subscribe to compressed images
        self.subscription = self.create_subscription(
            CompressedImage,
            'camera/image_raw/compressed',
            self.image_callback,
            10
        )
        
        # WebRTC setup
        self.latest_frame = None
        # ... aiortc setup
```

**Dependencies:**
- aiortc
- aiohttp
- opencv-python

### Phase 3: Web Interface

**Option A: Use Foxglove Studio**
- No custom code needed
- Modern, full-featured interface
- Built-in joystick support

**Option B: Custom Webapp**
- Port old webapp to work with foxglove_bridge WebSocket
- Or subscribe directly to ROS topics via rosbridge

**Option C: Simple Image View**
```bash
sudo apt install ros-jazzy-web-video-server

ros2 run web_video_server web_video_server
# Access: http://<pi_ip>:8080/stream?topic=/camera/image_raw/compressed
```

---

## Technical Specifications

### Image Encoding

**For Teleoperation (compressed):**
- Format: JPEG compressed (sensor_msgs/CompressedImage)
- Quality: 60-80%  (configurable)
- Resolution: 640x480 or 1280x720
- FPS: 15-30 (lower latency)

**For VSLAM (raw or lightly compressed):**
- Format: bgr8 or rgb8 (sensor_msgs/Image)
- Resolution: Higher quality (720p or 1080p)
- FPS: 30
- Camera calibration required

### Performance Considerations

**Bandwidth:**
- Raw 640x480@30fps RGB: ~27 MB/s
- JPEG 640x480@30fps (80% quality): ~3-5 MB/s
- H.264 640x480@30fps: ~1-2 MB/s (via WebRTC)

**Latency:**
- Raw/JPEG: ~50-100ms
- WebRTC: ~100-300ms
- MJPEG (HTTP): ~200-500ms

### Camera Calibration

For VSLAM, camera calibration is essential:

```bash
# Use ROS2 camera calibration
ros2 run camera_calibration cameracalibrator \
    --size 8x6 \
    --square 0.025 \
    image:=/camera/image_raw
```

Saves to `~/.ros/camera_info/camera_name.yaml`

---

## Message Specifications

### sensor_msgs/Image

```
std_msgs/Header header
  builtin_interfaces/Time stamp
  string frame_id
uint32 height
uint32 width
string encoding          # e.g., "bgr8", "rgb8", "mono8"
uint8 is_bigendian
uint32 step             # Row stride in bytes
uint8[] data            # Actual image data
```

### sensor_msgs/CompressedImage

```
std_msgs/Header header
string format           # "jpeg", "png"
uint8[] data           # Compressed image bytes
```

### sensor_msgs/CameraInfo

```
std_msgs/Header header
uint32 height
uint32 width
string distortion_model
float64[] d            # Distortion parameters
float64[9] k           # Camera intrinsic matrix
float64[9] r           # Rectification matrix
float64[12] p          # Projection matrix
uint32 binning_x
uint32 binning_y
sensor_msgs/RegionOfInterest roi
```

---

## Dependencies to Add

### package.xml
```xml
<!-- Camera dependencies -->
<depend>sensor_msgs</depend>
<depend>cv_bridge</depend>
<depend>image_transport</depend>
<depend>camera_info_manager</depend>

<!-- Optional: for compressed transport -->
<depend>image_transport_plugins</depend>

<!-- Optional: for WebRTC -->
<depend>foxglove_bridge</depend>

<!-- Optional: for simple web viewing -->
<depend>web_video_server</depend>
```

### Python Dependencies (if custom WebRTC)
```
opencv-python>=4.8.0
# For custom WebRTC node:
aiortc>=1.9.0
aiohttp>=3.10.0
```

---

## Configuration Files

### camera_config.yaml

```yaml
camera_node:
  ros__parameters:
    # Hardware
    device_id: 0                      # /dev/video0
    device_path: "/dev/video0"        # Alternative to device_id
    
    # Image format
    width: 640
    height: 480
    fps: 30
    encoding: "bgr8"                  # bgr8, rgb8, mono8
    
    # Frame identification
    frame_id: "camera_optical_frame"
    camera_name: "usb_camera"
    
    # Camera info
    publish_camera_info: true
    camera_info_url: ""               # Optional: file:///path/to/calibration.yaml
    
    # Performance
    buffer_size: 1                    # Keep only latest frame
    
    # Quality settings (for internal processing)
    auto_exposure: true
    auto_white_balance: true
```

### Integration with existing system

Add to `complete_system.launch.py`:
```python
# Camera node
Node(
    package='joy2',
    executable='camera_node',
    name='camera_node',
    parameters=[
        {'device_id': 0},
        {'width': 640},
        {'height': 480},
        {'fps': 30}
    ]
),

# Foxglove bridge for teleoperation
Node(
    package='foxglove_bridge',
    executable='foxglove_bridge',
    name='foxglove_bridge',
    parameters=[
        {'port': 8765},
        {'address': '0.0.0.0'}
    ]
),
```

---

## Testing Plan

### Phase 1: Camera Node Testing

```bash
# Terminal 1: Run camera node
ros2 run joy2 camera_node

# Terminal 2: Check topics
ros2 topic list | grep camera
# Should see:
# /camera/image_raw
# /camera/camera_info
# /camera/image_raw/compressed (if image_transport running)

# Terminal 3: View images
ros2 run rqt_image_view rqt_image_view /camera/image_raw

# Terminal 4: Check frequency
ros2 topic hz /camera/image_raw
```

### Phase 2: Compression Testing

```bash
# Check compressed topics
ros2 topic list | grep compressed

# View compressed image
ros2 run rqt_image_view rqt_image_view /camera/image_raw/compressed

# Check bandwidth
ros2 topic bw /camera/image_raw
ros2 topic bw /camera/image_raw/compressed
```

### Phase 3: Teleoperation Testing

**With Foxglove:**
```bash
# Launch system with foxglove_bridge
ros2 launch joy2 complete_system.launch.py

# Open browser to https://studio.foxglove.dev
# Connect to ws://<pi_ip>:8765
# Add Image panel for /camera/image_raw/compressed
# Test control and video simultaneously
```

**With web_video_server:**
```bash
# Access MJPEG stream
curl http://<pi_ip>:8080/stream?topic=/camera/image_raw/compressed
# Or open in browser
```

### Phase 4: Integration Testing

- [ ] Camera + motor control simultaneously
- [ ] Video during robot movement (check for dropped frames)
- [ ] Network bandwidth under load
- [ ] Latency measurements
- [ ] Multiple client connections

---

## Performance Optimization

### 1. Resolution/FPS Tradeoffs

| Resolution | FPS | Bandwidth (JPEG) | Latency | Use Case |
|------------|-----|------------------|---------|----------|
| 320x240    | 30  | ~1 MB/s          | Low     | Testing  |
| 640x480    | 30  | ~3-5 MB/s        | Medium  | Teleoperation |
| 640x480    | 15  | ~1.5-2.5 MB/s    | Lower   | Bandwidth-limited |
| 1280x720   | 30  | ~8-12 MB/s       | Higher  | VSLAM |
| 1920x1080  | 30  | ~15-20 MB/s      | High    | Recording |

### 2. Compression Quality

```yaml
# In camera_node or image_transport config
image_transport:
  compressed:
    jpeg_quality: 80      # 0-100 (higher = better quality, more bandwidth)
    png_level: 3          # 0-9 (higher = slower, smaller)
```

### 3. Network Optimization

- Use compressed topics for teleoperation
- Use raw topics only for VSLAM processing
- Consider H.264 via WebRTC for lowest bandwidth
- QoS profiles for reliability vs latency trade-offs

---

## Alternative: Custom Streaming Nodes

If Foxglove doesn't meet requirements, implement custom nodes:

### webrtc_streaming_node.py

**Subscribes to:** `/camera/image_raw/compressed`  
**Provides:** WebRTC stream via aiortc  
**Serves:** HTML interface with controls  
**Port:** 8080  

**Based on old system:**
- `temp_/joy2_old/src/joy2/video/webrtc_stream.py`
- Adapt to subscribe to ROS2 topics
- Integrate with ROS2 node lifecycle

### rtsp_streaming_node.py

**Subscribes to:** `/camera/image_raw`  
**Provides:** RTSP stream via GStreamer  
**URL:** `rtsp://<pi_ip>:8554/vslam`  

**Based on old system:**
- `temp_/joy2_old/src/joy2/video/rtsp_server.py`
- Convert to ROS2 subscriber pattern
- Use cv_bridge for image conversion

---

## Comparison: Foxglove vs Custom WebRTC

| Feature | Foxglove Bridge | Custom WebRTC Node |
|---------|----------------|-------------------|
| **Custom Webapp Support** | ❌ No (proprietary protocol) | ✅ Yes (standard WebRTC) |
| **Setup** | `apt install` | Custom code (~300 lines) |
| **Maintenance** | Official support | Self-maintained |
| **Interface** | Foxglove Studio only | Your custom webapp |
| **Mobile** | Excellent | Your webapp design |
| **ROS Integration** | Full (debugging) | Subscribe to camera topic |
| **Latency** | ~100-300ms | ~100-300ms |
| **Customization** | Limited | Full control |
| **Use Case** | Debugging/monitoring | **Production teleoperation** |

**CRITICAL:** If you want to use a custom webapp, you MUST implement the custom WebRTC node. Foxglove is only useful for development/debugging with Foxglove Studio.

---

## Timeline and Milestones

### v1.1.0 - Camera Streaming (Full Implementation for Custom Webapp)

- [x] v1.0.0 - Mecanum refactoring complete
- [ ] Phase 1: camera_node implementation (2-3 hours)
  - OpenCV VideoCapture
  - sensor_msgs/Image + CameraInfo publishers
  - Configuration support
- [ ] Phase 2: webrtc_node implementation (4-6 hours) ⭐ **REQUIRED**
  - Port from old system to ROS2
  - Subscribe to `/camera/image_raw/compressed`
  - aiortc WebRTC streaming
  - Serve signaling endpoints (/offer, /ice)
- [ ] Phase 3: image_transport integration (1 hour)
  - Install and configure
  - Test compression plugins
- [ ] Phase 4: Webapp integration (2-3 hours)
  - Update webapp to connect to webrtc_node endpoints
  - Integrate with ROS2 `/cmd_vel` topic (via WebSocket or HTTP)
  - Test on mobile devices
- [ ] Phase 5: Testing and documentation (2 hours)

**Estimated Total:** 11-15 hours

### v1.2.0 - Advanced Features (Optional)

- [ ] RTSP streaming node for alternative clients
- [ ] Camera calibration integration
- [ ] Multiple camera support
- [ ] H.264 hardware encoding (if available)
- [ ] Foxglove bridge (for debugging)

**Estimated Total:** 5-8 hours

---

## Questions to Resolve

1. ✅ **Primary streaming method?** → Foxglove Bridge (v1.1.0)
2. ❓ **Camera calibration?** → Will calibration file be provided, or calibrate later?
3. ❓ **Multiple cameras?** → Support for multiple cameras in future?
4. ❓ **Recording?** → Should we support bag recording of video?
5. ❓ **Webapp preference?** → Use Foxglove Studio or port old custom webapp?

---

## Risks and Mitigation

### Risk 1: Foxglove Bridge Performance
**Mitigation:** Test with actual hardware first, fallback to custom WebRTC if needed

### Risk 2: Camera Compatibility
**Mitigation:** Use v4l2-ctl to test camera before integration

### Risk 3: Network Bandwidth
**Mitigation:** Adjustable resolution/FPS/quality parameters

### Risk 4: VSLAM Integration Complexity
**Mitigation:** Start with standard topics, defer VSLAM to separate project phase

---

## FINAL Recommendation for Custom Webapp

**For v1.1.0, implement:**

1. ✅ **camera_node** - Standard ROS2 camera publisher ⭐ **CORE**
   - Publishes sensor_msgs/Image to `/camera/image_raw`
   - Publishes sensor_msgs/CameraInfo to `/camera/camera_info`
   - Enables all downstream consumers (VSLAM, recording, streaming)

2. ✅ **webrtc_node** - Custom WebRTC streaming ⭐ **REQUIRED FOR CUSTOM WEBAPP**
   - Subscribes to `/camera/image_raw/compressed`
   - Provides WebRTC streams using aiortc (standard WebRTC protocol)
   - Serves your custom webapp via aiohttp HTTP server
   - Handles WebRTC signaling (/offer, /ice endpoints)
   - Enables your existing webapp to work with ROS2

3. ✅ **image_transport** - Standard ROS2 package
   - Auto-creates compressed topics
   - Install via apt: `ros-jazzy-image-transport`

4. 📋 **foxglove_bridge** - Optional (for debugging)
   - Install via apt for development/monitoring only
   - NOT used for production teleoperation with custom webapp

**Why this approach:**
- ✅ Your custom webapp will work (via webrtc_node)
- ✅ Standard ROS2 camera topics for future VSLAM
- ✅ Can still use Foxglove Studio for debugging
- ✅ Flexible, maintainable, ROS2-native architecture

**Next Steps:**
1. Review and approve this revised plan
2. Switch to code mode for implementation
3. Create camera_node.py (standard ROS2 publisher)
4. Create webrtc_node.py (port aiortc WebRTC from old system)
5. Update/port webapp to connect to webrtc_node
6. Test teleoperation with video
7. Verify VSLAM-ready topics exist

---

**Last Updated**: 2025-09-30  
**Status**: Architecture Proposed, Awaiting Approval  
**Target Version**: v1.1.0
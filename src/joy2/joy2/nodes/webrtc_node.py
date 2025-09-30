#!/usr/bin/env python3
"""
ROS2 WebRTC Streaming Node for Joy2 Robot.

Provides low-latency WebRTC video streaming for teleoperation.
Subscribes to ROS2 camera topics and serves WebRTC streams to web clients.
"""

import asyncio
import json
import logging
import os
import sys
from typing import Optional, Dict, Any

import cv2
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, QoSReliabilityPolicy, QoSDurabilityPolicy
from sensor_msgs.msg import CompressedImage
from cv_bridge import CvBridge
from aiohttp import web
from aiortc import RTCPeerConnection, RTCSessionDescription
from aiortc.mediastreams import MediaStreamTrack
from av import VideoFrame
import numpy as np


class WebRTCVideoStreamTrack(MediaStreamTrack):
    """WebRTC video stream track that gets frames from ROS2 compressed images."""

    kind = "video"

    def __init__(self):
        super().__init__()
        self.latest_frame: Optional[np.ndarray] = None
        self.frame_timestamp = 0
        self.bridge = CvBridge()

    def update_frame(self, compressed_msg: CompressedImage):
        """Update the latest frame from ROS2 compressed image message."""
        try:
            # Decode compressed image
            if compressed_msg.format == "jpeg":
                # Convert compressed JPEG to numpy array
                frame = self.bridge.compressed_imgmsg_to_cv2(compressed_msg, desired_encoding="bgr8")
                self.latest_frame = frame
                self.frame_timestamp = compressed_msg.header.stamp.sec + compressed_msg.header.stamp.nanosec * 1e-9
                logging.debug(f"Updated frame: {frame.shape}")
            else:
                logging.warning(f"Unsupported compressed format: {compressed_msg.format}")
        except Exception as e:
            logging.error(f"Failed to decode compressed image: {e}")
            import traceback
            logging.error(f"Traceback: {traceback.format_exc()}")

    async def recv(self) -> VideoFrame:
        """Receive video frame for WebRTC - optimized for low latency."""
        import time
        from fractions import Fraction
        
        # No artificial delay - let WebRTC handle frame pacing for minimal latency
        
        if self.latest_frame is None:
            # Return black frame if no frame available
            logging.debug("No frame available, returning black frame")
            black_frame = np.zeros((480, 640, 3), dtype=np.uint8)
            video_frame = VideoFrame.from_ndarray(black_frame, format="bgr24")
            # Use monotonic clock for consistent timing
            video_frame.pts = int(time.monotonic() * 90000)  # 90kHz clock
            video_frame.time_base = Fraction(1, 90000)
            return video_frame

        # Convert BGR to RGB for WebRTC
        rgb_frame = cv2.cvtColor(self.latest_frame, cv2.COLOR_BGR2RGB)

        # Create VideoFrame
        video_frame = VideoFrame.from_ndarray(rgb_frame, format="rgb24")
        # Use monotonic clock for consistent, low-jitter timing
        video_frame.pts = int(time.monotonic() * 90000)  # 90kHz clock
        video_frame.time_base = Fraction(1, 90000)
        
        logging.debug(f"Sending frame: {rgb_frame.shape}, pts={video_frame.pts}")

        return video_frame


class WebRTCNode(Node):
    """ROS2 WebRTC streaming node."""

    def __init__(self):
        super().__init__('webrtc_node')

        # Declare parameters
        self.declare_parameter('port', 8080)
        self.declare_parameter('host', '0.0.0.0')
        self.declare_parameter('camera_topic', 'camera/image_raw/compressed')
        self.declare_parameter('qos_depth', 10)

        # Get parameters
        self.port = self.get_parameter('port').value
        self.host = self.get_parameter('host').value
        self.camera_topic = self.get_parameter('camera_topic').value
        qos_depth = self.get_parameter('qos_depth').value

        # QoS profile for camera subscription
        qos_profile = QoSProfile(
            reliability=QoSReliabilityPolicy.BEST_EFFORT,
            durability=QoSDurabilityPolicy.VOLATILE,
            depth=qos_depth
        )

        # ROS2 subscription to compressed camera images
        self.subscription = self.create_subscription(
            CompressedImage,
            self.camera_topic,
            self._image_callback,
            qos_profile
        )

        # WebRTC components
        self.video_track = WebRTCVideoStreamTrack()
        self.peer_connections: set = set()

        # Web server components
        self.app = None
        self.runner = None
        self.site = None

        # Start web server
        self._start_web_server()

        self.get_logger().info(
            f'WebRTC node initialized: listening on {self.host}:{self.port}, '
            f'subscribed to {self.camera_topic}'
        )

    def _image_callback(self, msg: CompressedImage):
        """Handle incoming compressed image messages."""
        self.video_track.update_frame(msg)

    def _start_web_server(self):
        """Start the web server for WebRTC signaling."""
        self.app = web.Application()
        self.app.router.add_get('/', self._index)
        self.app.router.add_post('/offer', self._offer)

        # Start server in background thread to avoid ROS2 event loop conflicts
        import threading
        def run_server():
            try:
                self.get_logger().info('Starting WebRTC server thread...')
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

                # Create and start the server
                self.runner = web.AppRunner(self.app)
                loop.run_until_complete(self.runner.setup())
                self.get_logger().info(f'AppRunner setup complete for {self.host}:{self.port}')

                self.site = web.TCPSite(self.runner, self.host, self.port)
                loop.run_until_complete(self.site.start())
                self.get_logger().info(f'WebRTC server started successfully on {self.host}:{self.port}')

                loop.run_forever()
            except Exception as e:
                self.get_logger().error(f'Failed to start web server thread: {e}')
                import traceback
                self.get_logger().error(f'Traceback: {traceback.format_exc()}')

        server_thread = threading.Thread(target=run_server, daemon=True)
        server_thread.start()
        self.get_logger().info('WebRTC server thread started')


    async def _index(self, request):
        """Serve the HTML client page."""
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Joy2 WebRTC Teleoperation</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 20px;
            background-color: #f0f0f0;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #333;
            text-align: center;
        }}
        video {{
            width: 100%;
            max-width: 640px;
            border: 2px solid #333;
            border-radius: 5px;
        }}
        .status {{
            margin: 10px 0;
            padding: 10px;
            border-radius: 5px;
        }}
        .status.connected {{
            background-color: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }}
        .status.disconnected {{
            background-color: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }}
        .controls {{
            margin-top: 20px;
            text-align: center;
        }}
        button {{
            padding: 10px 20px;
            margin: 0 10px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 16px;
        }}
        .connect-btn {{
            background-color: #007bff;
            color: white;
        }}
        .disconnect-btn {{
            background-color: #dc3545;
            color: white;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Joy2 Robot Teleoperation</h1>

        <div id="status" class="status disconnected">
            Status: Disconnected
        </div>

        <div style="text-align: center; margin: 20px 0;">
            <video id="video" autoplay playsinline muted></video>
        </div>

        <div class="controls">
            <button id="connectBtn" class="connect-btn">Connect</button>
            <button id="disconnectBtn" class="disconnect-btn" disabled>Disconnect</button>
        </div>

        <div style="margin-top: 20px;">
            <h3>Controls:</h3>
            <p>Use joystick/gamepad for robot control. Video stream updates in real-time.</p>
        </div>
    </div>

    <script>
        let peerConnection = null;
        let localStream = null;

        const video = document.getElementById('video');
        const status = document.getElementById('status');
        const connectBtn = document.getElementById('connectBtn');
        const disconnectBtn = document.getElementById('disconnectBtn');

        // WebRTC configuration
        const config = {{
            iceServers: [
                {{ urls: 'stun:stun.l.google.com:19302' }}
            ]
        }};

        async function connect() {{
            try {{
                status.textContent = 'Status: Connecting...';
                status.className = 'status disconnected';

                peerConnection = new RTCPeerConnection(config);

                peerConnection.ontrack = (event) => {{
                    if (event.track.kind === 'video') {{
                        video.srcObject = event.streams[0];
                    }}
                }};

                peerConnection.onconnectionstatechange = () => {{
                    console.log('Connection state:', peerConnection.connectionState);
                    if (peerConnection.connectionState === 'connected') {{
                        status.textContent = 'Status: Connected';
                        status.className = 'status connected';
                        connectBtn.disabled = true;
                        disconnectBtn.disabled = false;
                    }} else if (peerConnection.connectionState === 'disconnected' ||
                             peerConnection.connectionState === 'failed') {{
                        status.textContent = 'Status: Disconnected';
                        status.className = 'status disconnected';
                        connectBtn.disabled = false;
                        disconnectBtn.disabled = true;
                    }}
                }};

                // Add transceiver to request video from server
                peerConnection.addTransceiver('video', {{
                    direction: 'recvonly'
                }});

                // Create offer
                const offer = await peerConnection.createOffer();
                await peerConnection.setLocalDescription(offer);

                // Send offer to server
                const response = await fetch('/offer', {{
                    method: 'POST',
                    headers: {{
                        'Content-Type': 'application/json'
                    }},
                    body: JSON.stringify({{
                        sdp: offer.sdp,
                        type: offer.type
                    }})
                }});

                if (!response.ok) {{
                    throw new Error(`Server error: ${{response.status}}`);
                }}

                const answer = await response.json();
                await peerConnection.setRemoteDescription(answer);

            }} catch (error) {{
                console.error('Connection failed:', error);
                status.textContent = 'Status: Connection Failed';
                status.className = 'status disconnected';
                connectBtn.disabled = false;
                disconnectBtn.disabled = true;
            }}
        }}

        function disconnect() {{
            if (peerConnection) {{
                peerConnection.close();
                peerConnection = null;
            }}
            video.srcObject = null;
            status.textContent = 'Status: Disconnected';
            status.className = 'status disconnected';
            connectBtn.disabled = false;
            disconnectBtn.disabled = true;
        }}

        connectBtn.addEventListener('click', connect);
        disconnectBtn.addEventListener('click', disconnect);

        // Auto-connect on page load
        window.addEventListener('load', () => {{
            setTimeout(connect, 1000);
        }});
    </script>
</body>
</html>
        """
        return web.Response(text=html_content, content_type='text/html')

    async def _offer(self, request):
        """Handle WebRTC offer and return answer."""
        try:
            # Parse offer
            offer_data = await request.json()
            if 'sdp' not in offer_data or 'type' not in offer_data:
                raise ValueError("Invalid offer format")

            self.get_logger().info('Received WebRTC offer')

            # Create peer connection
            pc = RTCPeerConnection()
            self.peer_connections.add(pc)

            @pc.on("connectionstatechange")
            async def on_connectionstatechange():
                self.get_logger().info(f"WebRTC connection state: {pc.connectionState}")
                if pc.connectionState in ["failed", "closed"]:
                    self.peer_connections.discard(pc)

            # Set remote description first
            await pc.setRemoteDescription(RTCSessionDescription(
                sdp=offer_data["sdp"],
                type=offer_data["type"]
            ))

            # Check if there are video transceivers from the offer
            video_transceiver = None
            for transceiver in pc.getTransceivers():
                if transceiver.kind == "video":
                    video_transceiver = transceiver
                    break
            
            # If no video transceiver exists, add one
            if video_transceiver is None:
                video_transceiver = pc.addTransceiver(self.video_track, direction="sendonly")
            else:
                # Set the track on the existing transceiver (not async)
                video_transceiver.sender.replaceTrack(self.video_track)
                # Manually set the offer direction if it's None
                if not hasattr(video_transceiver, '_offerDirection') or video_transceiver._offerDirection is None:
                    video_transceiver._offerDirection = "recvonly"
                # Set our direction
                video_transceiver.direction = "sendonly"

            # Create answer
            answer = await pc.createAnswer()
            await pc.setLocalDescription(answer)

            # Return answer
            return web.json_response({
                "sdp": pc.localDescription.sdp,
                "type": pc.localDescription.type
            })

        except Exception as e:
            self.get_logger().error(f"WebRTC offer handling failed: {e}")
            return web.json_response({"error": str(e)}, status=500)

    def destroy_node(self):
        """Clean up resources."""
        self.get_logger().info("Shutting down WebRTC node...")

        # Close all peer connections
        for pc in self.peer_connections.copy():
            try:
                # Use asyncio to close peer connections
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(pc.close())
            except:
                pass
        self.peer_connections.clear()

        # Stop web server
        if self.site:
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(self.site.stop())
            except:
                pass
        if self.runner:
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(self.runner.cleanup())
            except:
                pass

        super().destroy_node()


def main(args=None):
    """Main entry point."""
    rclpy.init(args=args)

    try:
        node = WebRTCNode()
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f'Error: {e}')
    finally:
        rclpy.shutdown()


if __name__ == '__main__':
    main()
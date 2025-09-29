# Copyright 2016 Open Source Robotics Foundation, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import rclpy
from rclpy.node import Node
# from std_msgs.msg import String
from joy2_interfaces.msg import BuzzerCommand


class TestTalker(Node):

    def __init__(self):
        super().__init__('test_talker')
        self.publisher_ = self.create_publisher(BuzzerCommand, 'buzzer_command', 10)
        timer_period = 0.5  # seconds
        self.timer = self.create_timer(timer_period, self.timer_callback)
        self.i = 0

    def timer_callback(self):
        data = {
            'active': True,
            'frequency': 1000,
            'duration': 100
        }
        buzzer_cmd = BuzzerCommand()
        buzzer_cmd.active = bool(data.get('active', False))
        buzzer_cmd.frequency = int(data.get('frequency', 1000))
        buzzer_cmd.duration = int(data.get('duration', 100))
        # msg.data = 'Hello World: %d' % self.i
        self.get_logger().info('Publishing: "%s"' % buzzer_cmd)
        self.publisher_.publish(buzzer_cmd)
        self.i += 1


def main(args=None):
    rclpy.init(args=args)

    test_talker = TestTalker()

    rclpy.spin(test_talker)

    # Destroy the node explicitly
    # (optional - otherwise it will be done automatically
    # when the garbage collector destroys the node object)
    test_talker.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()

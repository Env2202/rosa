#  Copyright (c) 2024. Jet Propulsion Laboratory. All rights reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#  https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

import os
import shutil
import sys
import tempfile
import unittest
from datetime import datetime
from unittest.mock import patch, MagicMock, call

# Mock langchain before importing modules that use it
mock_langchain = MagicMock()
mock_langchain_agents = MagicMock()
mock_langchain_community = MagicMock()
mock_langchain_core = MagicMock()
mock_langchain_openai = MagicMock()
mock_langchain_ollama = MagicMock()

sys.modules["langchain"] = mock_langchain
sys.modules["langchain.agents"] = mock_langchain_agents
sys.modules["langchain.agents.format_scratchpad"] = MagicMock()
sys.modules["langchain.agents.format_scratchpad.openai_tools"] = MagicMock()
sys.modules["langchain.agents.output_parsers"] = MagicMock()
sys.modules["langchain.agents.output_parsers.openai_tools"] = MagicMock()
sys.modules["langchain.prompts"] = MagicMock()
sys.modules["langchain_community"] = mock_langchain_community
sys.modules["langchain_community.callbacks"] = MagicMock()
sys.modules["langchain_core"] = mock_langchain_core
sys.modules["langchain_core.messages"] = MagicMock()
sys.modules["langchain_core.prompts"] = MagicMock()
sys.modules["langchain_ollama"] = mock_langchain_ollama
sys.modules["langchain_openai"] = mock_langchain_openai

# Link modules
mock_langchain.agents = mock_langchain_agents
mock_langchain.prompts = sys.modules["langchain.prompts"]
mock_langchain_community.callbacks = sys.modules["langchain_community.callbacks"]
mock_langchain_core.messages = sys.modules["langchain_core.messages"]
mock_langchain_core.prompts = sys.modules["langchain_core.prompts"]

# Setup specific mock attributes
def mock_tool(func):
    func.func = func
    return func

mock_langchain_agents.tool = mock_tool
mock_langchain_agents.AgentExecutor = MagicMock()
mock_langchain_openai.ChatOpenAI = MagicMock()
mock_langchain_openai.AzureChatOpenAI = MagicMock()
mock_langchain_ollama.ChatOllama = MagicMock()

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../src"))

import rosa.tools.ros1_bag as ros1_bag
from rosa.tools.ros1_bag import (
    get_bags_directory,
    rosbag_record,
    rosbag_play,
    rosbag_list,
    rosbag_info,
    rosbag_delete,
)


class TestROS1BagTools(unittest.TestCase):
    """Test cases for ROS1 bag recording and playback tools."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()

    def tearDown(self):
        """Clean up test fixtures."""
        os.chdir(self.original_cwd)
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    @patch("os.getcwd")
    def test_get_bags_directory_creates_directory(self, mock_getcwd):
        """Test that get_bags_directory creates the bags directory if it doesn't exist."""
        mock_getcwd.return_value = self.test_dir
        bags_dir = get_bags_directory()
        self.assertTrue(os.path.exists(bags_dir))
        self.assertEqual(bags_dir, os.path.join(self.test_dir, "bags"))

    @patch("os.getcwd")
    def test_get_bags_directory_returns_existing_directory(self, mock_getcwd):
        """Test that get_bags_directory returns existing bags directory."""
        mock_getcwd.return_value = self.test_dir
        os.makedirs(os.path.join(self.test_dir, "bags"), exist_ok=True)
        bags_dir = get_bags_directory()
        self.assertTrue(os.path.exists(bags_dir))
        self.assertEqual(bags_dir, os.path.join(self.test_dir, "bags"))

    @patch("rosa.tools.ros1_bag.subprocess.Popen")
    @patch("rosa.tools.ros1_bag.get_bags_directory")
    @patch("rosa.tools.ros1_bag.datetime")
    @patch("rosa.tools.ros1_bag.os.path.exists", return_value=True)
    def test_rosbag_record_success(self, mock_exists, mock_datetime, mock_get_dir, mock_popen):
        """Test successful bag recording."""
        mock_get_dir.return_value = self.test_dir
        
        # Mock datetime
        mock_now = MagicMock()
        mock_now.strftime.return_value = "20240115_143022"
        mock_datetime.now.return_value = mock_now
        
        # Create a dummy bag file
        bag_file = os.path.join(self.test_dir, "20240115_143022.bag")
        with open(bag_file, "w") as f:
            f.write("dummy bag content")

        # Mock the subprocess
        mock_process = MagicMock()
        mock_process.communicate.return_value = (b"", b"")
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        result = rosbag_record.func(duration=5, topics=["/scan", "/odom"])

        self.assertTrue(result["success"])
        self.assertIn("bag_file", result)
        self.assertEqual(result["duration"], 5)
        self.assertEqual(result["topics_recorded"], ["/scan", "/odom"])
        self.assertIn("file_size_bytes", result)
        self.assertIn("file_size_mb", result)

    @patch("rosa.tools.ros1_bag.subprocess.Popen")
    @patch("rosa.tools.ros1_bag.get_bags_directory")
    @patch("rosa.tools.ros1_bag.datetime")
    @patch("rosa.tools.ros1_bag.os.path.exists", return_value=True)
    def test_rosbag_record_default_topics(self, mock_exists, mock_datetime, mock_get_dir, mock_popen):
        """Test that rosbag_record uses default topics when none are provided."""
        mock_get_dir.return_value = self.test_dir
        
        # Mock datetime
        mock_now = MagicMock()
        mock_now.strftime.return_value = "20240115_143022"
        mock_datetime.now.return_value = mock_now
        
        bag_file = os.path.join(self.test_dir, "20240115_143022.bag")
        with open(bag_file, "w") as f:
            f.write("dummy bag content")

        mock_process = MagicMock()
        mock_process.communicate.return_value = (b"", b"")
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        result = rosbag_record.func()

        self.assertTrue(result["success"])
        self.assertEqual(result["topics_recorded"], ["/scan", "/odom"])

    @patch("rosa.tools.ros1_bag.subprocess.Popen")
    @patch("rosa.tools.ros1_bag.get_bags_directory")
    def test_rosbag_record_invalid_duration(self, mock_get_dir, mock_popen):
        """Test rosbag_record with invalid duration."""
        mock_get_dir.return_value = self.test_dir

        result = rosbag_record.func(duration=-1)

        self.assertIn("error", result)
        self.assertIn("Duration must be greater than 0", result["error"])

    @patch("rosa.tools.ros1_bag.subprocess.Popen")
    @patch("rosa.tools.ros1_bag.get_bags_directory")
    def test_rosbag_record_file_not_created(self, mock_get_dir, mock_popen):
        """Test rosbag_record when bag file is not created."""
        mock_get_dir.return_value = self.test_dir

        mock_process = MagicMock()
        mock_process.communicate.return_value = (b"", b"")
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        result = rosbag_record.func(duration=5)

        self.assertIn("error", result)
        self.assertIn("Bag file was not created", result["error"])

    @patch("rosa.tools.ros1_bag.subprocess.Popen")
    @patch("rosa.tools.ros1_bag.get_bags_directory")
    def test_rosbag_record_process_failure(self, mock_get_dir, mock_popen):
        """Test rosbag_record when subprocess returns error."""
        mock_get_dir.return_value = self.test_dir

        mock_process = MagicMock()
        mock_process.communicate.return_value = (b"", b"Error message")
        mock_process.returncode = 1
        mock_popen.return_value = mock_process

        result = rosbag_record.func(duration=5)

        self.assertIn("error", result)
        self.assertIn("Failed to record bag", result["error"])

    @patch("rosa.tools.ros1_bag.subprocess.Popen")
    @patch("rosa.tools.ros1_bag.time.sleep")
    @patch("rosa.tools.ros1_bag.get_bags_directory")
    def test_rosbag_play_success(self, mock_get_dir, mock_sleep, mock_popen):
        """Test successful bag playback."""
        mock_get_dir.return_value = self.test_dir
        
        # Create a dummy bag file
        bag_file = os.path.join(self.test_dir, "20240115_143022.bag")
        with open(bag_file, "w") as f:
            f.write("dummy bag content")

        mock_process = MagicMock()
        mock_process.poll.return_value = None  # Process is still running
        mock_popen.return_value = mock_process

        result = rosbag_play.func("20240115_143022.bag")

        self.assertTrue(result["success"])
        self.assertIn("bag_file", result)
        self.assertEqual(result["rate"], 1.0)
        self.assertEqual(result["loop"], False)

    @patch("rosa.tools.ros1_bag.get_bags_directory")
    def test_rosbag_play_file_not_found(self, mock_get_dir):
        """Test rosbag_play when bag file doesn't exist."""
        mock_get_dir.return_value = self.test_dir

        result = rosbag_play.func("nonexistent.bag")

        self.assertIn("error", result)
        self.assertIn("Bag file not found", result["error"])

    @patch("rosa.tools.ros1_bag.subprocess.Popen")
    @patch("rosa.tools.ros1_bag.time.sleep")
    @patch("rosa.tools.ros1_bag.get_bags_directory")
    def test_rosbag_play_with_custom_rate(self, mock_get_dir, mock_sleep, mock_popen):
        """Test rosbag_play with custom playback rate."""
        mock_get_dir.return_value = self.test_dir
        
        bag_file = os.path.join(self.test_dir, "20240115_143022.bag")
        with open(bag_file, "w") as f:
            f.write("dummy bag content")

        mock_process = MagicMock()
        mock_process.poll.return_value = None
        mock_popen.return_value = mock_process

        result = rosbag_play.func("20240115_143022.bag", rate=2.0)

        self.assertTrue(result["success"])
        self.assertEqual(result["rate"], 2.0)

    @patch("rosa.tools.ros1_bag.subprocess.Popen")
    @patch("rosa.tools.ros1_bag.time.sleep")
    @patch("rosa.tools.ros1_bag.get_bags_directory")
    def test_rosbag_play_with_loop(self, mock_get_dir, mock_sleep, mock_popen):
        """Test rosbag_play with loop enabled."""
        mock_get_dir.return_value = self.test_dir
        
        bag_file = os.path.join(self.test_dir, "20240115_143022.bag")
        with open(bag_file, "w") as f:
            f.write("dummy bag content")

        mock_process = MagicMock()
        mock_process.poll.return_value = None
        mock_popen.return_value = mock_process

        result = rosbag_play.func("20240115_143022.bag", loop=True)

        self.assertTrue(result["success"])
        self.assertEqual(result["loop"], True)

    @patch("rosa.tools.ros1_bag.subprocess.Popen")
    @patch("rosa.tools.ros1_bag.time.sleep")
    @patch("rosa.tools.ros1_bag.get_bags_directory")
    def test_rosbag_play_process_failure(self, mock_get_dir, mock_sleep, mock_popen):
        """Test rosbag_play when subprocess fails to start."""
        mock_get_dir.return_value = self.test_dir
        
        bag_file = os.path.join(self.test_dir, "20240115_143022.bag")
        with open(bag_file, "w") as f:
            f.write("dummy bag content")

        mock_process = MagicMock()
        mock_process.poll.return_value = 1  # Process failed
        mock_process.communicate.return_value = (b"", b"Error")
        mock_popen.return_value = mock_process

        result = rosbag_play.func("20240115_143022.bag")

        self.assertIn("error", result)
        self.assertIn("Failed to start playback", result["error"])

    @patch("rosa.tools.ros1_bag.get_bags_directory")
    def test_rosbag_list_empty(self, mock_get_dir):
        """Test rosbag_list when no bags exist."""
        mock_get_dir.return_value = self.test_dir

        result = rosbag_list.func()

        self.assertEqual(result["total"], 0)
        self.assertEqual(result["bags"], [])

    @patch("rosa.tools.ros1_bag.get_bags_directory")
    def test_rosbag_list_with_files(self, mock_get_dir):
        """Test rosbag_list with existing bag files."""
        mock_get_dir.return_value = self.test_dir
        
        # Create dummy bag files
        bag_files = ["20240115_143022.bag", "20240115_143023.bag", "20240115_143024.bag"]
        for bag_file in bag_files:
            with open(os.path.join(self.test_dir, bag_file), "w") as f:
                f.write("dummy content")

        result = rosbag_list.func()

        self.assertEqual(result["total"], 3)
        self.assertEqual(len(result["bags"]), 3)
        self.assertIn("bags_directory", result)
        
        # We don't check order strictly because it depends on mtime resolution
        filenames = [bag["filename"] for bag in result["bags"]]
        self.assertEqual(set(filenames), set(bag_files))

    @patch("rosa.tools.ros1_bag.get_bags_directory")
    def test_rosbag_list_with_min_size(self, mock_get_dir):
        """Test rosbag_list with minimum size filter."""
        mock_get_dir.return_value = self.test_dir
        
        # Create bag files with different sizes
        small_file = os.path.join(self.test_dir, "small.bag")
        large_file = os.path.join(self.test_dir, "large.bag")
        
        with open(small_file, "w") as f:
            f.write("x" * 100)  # 100 bytes
        with open(large_file, "w") as f:
            f.write("x" * 1000)  # 1000 bytes

        result = rosbag_list.func(min_size=500)

        self.assertEqual(result["total"], 1)
        self.assertEqual(result["bags"][0]["filename"], "large.bag")

    @patch("rosa.tools.ros1_bag.get_bags_directory")
    def test_rosbag_list_with_pattern(self, mock_get_dir):
        """Test rosbag_list with pattern filter."""
        mock_get_dir.return_value = self.test_dir
        
        # Create bag files
        bag_files = ["20240115_143022.bag", "20240116_143023.bag", "20240115_143024.bag"]
        for bag_file in bag_files:
            with open(os.path.join(self.test_dir, bag_file), "w") as f:
                f.write("dummy content")

        result = rosbag_list.func(pattern="20240115")

        self.assertEqual(result["total"], 2)
        filenames = [bag["filename"] for bag in result["bags"]]
        self.assertTrue(all("20240115" in f for f in filenames))

    @patch("rosa.tools.ros1_bag.subprocess.Popen")
    @patch("rosa.tools.ros1_bag.get_bags_directory")
    def test_rosbag_info_success(self, mock_get_dir, mock_popen):
        """Test successful rosbag_info call."""
        mock_get_dir.return_value = self.test_dir
        
        bag_file = os.path.join(self.test_dir, "20240115_143022.bag")
        with open(bag_file, "w") as f:
            f.write("dummy bag content")

        mock_process = MagicMock()
        mock_process.communicate.return_value = (b"path: /path/to/bag.bag\nversion: 2.0\n", b"")
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        result = rosbag_info.func("20240115_143022.bag")

        self.assertTrue(result["success"])
        self.assertIn("info", result)
        self.assertIn("bag_file", result)
        self.assertIn("filename", result)

    @patch("rosa.tools.ros1_bag.get_bags_directory")
    def test_rosbag_info_file_not_found(self, mock_get_dir):
        """Test rosbag_info when bag file doesn't exist."""
        mock_get_dir.return_value = self.test_dir

        result = rosbag_info.func("nonexistent.bag")

        self.assertIn("error", result)
        self.assertIn("Bag file not found", result["error"])

    @patch("rosa.tools.ros1_bag.subprocess.Popen")
    @patch("rosa.tools.ros1_bag.get_bags_directory")
    def test_rosbag_info_command_failure(self, mock_get_dir, mock_popen):
        """Test rosbag_info when rosbag info command fails."""
        mock_get_dir.return_value = self.test_dir
        
        bag_file = os.path.join(self.test_dir, "20240115_143022.bag")
        with open(bag_file, "w") as f:
            f.write("dummy bag content")

        mock_process = MagicMock()
        mock_process.communicate.return_value = (b"", b"Error")
        mock_process.returncode = 1
        mock_popen.return_value = mock_process

        result = rosbag_info.func("20240115_143022.bag")

        self.assertIn("error", result)
        self.assertIn("Failed to get bag info", result["error"])

    @patch("rosa.tools.ros1_bag.get_bags_directory")
    def test_rosbag_delete_success(self, mock_get_dir):
        """Test successful bag file deletion."""
        mock_get_dir.return_value = self.test_dir
        
        bag_file = os.path.join(self.test_dir, "20240115_143022.bag")
        with open(bag_file, "w") as f:
            f.write("dummy bag content")

        result = rosbag_delete.func("20240115_143022.bag")

        self.assertTrue(result["success"])
        self.assertFalse(os.path.exists(bag_file))
        self.assertIn("deleted_file", result)

    @patch("rosa.tools.ros1_bag.get_bags_directory")
    def test_rosbag_delete_file_not_found(self, mock_get_dir):
        """Test rosbag_delete when bag file doesn't exist."""
        mock_get_dir.return_value = self.test_dir

        result = rosbag_delete.func("nonexistent.bag")

        self.assertIn("error", result)
        self.assertIn("Bag file not found", result["error"])

    @patch("rosa.tools.ros1_bag.get_bags_directory")
    def test_rosbag_play_with_absolute_path(self, mock_get_dir):
        """Test rosbag_play with absolute path."""
        mock_get_dir.return_value = self.test_dir
        
        bag_file = os.path.join(self.test_dir, "custom_path.bag")
        with open(bag_file, "w") as f:
            f.write("dummy bag content")

        with patch("rosa.tools.ros1_bag.subprocess.Popen") as mock_popen:
            with patch("rosa.tools.ros1_bag.time.sleep"):
                mock_process = MagicMock()
                mock_process.poll.return_value = None
                mock_popen.return_value = mock_process

                result = rosbag_play.func(bag_file)

                self.assertTrue(result["success"])

    @patch("rosa.tools.ros1_bag.get_bags_directory")
    def test_rosbag_list_with_metadata(self, mock_get_dir):
        """Test that rosbag_list returns correct metadata."""
        mock_get_dir.return_value = self.test_dir
        
        bag_file = os.path.join(self.test_dir, "test.bag")
        with open(bag_file, "w") as f:
            f.write("x" * 5000)

        result = rosbag_list.func()

        self.assertEqual(result["total"], 1)
        bag_info = result["bags"][0]
        
        self.assertIn("filename", bag_info)
        self.assertIn("path", bag_info)
        self.assertIn("size_bytes", bag_info)
        self.assertIn("size_mb", bag_info)
        self.assertIn("created", bag_info)
        
        self.assertEqual(bag_info["size_bytes"], 5000)
        self.assertAlmostEqual(bag_info["size_mb"], 0.0, places=2)


if __name__ == "__main__":
    unittest.main()

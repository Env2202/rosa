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

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../src"))

try:
    from rosa.tools.ros2_bag import (
        get_bags_directory,
        ros2bag_record,
        ros2bag_play,
        ros2bag_list,
        ros2bag_info,
        ros2bag_delete,
    )
except (ModuleNotFoundError, ImportError):
    pass


class TestROS2BagTools(unittest.TestCase):
    """Test cases for ROS2 bag recording and playback tools."""

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

    @patch("rosa.tools.ros2_bag.subprocess.Popen")
    @patch("rosa.tools.ros2_bag.get_bags_directory")
    def test_ros2bag_record_success(self, mock_get_dir, mock_popen):
        """Test successful bag recording."""
        mock_get_dir.return_value = self.test_dir
        
        # Create a dummy bag directory (ROS2 bags are directories)
        bag_dir = os.path.join(self.test_dir, "20240115_143022")
        os.makedirs(bag_dir, exist_ok=True)
        with open(os.path.join(bag_dir, "metadata.yaml"), "w") as f:
            f.write("dummy metadata")

        # Mock the subprocess
        mock_process = MagicMock()
        mock_process.communicate.return_value = (b"", b"")
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        result = ros2bag_record(duration=5, topics=["/scan", "/odom"])

        self.assertTrue(result["success"])
        self.assertIn("bag_file", result)
        self.assertEqual(result["duration"], 5)
        self.assertEqual(result["topics_recorded"], ["/scan", "/odom"])
        self.assertIn("file_size_bytes", result)
        self.assertIn("file_size_mb", result)

    @patch("rosa.tools.ros2_bag.subprocess.Popen")
    @patch("rosa.tools.ros2_bag.get_bags_directory")
    def test_ros2bag_record_default_topics(self, mock_get_dir, mock_popen):
        """Test that ros2bag_record uses default topics when none are provided."""
        mock_get_dir.return_value = self.test_dir
        
        # Create a dummy bag directory
        bag_dir = os.path.join(self.test_dir, "20240115_143022")
        os.makedirs(bag_dir, exist_ok=True)
        with open(os.path.join(bag_dir, "metadata.yaml"), "w") as f:
            f.write("dummy metadata")

        mock_process = MagicMock()
        mock_process.communicate.return_value = (b"", b"")
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        result = ros2bag_record()

        self.assertTrue(result["success"])
        self.assertEqual(result["topics_recorded"], ["/scan", "/odom"])

    @patch("rosa.tools.ros2_bag.subprocess.Popen")
    @patch("rosa.tools.ros2_bag.get_bags_directory")
    def test_ros2bag_record_invalid_duration(self, mock_get_dir, mock_popen):
        """Test ros2bag_record with invalid duration."""
        mock_get_dir.return_value = self.test_dir

        result = ros2bag_record(duration=-1)

        self.assertIn("error", result)
        self.assertIn("Duration must be greater than 0", result["error"])

    @patch("rosa.tools.ros2_bag.subprocess.Popen")
    @patch("rosa.tools.ros2_bag.get_bags_directory")
    def test_ros2bag_record_directory_not_created(self, mock_get_dir, mock_popen):
        """Test ros2bag_record when bag directory is not created."""
        mock_get_dir.return_value = self.test_dir

        mock_process = MagicMock()
        mock_process.communicate.return_value = (b"", b"")
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        result = ros2bag_record(duration=5)

        self.assertIn("error", result)
        self.assertIn("Bag directory was not created", result["error"])

    @patch("rosa.tools.ros2_bag.subprocess.Popen")
    @patch("rosa.tools.ros2_bag.get_bags_directory")
    def test_ros2bag_record_process_failure(self, mock_get_dir, mock_popen):
        """Test ros2bag_record when subprocess returns error."""
        mock_get_dir.return_value = self.test_dir

        mock_process = MagicMock()
        mock_process.communicate.return_value = (b"", b"Error message")
        mock_process.returncode = 1
        mock_popen.return_value = mock_process

        result = ros2bag_record(duration=5)

        self.assertIn("error", result)
        self.assertIn("Failed to record bag", result["error"])

    @patch("rosa.tools.ros2_bag.subprocess.Popen")
    @patch("rosa.tools.ros2_bag.time.sleep")
    @patch("rosa.tools.ros2_bag.get_bags_directory")
    def test_ros2bag_play_success(self, mock_get_dir, mock_sleep, mock_popen):
        """Test successful bag playback."""
        mock_get_dir.return_value = self.test_dir
        
        # Create a dummy bag directory (ROS2 bags are directories)
        bag_dir = os.path.join(self.test_dir, "20240115_143022")
        os.makedirs(bag_dir, exist_ok=True)

        mock_process = MagicMock()
        mock_process.poll.return_value = None  # Process is still running
        mock_popen.return_value = mock_process

        result = ros2bag_play("20240115_143022")

        self.assertTrue(result["success"])
        self.assertIn("bag_file", result)
        self.assertEqual(result["rate"], 1.0)
        self.assertEqual(result["loop"], False)

    @patch("rosa.tools.ros2_bag.get_bags_directory")
    def test_ros2bag_play_directory_not_found(self, mock_get_dir):
        """Test ros2bag_play when bag directory doesn't exist."""
        mock_get_dir.return_value = self.test_dir

        result = ros2bag_play("nonexistent")

        self.assertIn("error", result)
        self.assertIn("Bag directory not found", result["error"])

    @patch("rosa.tools.ros2_bag.subprocess.Popen")
    @patch("rosa.tools.ros2_bag.time.sleep")
    @patch("rosa.tools.ros2_bag.get_bags_directory")
    def test_ros2bag_play_with_custom_rate(self, mock_get_dir, mock_sleep, mock_popen):
        """Test ros2bag_play with custom playback rate."""
        mock_get_dir.return_value = self.test_dir
        
        bag_dir = os.path.join(self.test_dir, "20240115_143022")
        os.makedirs(bag_dir, exist_ok=True)

        mock_process = MagicMock()
        mock_process.poll.return_value = None
        mock_popen.return_value = mock_process

        result = ros2bag_play("20240115_143022", rate=2.0)

        self.assertTrue(result["success"])
        self.assertEqual(result["rate"], 2.0)

    @patch("rosa.tools.ros2_bag.subprocess.Popen")
    @patch("rosa.tools.ros2_bag.time.sleep")
    @patch("rosa.tools.ros2_bag.get_bags_directory")
    def test_ros2bag_play_with_loop(self, mock_get_dir, mock_sleep, mock_popen):
        """Test ros2bag_play with loop enabled."""
        mock_get_dir.return_value = self.test_dir
        
        bag_dir = os.path.join(self.test_dir, "20240115_143022")
        os.makedirs(bag_dir, exist_ok=True)

        mock_process = MagicMock()
        mock_process.poll.return_value = None
        mock_popen.return_value = mock_process

        result = ros2bag_play("20240115_143022", loop=True)

        self.assertTrue(result["success"])
        self.assertEqual(result["loop"], True)

    @patch("rosa.tools.ros2_bag.subprocess.Popen")
    @patch("rosa.tools.ros2_bag.time.sleep")
    @patch("rosa.tools.ros2_bag.get_bags_directory")
    def test_ros2bag_play_process_failure(self, mock_get_dir, mock_sleep, mock_popen):
        """Test ros2bag_play when subprocess fails to start."""
        mock_get_dir.return_value = self.test_dir
        
        bag_dir = os.path.join(self.test_dir, "20240115_143022")
        os.makedirs(bag_dir, exist_ok=True)

        mock_process = MagicMock()
        mock_process.poll.return_value = 1  # Process failed
        mock_process.communicate.return_value = (b"", b"Error")
        mock_popen.return_value = mock_process

        result = ros2bag_play("20240115_143022")

        self.assertIn("error", result)
        self.assertIn("Failed to start playback", result["error"])

    @patch("rosa.tools.ros2_bag.get_bags_directory")
    def test_ros2bag_list_empty(self, mock_get_dir):
        """Test ros2bag_list when no bags exist."""
        mock_get_dir.return_value = self.test_dir

        result = ros2bag_list()

        self.assertEqual(result["total"], 0)
        self.assertEqual(result["bags"], [])

    @patch("rosa.tools.ros2_bag.get_bags_directory")
    def test_ros2bag_list_with_directories(self, mock_get_dir):
        """Test ros2bag_list with existing bag directories."""
        mock_get_dir.return_value = self.test_dir
        
        # Create dummy bag directories (ROS2 bags are directories)
        bag_dirs = ["20240115_143022", "20240115_143023", "20240115_143024"]
        for bag_dir in bag_dirs:
            dirpath = os.path.join(self.test_dir, bag_dir)
            os.makedirs(dirpath, exist_ok=True)
            with open(os.path.join(dirpath, "metadata.yaml"), "w") as f:
                f.write("dummy metadata")

        result = ros2bag_list()

        self.assertEqual(result["total"], 3)
        self.assertEqual(len(result["bags"]), 3)
        self.assertIn("bags_directory", result)

    @patch("rosa.tools.ros2_bag.get_bags_directory")
    def test_ros2bag_list_with_min_size(self, mock_get_dir):
        """Test ros2bag_list with minimum size filter."""
        mock_get_dir.return_value = self.test_dir
        
        # Create bag directories with different sizes
        small_dir = os.path.join(self.test_dir, "small")
        large_dir = os.path.join(self.test_dir, "large")
        
        os.makedirs(small_dir, exist_ok=True)
        with open(os.path.join(small_dir, "data.db3"), "w") as f:
            f.write("x" * 100)  # 100 bytes
            
        os.makedirs(large_dir, exist_ok=True)
        with open(os.path.join(large_dir, "data.db3"), "w") as f:
            f.write("x" * 1000)  # 1000 bytes

        result = ros2bag_list(min_size=500)

        self.assertEqual(result["total"], 1)
        self.assertEqual(result["bags"][0]["filename"], "large")

    @patch("rosa.tools.ros2_bag.get_bags_directory")
    def test_ros2bag_list_with_pattern(self, mock_get_dir):
        """Test ros2bag_list with pattern filter."""
        mock_get_dir.return_value = self.test_dir
        
        # Create bag directories
        bag_dirs = ["20240115_143022", "20240116_143023", "20240115_143024"]
        for bag_dir in bag_dirs:
            dirpath = os.path.join(self.test_dir, bag_dir)
            os.makedirs(dirpath, exist_ok=True)
            with open(os.path.join(dirpath, "metadata.yaml"), "w") as f:
                f.write("dummy metadata")

        result = ros2bag_list(pattern="20240115")

        self.assertEqual(result["total"], 2)
        filenames = [bag["filename"] for bag in result["bags"]]
        self.assertTrue(all("20240115" in f for f in filenames))

    @patch("rosa.tools.ros2_bag.subprocess.Popen")
    @patch("rosa.tools.ros2_bag.get_bags_directory")
    def test_ros2bag_info_success(self, mock_get_dir, mock_popen):
        """Test successful ros2bag_info call."""
        mock_get_dir.return_value = self.test_dir
        
        bag_dir = os.path.join(self.test_dir, "20240115_143022")
        os.makedirs(bag_dir, exist_ok=True)

        mock_process = MagicMock()
        mock_process.communicate.return_value = (b"Files: metadata.yaml\nBag size: 1.2 KiB\n", b"")
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        result = ros2bag_info("20240115_143022")

        self.assertTrue(result["success"])
        self.assertIn("info", result)
        self.assertIn("bag_file", result)
        self.assertIn("filename", result)

    @patch("rosa.tools.ros2_bag.get_bags_directory")
    def test_ros2bag_info_directory_not_found(self, mock_get_dir):
        """Test ros2bag_info when bag directory doesn't exist."""
        mock_get_dir.return_value = self.test_dir

        result = ros2bag_info("nonexistent")

        self.assertIn("error", result)
        self.assertIn("Bag directory not found", result["error"])

    @patch("rosa.tools.ros2_bag.subprocess.Popen")
    @patch("rosa.tools.ros2_bag.get_bags_directory")
    def test_ros2bag_info_command_failure(self, mock_get_dir, mock_popen):
        """Test ros2bag_info when ros2 bag info command fails."""
        mock_get_dir.return_value = self.test_dir
        
        bag_dir = os.path.join(self.test_dir, "20240115_143022")
        os.makedirs(bag_dir, exist_ok=True)

        mock_process = MagicMock()
        mock_process.communicate.return_value = (b"", b"Error")
        mock_process.returncode = 1
        mock_popen.return_value = mock_process

        result = ros2bag_info("20240115_143022")

        self.assertIn("error", result)
        self.assertIn("Failed to get bag info", result["error"])

    @patch("rosa.tools.ros2_bag.get_bags_directory")
    def test_ros2bag_delete_success(self, mock_get_dir):
        """Test successful bag directory deletion."""
        mock_get_dir.return_value = self.test_dir
        
        bag_dir = os.path.join(self.test_dir, "20240115_143022")
        os.makedirs(bag_dir, exist_ok=True)
        with open(os.path.join(bag_dir, "metadata.yaml"), "w") as f:
            f.write("dummy metadata")

        result = ros2bag_delete("20240115_143022")

        self.assertTrue(result["success"])
        self.assertFalse(os.path.exists(bag_dir))
        self.assertIn("deleted_file", result)

    @patch("rosa.tools.ros2_bag.get_bags_directory")
    def test_ros2bag_delete_directory_not_found(self, mock_get_dir):
        """Test ros2bag_delete when bag directory doesn't exist."""
        mock_get_dir.return_value = self.test_dir

        result = ros2bag_delete("nonexistent")

        self.assertIn("error", result)
        self.assertIn("Bag directory not found", result["error"])

    @patch("rosa.tools.ros2_bag.get_bags_directory")
    def test_ros2bag_play_with_absolute_path(self, mock_get_dir):
        """Test ros2bag_play with absolute path."""
        mock_get_dir.return_value = self.test_dir
        
        bag_dir = os.path.join(self.test_dir, "custom_path")
        os.makedirs(bag_dir, exist_ok=True)

        with patch("rosa.tools.ros2_bag.subprocess.Popen") as mock_popen:
            with patch("rosa.tools.ros2_bag.time.sleep"):
                mock_process = MagicMock()
                mock_process.poll.return_value = None
                mock_popen.return_value = mock_process

                result = ros2bag_play(bag_dir)

                self.assertTrue(result["success"])

    @patch("rosa.tools.ros2_bag.get_bags_directory")
    def test_ros2bag_list_with_metadata(self, mock_get_dir):
        """Test that ros2bag_list returns correct metadata."""
        mock_get_dir.return_value = self.test_dir
        
        bag_dir = os.path.join(self.test_dir, "test_bag")
        os.makedirs(bag_dir, exist_ok=True)
        with open(os.path.join(bag_dir, "data.db3"), "w") as f:
            f.write("x" * 5000)

        result = ros2bag_list()

        self.assertEqual(result["total"], 1)
        bag_info = result["bags"][0]
        
        self.assertIn("filename", bag_info)
        self.assertIn("path", bag_info)
        self.assertIn("size_bytes", bag_info)
        self.assertIn("size_mb", bag_info)
        self.assertIn("created", bag_info)
        
        self.assertEqual(bag_info["size_bytes"], 5000)
        self.assertAlmostEqual(bag_info["size_mb"], 0.0, places=2)

    @patch("rosa.tools.ros2_bag.get_bags_directory")
    def test_ros2bag_list_ignores_hidden_directories(self, mock_get_dir):
        """Test that ros2bag_list ignores hidden directories."""
        mock_get_dir.return_value = self.test_dir
        
        # Create a regular bag directory
        regular_dir = os.path.join(self.test_dir, "20240115_143022")
        os.makedirs(regular_dir, exist_ok=True)
        with open(os.path.join(regular_dir, "metadata.yaml"), "w") as f:
            f.write("dummy metadata")
        
        # Create a hidden directory
        hidden_dir = os.path.join(self.test_dir, ".hidden")
        os.makedirs(hidden_dir, exist_ok=True)
        with open(os.path.join(hidden_dir, "data.db3"), "w") as f:
            f.write("hidden data")

        result = ros2bag_list()

        self.assertEqual(result["total"], 1)
        self.assertEqual(result["bags"][0]["filename"], "20240115_143022")


if __name__ == "__main__":
    unittest.main()

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
import re
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict

from langchain.agents import tool


def get_bags_directory() -> str:
    """Get or create the bags directory in the current working directory."""
    bags_dir = os.path.join(os.getcwd(), "bags")
    if not os.path.exists(bags_dir):
        os.makedirs(bags_dir)
    return bags_dir


@tool
def ros2bag_record(
    duration: int = 5,
    topics: Optional[List[str]] = None,
) -> dict:
    """
    Records ROS2 topics to a bag file.

    Records sensor data from specified topics for a given duration and saves it to a timestamped
    bag file in the bags/ directory. By default, records the 'scan' and 'odom' topics which are
    common sensor data topics for mobile robots.

    :param duration: Duration to record in seconds. Defaults to 5 seconds.
    :param topics: List of topic names to record. If not provided, defaults to ['/scan', '/odom'].
                   These are common sensor topics for mobile robots.
    :return: Dictionary with status, bag file path, and metadata about the recording.

    Example:
        To record for 10 seconds with custom topics:
        ros2bag_record(duration=10, topics=['/scan', '/odom', '/imu'])

        To record for default 5 seconds with default topics:
        ros2bag_record()
    """
    if topics is None:
        topics = ["/scan", "/odom"]

    if duration <= 0:
        return {"error": "Duration must be greater than 0 seconds."}

    bags_dir = get_bags_directory()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    bag_filename = f"{timestamp}"
    bag_filepath = os.path.join(bags_dir, bag_filename)

    # Build the ros2 bag record command
    # ROS2 uses 'ros2 bag record' with different options than ROS1
    topic_str = " ".join(topics)
    cmd = f"ros2 bag record -o {bag_filepath} -d {duration} {topic_str}"

    try:
        # Run the ros2 bag record command
        process = subprocess.Popen(
            cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        # Wait for the process to complete
        stdout, stderr = process.communicate(timeout=duration + 15)

        if process.returncode != 0:
            error_msg = stderr.decode() if stderr else "Unknown error"
            return {
                "error": f"Failed to record bag: {error_msg}",
                "return_code": process.returncode,
            }

        # In ROS2, bag files are stored in a directory with metadata
        # Check if the bag directory was created
        if not os.path.exists(bag_filepath):
            return {
                "error": "Bag directory was not created. Check if topics are available and ROS2 is running."
            }

        # Get the size of the bag directory
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(bag_filepath):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                total_size += os.path.getsize(fp)

        file_size_mb = total_size / (1024 * 1024)

        return {
            "success": True,
            "bag_file": bag_filepath,
            "filename": bag_filename,
            "duration": duration,
            "topics_recorded": topics,
            "file_size_bytes": total_size,
            "file_size_mb": round(file_size_mb, 2),
            "message": f"Successfully recorded {duration} seconds of sensor data to {bag_filename}",
        }

    except subprocess.TimeoutExpired:
        process.kill()
        return {
            "error": f"Recording process timed out after {duration + 15} seconds."
        }
    except Exception as e:
        return {"error": f"An error occurred during recording: {str(e)}"}


@tool
def ros2bag_play(
    bag_file: str,
    rate: float = 1.0,
    loop: bool = False,
    start_time: Optional[float] = None,
) -> dict:
    """
    Plays back a recorded ROS2 bag file.

    Replays the sensor data from a previously recorded bag file. This allows you to test
    algorithms and debug robot behavior using recorded sensor data without needing the
    actual robot or live sensor streams.

    :param bag_file: Name of the bag file/directory or full path.
                     Can be just the name if it's in the bags/ directory.
    :param rate: Playback rate multiplier. 1.0 = normal speed, 2.0 = 2x speed, 0.5 = half speed.
    :param loop: If True, loop the bag file playback continuously.
    :param start_time: Optional start time offset in seconds within the bag file.
    :return: Dictionary with status and playback information.

    Example:
        To play back a bag file at normal speed:
        ros2bag_play("20240115_143022")

        To play back at 2x speed:
        ros2bag_play("20240115_143022", rate=2.0)

        To loop playback continuously:
        ros2bag_play("20240115_143022", loop=True)
    """
    bags_dir = get_bags_directory()

    # Handle both full path and filename
    if os.path.isabs(bag_file):
        bag_filepath = bag_file
    else:
        bag_filepath = os.path.join(bags_dir, bag_file)

    # In ROS2, bags are directories, not single files
    # Check if it exists as a directory
    if not os.path.exists(bag_filepath):
        return {
            "error": f"Bag directory not found: {bag_filepath}",
            "available_bags": ros2bag_list()["bags"] if ros2bag_list()["total"] > 0 else [],
        }

    # Build the ros2 bag play command
    cmd = f"ros2 bag play {bag_filepath} --rate {rate}"

    if loop:
        cmd += " --loop"

    if start_time is not None and start_time > 0:
        cmd += f" --start-offset {start_time}"

    try:
        # Run the ros2 bag play command (non-blocking, returns immediately)
        process = subprocess.Popen(
            cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        # Give it a moment to start and check for immediate errors
        time.sleep(0.5)

        # Check if process is still running
        poll_result = process.poll()
        if poll_result is not None and poll_result != 0:
            _, stderr = process.communicate()
            error_msg = stderr.decode() if stderr else "Unknown error"
            return {
                "error": f"Failed to start playback: {error_msg}",
                "return_code": poll_result,
            }

        return {
            "success": True,
            "bag_file": bag_filepath,
            "filename": os.path.basename(bag_filepath),
            "rate": rate,
            "loop": loop,
            "start_time": start_time,
            "message": f"Playback started for {os.path.basename(bag_filepath)} at {rate}x speed.",
            "note": "Playback is running in the background. Press Ctrl+C in the terminal to stop playback.",
        }

    except Exception as e:
        return {"error": f"An error occurred during playback: {str(e)}"}


@tool
def ros2bag_list(
    min_size: int = 0,
    pattern: Optional[str] = None,
) -> dict:
    """
    Lists all recorded ROS2 bag files available in the bags/ directory.

    Returns a list of all bag files that have been recorded, along with metadata
    such as file size and creation time. This helps you find and select bag files
    for playback or analysis.

    :param min_size: Minimum file size in bytes to include in the list. Default is 0 (no filter).
    :param pattern: Optional regex pattern to filter bag files by name.
    :return: Dictionary with list of bag files and metadata.

    Example:
        To list all bags:
        ros2bag_list()

        To list only bags larger than 1MB:
        ros2bag_list(min_size=1048576)

        To list bags from a specific date:
        ros2bag_list(pattern="20240115.*")
    """
    bags_dir = get_bags_directory()

    if not os.path.exists(bags_dir):
        return {"total": 0, "bags": []}

    try:
        # In ROS2, bags are directories, not single files
        # Get all directories in the bags directory
        bag_dirs = [
            d
            for d in os.listdir(bags_dir)
            if os.path.isdir(os.path.join(bags_dir, d))
            and not d.startswith(".")  # Skip hidden directories
        ]

        # Calculate size for each bag directory
        bags_info = []
        for bag_dir in bag_dirs:
            dirpath = os.path.join(bags_dir, bag_dir)
            total_size = 0
            for root, dirs, files in os.walk(dirpath):
                for f in files:
                    fp = os.path.join(root, f)
                    total_size += os.path.getsize(fp)

            mod_time = os.path.getmtime(dirpath)
            mod_datetime = datetime.fromtimestamp(mod_time).strftime(
                "%Y-%m-%d %H:%M:%S"
            )

            file_size_mb = total_size / (1024 * 1024)

            bags_info.append(
                {
                    "filename": bag_dir,
                    "path": dirpath,
                    "size_bytes": total_size,
                    "size_mb": round(file_size_mb, 2),
                    "created": mod_datetime,
                }
            )

        # Filter by minimum size
        if min_size > 0:
            bags_info = [b for b in bags_info if b["size_bytes"] >= min_size]

        # Filter by pattern if provided
        if pattern:
            bags_info = [b for b in bags_info if re.match(f".*{pattern}.*", b["filename"])]

        # Sort by modification time (newest first)
        bags_info.sort(key=lambda x: x["created"], reverse=True)

        return {
            "total": len(bags_info),
            "bags_directory": bags_dir,
            "bags": bags_info,
        }

    except Exception as e:
        return {"error": f"Failed to list bag files: {str(e)}", "total": 0, "bags": []}


@tool
def ros2bag_info(bag_file: str) -> dict:
    """
    Gets detailed information about a specific ROS2 bag file.

    Retrieves metadata about a bag file including topics recorded, message counts,
    start/end times, and duration. This is useful for understanding what data is
    available in a bag before playing it back.

    :param bag_file: Name of the bag directory or full path.
    :return: Dictionary with bag file information.

    Example:
        ros2bag_info("20240115_143022")
    """
    bags_dir = get_bags_directory()

    # Handle both full path and filename
    if os.path.isabs(bag_file):
        bag_filepath = bag_file
    else:
        bag_filepath = os.path.join(bags_dir, bag_file)

    # Verify the bag directory exists
    if not os.path.exists(bag_filepath):
        return {"error": f"Bag directory not found: {bag_filepath}"}

    try:
        # Run ros2 bag info command
        cmd = f"ros2 bag info {bag_filepath}"
        process = subprocess.Popen(
            cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        stdout, stderr = process.communicate(timeout=10)

        if process.returncode != 0:
            error_msg = stderr.decode() if stderr else "Unknown error"
            return {"error": f"Failed to get bag info: {error_msg}"}

        info_text = stdout.decode()

        return {
            "success": True,
            "bag_file": bag_filepath,
            "filename": os.path.basename(bag_filepath),
            "info": info_text,
        }

    except subprocess.TimeoutExpired:
        process.kill()
        return {"error": "Command timed out while getting bag information."}
    except Exception as e:
        return {"error": f"An error occurred: {str(e)}"}


@tool
def ros2bag_delete(bag_file: str) -> dict:
    """
    Deletes a recorded ROS2 bag directory.

    Removes a bag directory from the bags/ directory. Use with caution as this operation
    cannot be undone.

    :param bag_file: Name of the bag directory or full path.
    :return: Dictionary with status of the deletion.

    Example:
        ros2bag_delete("20240115_143022")
    """
    import shutil

    bags_dir = get_bags_directory()

    # Handle both full path and filename
    if os.path.isabs(bag_file):
        bag_filepath = bag_file
    else:
        bag_filepath = os.path.join(bags_dir, bag_file)

    # Verify the bag directory exists
    if not os.path.exists(bag_filepath):
        return {"error": f"Bag directory not found: {bag_filepath}"}

    try:
        shutil.rmtree(bag_filepath)
        return {
            "success": True,
            "message": f"Successfully deleted {os.path.basename(bag_filepath)}",
            "deleted_file": bag_filepath,
        }
    except Exception as e:
        return {"error": f"Failed to delete bag directory: {str(e)}"}

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
def rosbag_record(
    duration: int = 5,
    topics: Optional[List[str]] = None,
) -> dict:
    """
    Records ROS topics to a bag file.

    Records sensor data from specified topics for a given duration and saves it to a timestamped
    bag file in the bags/ directory. By default, records the 'scan' and 'odom' topics which are
    common sensor data topics for mobile robots.

    :param duration: Duration to record in seconds. Defaults to 5 seconds.
    :param topics: List of topic names to record. If not provided, defaults to ['/scan', '/odom'].
                   These are common sensor topics for mobile robots.
    :return: Dictionary with status, bag file path, and metadata about the recording.

    Example:
        To record for 10 seconds with custom topics:
        rosbag_record(duration=10, topics=['/scan', '/odom', '/imu'])

        To record for default 5 seconds with default topics:
        rosbag_record()
    """
    if topics is None:
        topics = ["/scan", "/odom"]

    if duration <= 0:
        return {"error": "Duration must be greater than 0 seconds."}

    bags_dir = get_bags_directory()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    bag_filename = f"{timestamp}.bag"
    bag_filepath = os.path.join(bags_dir, bag_filename)

    # Build the rosbag record command
    topic_str = " ".join(topics)
    cmd = f"rosbag record -O {bag_filepath} -d {duration} {topic_str}"

    try:
        # Run the rosbag record command
        process = subprocess.Popen(
            cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        # Wait for the process to complete
        stdout, stderr = process.communicate(timeout=duration + 10)

        if process.returncode != 0:
            error_msg = stderr.decode() if stderr else "Unknown error"
            return {
                "error": f"Failed to record bag: {error_msg}",
                "return_code": process.returncode,
            }

        # Verify the bag file was created
        if not os.path.exists(bag_filepath):
            return {
                "error": "Bag file was not created. Check if topics are available and ROS is running."
            }

        # Get file size
        file_size = os.path.getsize(bag_filepath)
        file_size_mb = file_size / (1024 * 1024)

        return {
            "success": True,
            "bag_file": bag_filepath,
            "filename": bag_filename,
            "duration": duration,
            "topics_recorded": topics,
            "file_size_bytes": file_size,
            "file_size_mb": round(file_size_mb, 2),
            "message": f"Successfully recorded {duration} seconds of sensor data to {bag_filename}",
        }

    except subprocess.TimeoutExpired:
        process.kill()
        return {
            "error": f"Recording process timed out after {duration + 10} seconds."
        }
    except Exception as e:
        return {"error": f"An error occurred during recording: {str(e)}"}


@tool
def rosbag_play(
    bag_file: str,
    rate: float = 1.0,
    loop: bool = False,
    start_time: Optional[float] = None,
) -> dict:
    """
    Plays back a recorded ROS bag file.

    Replays the sensor data from a previously recorded bag file. This allows you to test
    algorithms and debug robot behavior using recorded sensor data without needing the
    actual robot or live sensor streams.

    :param bag_file: Name of the bag file (with or without .bag extension) or full path.
                     Can be just the filename if it's in the bags/ directory.
    :param rate: Playback rate multiplier. 1.0 = normal speed, 2.0 = 2x speed, 0.5 = half speed.
    :param loop: If True, loop the bag file playback continuously.
    :param start_time: Optional start time offset in seconds within the bag file.
    :return: Dictionary with status and playback information.

    Example:
        To play back a bag file at normal speed:
        rosbag_play("20240115_143022.bag")

        To play back at 2x speed:
        rosbag_play("20240115_143022.bag", rate=2.0)

        To loop playback continuously:
        rosbag_play("20240115_143022.bag", loop=True)
    """
    bags_dir = get_bags_directory()

    # Handle both full path and filename
    if os.path.isabs(bag_file):
        bag_filepath = bag_file
    else:
        # Remove .bag extension if provided
        if bag_file.endswith(".bag"):
            bag_file = bag_file[:-4]
        bag_filepath = os.path.join(bags_dir, f"{bag_file}.bag")

    # Verify the bag file exists
    if not os.path.exists(bag_filepath):
        return {
            "error": f"Bag file not found: {bag_filepath}",
            "available_bags": rosbag_list.func()["bags"] if rosbag_list.func()["total"] > 0 else [],
        }

    # Build the rosbag play command
    cmd = f"rosbag play {bag_filepath} --rate={rate}"

    if loop:
        cmd += " --loop"

    if start_time is not None and start_time > 0:
        cmd += f" --start={start_time}"

    try:
        # Run the rosbag play command (non-blocking, returns immediately)
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
            "note": "Playback is running in the background. Use 'rosbag_stop' to stop playback or press Ctrl+C in the terminal.",
        }

    except Exception as e:
        return {"error": f"An error occurred during playback: {str(e)}"}


@tool
def rosbag_list(
    min_size: int = 0,
    pattern: Optional[str] = None,
) -> dict:
    """
    Lists all recorded ROS bag files available in the bags/ directory.

    Returns a list of all bag files that have been recorded, along with metadata
    such as file size and creation time. This helps you find and select bag files
    for playback or analysis.

    :param min_size: Minimum file size in bytes to include in the list. Default is 0 (no filter).
    :param pattern: Optional regex pattern to filter bag files by name.
    :return: Dictionary with list of bag files and metadata.

    Example:
        To list all bags:
        rosbag_list.func()

        To list only bags larger than 1MB:
        rosbag_list(min_size=1048576)

        To list bags from a specific date:
        rosbag_list(pattern="20240115.*")
    """
    bags_dir = get_bags_directory()

    if not os.path.exists(bags_dir):
        return {"total": 0, "bags": []}

    try:
        # Get all .bag files in the bags directory
        bag_files = [
            f
            for f in os.listdir(bags_dir)
            if os.path.isfile(os.path.join(bags_dir, f)) and f.endswith(".bag")
        ]

        # Filter by minimum size
        if min_size > 0:
            bag_files = [
                f
                for f in bag_files
                if os.path.getsize(os.path.join(bags_dir, f)) >= min_size
            ]

        # Filter by pattern if provided
        if pattern:
            import re

            bag_files = [f for f in bag_files if re.match(f".*{pattern}.*", f)]

        # Sort by modification time (newest first)
        bag_files.sort(
            key=lambda f: os.path.getmtime(os.path.join(bags_dir, f)), reverse=True
        )

        # Create detailed metadata for each bag file
        bags_info = []
        for bag_file in bag_files:
            filepath = os.path.join(bags_dir, bag_file)
            file_size = os.path.getsize(filepath)
            mod_time = os.path.getmtime(filepath)
            mod_datetime = datetime.fromtimestamp(mod_time).strftime(
                "%Y-%m-%d %H:%M:%S"
            )

            file_size_mb = file_size / (1024 * 1024)

            bags_info.append(
                {
                    "filename": bag_file,
                    "path": filepath,
                    "size_bytes": file_size,
                    "size_mb": round(file_size_mb, 2),
                    "created": mod_datetime,
                }
            )

        return {
            "total": len(bags_info),
            "bags_directory": bags_dir,
            "bags": bags_info,
        }

    except Exception as e:
        return {"error": f"Failed to list bag files: {str(e)}", "total": 0, "bags": []}


@tool
def rosbag_info(bag_file: str) -> dict:
    """
    Gets detailed information about a specific ROS bag file.

    Retrieves metadata about a bag file including topics recorded, message counts,
    start/end times, and duration. This is useful for understanding what data is
    available in a bag before playing it back.

    :param bag_file: Name of the bag file (with or without .bag extension) or full path.
    :return: Dictionary with bag file information.

    Example:
        rosbag_info("20240115_143022.bag")
    """
    bags_dir = get_bags_directory()

    # Handle both full path and filename
    if os.path.isabs(bag_file):
        bag_filepath = bag_file
    else:
        # Remove .bag extension if provided
        if bag_file.endswith(".bag"):
            bag_file = bag_file[:-4]
        bag_filepath = os.path.join(bags_dir, f"{bag_file}.bag")

    # Verify the bag file exists
    if not os.path.exists(bag_filepath):
        return {"error": f"Bag file not found: {bag_filepath}"}

    try:
        # Run rosbag info command
        cmd = f"rosbag info {bag_filepath}"
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
def rosbag_delete(bag_file: str) -> dict:
    """
    Deletes a recorded ROS bag file.

    Removes a bag file from the bags/ directory. Use with caution as this operation
    cannot be undone.

    :param bag_file: Name of the bag file (with or without .bag extension) or full path.
    :return: Dictionary with status of the deletion.

    Example:
        rosbag_delete("20240115_143022.bag")
    """
    bags_dir = get_bags_directory()

    # Handle both full path and filename
    if os.path.isabs(bag_file):
        bag_filepath = bag_file
    else:
        # Remove .bag extension if provided
        if bag_file.endswith(".bag"):
            bag_file = bag_file[:-4]
        bag_filepath = os.path.join(bags_dir, f"{bag_file}.bag")

    # Verify the bag file exists
    if not os.path.exists(bag_filepath):
        return {"error": f"Bag file not found: {bag_filepath}"}

    try:
        os.remove(bag_filepath)
        return {
            "success": True,
            "message": f"Successfully deleted {os.path.basename(bag_filepath)}",
            "deleted_file": bag_filepath,
        }
    except Exception as e:
        return {"error": f"Failed to delete bag file: {str(e)}"}

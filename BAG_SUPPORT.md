# ROS1 Bag Support in ROSA

## Overview

This document describes the bag recording and playback functionality added to ROSA for ROS1. Bags are the primary way ROS systems record and replay sensor data, which is essential for debugging robot behavior offline without needing the actual robot or live sensor streams.

## Features

The ROSA bag support module provides the following functionality:

### 1. **Record Bags** (`rosbag_record`)
Records sensor data from specified ROS topics for a given duration and saves it to a timestamped bag file.

**Parameters:**
- `duration` (int, default=5): Duration to record in seconds
- `topics` (List[str], optional): List of topic names to record. Defaults to `['/scan', '/odom']`

**Returns:**
- Success response with bag file path, size, and metadata
- Error response if recording fails

**Example:**
```python
# Record for default 5 seconds with default topics (/scan, /odom)
result = rosbag_record()

# Record for 10 seconds with custom topics
result = rosbag_record(duration=10, topics=['/scan', '/odom', '/imu'])
```

### 2. **Play Bags** (`rosbag_play`)
Plays back a previously recorded bag file, replaying sensor data to allow testing algorithms without live sensors.

**Parameters:**
- `bag_file` (str): Name of the bag file (with or without .bag extension) or full path
- `rate` (float, default=1.0): Playback rate multiplier (1.0 = normal, 2.0 = 2x speed, 0.5 = half speed)
- `loop` (bool, default=False): If True, loop the playback continuously
- `start_time` (float, optional): Start time offset in seconds within the bag file

**Returns:**
- Success response with playback details
- Error response if playback cannot start

**Example:**
```python
# Play back at normal speed
rosbag_play("20240115_143022.bag")

# Play back at 2x speed
rosbag_play("20240115_143022.bag", rate=2.0)

# Loop playback continuously
rosbag_play("20240115_143022.bag", loop=True)

# Play back starting from 5 seconds into the bag
rosbag_play("20240115_143022.bag", start_time=5.0)
```

### 3. **List Bags** (`rosbag_list`)
Lists all recorded bag files available in the bags/ directory with metadata.

**Parameters:**
- `min_size` (int, default=0): Minimum file size in bytes to include
- `pattern` (str, optional): Regex pattern to filter bag files by name

**Returns:**
- Dictionary with list of bags and metadata (filename, path, size, creation time)

**Example:**
```python
# List all bags
rosbag_list()

# List only bags larger than 1MB
rosbag_list(min_size=1048576)

# List bags from a specific date
rosbag_list(pattern="20240115.*")
```

### 4. **Get Bag Info** (`rosbag_info`)
Retrieves detailed information about a specific bag file including topics, message counts, and duration.

**Parameters:**
- `bag_file` (str): Name of the bag file (with or without .bag extension) or full path

**Returns:**
- Dictionary with bag metadata and detailed info from `rosbag info` command

**Example:**
```python
rosbag_info("20240115_143022.bag")
```

### 5. **Delete Bags** (`rosbag_delete`)
Removes a bag file from the bags/ directory.

**Parameters:**
- `bag_file` (str): Name of the bag file (with or without .bag extension) or full path

**Returns:**
- Success response confirming deletion
- Error response if deletion fails

**Example:**
```python
rosbag_delete("20240115_143022.bag")
```

## Directory Structure

All bag files are stored in a `bags/` directory created in the current working directory. The structure is:

```
<current_working_directory>/
├── bags/
│   ├── 20240115_143022.bag
│   ├── 20240115_143023.bag
│   └── 20240115_143024.bag
└── ... other files
```

## Bag File Naming

Bag files are automatically named with timestamps in the format: `YYYYMMDD_HHMMSS.bag`

Example: `20240115_143022.bag` (January 15, 2024 at 14:30:22)

## Default Topics

By default, `rosbag_record` records the following topics which are common sensor data topics for mobile robots:
- `/scan` - LIDAR/laser scanner data
- `/odom` - Odometry data

You can override these defaults by providing your own topic list.

## Integration with ROSA

The bag tools are fully integrated into ROSA as LangChain tools, making them accessible through the ROSA natural language interface:

```python
from rosa import ROSA

agent = ROSA(ros_version=1, llm=your_llm)

# Natural language queries can now use bag functions
agent.invoke("Record sensor data for 10 seconds and save it")
agent.invoke("List all bag files recorded today")
agent.invoke("Play back the most recent bag file at 2x speed")
```

## Implementation Details

### Files Modified/Created

1. **New File: `src/rosa/tools/ros1_bag.py`**
   - Contains all bag-related functions
   - Uses subprocess to call ROS bag commands
   - Handles file management and metadata

2. **Modified: `src/rosa/tools/ros1.py`**
   - Added import for ros1_bag module
   - Exported bag functions at module level
   - Functions are automatically picked up by ROSATools

3. **New File: `tests/test_rosa/tools/test_ros1_bag.py`**
   - Comprehensive unit tests for all bag functions
   - 25+ test cases covering success and failure scenarios
   - Tests use mocking to avoid ROS dependencies

### Key Design Decisions

1. **Timestamp-based Naming**: Bag files use timestamps to ensure unique names and easy sorting
2. **Default Topics**: `/scan` and `/odom` are sensible defaults for mobile robots
3. **Flexible Paths**: Functions accept both relative filenames and absolute paths
4. **Error Handling**: All functions return structured error responses for easy parsing
5. **Non-blocking Playback**: `rosbag_play` runs in background, allowing continued interaction

## Testing

Comprehensive unit tests are provided in `tests/test_rosa/tools/test_ros1_bag.py`. To run them:

```bash
python3 -m unittest tests.test_rosa.tools.test_ros1_bag.TestROS1BagTools -v
```

Test coverage includes:
- Directory creation and management
- Successful recording with various parameters
- Playback with different rates and options
- Listing bags with filtering
- Getting bag information
- Deleting bags
- Error handling for missing files
- Edge cases and parameter validation

## Future Enhancements

Planned features for future releases:

1. **ROS2 Support**: Similar bag functionality for ROS2 (using `ros2 bag`)
2. **Bag Filtering**: Filter bags by topic, date range, or message count
3. **Bag Merging**: Combine multiple bag files
4. **Bag Splitting**: Split large bags into smaller files
5. **Topic Filtering During Playback**: Play back only specific topics from a bag
6. **Bag Compression**: Automatically compress old bags to save space
7. **Cloud Storage**: Upload bags to cloud storage services

## Troubleshooting

### "Bag file was not created"
- Ensure ROS is running
- Verify the topics you're recording actually have publishers
- Check disk space availability

### "Bag file not found"
- Verify the filename is correct
- Check that the file exists in the `bags/` directory
- Use `rosbag_list()` to see available bags

### "Failed to start playback"
- Ensure the bag file is valid (not corrupted)
- Check that ROS is running
- Verify the playback rate is a positive number

## Dependencies

The bag support requires:
- ROS1 (Noetic or compatible version)
- `rosbag` command-line tools (usually installed with ROS)
- Python 3.9+
- LangChain

## License

Copyright (c) 2024. Jet Propulsion Laboratory. All rights reserved.
Licensed under the Apache License, Version 2.0.

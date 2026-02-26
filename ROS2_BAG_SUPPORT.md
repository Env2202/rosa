# ROS2 Bag Support in ROSA

## Overview

This document describes the bag recording and playback functionality added to ROSA for ROS2. ROS2 uses `ros2 bag` commands which differ from ROS1's `rosbag` tool. Bags are stored as directories containing metadata and data files, rather than single `.bag` files.

## Key Differences from ROS1

| Feature | ROS1 | ROS2 |
|---------|------|------|
| Storage Format | Single `.bag` file | Directory with multiple files |
| Command | `rosbag record/play` | `ros2 bag record/play` |
| Duration Flag | `-d` (seconds) | `-d` (seconds) |
| Output Flag | `-O` (file) | `-o` (directory) |
| Rate Flag | `--rate=` | `--rate` |
| Loop Flag | `--loop` | `--loop` |
| Start Time | `--start=` | `--start-offset` |

## Features

The ROSA ROS2 bag support module provides the following functionality:

### 1. **Record Bags** (`ros2bag_record`)
Records sensor data from specified ROS2 topics for a given duration and saves it to a timestamped bag directory.

**Parameters:**
- `duration` (int, default=5): Duration to record in seconds
- `topics` (List[str], optional): List of topic names to record. Defaults to `['/scan', '/odom']`

**Returns:**
- Success response with bag directory path, size, and metadata
- Error response if recording fails

**Example:**
```python
# Record for default 5 seconds with default topics
result = ros2bag_record()

# Record for 10 seconds with custom topics
result = ros2bag_record(duration=10, topics=['/scan', '/odom', '/imu'])
```

### 2. **Play Bags** (`ros2bag_play`)
Plays back a previously recorded ROS2 bag directory.

**Parameters:**
- `bag_file` (str): Name of the bag directory or full path
- `rate` (float, default=1.0): Playback rate multiplier
- `loop` (bool, default=False): If True, loop the playback continuously
- `start_time` (float, optional): Start time offset in seconds within the bag

**Returns:**
- Success response with playback details
- Error response if playback cannot start

**Example:**
```python
# Play back at normal speed
ros2bag_play("20240115_143022")

# Play back at 2x speed
ros2bag_play("20240115_143022", rate=2.0)

# Loop playback continuously
ros2bag_play("20240115_143022", loop=True)
```

### 3. **List Bags** (`ros2bag_list`)
Lists all recorded ROS2 bag directories available in the bags/ directory.

**Parameters:**
- `min_size` (int, default=0): Minimum directory size in bytes to include
- `pattern` (str, optional): Regex pattern to filter bag directories by name

**Returns:**
- Dictionary with list of bag directories and metadata

**Example:**
```python
# List all bags
ros2bag_list()

# List only bags larger than 1MB
ros2bag_list(min_size=1048576)

# List bags from a specific date
ros2bag_list(pattern="20240115.*")
```

### 4. **Get Bag Info** (`ros2bag_info`)
Gets detailed information about a specific ROS2 bag directory.

**Parameters:**
- `bag_file` (str): Name of the bag directory or full path

**Returns:**
- Dictionary with bag directory information

**Example:**
```python
ros2bag_info("20240115_143022")
```

### 5. **Delete Bags** (`ros2bag_delete`)
Deletes a recorded ROS2 bag directory.

**Parameters:**
- `bag_file` (str): Name of the bag directory or full path

**Returns:**
- Dictionary with status of the deletion

**Example:**
```python
ros2bag_delete("20240115_143022")
```

## Directory Structure

In ROS2, bags are stored as directories containing multiple files:

```
bags/
├── 20240115_143022/
│   ├── metadata.yaml
│   ├── data.db3
│   └── data.db3-shm
├── 20240115_143023/
│   ├── metadata.yaml
│   └── data.db3
└── 20240115_143024/
    ├── metadata.yaml
    └── data.db3
```

**Key Files:**
- `metadata.yaml` - Bag metadata (topics, message counts, timestamps)
- `data.db3` - SQLite database containing the actual message data
- `data.db3-shm` - Shared memory file for SQLite (temporary)

## Bag Directory Naming

Bag directories are automatically named with timestamps in the format: `YYYYMMDD_HHMMSS`

Example: `20240115_143022` (January 15, 2024 at 14:30:22)

## Default Topics

By default, `ros2bag_record` records the following topics:
- `/scan` - LIDAR/laser scanner data
- `/odom` - Odometry data

You can override these defaults by providing your own topic list.

## Integration with ROSA

The bag tools are fully integrated into ROSA as LangChain tools:

```python
from rosa import ROSA

agent = ROSA(ros_version=2, llm=your_llm)

# Natural language queries can now use bag functions
agent.invoke("Record sensor data for 10 seconds and save it")
agent.invoke("List all bag files recorded today")
agent.invoke("Play back the most recent bag file at 2x speed")
```

## Implementation Details

### Files Modified/Created

1. **New File: `src/rosa/tools/ros2_bag.py`**
   - Contains all ROS2 bag-related functions
   - Uses subprocess to call `ros2 bag` commands
   - Handles directory management and metadata
   - Calculates total directory size for bag listings

2. **Modified: `src/rosa/tools/ros2.py`**
   - Added import for ros2_bag module
   - Exported bag functions at module level
   - Functions automatically picked up by ROSATools

3. **New File: `tests/test_rosa/tools/test_ros2_bag.py`**
   - Comprehensive unit tests for all ROS2 bag functions
   - 25+ test cases covering success and failure scenarios
   - Tests use mocking to avoid ROS2 dependencies
   - Accounts for ROS2's directory-based bag storage

### Key Design Decisions

1. **Directory-Based Storage**: ROS2 bags are directories, not single files
2. **Size Calculation**: Total size includes all files in the bag directory
3. **Hidden Directory Filtering**: `.hidden` directories are ignored
4. **Recursive Deletion**: Uses `shutil.rmtree()` for directory deletion
5. **Consistent API**: Same function signatures as ROS1 for easy migration

## Testing

Comprehensive unit tests are provided in `tests/test_rosa/tools/test_ros2_bag.py`. To run them:

```bash
python3 -m unittest tests.test_rosa.tools.test_ros2_bag.TestROS2BagTools -v
```

Test coverage includes:
- Directory creation and management
- Successful recording with various parameters
- Playback with different rates and options
- Listing bags with filtering
- Getting bag information
- Deleting bags
- Error handling for missing directories
- Edge cases and parameter validation
- Hidden directory filtering

## Troubleshooting

### "Bag directory was not created"
- Ensure ROS2 is running: `ros2 topic list`
- Verify the topics you're recording actually have publishers
- Check disk space availability

### "Bag directory not found"
- Use `ros2bag_list()` to see available bags
- Check that the `bags/` directory exists
- Verify directory name is correct (no `.bag` extension in ROS2)

### "Failed to start playback"
- Ensure the bag directory is valid (contains `metadata.yaml`)
- Check that ROS2 is running
- Verify playback rate is a positive number

## Dependencies

The ROS2 bag support requires:
- ROS2 (Humble, Iron, Jazzy, or compatible)
- `ros2 bag` command-line tools (usually installed with ROS2)
- Python 3.9+
- LangChain

## Migration from ROS1

If you're migrating from ROS1 to ROS2:

1. **Function Names**: Change from `rosbag_*` to `ros2bag_*`
2. **Bag Format**: ROS1 `.bag` files need conversion for ROS2
3. **Topics**: Topic names may differ between ROS1 and ROS2
4. **Storage**: Remember ROS2 uses directories, not single files

Example migration:
```python
# ROS1
from rosa.tools.ros1_bag import rosbag_record
result = rosbag_record(duration=5)

# ROS2
from rosa.tools.ros2_bag import ros2bag_record
result = ros2bag_record(duration=5)
```

## License

Copyright (c) 2024. Jet Propulsion Laboratory. All rights reserved.
Licensed under the Apache License, Version 2.0.

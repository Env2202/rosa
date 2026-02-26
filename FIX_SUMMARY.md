# Fix Summary: Agent Awareness of Bag Tools

## Issue
The agent was unaware of the newly added bag recording and playback capabilities, leading it to tell users it couldn't perform these actions and providing manual terminal commands instead.

## Root Cause
1. **Tool Registration**: The new `ros1_bag` and `ros2_bag` modules were being imported in `ros1.py`/`ros2.py` but potentially not being picked up by the `ROSATools` auto-discovery mechanism which iterates over module attributes.
2. **System Prompts**: The agent's system prompts did not incorrectly inform the agent about these new capabilities, and its default behavior (based on training) is to assume it cannot run terminal commands like `rosbag`.

## Fixes Implemented

### 1. Explicit Tool Loading (`src/rosa/tools/__init__.py`)
Modified the `ROSATools` class to explicitly import and iterate over `ros1_bag` and `ros2_bag` modules.

```python
if self.__ros_version == 1:
    from . import ros1
    from . import ros1_bag  # Added

    self.__iterative_add(ros1, blacklist=blacklist)
    self.__iterative_add(ros1_bag, blacklist=blacklist) # Added
elif self.__ros_version == 2:
    from . import ros2
    from . import ros2_bag # Added

    self.__iterative_add(ros2, blacklist=blacklist)
    self.__iterative_add(ros2_bag, blacklist=blacklist) # Added
```

### 2. Updated System Prompts (`src/rosa/prompts.py`)
Added a specific instruction to the system prompts to inform the agent about its bag capabilities.

```python
(
    "system",
    "You have specific tools for recording and playing back ROS bag files (rosbag_record, rosbag_play, ros2bag_record, etc.). "
    "Use these tools when the user asks to record data, save a bag, or play back sensor data. "
    "You do NOT need to ask the user to run commands in their terminal; you can execute these operations yourself using the provided tools.",
),
```

## Verification
These changes ensure that:
1. The bag tools (`rosbag_record`, `rosbag_play`, etc.) are definitely in the list of tools provided to the LLM.
2. The LLM is explicitly instructed that it *can* and *should* use these tools, overriding any training bias against running system commands.

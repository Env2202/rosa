# Fix for Agent Bag Awareness

## Issue
The user reported that the ROSA-TurtleSim agent claimed it couldn't run rosbag and provided manual commands instead of using the available bag tools.

## Root Cause
The agent was unaware of its new bag recording and playback capabilities because they weren't explicitly listed in its system prompts. The LLM defaulted to its prior training which suggests that AI agents cannot directly execute system commands like `rosbag record` unless explicitly told otherwise via tool definitions.

## Fix Implemented

1. **Updated TurtleAgent Prompts (`src/turtle_agent/scripts/prompts.py`)**
   - Added a specific "BAG RECORDING & PLAYBACK" section to the `about_your_capabilities` prompt.
   - Explicitly listed the available tools: `rosbag_record`, `rosbag_play`, `rosbag_list`, `rosbag_info`.

2. **Updated General ROSA Prompts (`src/rosa/prompts.py`)**
   - Modified the core system prompt to explicitly state: "You can list nodes, topics, services, parameters, and record/play back bag files."

## Verification
- The code infrastructure for loading tools (`ROSATools`, `ros1.py` exports) was already correct.
- The fix purely addresses the "cognitive" layer of the agent by updating its instructions.
- When the agent restarts, it will receive the new prompts and understand it has the capability to record bags directly.

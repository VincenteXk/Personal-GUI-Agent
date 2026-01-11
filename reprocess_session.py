#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from src.learning.behavior_analyzer import DataParser, DataProcessor
from src.learning.vlm_analyzer import VLMAnalyzer
from src.learning.behavior_summarizer import BehaviorSummarizer


def load_config():
    config_file = "config.json"
    with open(config_file, "r", encoding="utf-8") as f:
        config = json.load(f)
        return config["learning_config"]


def process_session(session_id: str = "20260111_185143_77de"):
    base_path = f"data/sessions/{session_id}"
    raw_dir = os.path.join(base_path, "raw")
    screenshots_dir = os.path.join(base_path, "screenshots")
    processed_dir = os.path.join(base_path, "processed")
    analysis_dir = os.path.join(base_path, "analysis")
    events_file = os.path.join(processed_dir, "events.json")
    summary_file = os.path.join(processed_dir, "session_summary.json")
    llm_file = os.path.join(processed_dir, f"{session_id}_for_vlm.json")
    vlm_file = os.path.join(analysis_dir, f"{session_id}_vlm.json")
    behavior_summary_file = os.path.join(analysis_dir, f"{session_id}_llm_summary.json")
    
    # =========================================================================
    # STEP 1: Parse Raw Data
    # =========================================================================

    parser = DataParser()

    # Parse all raw data sources
    logcat_events = parser.parse_logcat_data(os.path.join(raw_dir, "logcat.log"))
    uiautomator_events = parser.parse_uiautomator_data(os.path.join(raw_dir, "uiautomator.log"))
    window_events = parser.parse_window_data(os.path.join(raw_dir, "window.log"))

    screenshot_events = []

    combined_events = logcat_events + uiautomator_events + window_events
    combined_events.sort(key=lambda x: x.get("timestamp", ""))

    # Now add screenshot events with proper timestamps
    screenshot_timestamp_map = {}
    for event in combined_events:
        if event.get("event_type") == "screenshot":
            filepath = event.get("filepath", "")
            timestamp = event.get("timestamp", "")
            if filepath and timestamp:
                # Normalize path for comparison
                screenshot_timestamp_map[filepath] = timestamp

    # Process actual screenshot files
    for filename in sorted(os.listdir(screenshots_dir)):
        if filename.endswith('.png'):
            rel_path = os.path.join("screenshots", filename)

            # Try to find timestamp from map first
            timestamp = screenshot_timestamp_map.get(rel_path)

            if not timestamp:
                # Fallback to file modification time
                filepath = os.path.join(screenshots_dir, filename)
                
                mtime = os.path.getmtime(filepath)
                timestamp = datetime.fromtimestamp(mtime).isoformat() + "Z"

            # Only add if not already in combined_events
            if rel_path not in screenshot_timestamp_map:
                screenshot_events.append({
                    "timestamp": timestamp,
                    "event_type": "screenshot",
                    "source": "screenshot",
                    "filepath": rel_path
                })


    # Combine all events
    all_events = combined_events + screenshot_events

    # Sort by timestamp
    all_events.sort(key=lambda x: x.get("timestamp", ""))


    # =========================================================================
    # STEP 2: Save events.json (raw processed events)
    # =========================================================================

    # Get session start time from first event
    start_time = all_events[0].get("timestamp") if all_events else datetime.now().isoformat() + "Z"
    end_time = all_events[-1].get("timestamp") if all_events else datetime.now().isoformat() + "Z"

    events_data = {
        "session_id": session_id,
        "start_time": start_time,
        "end_time": end_time,
        "events": all_events
    }

    with open(events_file, "w", encoding="utf-8") as f:
        json.dump(events_data, f, ensure_ascii=False, indent=2)

    # =========================================================================
    # STEP 3: Process events (build app sessions)
    # =========================================================================

    processor = DataProcessor()
    app_sessions = processor.build_app_sessions(all_events)


    # Count activities and interactions
    total_activities = 0
    total_interactions = 0

    for app in app_sessions:
        activities = app.get("activities", [])
        total_activities += len(activities)

        for activity in activities:
            interactions = activity.get("interactions", [])
            total_interactions += len(interactions)


    # =========================================================================
    # STEP 4: Build context window
    # =========================================================================

    context_result = processor.build_context_window(events_data)

    # =========================================================================
    # STEP 6: Save session_summary.json
    # =========================================================================

    session_summary_data = context_result.copy()
    session_summary_data["session_id"] = session_id
    session_summary_data["events"] = all_events  # Add raw events for prepare_for_llm

    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(session_summary_data, f, ensure_ascii=False, indent=2)


    # =========================================================================
    # STEP 7: Prepare for LLM (add data quality metrics)
    # =========================================================================

    llm_data = processor.prepare_for_llm(session_summary_data)

    user_activities = llm_data.get("user_activities")
    screenshots = llm_data.get("screenshots")

    activities_with_data = sum(
        1 for app in user_activities
        if len(app.get("activities", [])) > 0
    )
    # Add data quality metrics
    llm_data["data_quality"] = {
        "total_events": len(all_events),
        "total_interactions": total_interactions,
        "total_screenshots": len(screenshots),
        "apps_with_data": activities_with_data,
        "coverage_percentage": (
            (total_interactions + len(screenshots)) / len(all_events) * 100
            if all_events else 0
        )
    }

    llm_data["session_id"] = session_id

    # =========================================================================
    # STEP 8: Save _llm.json
    # =========================================================================

    with open(llm_file, "w", encoding="utf-8") as f:
        json.dump(llm_data, f, ensure_ascii=False, indent=2)

    # =========================================================================
    # STEP 9: VLM Analysis
    # =========================================================================
    config = load_config()

    vlm_analyzer = VLMAnalyzer(api_key=config.get("api_key"), model=config.get("model"))
    vlm_analysis = vlm_analyzer.analyze_session_with_screenshots(llm_data)

    with open(vlm_file, "w", encoding="utf-8") as f:
        json.dump(vlm_analysis, f, ensure_ascii=False, indent=2)

    # =========================================================================
    # STEP 10: Behavior Summarization (LLM synthesis of VLM results)
    # =========================================================================

    behavior_summary = None

    config = load_config()
    behavior_summarizer = BehaviorSummarizer(config)

    vlm_outputs_list = [
        {
            "status": "success" if vlm_analysis.get("success") else "error",
            "analysis": vlm_analysis.get("analysis", {}),
            **vlm_analysis
        }
    ]

    behavior_summary = behavior_summarizer.summarize_cross_app_behavior(vlm_outputs_list)

    with open(behavior_summary_file, "w", encoding="utf-8") as f:
        json.dump(behavior_summary, f, ensure_ascii=False, indent=2)

    # =========================================================================
    # STEP 11: Summary and validation
    # =========================================================================
    return {
        "session_id": session_id,
        "events_file": events_file,
        "summary_file": summary_file,
        "llm_file": llm_file,
        "vlm_file": vlm_file,
        "behavior_summary_file": behavior_summary_file,
        "stats": {
            "total_events": len(all_events),
            "app_sessions": len(app_sessions),
            "activities": total_activities,
            "interactions": total_interactions,
            "screenshots": len(llm_data.get('screenshots', []))
        }
    }


if __name__ == "__main__":
    result = process_session()
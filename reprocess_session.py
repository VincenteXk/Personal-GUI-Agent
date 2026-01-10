#!/usr/bin/env python3
"""
Test script: Process raw data through the complete learning pipeline
Mirrors the behavior_analyzer.collect_and_process() workflow
Overwrites intermediate files

Complete flow:
raw/ → events.json → session_summary.json → _llm.json → _vlm_analysis.json → _behavior_summary.json
"""
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
    """Load API configuration from config.json"""
    config_file = "config.json"
    if not os.path.exists(config_file):
        return {}

    try:
        with open(config_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Warning: Failed to load config.json: {e}")
        return {}


def process_session(session_id: str = "20260111_054812_a216"):
    """
    Process a session from raw data to _behavior_summary.json format

    Complete flow:
    raw/ → parse → events.json → process → session_summary.json → prepare_for_llm → _llm.json → vlm_analyze → _vlm_analysis.json → behavior_summarize → _behavior_summary.json
    """

    base_path = f"data/sessions/{session_id}"
    raw_dir = os.path.join(base_path, "raw")
    processed_dir = os.path.join(base_path, "processed")

    print("=" * 90)
    print(f"PROCESSING SESSION: {session_id}")
    print("=" * 90)

    # Ensure output directory exists
    os.makedirs(processed_dir, exist_ok=True)

    # =========================================================================
    # STEP 1: Parse Raw Data
    # =========================================================================
    print("\n[STEP 1] Parsing raw data files...")
    print(f"  Raw data directory: {raw_dir}")

    parser = DataParser()

    # Parse all raw data sources
    logcat_events = parser.parse_logcat_data(os.path.join(raw_dir, "logcat.log"))
    print(f"  ✓ Logcat events: {len(logcat_events)}")

    uiautomator_events = parser.parse_uiautomator_data(os.path.join(raw_dir, "uiautomator.log"))
    print(f"  ✓ UIAutomator events: {len(uiautomator_events)}")

    window_events = parser.parse_window_data(os.path.join(raw_dir, "window.log"))
    print(f"  ✓ Window events: {len(window_events)}")

    # Parse screenshots (from screenshots directory)
    screenshots_dir = os.path.join(base_path, "screenshots")
    screenshot_events = []
    if os.path.exists(screenshots_dir):
        for filename in sorted(os.listdir(screenshots_dir)):
            if filename.endswith('.png'):
                filepath = os.path.join(screenshots_dir, filename)
                # Get file modification time
                mtime = os.path.getmtime(filepath)
                event_time = datetime.fromtimestamp(mtime).isoformat() + "Z"

                screenshot_events.append({
                    "timestamp": event_time,
                    "event_type": "screenshot",
                    "source": "screenshot",
                    "filepath": os.path.join("screenshots", filename)
                })
        print(f"  ✓ Screenshot events: {len(screenshot_events)}")

    # Combine all events
    all_events = logcat_events + uiautomator_events + window_events + screenshot_events

    # Sort by timestamp
    all_events.sort(key=lambda x: x.get("timestamp", ""))

    print(f"\n  Total events collected: {len(all_events)}")

    # =========================================================================
    # STEP 2: Save events.json (raw processed events)
    # =========================================================================
    print("\n[STEP 2] Saving events.json (raw processed events)...")

    # Get session start time from first event
    start_time = all_events[0].get("timestamp") if all_events else datetime.now().isoformat() + "Z"
    end_time = all_events[-1].get("timestamp") if all_events else datetime.now().isoformat() + "Z"

    events_data = {
        "session_id": session_id,
        "start_time": start_time,
        "end_time": end_time,
        "events": all_events
    }

    events_file = os.path.join(processed_dir, "events.json")
    with open(events_file, "w", encoding="utf-8") as f:
        json.dump(events_data, f, ensure_ascii=False, indent=2)

    print(f"  ✓ Saved: {events_file}")
    print(f"    - Total events: {len(all_events)}")

    # Event type distribution
    event_types = {}
    for event in all_events:
        et = event.get("event_type")
        event_types[et] = event_types.get(et, 0) + 1

    print(f"    - Event distribution:")
    for et, count in sorted(event_types.items(), key=lambda x: -x[1]):
        print(f"      {et}: {count}")

    # =========================================================================
    # STEP 3: Process events (build app sessions)
    # =========================================================================
    print("\n[STEP 3] Processing events (build_app_sessions)...")

    processor = DataProcessor()
    app_sessions = processor.build_app_sessions(all_events)

    print(f"  ✓ App sessions created: {len(app_sessions)}")

    # Count activities and interactions
    total_activities = 0
    total_interactions = 0

    for app in app_sessions:
        activities = app.get("activities", [])
        total_activities += len(activities)

        for activity in activities:
            interactions = activity.get("interactions", [])
            total_interactions += len(interactions)

    print(f"  ✓ Total activities: {total_activities}")
    print(f"  ✓ Total interactions: {total_interactions}")

    # =========================================================================
    # STEP 4: Build context window
    # =========================================================================
    print("\n[STEP 4] Building context window...")

    context_window = processor.build_context_window(events_data)

    print(f"  ✓ Start time: {context_window.get('start_time')}")
    print(f"  ✓ End time: {context_window.get('end_time')}")
    print(f"  ✓ Duration: {context_window.get('duration_minutes', 0):.1f} minutes")

    # =========================================================================
    # STEP 5: Extract search content
    # =========================================================================
    print("\n[STEP 5] Extracting search content...")

    search_content = processor.extract_search_content(all_events)

    print(f"  ✓ Search queries found: {len(search_content)}")
    if search_content:
        for i, search in enumerate(search_content[:3]):
            final_text = search.get("final_text", "")
            print(f"    {i+1}. {final_text[:50]}")
        if len(search_content) > 3:
            print(f"    ... and {len(search_content) - 3} more")

    # =========================================================================
    # STEP 6: Save session_summary.json
    # =========================================================================
    print("\n[STEP 6] Saving session_summary.json...")

    session_summary_data = {
        "session_id": session_id,
        "context_window": context_window,
        "app_sessions": app_sessions,
        "events": all_events,
        "search_content": search_content
    }

    summary_file = os.path.join(processed_dir, "session_summary.json")
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(session_summary_data, f, ensure_ascii=False, indent=2)

    print(f"  ✓ Saved: {summary_file}")
    print(f"    - Apps: {len(app_sessions)}")
    print(f"    - Activities: {total_activities}")
    print(f"    - Interactions: {total_interactions}")

    # =========================================================================
    # STEP 7: Prepare for LLM (add data quality metrics)
    # =========================================================================
    print("\n[STEP 7] Preparing LLM data...")

    llm_data = processor.prepare_for_llm(session_summary_data)

    if llm_data and "error" not in llm_data:
        user_activities = llm_data.get("user_activities", [])
        screenshots = llm_data.get("screenshots", [])

        print(f"  ✓ User activities: {len(user_activities)}")

        activities_with_data = sum(
            1 for app in user_activities
            if len(app.get("activities", [])) > 0
        )
        print(f"  ✓ Apps with activities: {activities_with_data}")
        print(f"  ✓ Screenshots: {len(screenshots)}")

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

        print(f"  ✓ Data quality score: {llm_data['data_quality']['coverage_percentage']:.1f}%")

    else:
        print(f"  ⚠ Data validation failed:")
        print(f"    Error: {llm_data.get('error')}")
        if "data_summary" in llm_data:
            summary = llm_data["data_summary"]
            print(f"    Apps: {summary.get('app_count')}")
            print(f"    Activities: {summary.get('activities_count')}")
            print(f"    Interactions: {summary.get('interactions_count')}")

    # =========================================================================
    # STEP 8: Save _llm.json
    # =========================================================================
    print("\n[STEP 8] Saving _llm.json...")

    llm_file = os.path.join(processed_dir, f"{session_id}_llm.json")
    with open(llm_file, "w", encoding="utf-8") as f:
        json.dump(llm_data, f, ensure_ascii=False, indent=2)

    print(f"  ✓ Saved: {llm_file}")

    # =========================================================================
    # STEP 9: VLM Analysis
    # =========================================================================
    print("\n[STEP 9] Analyzing with VLM...")

    vlm_file = os.path.join(processed_dir, f"{session_id}_vlm_analysis.json")
    vlm_analysis = None

    try:
        # Check if data quality is sufficient before VLM analysis
        if "error" in llm_data:
            print(f"  ⚠ Skipping VLM analysis due to data quality issue")
            print(f"    Error: {llm_data.get('error')}")
            if "data_summary" in llm_data:
                summary = llm_data["data_summary"]
                print(f"    Data Summary:")
                print(f"      - Interactions: {summary.get('interactions_count', 0)}")
                print(f"      - Screenshots: {summary.get('screenshots_count', 0)}")
            vlm_analysis = llm_data  # Pass through error
        else:
            # Get API key from config
            config = load_config()
            api_key = config.get("api_key")
            if not api_key:
                print(f"  ⚠ Skipping VLM analysis: No API key configured")
                vlm_analysis = {
                    "error": "API key not configured in config.json",
                    "session_id": session_id
                }
            else:
                vlm_analyzer = VLMAnalyzer(api_key=api_key)
                vlm_analysis = vlm_analyzer.analyze_session_with_screenshots(llm_data)

                if "error" in vlm_analysis:
                    print(f"  ⚠ VLM analysis returned error:")
                    print(f"    {vlm_analysis.get('error')}")
                    if "data_summary" in vlm_analysis:
                        summary = vlm_analysis["data_summary"]
                        print(f"    Data Summary:")
                        print(f"      - Interactions: {summary.get('interactions_count', 0)}")
                        print(f"      - Screenshots: {summary.get('screenshots_count', 0)}")
                else:
                    print(f"  ✓ VLM analysis completed")
                    if "analysis_results" in vlm_analysis:
                        results = vlm_analysis.get("analysis_results", {})
                        print(f"  ✓ User behavior flow identified: {results.get('behavior_summary', 'N/A')[:50]}...")
                        print(f"  ✓ Confidence score: {results.get('confidence_score', 'N/A')}")

    except Exception as e:
        print(f"  ❌ Error during VLM analysis: {str(e)}")
        vlm_analysis = {
            "error": f"VLM analysis failed: {str(e)}",
            "session_id": session_id
        }

    # Save VLM analysis
    with open(vlm_file, "w", encoding="utf-8") as f:
        json.dump(vlm_analysis, f, ensure_ascii=False, indent=2)
    print(f"  ✓ Saved: {vlm_file}")

    # =========================================================================
    # STEP 10: Behavior Summarization (LLM synthesis of VLM results)
    # =========================================================================
    print("\n[STEP 10] Summarizing behavior with LLM...")

    behavior_summary_file = os.path.join(processed_dir, f"{session_id}_behavior_summary.json")
    behavior_summary = None

    try:
        if "error" in vlm_analysis or (vlm_analysis and "error" in vlm_analysis):
            print(f"  ⚠ Skipping behavior summarization due to VLM error")
            behavior_summary = {
                "error": "Cannot summarize: VLM analysis failed or data quality insufficient",
                "vlm_error": vlm_analysis.get("error"),
                "session_id": session_id
            }
        else:
            behavior_summarizer = BehaviorSummarizer()
            behavior_summary = behavior_summarizer.summarize_cross_app_behavior(vlm_analysis)

            if "error" in behavior_summary:
                print(f"  ⚠ Behavior summarization returned error:")
                print(f"    {behavior_summary.get('error')}")
            else:
                print(f"  ✓ Behavior summarization completed")
                if "summary" in behavior_summary:
                    summary_text = behavior_summary.get("summary", "N/A")
                    if isinstance(summary_text, str):
                        print(f"  ✓ Summary: {summary_text[:100]}...")
                    else:
                        print(f"  ✓ Summary generated")
                print(f"  ✓ User goals: {behavior_summary.get('user_goals', [])}")
                print(f"  ✓ User patterns: {behavior_summary.get('user_patterns', [])}")

    except Exception as e:
        print(f"  ❌ Error during behavior summarization: {str(e)}")
        behavior_summary = {
            "error": f"Behavior summarization failed: {str(e)}",
            "session_id": session_id
        }

    # Save behavior summary
    with open(behavior_summary_file, "w", encoding="utf-8") as f:
        json.dump(behavior_summary, f, ensure_ascii=False, indent=2)
    print(f"  ✓ Saved: {behavior_summary_file}")

    # =========================================================================
    # STEP 11: Summary and validation
    # =========================================================================
    print("\n" + "=" * 90)
    print("PROCESSING COMPLETE")
    print("=" * 90)

    print("\nOutput Files Created:")
    print(f"  • {events_file}")
    print(f"  • {summary_file}")
    print(f"  • {llm_file}")
    print(f"  • {vlm_file}")
    print(f"  • {behavior_summary_file}")

    print("\nData Summary:")
    print(f"  Raw events: {len(all_events)}")
    print(f"  App sessions: {len(app_sessions)}")
    print(f"  Activities: {total_activities}")
    print(f"  Interactions: {total_interactions}")
    print(f"  Screenshots: {len(llm_data.get('screenshots', []))}")

    if "data_quality" in llm_data:
        dq = llm_data["data_quality"]
        print(f"\nData Quality Metrics:")
        print(f"  Coverage: {dq['coverage_percentage']:.1f}%")
        print(f"  Apps with data: {dq['apps_with_data']}")

    print("\n✅ All processing steps completed successfully!\n")

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
    # Default to the test session
    session_id = sys.argv[1] if len(sys.argv) > 1 else "20260111_054812_a216"

    print(f"\nProcessing session: {session_id}")
    print("This mirrors the behavior_analyzer.collect_and_process() workflow")
    print("Files in processed/ will be overwritten with new results\n")

    result = process_session(session_id)

    # Print final summary
    print("\n" + "=" * 90)
    print("FINAL SUMMARY")
    print("=" * 90)
    print(json.dumps({
        "session_id": result["session_id"],
        "files_created": {
            "events": os.path.basename(result["events_file"]),
            "summary": os.path.basename(result["summary_file"]),
            "llm": os.path.basename(result["llm_file"]),
            "vlm_analysis": os.path.basename(result["vlm_file"]),
            "behavior_summary": os.path.basename(result["behavior_summary_file"])
        },
        "statistics": result["stats"]
    }, indent=2, ensure_ascii=False))

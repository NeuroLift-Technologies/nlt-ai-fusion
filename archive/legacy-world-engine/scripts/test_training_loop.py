#!/usr/bin/env python3
"""
Test Training Loop - Demonstrates a complete Avatar-Aide training session
using the current SessionOrchestrator API (rule-based by default).

This script:
1. Creates a StayAlert Avatar
2. Creates an AttentionCoaching Aide and pairs it with the Avatar
3. Runs a training session with two scenarios via SessionOrchestrator
4. Displays results and metrics (JSON summary)

Model-awareness is opt-in and OFF by default, so this runs end-to-end with
no torch/transformers dependency.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import uuid
from datetime import datetime

from src.avatars.adhd_traits.stay_alert_avatar import StayAlertAvatar
from src.aides.executive_function_expertise.attention_coaching import AttentionCoaching
from src.core.events import EventBus
from src.simulation.session_orchestrator import SessionConfig, SessionOrchestrator


DEFAULT_SCENARIOS = [
    {
        "name": "Morning planning sprint",
        "task_type": "planning",
        "base_success_rate": 0.55,
        "cognitive_demand": 0.65,
    },
    {
        "name": "Inbox triage",
        "task_type": "email_management",
        "base_success_rate": 0.50,
        "cognitive_demand": 0.60,
    },
]


def initialize_avatar_and_aide():
    """Create and initialize Avatar and Aide instances (paired)."""
    print("\n" + "=" * 60)
    print("INITIALIZING AVATAR AND AIDE")
    print("=" * 60 + "\n")

    avatar_id = f"avatar_stay_alert_{uuid.uuid4().hex[:8]}"
    aide_id = f"aide_attention_{uuid.uuid4().hex[:8]}"

    avatar_config = {
        "trait_name": "StayAlert",
        "attention_duration": 15,
        "drift_probability": 0.3,
        "hyperfocus_tendency": 0.2,
    }
    aide_config = {"expertise_area": "sustained_attention"}

    avatar = StayAlertAvatar(avatar_id, avatar_config)
    aide = AttentionCoaching(aide_id, aide_config)

    print(f"Avatar Created:")
    print(f"  - ID: {avatar_id}")
    print(f"  - Trait: {avatar.trait_name}")
    print(f"  - State: {avatar.current_state.value}")

    print(f"\nAide Created:")
    print(f"  - ID: {aide_id}")
    print(f"  - Expertise: {aide.expertise_area}")

    save_to_supabase(avatar_id, aide_id, avatar.trait_name, aide.expertise_area)

    return avatar, aide


def save_to_supabase(avatar_id, aide_id, trait_name, expertise_area):
    """Best-effort Supabase persistence; never fails the script."""
    try:
        from src.database.supabase_client import SupabaseClient

        db_client = SupabaseClient()
        avatar_record = db_client.create_avatar(avatar_id, trait_name, {})
        aide_record = db_client.create_aide(aide_id, expertise_area, {})
        if avatar_record and aide_record:
            print("\nSuccessfully saved to Supabase")
        else:
            print("\nPartial database save")
    except Exception as e:
        print(f"\nCould not save to Supabase: {e}")
        print("  (Continuing with local session...)")


def select_scenario(scenarios):
    """Select a scenario list for training (prints the choices)."""
    print("\n" + "=" * 60)
    print("SELECTING SCENARIO")
    print("=" * 60 + "\n")

    print("Scheduled Scenarios:")
    for i, scenario in enumerate(scenarios, 1):
        print(f"\n{i}. {scenario['name']}")
        print(f"   Task type: {scenario['task_type']}")
        print(f"   Base success rate: {scenario['base_success_rate']}")
        print(f"   Cognitive demand: {scenario['cognitive_demand']}")

    print(f"\nSelected: {len(scenarios)} scenarios")
    return scenarios


def run_training_session(avatar, aide, scenarios):
    """Execute the training session via SessionOrchestrator."""
    print("\n" + "=" * 60)
    print("RUNNING TRAINING SESSION")
    print("=" * 60)

    # The SessionOrchestrator pairs the Aide to the Avatar internally.
    config = SessionConfig(
        max_attempts_per_scenario=4,
        max_coaching_per_attempt=2,
        check_fusion_readiness=True,
    )
    orchestrator = SessionOrchestrator(avatar=avatar, aide=aide, config=config)
    result = orchestrator.run_session(scenarios)
    return result


def display_results(avatar, aide, result):
    """Display the session result summary."""
    print("\n" + "=" * 60)
    print("SESSION RESULTS")
    print("=" * 60 + "\n")

    d = result.to_dict()
    print(f"Session ID: {d['session_id']}")
    print(f"Avatar: {d['avatar_id']}")
    print(f"Aide: {d['aide_id']}")
    print(f"Status: {'COMPLETED'}")
    print(f"\nAttempts: {d['total_attempts']}")
    print(f"Successes: {d['total_successes']}")
    print(f"Coaching Interventions: {d['total_coaching']}")
    print(f"Success Rate: {d['success_rate']:.2f}")
    print(f"Final Independence: {d['final_independence']:.2f}")
    print(f"Fusion Ready: {d['fusion_ready']}")

    print(f"\n--- Scenarios ---")
    for sc in d["scenarios"]:
        print(f"  {sc['name']}: {sc['successes']}/{sc['attempts']} "
              f"(independence {sc['independence']})")

    print(f"\n--- Avatar Final State ---")
    summary = avatar.get_state_summary()
    print(f"Current State: {avatar.current_state.value}")
    print(f"Emotional State: {avatar.emotional_state}")
    print(f"Cognitive Load: {avatar.cognitive_load:.2f}")
    print(f"Stress Level: {avatar.stress_level:.2f}")
    print(f"Overall Independence: {avatar.get_independence_level():.2f}")
    print(f"Success Rate: {summary['success_rate']:.2f}")
    print(f"Total Tasks Completed: {avatar.total_tasks_completed}")

    print(f"\n--- Aide Metrics ---")
    metrics = aide.get_coaching_effectiveness_metrics()
    print(f"Total Interventions: {metrics['total_interventions']}")
    print(f"Successful Interventions: {metrics['successful_interventions']}")
    print(f"Success Rate: {metrics['success_rate']:.2f}")
    print(f"Crisis Interventions: {metrics['crisis_interventions']}")

    print(f"\n--- Full Result (JSON) ---")
    import json
    print(json.dumps(d, indent=2, default=str))


def main():
    """Main test execution."""
    print("\n" + "=" * 80)
    print("NEUROLIFT TECHNOLOGIES - TRAINING LOOP TEST")
    print("=" * 80)

    try:
        avatar, aide = initialize_avatar_and_aide()
        scenarios = select_scenario(DEFAULT_SCENARIOS)
        result = run_training_session(avatar, aide, scenarios)
        display_results(avatar, aide, result)

        print("\n" + "=" * 80)
        print("TEST COMPLETED SUCCESSFULLY")
        print("=" * 80 + "\n")

        return 0

    except Exception as e:
        print(f"\nError during test execution: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

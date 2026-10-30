#!/usr/bin/env python3
"""
Training Session Runner

Demonstrates the NeuroLift Technologies Simulation Environment by running
a training session with the StayAlert Avatar and AttentionCoaching Aide.
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
import json

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from avatars.adhd_traits.attention_deficit import AttentionDeficit
from aides.executive_function_expertise.attention_coaching import AttentionCoaching
from utils.config_loader import ConfigLoader


def load_avatar_config():
    """Load StayAlert Avatar configuration"""
    config_loader = ConfigLoader()
    return config_loader.load_avatar_config("stay_alert")


def load_aide_config():
    """Load StayAlert Aide configuration"""
    config_loader = ConfigLoader()
    return config_loader.load_aide_config("stay_alert_aide")


def create_training_scenarios():
    """Create sample training scenarios"""
    return [
        {
            "scenario_id": "focus_task_1",
            "name": "Sustained Reading Task",
            "description": "Read and summarize a 5-page document",
            "task_type": "repetitive",
            "expected_duration": timedelta(minutes=15),
            "base_success_rate": 0.7,
            "task_engagement": 0.3,  # Low engagement for reading
            "cognitive_demand": 0.6,
            "novelty": 0.2,
            "immediate_rewards": 0.1,
        },
        {
            "scenario_id": "focus_task_2", 
            "name": "Creative Problem Solving",
            "description": "Brainstorm solutions to a complex problem",
            "task_type": "creative",
            "expected_duration": timedelta(minutes=20),
            "base_success_rate": 0.8,
            "task_engagement": 0.8,  # High engagement for creative work
            "cognitive_demand": 0.7,
            "novelty": 0.9,
            "immediate_rewards": 0.3,
        },
        {
            "scenario_id": "focus_task_3",
            "name": "Data Entry Task",
            "description": "Enter data from forms into spreadsheet",
            "task_type": "repetitive",
            "expected_duration": timedelta(minutes=25),
            "base_success_rate": 0.6,
            "task_engagement": 0.2,  # Very low engagement
            "cognitive_demand": 0.4,
            "novelty": 0.1,
            "immediate_rewards": 0.0,
        }
    ]


def run_training_session():
    """Run a complete training session"""
    print("🧠 NeuroLift Technologies Simulation Environment")
    print("=" * 60)
    print("Training Session: StayAlert Avatar + AttentionCoaching Aide")
    print("=" * 60)
    
    # Load configurations
    print("\n📋 Loading configurations...")
    avatar_config = load_avatar_config()
    aide_config = load_aide_config()
    
    # Create Avatar and Aide
    print("👤 Creating Avatar and Aide...")
    avatar = AttentionDeficit("stay_alert_001", avatar_config["trait_config"])
    aide = AttentionCoaching("attention_coach_001", aide_config["expertise_config"])
    
    print(f"   Avatar: {avatar.avatar_id} ({avatar.trait_name})")
    print(f"   Aide: {aide.aide_id} ({aide.expertise_area})")
    
    # Create training scenarios
    scenarios = create_training_scenarios()
    print(f"\n🎯 Created {len(scenarios)} training scenarios")
    
    # Run training session
    print("\n🚀 Starting training session...")
    print("-" * 60)
    
    session_results = []
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"\n📝 Scenario {i}: {scenario['name']}")
        print(f"   Description: {scenario['description']}")
        print(f"   Expected Duration: {scenario['expected_duration']}")
        print(f"   Task Engagement: {scenario['task_engagement']:.1f}")
        
        # Avatar attempts task
        print("\n   👤 Avatar attempting task...")
        result = avatar.attempt_task(scenario)
        
        print(f"   📊 Result: {'✅ SUCCESS' if result.success else '❌ FAILED'}")
        print(f"   ⏱️  Completion Time: {result.completion_time}")
        print(f"   🎯 Quality Score: {result.quality_score:.2f}")
        print(f"   😊 Emotional State: {result.emotional_state}")
        print(f"   🧠 Cognitive Load: {result.cognitive_load:.2f}")
        print(f"   ⚠️  Struggles: {', '.join(result.struggle_indicators) if result.struggle_indicators else 'None'}")
        
        # Aide provides coaching if needed
        if not result.success or result.quality_score < 0.7:
            print("\n   🤝 Aide providing coaching...")
            
            # Create coaching context
            from aides.base_aide import CoachingContext
            context = CoachingContext(
                avatar=avatar,
                task_context=scenario,
                current_struggle=result.struggle_indicators,
                emotional_state=result.emotional_state,
                cognitive_load=result.cognitive_load,
                stress_level=avatar.stress_level,
                recent_performance=[result],
                coaching_history=avatar.coaching_history,
            )
            
            # Get coaching action
            coaching_action = aide.provide_coaching(context)
            
            if coaching_action:
                print(f"   💡 Strategy: {coaching_action.strategy}")
                print(f"   🔧 Techniques: {', '.join(coaching_action.specific_techniques[:3])}...")
                print(f"   📈 Expected Outcomes: {', '.join(coaching_action.expected_outcomes[:2])}...")
                
                # Apply coaching
                avatar.receive_coaching(coaching_action.to_dict())
                
                # Track effectiveness
                aide.track_intervention_effectiveness(coaching_action, result)
            else:
                print("   ℹ️  No coaching intervention needed")
        
        # Update Avatar attention state
        avatar.update_attention_state()
        
        # Store results
        session_results.append({
            "scenario": scenario,
            "result": result.to_dict(),
            "avatar_state": avatar.get_state_summary(),
        })
        
        print(f"   📈 Current Independence: {avatar.get_independence_level():.2f}")
        print(f"   🔥 Burnout Risk: {avatar.assess_burnout_risk()['risk_level']}")
    
    # Session summary
    print("\n" + "=" * 60)
    print("📊 TRAINING SESSION SUMMARY")
    print("=" * 60)
    
    total_attempts = avatar.total_tasks_attempted
    total_successes = avatar.total_tasks_completed
    total_coaching = avatar.total_coaching_sessions
    
    print(f"📝 Total Tasks Attempted: {total_attempts}")
    print(f"✅ Total Tasks Completed: {total_successes}")
    print(f"📈 Success Rate: {total_successes/max(total_attempts,1):.2f}")
    print(f"🤝 Coaching Sessions: {total_coaching}")
    print(f"🎯 Overall Independence: {avatar.get_independence_level():.2f}")
    
    # Aide effectiveness
    aide_metrics = aide.get_coaching_effectiveness_metrics()
    print(f"👨‍🏫 Aide Success Rate: {aide_metrics['success_rate']:.2f}")
    print(f"🚨 Crisis Interventions: {aide_metrics['crisis_interventions']}")
    
    # Learning progress by task type
    print("\n📚 Learning Progress by Task Type:")
    for task_type, progress in avatar.learning_progress.items():
        print(f"   {task_type}: {progress.current_independence_level:.2f} independence "
              f"({progress.success_rate:.2f} success rate)")
    
    # Save session results
    results_file = Path("data/training_logs") / f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    results_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(results_file, 'w') as f:
        json.dump({
            "session_timestamp": datetime.now().isoformat(),
            "avatar_id": avatar.avatar_id,
            "aide_id": aide.aide_id,
            "scenarios_completed": len(scenarios),
            "session_results": session_results,
            "final_avatar_state": avatar.get_state_summary(),
            "final_aide_metrics": aide_metrics,
        }, f, indent=2)
    
    print(f"\n💾 Session results saved to: {results_file}")
    print("\n🎉 Training session completed!")


if __name__ == "__main__":
    try:
        run_training_session()
    except KeyboardInterrupt:
        print("\n\n⏹️  Training session interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Training session failed: {e}")
        import traceback
        traceback.print_exc()
"""
Training Session Manager

Orchestrates training sessions between Avatar-Aide pairs.
Manages scenario execution, progress tracking, and data persistence.
"""

from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import uuid
import time

from ..avatars.base_avatar import BaseAvatar, TaskResult
from ..aides.base_aide import BaseAide, CoachingContext
from ..database.supabase_client import SupabaseClient
from .environment.scenarios import Scenario, ScenarioLibrary


class TrainingSession:
    """
    Manages a single training session between an Avatar and Aide.

    Handles scenario execution, coaching, progress tracking, and data persistence.
    """

    def __init__(self, avatar: BaseAvatar, aide: BaseAide, scenario: Scenario):
        self.session_id = str(uuid.uuid4())
        self.avatar = avatar
        self.aide = aide
        self.scenario = scenario

        self.start_time = datetime.now()
        self.end_time: Optional[datetime] = None
        self.duration_seconds = 0

        self.task_results: List[TaskResult] = []
        self.coaching_actions: List[Dict[str, Any]] = []
        self.progress_data: Dict[str, Any] = {}

        self.db_client = SupabaseClient()
        self.session_record = self._create_session_record()

    def _create_session_record(self) -> Dict[str, Any]:
        """Create session record in database"""
        try:
            record = self.db_client.create_training_session(
                session_id=self.session_id,
                avatar_id=self.avatar.avatar_id,
                aide_id=self.aide.aide_id,
                session_type="standard",
                scenario=self.scenario.scenario_id
            )
            return record
        except Exception as e:
            print(f"Warning: Could not create session record: {e}")
            return {}

    def run(self) -> Dict[str, Any]:
        """
        Execute a complete training session.

        Returns session results and metrics.
        """
        print(f"\n{'='*60}")
        print(f"Training Session: {self.avatar.trait_name} Avatar")
        print(f"Scenario: {self.scenario.name}")
        print(f"Session ID: {self.session_id[:8]}...")
        print(f"{'='*60}\n")

        attempt_count = 0
        max_attempts = 3
        success = False

        while attempt_count < max_attempts and not success:
            attempt_count += 1
            print(f"\nAttempt {attempt_count}/{max_attempts}: {self.scenario.name}")
            print(f"{'-'*40}")

            task_result = self._run_task_attempt()
            self.task_results.append(task_result)

            print(f"Result: {'SUCCESS' if task_result.success else 'FAILED'}")
            print(f"Quality Score: {task_result.quality_score:.2f}")
            print(f"Struggle Indicators: {', '.join(task_result.struggle_indicators)}")

            if task_result.success:
                success = True
                self._record_task_result(task_result)
                print("\nAvatar completed task successfully!")

            else:
                print("\nAvatar struggling. Providing coaching intervention...")
                coaching_action = self._provide_coaching(task_result)

                if coaching_action:
                    print(f"Coaching Strategy: {coaching_action.get('strategy', 'N/A')}")
                    print(f"Techniques: {', '.join(coaching_action.get('specific_techniques', []))}")
                    self.coaching_actions.append(coaching_action)
                    self._record_coaching_action(coaching_action)

                if attempt_count < max_attempts:
                    print(f"\nRetrying after coaching...\n")

        self._finalize_session()

        return self._get_session_summary()

    def _run_task_attempt(self) -> TaskResult:
        """Execute a single task attempt"""
        task_context = {
            "task_type": self.scenario.task_type,
            "expected_duration": self.scenario.expected_duration,
            "complexity": self.scenario.complexity,
            "cognitive_demand": self.scenario.cognitive_demand,
            "base_success_rate": self.scenario.base_success_rate,
            "requires_sustained_focus": self.scenario.requires_sustained_focus,
            "duration_minutes": self.scenario.expected_duration.total_seconds() / 60,
            "aversiveness": self.scenario.aversiveness,
            **self.scenario.context
        }

        result = self.avatar.attempt_task(task_context)
        return result

    def _provide_coaching(self, task_result: TaskResult) -> Optional[Dict[str, Any]]:
        """Provide coaching intervention based on task result"""
        coaching_context = CoachingContext(
            avatar=self.avatar,
            task_context={
                "task_type": self.scenario.task_type,
                "duration_minutes": self.scenario.expected_duration.total_seconds() / 60,
            },
            current_struggle=task_result.struggle_indicators,
            emotional_state=task_result.emotional_state,
            cognitive_load=task_result.cognitive_load,
            stress_level=self.avatar.stress_level,
            recent_performance=self.task_results[-5:],
            coaching_history=self.aide.intervention_history[-5:],
        )

        coaching_action = self.aide.provide_coaching(coaching_context)

        if coaching_action:
            action_dict = coaching_action.to_dict()
            self.avatar.receive_coaching(action_dict)
            self.aide.track_intervention_effectiveness(coaching_action, task_result)
            return action_dict

        return None

    def _record_task_result(self, result: TaskResult) -> None:
        """Record task result to database"""
        try:
            self.db_client.create_task_result(
                session_id=self.session_id,
                avatar_id=self.avatar.avatar_id,
                task_type=self.scenario.task_type,
                success=result.success,
                completion_time=result.completion_time.total_seconds() if result.completion_time else None,
                quality_score=result.quality_score,
                struggle_indicators=result.struggle_indicators,
                emotional_state=result.emotional_state,
                cognitive_load=result.cognitive_load,
                result_data=result.to_dict()
            )
        except Exception as e:
            print(f"Warning: Could not record task result: {e}")

    def _record_coaching_action(self, action: Dict[str, Any]) -> None:
        """Record coaching action to database"""
        try:
            self.db_client.create_coaching_action(
                coaching_id=action.get("action_id", str(uuid.uuid4())),
                session_id=self.session_id,
                avatar_id=self.avatar.avatar_id,
                aide_id=self.aide.aide_id,
                coaching_type=action.get("coaching_type", "unknown"),
                urgency=action.get("urgency", "medium"),
                strategy=action.get("strategy", ""),
                techniques=action.get("specific_techniques", []),
                expected_outcomes=action.get("expected_outcomes", []),
                stress_reduction=action.get("stress_reduction", 0.0),
                emotional_boost=action.get("emotional_boost", 0.0),
                cognitive_support=action.get("cognitive_support", 0.0),
                independence_building=action.get("independence_building", 0.0)
            )
        except Exception as e:
            print(f"Warning: Could not record coaching action: {e}")

    def _finalize_session(self) -> None:
        """Finalize session and update database"""
        self.end_time = datetime.now()
        self.duration_seconds = int((self.end_time - self.start_time).total_seconds())

        self._update_avatar_progress()
        self._record_session_metrics()

        try:
            self.db_client.end_training_session(self.session_id, self.duration_seconds)
            self.db_client.update_avatar_state(
                self.avatar.avatar_id,
                {
                    "current_state": self.avatar.current_state.value,
                    "emotional_state": self.avatar.emotional_state,
                    "cognitive_load": self.avatar.cognitive_load,
                    "stress_level": self.avatar.stress_level,
                    "burnout_risk_level": self.avatar.burnout_risk_level,
                    "total_tasks_attempted": self.avatar.total_tasks_attempted,
                    "total_tasks_completed": self.avatar.total_tasks_completed,
                    "total_coaching_sessions": self.avatar.total_coaching_sessions,
                }
            )
        except Exception as e:
            print(f"Warning: Could not finalize session: {e}")

    def _update_avatar_progress(self) -> None:
        """Update avatar progress tracking"""
        task_type = self.scenario.task_type
        successful = any(result.success for result in self.task_results)

        try:
            existing = self.db_client.get_avatar_progress(self.avatar.avatar_id, task_type)

            if not existing:
                self.db_client.create_avatar_progress(self.avatar.avatar_id, task_type)

            progress = self.avatar.learning_progress.get(task_type)
            if progress:
                updates = {
                    "attempts": progress.attempts,
                    "successes": progress.successes,
                    "success_rate": progress.success_rate,
                    "independence_level": progress.current_independence_level,
                    "coaching_sessions": progress.total_coaching_sessions,
                }
                self.db_client.update_avatar_progress(
                    self.avatar.avatar_id,
                    task_type,
                    updates
                )
        except Exception as e:
            print(f"Warning: Could not update avatar progress: {e}")

    def _record_session_metrics(self) -> None:
        """Record session metrics to database"""
        try:
            success_rate = sum(1 for r in self.task_results if r.success) / len(self.task_results)
            avg_quality = sum(r.quality_score for r in self.task_results) / len(self.task_results)
            total_struggle_indicators = sum(len(r.struggle_indicators) for r in self.task_results)

            self.db_client.record_metric(
                metric_type="session_success_rate",
                metric_value=success_rate,
                avatar_id=self.avatar.avatar_id,
                metric_data={
                    "session_id": self.session_id,
                    "scenario": self.scenario.scenario_id,
                    "attempts": len(self.task_results)
                }
            )

            self.db_client.record_metric(
                metric_type="session_quality",
                metric_value=avg_quality,
                avatar_id=self.avatar.avatar_id,
                metric_data={
                    "session_id": self.session_id,
                    "scenario": self.scenario.scenario_id
                }
            )

            burnout_assessment = self.avatar.assess_burnout_risk()
            self.db_client.record_metric(
                metric_type="burnout_risk",
                metric_value=burnout_assessment["risk_score"],
                avatar_id=self.avatar.avatar_id,
                metric_data={
                    "session_id": self.session_id,
                    "risk_level": burnout_assessment["risk_level"]
                }
            )

        except Exception as e:
            print(f"Warning: Could not record session metrics: {e}")

    def _get_session_summary(self) -> Dict[str, Any]:
        """Generate session summary"""
        successful_attempts = sum(1 for r in self.task_results if r.success)
        total_attempts = len(self.task_results)
        avg_quality = (sum(r.quality_score for r in self.task_results) / len(self.task_results)
                      if self.task_results else 0)

        return {
            "session_id": self.session_id,
            "avatar": self.avatar.trait_name,
            "scenario": self.scenario.name,
            "successful": successful_attempts > 0,
            "attempts": total_attempts,
            "successful_attempts": successful_attempts,
            "average_quality_score": avg_quality,
            "coaching_interventions": len(self.coaching_actions),
            "duration_seconds": self.duration_seconds,
            "avatar_final_state": self.avatar.get_state_summary(),
            "aide_metrics": self.aide.get_coaching_effectiveness_metrics(),
        }

#!/usr/bin/env python3
"""
Environment Setup Script

Sets up the NeuroLift Technologies Simulation Environment with necessary
directories, configuration files, and initial data structures.
"""

import os
import sys
from pathlib import Path
import json
import yaml


def create_directory_structure():
    """Create necessary directory structure"""
    print("📁 Creating directory structure...")
    
    directories = [
        "data/training_logs",
        "data/avatar_progress", 
        "data/aide_interactions",
        "data/fusion_records",
        "configs/avatars",
        "configs/aides",
        "configs/simulation",
        "logs",
        "htmlcov",  # For test coverage reports
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"   ✅ {directory}")


def create_default_configs():
    """Create default configuration files"""
    print("\n⚙️  Creating default configuration files...")
    
    # Simulation configuration
    simulation_config = {
        "simulation_id": "default_simulation",
        "description": "Default simulation environment configuration",
        "world_config": {
            "gravity": 9.8,
            "time_scale": 1.0,
            "realism_level": "high",
            "consequence_severity": "realistic",
            "social_dynamics": "enabled",
            "random_events": "enabled"
        },
        "time_config": {
            "simulation_speed": 1.0,
            "time_compression": False,
            "real_time_sync": True
        },
        "consequence_config": {
            "immediate_consequences": True,
            "realistic_impact": True,
            "learning_from_failures": True
        },
        "difficulty_scaling": {
            "adaptive_difficulty": True,
            "success_threshold": 0.7,
            "failure_penalty": 0.1
        },
        "random_events": {
            "dysfunction_injection": True,
            "environmental_changes": True,
            "social_interactions": True
        },
        "performance_metrics": {
            "track_learning_progress": True,
            "measure_independence": True,
            "assess_burnout_risk": True
        }
    }
    
    with open("configs/simulation_config.yaml", 'w') as f:
        yaml.dump(simulation_config, f, default_flow_style=False)
    print("   ✅ configs/simulation_config.yaml")
    
    # Training configuration
    training_config = {
        "training_id": "default_training",
        "description": "Default training session configuration",
        "avatar_config": {
            "avatar_type": "attention_deficit",
            "initial_difficulty": 0.7,
            "learning_rate": 0.6,
            "burnout_threshold": 0.8
        },
        "aide_config": {
            "aide_type": "attention_coaching",
            "intervention_threshold": 0.6,
            "coaching_style": "supportive_skill_building"
        },
        "scenario_config": {
            "scenario_types": ["workplace", "personal", "social"],
            "difficulty_progression": "gradual",
            "randomization": True
        },
        "duration": "1_hour",
        "success_criteria": {
            "independence_threshold": 0.8,
            "success_rate_threshold": 0.7,
            "burnout_risk_max": 0.3
        },
        "evaluation_metrics": {
            "learning_curve_analysis": True,
            "coaching_effectiveness": True,
            "fusion_readiness": True
        }
    }
    
    with open("configs/training_config.yaml", 'w') as f:
        yaml.dump(training_config, f, default_flow_style=False)
    print("   ✅ configs/training_config.yaml")


def create_initial_data():
    """Create initial data structures"""
    print("\n📊 Creating initial data structures...")
    
    # Training session template
    session_template = {
        "session_id": "",
        "timestamp": "",
        "avatar_id": "",
        "aide_id": "",
        "scenarios": [],
        "results": [],
        "learning_progress": {},
        "coaching_interventions": [],
        "final_metrics": {}
    }
    
    with open("data/training_logs/session_template.json", 'w') as f:
        json.dump(session_template, f, indent=2)
    print("   ✅ data/training_logs/session_template.json")
    
    # Avatar progress template
    progress_template = {
        "avatar_id": "",
        "trait_name": "",
        "learning_sessions": [],
        "independence_milestones": [],
        "struggle_patterns": [],
        "success_patterns": [],
        "current_independence": 0.0,
        "last_updated": ""
    }
    
    with open("data/avatar_progress/progress_template.json", 'w') as f:
        json.dump(progress_template, f, indent=2)
    print("   ✅ data/avatar_progress/progress_template.json")
    
    # Aide interaction template
    interaction_template = {
        "aide_id": "",
        "expertise_area": "",
        "interventions": [],
        "effectiveness_metrics": {},
        "success_patterns": {},
        "failure_patterns": {},
        "last_intervention": ""
    }
    
    with open("data/aide_interactions/interaction_template.json", 'w') as f:
        json.dump(interaction_template, f, indent=2)
    print("   ✅ data/aide_interactions/interaction_template.json")


def create_gitignore():
    """Create .gitignore file"""
    print("\n🚫 Creating .gitignore...")
    
    gitignore_content = """# NeuroLift Technologies Simulation Environment

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST

# Virtual environments
venv/
env/
ENV/
env.bak/
venv.bak/

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# Testing
.pytest_cache/
.coverage
htmlcov/
.tox/
.cache
nosetests.xml
coverage.xml
*.cover
.hypothesis/

# Data and logs (keep templates, ignore actual data)
data/training_logs/*.json
!data/training_logs/*template.json
data/avatar_progress/*.json
!data/avatar_progress/*template.json
data/aide_interactions/*.json
!data/aide_interactions/*template.json
data/fusion_records/*.json
logs/*.log

# Configuration overrides
configs/local_*.yaml
configs/personal_*.json

# OS
.DS_Store
.DS_Store?
._*
.Spotlight-V100
.Trashes
ehthumbs.db
Thumbs.db

# Temporary files
*.tmp
*.temp
*.bak
"""
    
    with open(".gitignore", 'w') as f:
        f.write(gitignore_content)
    print("   ✅ .gitignore")


def create_license():
    """Create LICENSE file"""
    print("\n📄 Creating LICENSE...")
    
    license_content = """MIT License

Copyright (c) 2025 NeuroLift Technologies

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
    
    with open("LICENSE", 'w') as f:
        f.write(license_content)
    print("   ✅ LICENSE")


def main():
    """Main setup function"""
    print("🧠 NeuroLift Technologies Simulation Environment Setup")
    print("=" * 60)
    
    try:
        create_directory_structure()
        create_default_configs()
        create_initial_data()
        create_gitignore()
        create_license()
        
        print("\n" + "=" * 60)
        print("✅ Environment setup completed successfully!")
        print("=" * 60)
        print("\n🚀 Next steps:")
        print("   1. Install dependencies: pip install -r requirements.txt")
        print("   2. Run tests: pytest")
        print("   3. Start training session: python scripts/run_training_session.py")
        print("\n📚 Documentation:")
        print("   - README.md: Project overview and setup")
        print("   - docs/architecture.md: System architecture")
        print("   - docs/avatar-aide-advocate-process.md: Training process")
        
    except Exception as e:
        print(f"\n❌ Setup failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
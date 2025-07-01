#!/usr/bin/env python3
"""
Test script for OpsMind - Autonomous Incident-to-Insight Assistant
"""

import os
import sys
import json
from pathlib import Path

# Add the current directory to Python path
sys.path.append('.')
sys.path.append('./opsmind_agents')

def test_data_loading():
    """Test that we can load the datasets"""
    print("🔍 Testing data loading...")
    
    try:
        from opsmind_agents.agent import load_incident_data, load_jira_data
        
        # Test incident data loading
        incident_df = load_incident_data()
        print(f"✅ Loaded {len(incident_df)} incident records")
        
        # Test Jira data loading  
        jira_df = load_jira_data()
        print(f"✅ Loaded {len(jira_df)} Jira issues")
        
        # Show sample data
        if not incident_df.empty:
            print("\n📋 Sample incident data:")
            print(incident_df[['number', 'incident_state', 'category', 'priority']].head(3))
            
        if not jira_df.empty:
            print("\n🎫 Sample Jira data:")
            print(jira_df[['key', 'summary', 'priority.name', 'status.name']].head(3))
            
        return True
    except Exception as e:
        print(f"❌ Error loading data: {e}")
        return False

def test_agent_imports():
    """Test that we can import the agents"""
    print("\n🤖 Testing agent imports...")
    
    try:
        from opsmind_agents.agent import root_agent, listener_agent, synthesizer_agent, writer_agent
        print("✅ Successfully imported all agents")
        print(f"   - Root agent: {root_agent.name}")
        print(f"   - Listener agent: {listener_agent.name}")
        print(f"   - Synthesizer agent: {synthesizer_agent.name}")
        print(f"   - Writer agent: {writer_agent.name}")
        return True
    except Exception as e:
        print(f"❌ Error importing agents: {e}")
        return False

def test_tool_functions():
    """Test that tool functions work"""
    print("\n🔧 Testing tool functions...")
    
    try:
        from opsmind_agents.agent import get_incident_context, create_incident_summary
        
        # Simple test to verify functions exist and are callable
        print("✅ Tool functions imported successfully")
        print("   - get_incident_context: available")
        print("   - create_incident_summary: available")
        
        return True
    except Exception as e:
        print(f"❌ Error testing tools: {e}")
        return False

def test_output_directory():
    """Test that output directory exists"""
    print("\n📁 Testing output directory...")
    
    output_dir = Path("./output")
    if not output_dir.exists():
        output_dir.mkdir(exist_ok=True)
        print("✅ Created output directory")
    else:
        print("✅ Output directory already exists")
    
    return True

def create_sample_incident():
    """Create a sample incident for testing"""
    return {
        "number": "INC0001234",
        "incident_state": "New",
        "category": "Database",
        "subcategory": "Connection Error",
        "u_symptom": "Unable to connect to production database",
        "priority": "1 - Critical",
        "impact": "1 - High",
        "assignment_group": "Database Team",
        "opened_at": "2024-01-15 10:30:00"
    }

def main():
    """Run all tests"""
    print("🚀 OpsMind MVP Test Suite")
    print("=" * 40)
    
    tests = [
        test_data_loading,
        test_agent_imports,
        test_tool_functions,
        test_output_directory
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} failed with exception: {e}")
            failed += 1
    
    print(f"\n📊 Test Results:")
    print(f"   ✅ Passed: {passed}")
    print(f"   ❌ Failed: {failed}")
    
    if failed == 0:
        print("\n🎉 All tests passed! OpsMind is ready to use.")
        print("\nNext steps:")
        print("1. Configure your .env file with Google Cloud credentials")
        print("2. Run: adk run opsmind_agents")
        print("3. Or run: adk web (for web interface)")
        
        # Show sample incident for testing
        sample = create_sample_incident()
        print(f"\n📋 Sample incident JSON for testing:")
        print(json.dumps(sample, indent=2))
    else:
        print("\n⚠️  Some tests failed. Please check the errors above.")
        
    return failed == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 
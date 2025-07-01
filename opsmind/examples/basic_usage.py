#!/usr/bin/env python3
"""
Basic usage example for OpsMind
"""

import sys
from pathlib import Path

# Add the project root directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

def main():
    """Basic OpsMind usage example"""
    print("🚀 OpsMind Basic Usage Example")
    print("=" * 40)
    
    try:
        # Import the main agent
        from opsmind import root_agent
        
        print(f"✅ Successfully imported OpsMind root agent: {root_agent.name}")
        print(f"📝 Description: {root_agent.description}")
        
        print("\n🔧 Available tools:")
        for tool in root_agent.tools:
            print(f"   - {tool.__name__ if hasattr(tool, '__name__') else str(tool)}")
        
        print("\n💡 Example usage:")
        print("   1. 'Process recent incidents' - Analyze incident data with Jira context")
        print("   2. 'Summarize incident INC0001234' - Create summary using related Jira data")
        print("   3. 'Generate postmortem for INC0001234' - Create comprehensive postmortem")
        print("   4. 'List postmortems' - Show existing postmortem files")
        
        print("\n🎯 To run OpsMind:")
        print("   - Command line: adk run opsmind")
        print("   - Web interface: adk web")
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure you have installed the dependencies:")
        print("   pip install -r requirements.txt")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main() 
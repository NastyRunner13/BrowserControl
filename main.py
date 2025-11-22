import asyncio
import sys
import argparse
from core.planner import AutomationAgent, DynamicAutomationAgent
from utils.logger import setup_logger
from config.settings import settings

logger = setup_logger(__name__)

async def run_interactive_mode(mode: str = "dynamic"):
    """Run the agent in an interactive loop."""
    print("\n" + "="*60)
    print(f"🤖 BROWSER AGENT - INTERACTIVE MODE ({mode.upper()})")
    print("Type 'exit' or 'quit' to stop.")
    print("Type 'switch' to toggle between modes.")
    print("="*60)

    current_mode = mode

    while True:
        try:
            user_input = input(f"\n[{current_mode.upper()}] What would you like to do? \n> ").strip()
            
            if user_input.lower() in ['exit', 'quit', 'q']:
                print("Goodbye! 👋")
                break
            
            if user_input.lower() == 'switch':
                current_mode = "linear" if current_mode == "dynamic" else "dynamic"
                print(f"✓ Switched to {current_mode.upper()} mode")
                continue
            
            if not user_input:
                continue
            
            # Choose agent based on mode
            if current_mode == "dynamic" and settings.ENABLE_DYNAMIC_AGENT:
                agent = DynamicAutomationAgent()
                await agent.run_dynamic(user_input, headless=False)
            else:
                agent = AutomationAgent()
                await agent.run(user_input, headless=False)
            
        except KeyboardInterrupt:
            print("\n\nOperation cancelled by user.")
            break
        except Exception as e:
            logger.error(f"Error in interactive loop: {e}")
            print(f"❌ Error: {e}")

async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Intelligent Browser Automation Agent with Vision & Self-Correction",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py "Go to google.com and search for AI news"
  python main.py --mode=linear "Navigate to example.com"
  python main.py --headless "Search for python tutorials"
        """
    )
    parser.add_argument("task", nargs="?", help="Natural language task to perform")
    parser.add_argument("--headless", action="store_true", help="Run in headless mode (no browser UI)")
    parser.add_argument(
        "--mode", 
        choices=["linear", "dynamic"], 
        default="dynamic" if settings.ENABLE_DYNAMIC_AGENT else "linear",
        help="Execution mode: 'linear' (old, fixed steps) or 'dynamic' (new, adaptive)"
    )
    
    args = parser.parse_args()
    
    # Show banner and feature flags
    print("\n" + "="*60)
    print("🚀 BrowserControl - Enhanced Edition")
    print("="*60)
    print("\n🔧 Active Features:")
    for feature, enabled in settings.get_feature_flags().items():
        status = "✓ Enabled" if enabled else "✗ Disabled"
        print(f"  {feature:25s} {status}")
    print()
    
    if args.task:
        # One-off command mode
        if args.mode == "dynamic" and settings.ENABLE_DYNAMIC_AGENT:
            print(f"🎯 Running in DYNAMIC mode (adaptive planning)")
            agent = DynamicAutomationAgent()
            await agent.run_dynamic(args.task, headless=args.headless)
        else:
            print(f"🎯 Running in LINEAR mode (fixed plan)")
            agent = AutomationAgent()
            await agent.run(args.task, headless=args.headless)
    else:
        # Interactive mode
        await run_interactive_mode(args.mode)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
        sys.exit(0)
import asyncio
import sys
import argparse
from core.planner import AutomationAgent
from utils.logger import setup_logger

logger = setup_logger(__name__)

async def run_interactive_mode():
    """Run the agent in an interactive loop."""
    agent = AutomationAgent()
    print("\n" + "="*60)
    print("🤖 BROWSER AGENT - INTERACTIVE MODE")
    print("Type 'exit' or 'quit' to stop.")
    print("="*60)

    while True:
        try:
            user_input = input("\nWhat would you like to do? \n> ").strip()
            
            if user_input.lower() in ['exit', 'quit', 'q']:
                print("Goodbye! 👋")
                break
            
            if not user_input:
                continue
                
            # Decide if headless based on simple heuristic or arg
            # For interactive mode, seeing the browser is usually better
            await agent.run(user_input, headless=False)
            
        except KeyboardInterrupt:
            print("\nOperation cancelled by user.")
            break
        except Exception as e:
            logger.error(f"Error in interactive loop: {e}")
            print(f"Error: {e}")

async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Intelligent Browser Automation Agent")
    parser.add_argument("task", nargs="?", help="The natural language task to perform")
    parser.add_argument("--headless", action="store_true", help="Run in headless mode (no UI)")
    
    args = parser.parse_args()
    
    if args.task:
        # One-off command mode
        agent = AutomationAgent()
        await agent.run(args.task, headless=args.headless)
    else:
        # Interactive mode
        await run_interactive_mode()

if __name__ == "__main__":
    asyncio.run(main())
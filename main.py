import asyncio
import json
from tools.automation_tools import execute_intelligent_parallel_tasks
from workflows.templates import WorkflowTemplates
from utils.logger import setup_logger

logger = setup_logger(__name__)

async def demo_ecommerce_search():
    """Demo: E-commerce product search."""
    print("\n" + "="*60)
    print("DEMO: E-commerce Product Search")
    print("="*60)
    
    task = WorkflowTemplates.create_ecommerce_search(
        site_url="https://www.amazon.com",
        product_query="wireless headphones",
        site_context="Looking for audio products"
    )
    
    result = await execute_intelligent_parallel_tasks.ainvoke({
        "tasks_json": json.dumps([task.to_dict()]),
        "headless": False
    })
    
    print(result)

async def demo_price_comparison():
    """Demo: Price comparison across multiple sites."""
    print("\n" + "="*60)
    print("DEMO: Price Comparison")
    print("="*60)
    
    tasks = WorkflowTemplates.create_price_comparison(
        product_name="laptop",
        websites=["amazon.com", "bestbuy.com"]
    )
    
    result = await execute_intelligent_parallel_tasks.ainvoke({
        "tasks_json": json.dumps([task.to_dict() for task in tasks]),
        "headless": False
    })
    
    print(result)

async def demo_custom_workflow():
    """Demo: Custom workflow with manual task definition."""
    print("\n" + "="*60)
    print("DEMO: Custom Google Search")
    print("="*60)
    
    custom_task = {
        "task_id": "custom_google_search",
        "name": "Custom Google Search",
        "context": "Testing intelligent element finding on Google",
        "steps": [
            {"action": "navigate", "url": "https://www.google.com"},
            {"action": "wait", "seconds": 2},
            {"action": "intelligent_type", 
             "description": "search box", 
             "text": "browser automation python"},
            {"action": "intelligent_click", 
             "description": "search button"},
            {"action": "wait", "seconds": 3},
            {"action": "screenshot", 
             "filename": "google_search_results.png"}
        ]
    }
    
    result = await execute_intelligent_parallel_tasks.ainvoke({
        "tasks_json": json.dumps([custom_task]),
        "headless": False
    })
    
    print(result)

async def interactive_mode():
    """Interactive mode for custom commands."""
    print("\n" + "="*60)
    print("INTERACTIVE MODE")
    print("="*60)
    print("Available commands:")
    print("  1 - E-commerce Search Demo")
    print("  2 - Price Comparison Demo")
    print("  3 - Custom Google Search")
    print("  q - Quit")
    print("="*60)
    
    while True:
        choice = input("\nEnter command: ").strip().lower()
        
        if choice == 'q':
            break
        elif choice == '1':
            await demo_ecommerce_search()
        elif choice == '2':
            await demo_price_comparison()
        elif choice == '3':
            await demo_custom_workflow()
        else:
            print("Invalid command. Try again.")

async def main():
    """Main entry point."""
    print("="*60)
    print("INTELLIGENT BROWSER AUTOMATION PLATFORM")
    print("="*60)
    
    # Run demos
    try:
        await demo_custom_workflow()
    except KeyboardInterrupt:
        print("\nShutdown requested...")
    except Exception as e:
        logger.error(f"Error in main: {e}")
        print(f"Error: {e}")
    
    print("\nDone!")

if __name__ == "__main__":
    asyncio.run(main())
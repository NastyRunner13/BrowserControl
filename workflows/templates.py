import time
from typing import Dict, List
from models.task import IntelligentParallelTask

class WorkflowTemplates:
    """Pre-built workflow templates for common automation tasks."""
    
    @staticmethod
    def create_ecommerce_search(site_url: str, product_query: str, 
                               site_context: str = "") -> IntelligentParallelTask:
        """Create an e-commerce product search workflow."""
        return IntelligentParallelTask(
            task_id=f"ecommerce_search_{int(time.time())}",
            name=f"Product Search - {site_url}",
            context=f"Searching for '{product_query}' on e-commerce site. {site_context}",
            steps=[
                {"action": "navigate", "url": site_url},
                {"action": "wait", "seconds": 2},
                {"action": "intelligent_type", 
                 "description": "main search box or product search field", 
                 "text": product_query},
                {"action": "intelligent_click", 
                 "description": "search button or magnifying glass icon"},
                {"action": "intelligent_wait", 
                 "condition": "element", 
                 "description": "product results or search results container",
                 "timeout": 15000},
                {"action": "intelligent_extract", 
                 "description": "first three product titles", 
                 "data_type": "text"},
                {"action": "intelligent_extract", 
                 "description": "first three product prices", 
                 "data_type": "text"},
                {"action": "screenshot", 
                 "filename": f"search_results_{site_url.replace('https://', '').replace('.', '_')}.png"}
            ]
        )
    
    @staticmethod
    def create_job_search(job_site_url: str, job_title: str, 
                         location: str) -> IntelligentParallelTask:
        """Create a job search workflow."""
        return IntelligentParallelTask(
            task_id=f"job_search_{int(time.time())}",
            name=f"Job Search - {job_site_url}",
            context=f"Searching for '{job_title}' positions in {location}",
            steps=[
                {"action": "navigate", "url": job_site_url},
                {"action": "wait", "seconds": 3},
                {"action": "intelligent_type", 
                 "description": "job title search field or what field", 
                 "text": job_title},
                {"action": "intelligent_type", 
                 "description": "location search field or where field", 
                 "text": location},
                {"action": "intelligent_click", 
                 "description": "search jobs button or find jobs button"},
                {"action": "intelligent_wait", 
                 "condition": "element", 
                 "description": "job listings or job results",
                 "timeout": 10000},
                {"action": "intelligent_extract", 
                 "description": "first five job titles", 
                 "data_type": "text"},
                {"action": "screenshot", 
                 "filename": f"job_results_{job_site_url.replace('https://', '').replace('.', '_')}.png"}
            ]
        )
    
    @staticmethod
    def create_form_fill(site_url: str, form_data: Dict[str, str]) -> IntelligentParallelTask:
        """Create a form filling workflow."""
        steps = [
            {"action": "navigate", "url": site_url},
            {"action": "wait", "seconds": 2}
        ]
        
        for field_description, value in form_data.items():
            steps.append({
                "action": "intelligent_type",
                "description": field_description,
                "text": value
            })
        
        steps.append({
            "action": "intelligent_click",
            "description": "submit button or send button"
        })
        
        steps.append({
            "action": "screenshot",
            "filename": f"form_submitted_{int(time.time())}.png"
        })
        
        return IntelligentParallelTask(
            task_id=f"form_fill_{int(time.time())}",
            name=f"Form Fill - {site_url}",
            context=f"Filling form on {site_url}",
            steps=steps
        )
    
    @staticmethod
    def create_price_comparison(product_name: str, 
                               websites: List[str]) -> List[IntelligentParallelTask]:
        """Create multiple price comparison tasks."""
        tasks = []
        
        for i, website in enumerate(websites):
            task = IntelligentParallelTask(
                task_id=f"price_comparison_{i}_{int(time.time())}",
                name=f"Price Check - {website}",
                context=f"Price comparison for {product_name} on {website}",
                steps=[
                    {"action": "navigate", "url": f"https://{website}"},
                    {"action": "wait", "seconds": 2},
                    {"action": "intelligent_type", 
                     "description": "main search input field or search box", 
                     "text": product_name},
                    {"action": "intelligent_click", 
                     "description": "search button or submit button"},
                    {"action": "intelligent_wait", 
                     "condition": "element", 
                     "description": "search results or product listings",
                     "timeout": 10000},
                    {"action": "intelligent_extract", 
                     "description": "first product price or main price", 
                     "data_type": "text"},
                    {"action": "intelligent_extract", 
                     "description": "first product title or name", 
                     "data_type": "text"},
                    {"action": "screenshot", 
                     "filename": f"price_{website.replace('.', '_')}_{product_name.replace(' ', '_')}.png"}
                ]
            )
            tasks.append(task)
        
        return tasks
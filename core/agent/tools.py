from typing import Dict, Any, List, Optional
from langchain_core.tools import tool
from core.common.knowledge_service import KnowledgeBaseService
from core.common.specific_question_service import SpecificQuestionService
from core.common.vector_store import DocumentVectorStore


@tool(description="Get all knowledge bases from the system")
def get_all_knowledge_bases() -> List[Dict[str, Any]]:
    """
    Retrieve all knowledge base records from the system.
    
    Returns:
        List of knowledge base records with their details
    """
    try:
        return KnowledgeBaseService.get_all_knowledge_bases()
    except Exception as e:
        return {"error": f"Failed to get knowledge bases: {str(e)}"}


@tool(description="Get current knowledge base URL configuration")
def get_current_knowledge_base_url() -> str:
    """
    Get the currently configured knowledge base URL.
    
    Returns:
        Current knowledge base URL string
    """
    try:
        return KnowledgeBaseService.get_current_knowledge_base_url()
    except Exception as e:
        return {"error": f"Failed to get current knowledge base URL: {str(e)}"}


@tool(description="Get a specific knowledge base by ID")
def get_knowledge_base_by_id(kb_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve a specific knowledge base record by its ID.
    
    Args:
        kb_id: The knowledge base ID
        
    Returns:
        Knowledge base record or None if not found
    """
    try:
        return KnowledgeBaseService.get_knowledge_base_by_id(kb_id)
    except Exception as e:
        return {"error": f"Failed to get knowledge base by ID: {str(e)}"}


@tool(description="Create a new knowledge base by crawling the specified URL")
def create_knowledge_base(seed_url: str) -> Dict[str, Any]:
    """
    Create a new knowledge base by crawling the specified URL.
    
    Args:
        seed_url: The URL to crawl for creating the knowledge base
        
    Returns:
        Result of the creation operation
    """
    try:
        return KnowledgeBaseService.create_knowledge_base(seed_url)
    except Exception as e:
        return {"error": f"Failed to create knowledge base: {str(e)}"}


@tool(description="Update a knowledge base URL with optional rebuild")
def update_knowledge_base(kb_id: str, new_url: str, rebuild: bool = False) -> Dict[str, Any]:
    """
    Update a knowledge base URL with optional rebuild of content.
    
    Args:
        kb_id: The knowledge base ID to update
        new_url: The new URL to set
        rebuild: Whether to rebuild the content by re-crawling (default: False)
        
    Returns:
        Result of the update operation
    """
    try:
        return KnowledgeBaseService.update_knowledge_base(kb_id, new_url, rebuild)
    except Exception as e:
        return {"error": f"Failed to update knowledge base: {str(e)}"}


@tool(description="Delete a knowledge base by ID")
def delete_knowledge_base(kb_id: str) -> Dict[str, Any]:
    """
    Delete a knowledge base by its ID.
    
    Args:
        kb_id: The knowledge base ID to delete
        
    Returns:
        Result of the deletion operation
    """
    try:
        success = KnowledgeBaseService.delete_knowledge_base(kb_id)
        if success:
            return {"message": "Knowledge base deleted successfully"}
        else:
            return {"error": "Failed to delete knowledge base"}
    except Exception as e:
        return {"error": f"Failed to delete knowledge base: {str(e)}"}


@tool(description="Rebuild a specific knowledge base by re-crawling its URL")
def rebuild_knowledge_base(kb_id: str) -> Dict[str, Any]:
    """
    Rebuild a specific knowledge base by re-crawling its URL.
    
    Args:
        kb_id: The knowledge base ID to rebuild
        
    Returns:
        Result of the rebuild operation
    """
    try:
        return KnowledgeBaseService.rebuild_knowledge_base(kb_id)
    except Exception as e:
        return {"error": f"Failed to rebuild knowledge base: {str(e)}"}


@tool(description="Rebuild the current knowledge base by re-crawling the configured URL")
def rebuild_current_knowledge_base() -> Dict[str, Any]:
    """
    Rebuild the current knowledge base by re-crawling the configured URL.
    
    Returns:
        Result of the rebuild operation
    """
    try:
        return KnowledgeBaseService.rebuild_current_knowledge_base()
    except Exception as e:
        return {"error": f"Failed to rebuild current knowledge base: {str(e)}"}


@tool(description="Get all enabled special question flows")
def get_enabled_special_question_flows() -> List[Dict[str, Any]]:
    """
    Retrieve all enabled special question flows from the system.
    
    Returns:
        List of enabled special question flows with key and description
    """
    try:
        return SpecificQuestionService.get_enabled_specific_questions()
    except Exception as e:
        return {"error": f"Failed to get enabled special question flows: {str(e)}"}


@tool(description="Get a specific question flow configuration by key")
def get_specific_question_flow(key: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve a specific question flow configuration by its key.
    
    Args:
        key: The special question flow key
        
    Returns:
        Flow configuration with prompt and flow fields, or None if not found
    """
    try:
        return SpecificQuestionService.get_specific_question_flow(key)
    except Exception as e:
        return {"error": f"Failed to get specific question flow: {str(e)}"}


@tool(description="Format special questions for prompt usage")
def format_special_questions_for_prompt(special_questions: List[Dict[str, Any]]) -> str:
    """
    Format special questions list into a string suitable for prompt usage.
    
    Args:
        special_questions: List of special questions with key and desc fields
        
    Returns:
        Formatted string for prompt usage
    """
    try:
        return SpecificQuestionService.format_specific_questions_for_prompt(special_questions)
    except Exception as e:
        return {"error": f"Failed to format special questions for prompt: {str(e)}"}


@tool(description="Get all special question flows (including disabled ones)")
def get_all_special_question_flows() -> List[Dict[str, Any]]:
    """
    Retrieve all special question flows, including disabled ones.
    
    Returns:
        List of all special question flows with their details
    """
    try:
        data = SpecificQuestionService.get_all_special_question_flows()

        return {"data": data, "count": len(data)}
    except Exception as e:
        return {"error": f"Failed to get all special question flows: {str(e)}"}


@tool(description="Create a new special question flow")
def create_special_question_flow(key: str, desc: str, flow: str, status: str = "active") -> Dict[str, Any]:
    """
    Create a new special question flow.
    
    Args:
        key: Unique identifier for the flow
        desc: Description of the flow
        flow: Flow definition/configuration
        status: Status of the flow (default: "active")
        
    Returns:
        Result of the creation operation
    """
    try:
        success = SpecificQuestionService.create_special_question_flow(key, desc, flow, status)
        if success:
            return {"message": "Special question flow created successfully"}
        else:
            return {"error": "Failed to create special question flow"}
    except Exception as e:
        return {"error": f"Failed to create special question flow: {str(e)}"}


@tool(description="Update an existing special question flow")
def update_special_question_flow(key: str, desc: str, flow: str, status: str = "active") -> Dict[str, Any]:
    """
    Update an existing special question flow.
    
    Args:
        key: Unique identifier for the flow
        desc: Updated description of the flow
        flow: Updated flow definition/configuration
        status: Updated status of the flow (default: "active")
        
    Returns:
        Result of the update operation
    """
    try:
        success = SpecificQuestionService.update_special_question_flow(key, desc, flow, status)
        if success:
            return {"message": "Special question flow updated successfully"}
        else:
            return {"error": "Failed to update special question flow"}
    except Exception as e:
        return {"error": f"Failed to update special question flow: {str(e)}"}


@tool(description="Delete a special question flow by key")
def delete_special_question_flow(key: str) -> Dict[str, Any]:
    """
    Delete a special question flow by its key.
    
    Args:
        key: Unique identifier for the flow to delete
        
    Returns:
        Result of the deletion operation
    """
    try:
        success = SpecificQuestionService.delete_special_question_flow(key)
        if success:
            return {"message": "Special question flow deleted successfully"}
        else:
            return {"error": "Failed to delete special question flow"}
    except Exception as e:
        return {"error": f"Failed to delete special question flow: {str(e)}"}


@tool(description="Navigate to a specified page URL (frontend tool)",extras={"executor": "frontend"},parse_docstring=True)
def navigate_to_page(page_url: str, page_name: str = "") -> Dict[str, Any]:
    """
    Navigate to a specified page URL. This is a frontend tool that returns instructions for the frontend to execute.
    
    Args:
        page_url: The URL to navigate to. Only allowed URLs are:
                  - "/robot" 
                  - "/admin#knowledge-base"
                  - "/admin#special-flows"
                  - "/admin#error_feedback"
        page_name: Optional name/description of the page
    
        
    Returns:
        JSON result with method name and parameters for frontend execution
    """
    return {
        "tool_type": "frontend",
        "tool_name": "navigate_to_page",
        "parameters": {
            "page_url": page_url,
            "page_name": page_name
        }
    }


@tool(description="Refresh the current page or interface (frontend tool)",extras={"executor": "frontend"})
def refresh_page() -> Dict[str, Any]:
    """
    Refresh the current page or interface. This is a frontend tool that returns instructions for the frontend to execute.
    
    Returns:
        JSON result with method name and parameters for frontend execution
    """
    return {
        "tool_type": "frontend",
        "tool_name": "refresh_robot",
        "parameters": {}
    }


@tool(description="Search for information in a specific document collection in the vector store")
def search_document_collection(collection_name: str, query: str, n_results: int = 5) -> List[Dict[str, Any]]:
    """
    Search for information in a specific document collection in the vector store.
    
    Args:
        collection_name: The name of the collection to search in
        query: The search query text
        n_results: Number of results to return (default: 5)
        
    Returns:
        List of search results with content, source, chunk_index, total_chunks, and distance
    """
    try:
        doc_vector_store = DocumentVectorStore()
        results = doc_vector_store.search_in_document_collection(collection_name, query, n_results)
        return results
    except Exception as e:
        return {"error": f"Failed to search document collection: {str(e)}"}

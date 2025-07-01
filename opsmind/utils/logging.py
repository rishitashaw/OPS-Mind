"""
Callback logging for OpsMind ADK agents
"""
import logging

def log_query_to_model(context) -> None:
    """Log the query being sent to the model"""
    logging.info(f"[QUERY TO MODEL] {getattr(context, 'query', 'N/A')}")

def log_model_response(context) -> None:
    """Log the response from the model"""
    logging.info(f"[MODEL RESPONSE] {getattr(context, 'response', 'N/A')}") 
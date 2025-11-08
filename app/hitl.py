from .storage import save_hitl_update
from .models import HITLUpdate

def apply_hitl_update(update: HITLUpdate):
    save_hitl_update(update.doc_id, update.dict())

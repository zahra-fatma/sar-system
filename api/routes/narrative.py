from fastapi import APIRouter, HTTPException
from api.narrative import generate_narrative

router = APIRouter()

@router.post("/cases/{case_id}/generate")
def generate(case_id: int):
    try:
        result = generate_narrative(case_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")
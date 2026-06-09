from fastapi import APIRouter, Request, Response

from app.models.ambience import Ambience, AmbienceRequest

router = APIRouter(prefix="/ambiences", tags=["ambiences"])


@router.post("", status_code=201, response_model=Ambience)
async def create_ambience(
    body: AmbienceRequest,
    request: Request,
    response: Response,
) -> Ambience:
    request.app.state.rate_limiter.check(body.user_id)
    ambience: Ambience = request.app.state.service.create(body)
    response.headers["Location"] = f"/ambiences/{ambience.uuid}"
    return ambience

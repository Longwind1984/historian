"""Private, session-scoped book exploration endpoints."""
from fastapi import APIRouter, HTTPException, Response, status

from ..schemas.exploration import (
    ComposeRequest,
    ComposerMutationResult,
    EpubImportRequest,
    ExplorationMutation,
    ExplorationSnapshot,
    ImportExplorationRequest,
    PromptExplorationRequest,
)
from ..services.exploration_service import (
    ExplorationNotFound,
    InvalidPrivateText,
    RevisionConflict,
    UnknownAnchor,
    UnknownScene,
    exploration_store,
)


router = APIRouter()


def _translate_error(error: Exception) -> HTTPException:
    if isinstance(error, ExplorationNotFound):
        return HTTPException(status_code=404, detail=str(error))
    if isinstance(error, RevisionConflict):
        return HTTPException(
            status_code=409,
            detail={
                "code": "revision_conflict",
                "expected": error.expected,
                "current": error.actual,
            },
        )
    if isinstance(error, (InvalidPrivateText, UnknownAnchor, UnknownScene)):
        return HTTPException(status_code=422, detail=str(error))
    return HTTPException(status_code=500, detail="Unexpected exploration error")


@router.post(
    "/from-prompt",
    response_model=ExplorationSnapshot,
    status_code=status.HTTP_201_CREATED,
)
def create_prompt_exploration(request: PromptExplorationRequest):
    """Create a research scope scaffold without pretending to answer it."""
    try:
        return exploration_store.create_from_prompt(request)
    except InvalidPrivateText as error:
        raise _translate_error(error) from error


@router.post(
    "/import",
    response_model=ExplorationSnapshot,
    status_code=status.HTTP_201_CREATED,
)
def import_private_text(request: ImportExplorationRequest):
    """Parse private TXT/Markdown into session-only paragraph anchors."""
    try:
        return exploration_store.create(request)
    except InvalidPrivateText as error:
        raise _translate_error(error) from error


@router.post(
    "/import-epub",
    response_model=ExplorationSnapshot,
    status_code=status.HTTP_201_CREATED,
)
def import_private_epub(request: EpubImportRequest):
    """Parse an untrusted EPUB into process-only OPF/spine paragraph anchors."""
    try:
        return exploration_store.create_epub(request)
    except InvalidPrivateText as error:
        raise _translate_error(error) from error


@router.get("/{exploration_id}", response_model=ExplorationSnapshot)
def get_exploration(exploration_id: str):
    try:
        return exploration_store.get(exploration_id)
    except ExplorationNotFound as error:
        raise _translate_error(error) from error


@router.post(
    "/{exploration_id}/compose",
    response_model=ComposerMutationResult,
)
def compose_exploration(exploration_id: str, request: ComposeRequest):
    """Record a composer entry or create an explicitly unreviewed Scene proposal."""
    try:
        return exploration_store.compose(exploration_id, request)
    except (
        ExplorationNotFound,
        RevisionConflict,
        UnknownAnchor,
    ) as error:
        raise _translate_error(error) from error


@router.post(
    "/{exploration_id}/mutations",
    response_model=ExplorationSnapshot,
)
def mutate_exploration(
    exploration_id: str,
    mutation: ExplorationMutation,
):
    """Apply optimistic, reversible UI/review state mutations."""
    try:
        return exploration_store.mutate(exploration_id, mutation)
    except (
        ExplorationNotFound,
        InvalidPrivateText,
        RevisionConflict,
        UnknownAnchor,
        UnknownScene,
    ) as error:
        raise _translate_error(error) from error


@router.delete(
    "/{exploration_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
def clear_exploration(exploration_id: str):
    """Explicitly clear the process-local private text and exploration state."""
    try:
        exploration_store.delete(exploration_id)
    except ExplorationNotFound as error:
        raise _translate_error(error) from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)

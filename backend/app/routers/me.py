import io
import secrets
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile
from PIL import Image, ImageOps, UnidentifiedImageError

from app.config import get_settings
from app.deps import DB, CurrentUser
from app.schemas.user import MeOut, MeUpdate
from app.services.people import build_me

router = APIRouter(prefix="/me", tags=["profile"])

AVATAR_SIZE = 512


def _avatars_dir() -> Path:
    path = Path(get_settings().media_dir) / "avatars"
    path.mkdir(parents=True, exist_ok=True)
    return path


@router.get("", response_model=MeOut)
def get_me(user: CurrentUser, db: DB):
    return build_me(db, user)


@router.patch("", response_model=MeOut)
def update_me(data: MeUpdate, user: CurrentUser, db: DB):
    fields = data.model_dump(exclude_unset=True)
    if "name" in fields and fields["name"] is None:
        raise HTTPException(status_code=422, detail="Имя не может быть пустым")
    if fields.get("timezone") is None:
        fields.pop("timezone", None)
    for key, value in fields.items():
        setattr(user, key, value)
    db.commit()
    return build_me(db, user)


@router.post("/avatar", response_model=MeOut)
def upload_avatar(file: UploadFile, user: CurrentUser, db: DB):
    """Принимает картинку, перекодирует в JPEG не больше 512 px: чужие файлы не сохраняем."""
    limit = get_settings().max_avatar_mb * 1024 * 1024
    raw = file.file.read(limit + 1)
    if len(raw) > limit:
        raise HTTPException(status_code=413, detail="Файл слишком большой")
    try:
        image = Image.open(io.BytesIO(raw))
        image.load()
        image = ImageOps.exif_transpose(image)
        image = ImageOps.fit(image.convert("RGB"), (AVATAR_SIZE, AVATAR_SIZE))
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
        raise HTTPException(status_code=400, detail="Не удалось прочитать изображение") from None

    directory = _avatars_dir()
    filename = f"{user.id}-{secrets.token_hex(6)}.jpg"
    image.save(directory / filename, format="JPEG", quality=85)

    if user.avatar_path:
        (directory / user.avatar_path).unlink(missing_ok=True)
    user.avatar_path = filename
    db.commit()
    return build_me(db, user)
